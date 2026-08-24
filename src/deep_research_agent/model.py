"""Minimal OpenAI-compatible chat transport for model role adapters.

The transport only handles protocol, retries, and redaction.  It does not own
role prompts, tool permissions, research state, or stage routing.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

import httpx


class ModelAuthError(RuntimeError):
    """The credential was refused, so the request never ran and nothing was billed."""


class ModelRateLimitError(RuntimeError):
    """The provider throttled the request before running it; nothing was billed."""


class ModelUnavailableError(RuntimeError):
    """No usable response arrived, and whether the request ran is unknowable.

    Deliberately *not* treated as "definitely not executed", unlike the two above:
    a read timeout may mean the provider did the work and the answer was lost on
    the way back.  Retrying on the same operation key could pay twice, so the
    ledger freezes it for reconciliation instead.
    """


class ModelProtocolError(RuntimeError):
    """A reply arrived but its shape cannot be trusted; the call was billed."""


class ModelOutputTruncated(RuntimeError):
    """The reply is complete as far as it goes and stops mid-thought.

    Its own category because it is the one model failure whose cause is a
    *setting* rather than the request: the output ceiling was too low for what
    the role was asked to produce.  That makes it decided (the provider told us
    plainly), billed, and fixable only by raising the ceiling -- so it must never
    reach reconciliation, which exists for outcomes nobody can determine.

    Truncated text must never be accepted as a finished product.  One transport
    used to return it as an ordinary reply, so a report cut off halfway had
    nothing left to stop it: it passed the Author's validator, became a report
    artifact, went through review, and could publish.  A report missing its
    limitations section is exactly the over-confident document this architecture
    exists to prevent.
    """


class ModelRequestRejected(RuntimeError):
    """The provider refused the request before running it, so nothing was billed.

    Kept distinct from :class:`ModelProtocolError` because the two have opposite
    billing consequences: a rejected request may be safely retried on the same
    operation key, while a malformed reply means the provider already charged for
    work whose outcome is now in doubt.
    """


#: Every way a model call can fail.  Declared beside the classes so a caller that
#: has to handle "the model did not answer" cannot list four of the five: the
#: whole point of splitting them was that each says something different about
#: billing, and a set assembled from memory somewhere else would drift.
MODEL_FAILURES: tuple[type[Exception], ...] = (
    ModelAuthError,
    ModelOutputTruncated,
    ModelProtocolError,
    ModelRateLimitError,
    ModelRequestRejected,
    ModelUnavailableError,
)

#: Output ceiling above which a request must stream.  A non-streaming call this
#: large sits on one HTTP connection for minutes and eventually trips the read
#: timeout -- and a timeout is an *unknown* outcome, so §8.2 can only freeze it
#: for reconciliation.  That turns a report the model was writing correctly into
#: an operation a human has to adjudicate, which is why the threshold exists
#: rather than being left to each vendor's defaults.
STREAMING_THRESHOLD_TOKENS = 16_000


def truncation_problem(stop: str) -> str:
    """Describe a stop signal that means "the output was cut off", or "".

    One definition, two transports.  The OpenAI protocol says ``length`` and the
    Messages API says ``max_tokens`` for the same event, and only one of them was
    ever checked -- so the same truncation raised on one vendor and published
    silently on the other.  Naming both here is what keeps the two paths from
    disagreeing again.
    """

    if stop in ("length", "max_tokens"):
        return (
            "模型输出撞到 max_tokens 上限，回复不完整。这是执行配置问题，不是研究结论："
            "请提高该角色的输出上限后重跑（提高上限会产生一次新的调用，不需要对账）。"
        )
    return ""


def _redacted_error(response: "httpx.Response") -> str:
    """Surface the provider's reason without echoing payloads or credentials."""

    try:
        message = response.json().get("error", {}).get("message", "")
    except ValueError:
        return "no machine-readable reason"
    return str(message)[:200] or "no machine-readable reason"


@dataclass(frozen=True, slots=True)
class ToolSpec:
    name: str
    description: str
    parameters: Mapping[str, Any]

    def as_api_value(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": dict(self.parameters),
            },
        }


@dataclass(frozen=True, slots=True)
class ModelToolCall:
    call_id: str
    name: str
    arguments: str

    def parsed_arguments(self) -> dict[str, Any]:
        try:
            value = json.loads(self.arguments)
        except json.JSONDecodeError as exc:
            raise ModelProtocolError(
                f"tool {self.name!r} returned invalid JSON arguments"
            ) from exc
        if not isinstance(value, dict):
            raise ModelProtocolError(
                f"tool {self.name!r} arguments must be a JSON object"
            )
        return value


@dataclass(frozen=True, slots=True)
class TokenUsage:
    """What one provider call actually consumed.

    Recorded because a research system that cannot say what it spent cannot be
    held to a resource budget, and Phase 1e showed the resource axis is invisible
    inside any single run -- the hundredfold spread in yield per search only
    appeared across runs.  ``cached_input_tokens`` is reported separately by
    several vendors and is billed differently, so it is kept rather than folded
    into the input total.
    """

    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0

    def __post_init__(self) -> None:
        for name in ("input_tokens", "output_tokens", "cached_input_tokens"):
            value = getattr(self, name)
            if not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any] | None) -> TokenUsage | None:
        """Read a usage block, tolerating vendors that omit or rename fields.

        Absent usage returns ``None`` rather than a zeroed record: "the provider
        did not tell us" and "this call cost nothing" must not look the same in
        the ledger, or a spend report would silently under-count.
        """

        if not isinstance(payload, Mapping):
            return None

        def count(*names: str) -> int:
            for name in names:
                value = payload.get(name)
                if isinstance(value, bool):
                    continue
                if isinstance(value, int) and value >= 0:
                    return value
            return 0

        details = payload.get("prompt_tokens_details")
        cached = 0
        if isinstance(details, Mapping):
            raw = details.get("cached_tokens")
            cached = raw if isinstance(raw, int) and raw >= 0 else 0
        cached = cached or count("cache_read_input_tokens", "prompt_cache_hit_tokens")

        usage = cls(
            input_tokens=count("prompt_tokens", "input_tokens"),
            output_tokens=count("completion_tokens", "output_tokens"),
            cached_input_tokens=cached,
        )
        if usage.total_tokens == 0 and usage.cached_input_tokens == 0:
            return None
        return usage


@dataclass(frozen=True, slots=True)
class ModelReply:
    content: str = ""
    tool_calls: tuple[ModelToolCall, ...] = ()
    reasoning_content: str = ""
    usage: TokenUsage | None = None

    def assistant_message(self) -> dict[str, Any]:
        value: dict[str, Any] = {"role": "assistant", "content": self.content or None}
        if self.reasoning_content:
            value["reasoning_content"] = self.reasoning_content
        if self.tool_calls:
            value["tool_calls"] = [
                {
                    "id": item.call_id,
                    "type": "function",
                    "function": {
                        "name": item.name,
                        "arguments": item.arguments,
                    },
                }
                for item in self.tool_calls
            ]
        return value


class ChatModel(Protocol):
    async def complete(
        self,
        messages: Sequence[Mapping[str, Any]],
        *,
        tools: Sequence[ToolSpec] = (),
        tool_choice: Literal["auto", "none", "required"] | None = None,
    ) -> ModelReply: ...


Sleep = Callable[[float], Awaitable[None]]


@dataclass(slots=True)
class OpenAICompatibleClient:
    """Chat Completions transport for any OpenAI-compatible vendor.

    One transport serves every vendor in the registry because they all speak
    this protocol; the vendor is data (``api_base``), not a subclass.
    """

    api_key: str = field(repr=False)
    model: str = "deepseek-v4-pro"
    api_base: str = "https://api.deepseek.com"
    max_output_tokens: int = 65_536
    timeout_seconds: float = 180.0
    transient_retries: int = 2
    client: httpx.AsyncClient | None = field(default=None, repr=False)
    sleep: Sleep = field(default=asyncio.sleep, repr=False)

    def __post_init__(self) -> None:
        if not self.api_key.strip():
            raise ValueError("api_key must not be empty")
        if not self.model.strip():
            raise ValueError("model must not be empty")
        if not self.api_base.startswith("https://"):
            raise ValueError("api_base must be an HTTPS origin")
        if self.max_output_tokens < 1:
            raise ValueError("max_output_tokens must be positive")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.transient_retries < 0:
            raise ValueError("transient_retries must be non-negative")

    async def complete(
        self,
        messages: Sequence[Mapping[str, Any]],
        *,
        tools: Sequence[ToolSpec] = (),
        tool_choice: Literal["auto", "none", "required"] | None = None,
    ) -> ModelReply:
        if not messages:
            raise ValueError("messages must not be empty")
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [dict(message) for message in messages],
            "max_tokens": self.max_output_tokens,
            "stream": False,
        }
        if tools:
            payload["tools"] = [item.as_api_value() for item in tools]
            payload["tool_choice"] = tool_choice or "auto"
        elif tool_choice is not None:
            raise ValueError("tool_choice requires at least one tool")

        owns_client = self.client is None
        client = self.client or httpx.AsyncClient(timeout=self.timeout_seconds)
        try:
            for attempt in range(self.transient_retries + 1):
                try:
                    response = await client.post(
                        f"{self.api_base.rstrip('/')}/chat/completions",
                        json=payload,
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                    )
                except (httpx.TimeoutException, httpx.NetworkError) as exc:
                    if attempt >= self.transient_retries:
                        raise ModelUnavailableError("model request unavailable") from exc
                    await self.sleep(min(2**attempt, 8))
                    continue
                if response.status_code in {401, 403}:
                    raise ModelAuthError(
                        f"model authentication failed with HTTP {response.status_code}"
                    )
                if response.status_code == 429:
                    if attempt >= self.transient_retries:
                        raise ModelRateLimitError("model rate limit retry exhausted")
                    await self.sleep(min(2**attempt, 8))
                    continue
                if response.status_code >= 500:
                    if attempt >= self.transient_retries:
                        raise ModelUnavailableError(
                            f"model unavailable with HTTP {response.status_code}"
                        )
                    await self.sleep(min(2**attempt, 8))
                    continue
                if response.status_code >= 400:
                    raise ModelRequestRejected(
                        f"model request rejected with HTTP {response.status_code}: "
                        f"{_redacted_error(response)}"
                    )
                return self._parse_response(response)
            raise AssertionError("unreachable retry state")
        finally:
            if owns_client:
                await client.aclose()

    @staticmethod
    def _parse_response(response: httpx.Response) -> ModelReply:
        try:
            data = response.json()
            choice = data["choices"][0]
            message = choice["message"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise ModelProtocolError("model response has an invalid shape") from exc
        truncated = truncation_problem(str(choice.get("finish_reason") or ""))
        if truncated:
            raise ModelOutputTruncated(truncated)
        calls: list[ModelToolCall] = []
        for item in message.get("tool_calls") or ():
            try:
                calls.append(
                    ModelToolCall(
                        call_id=str(item["id"]),
                        name=str(item["function"]["name"]),
                        arguments=str(item["function"]["arguments"]),
                    )
                )
            except (KeyError, TypeError) as exc:
                raise ModelProtocolError("model tool call has an invalid shape") from exc
        content = message.get("content") or ""
        if not isinstance(content, str):
            raise ModelProtocolError("model message content must be text or null")
        if not content and not calls:
            raise ModelProtocolError("model returned neither content nor tool calls")
        return ModelReply(
            content=content,
            tool_calls=tuple(calls),
            reasoning_content=str(message.get("reasoning_content") or ""),
            usage=TokenUsage.from_payload(data.get("usage")),
        )


__all__ = [
    "MODEL_FAILURES",
    "STREAMING_THRESHOLD_TOKENS",
    "ChatModel",
    "OpenAICompatibleClient",
    "ModelAuthError",
    "ModelOutputTruncated",
    "ModelProtocolError",
    "ModelRequestRejected",
    "ModelRateLimitError",
    "ModelReply",
    "ModelToolCall",
    "ModelUnavailableError",
    "TokenUsage",
    "ToolSpec",
    "truncation_problem",
]
