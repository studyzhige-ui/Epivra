"""Minimal OpenAI-compatible chat transport for model role adapters.

The transport only handles protocol, retries, and redaction.  It does not own
role prompts, tool permissions, research state, or stage routing.
"""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

import httpx


# DeepSeek V4 currently exposes a 1M-token context.  Characters are only a
# conservative transport proxy, so this leaves ample room for the configured
# 65K-token output while avoiding needless role-internal batching.  Alternate
# model runtimes can lower the explicit composition setting.
DEFAULT_MAX_PAYLOAD_CHARS = 400_000


class MessageCapacityError(RuntimeError):
    """A model call cannot preserve its fixed and most recent context safely."""


def serialized_messages_chars(messages: Sequence[Mapping[str, Any]]) -> int:
    """Measure exactly the JSON character payload used for message capacity."""

    return len(
        json.dumps(
            [dict(message) for message in messages],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
    )


def serialized_model_request_chars(
    messages: Sequence[Mapping[str, Any]],
    *,
    json_output: bool = False,
    tools: Sequence[ToolSpec] = (),
    tool_choice: Literal["auto", "none", "required"] | None = None,
) -> int:
    """Measure the complete model-facing context envelope in JSON characters."""

    payload: dict[str, Any] = {
        "messages": [dict(message) for message in messages]
    }
    if json_output:
        payload["response_format"] = {"type": "json_object"}
    if tools:
        payload["tools"] = [tool.as_api_value() for tool in tools]
        payload["tool_choice"] = tool_choice or "auto"
    elif tool_choice is not None:
        raise ValueError("tool_choice requires at least one tool")
    return len(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
    )


def compact_tool_loop_messages(
    messages: Sequence[Mapping[str, Any]],
    *,
    max_payload_chars: int = DEFAULT_MAX_PAYLOAD_CHARS,
    inspect_hint: str,
    tools: Sequence[ToolSpec] = (),
    tool_choice: Literal["auto", "none", "required"] | None = None,
) -> list[dict[str, Any]]:
    """Bound a tool loop without summarizing or changing its semantic decisions.

    The system message and initial user context are immutable.  Later history is
    removed only as whole assistant interaction blocks, so tool calls are never
    separated from their observations.  The latest complete block is retained.
    """

    if (
        isinstance(max_payload_chars, bool)
        or not isinstance(max_payload_chars, int)
        or max_payload_chars < 1
    ):
        raise ValueError("max_payload_chars must be a positive integer")
    values = [dict(message) for message in messages]
    if len(values) < 2:
        raise MessageCapacityError(
            "tool-loop context must contain a system message and initial user message"
        )
    fixed = values[:2]
    def request_chars(value: Sequence[Mapping[str, Any]]) -> int:
        return serialized_model_request_chars(
            value, tools=tools, tool_choice=tool_choice
        )

    if request_chars(fixed) > max_payload_chars:
        raise MessageCapacityError(
            "fixed tool-loop context exceeds max_payload_chars; refusing to omit it"
        )
    if request_chars(values) <= max_payload_chars:
        return values

    blocks: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    for message in values[2:]:
        if message.get("role") == "assistant" and current:
            blocks.append(current)
            current = []
        current.append(message)
    if current:
        blocks.append(current)
    if not blocks:
        raise MessageCapacityError(
            "tool-loop context exceeds max_payload_chars without removable history"
        )

    notice = {
        "role": "user",
        "content": (
            "Earlier complete tool interactions were omitted only for context "
            "capacity. Do not infer that their evidence disappeared; use "
            f"{inspect_hint} to retrieve the needed saved state."
        ),
    }
    retained = list(blocks)
    while len(retained) > 1:
        candidate = [*fixed, notice, *[item for block in retained for item in block]]
        if request_chars(candidate) <= max_payload_chars:
            return candidate
        retained.pop(0)
    candidate = [*fixed, notice, *retained[0]]
    if request_chars(candidate) <= max_payload_chars:
        return candidate
    raise MessageCapacityError(
        "fixed tool-loop context plus its most recent complete interaction exceeds "
        "max_payload_chars; refusing unsafe truncation"
    )


class ModelAuthError(RuntimeError):
    pass


class ModelRateLimitError(RuntimeError):
    pass


class ModelUnavailableError(RuntimeError):
    pass


class ModelProtocolError(RuntimeError):
    pass


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
class ModelReply:
    content: str = ""
    tool_calls: tuple[ModelToolCall, ...] = ()
    reasoning_content: str = ""

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
        json_output: bool = False,
        tools: Sequence[ToolSpec] = (),
        tool_choice: Literal["auto", "none", "required"] | None = None,
    ) -> ModelReply: ...


Sleep = Callable[[float], Awaitable[None]]


@dataclass(slots=True)
class DeepSeekChatClient:
    """Current DeepSeek OpenAI-compatible Chat Completions transport."""

    api_key: str = field(repr=False)
    model: str = "deepseek-v4-pro"
    max_output_tokens: int = 65_536
    timeout_seconds: float = 180.0
    transient_retries: int = 2
    client: httpx.AsyncClient | None = field(default=None, repr=False)
    sleep: Sleep = field(default=asyncio.sleep, repr=False)

    def __post_init__(self) -> None:
        if not self.api_key.strip():
            raise ValueError("DeepSeek api_key must not be empty")
        if not self.model.strip():
            raise ValueError("DeepSeek model must not be empty")
        if self.max_output_tokens < 1:
            raise ValueError("max_output_tokens must be positive")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.transient_retries < 0:
            raise ValueError("transient_retries must be non-negative")

    @classmethod
    def from_environment(
        cls,
        *,
        env_var: str = "DEEPSEEK_API_KEY",
        model: str | None = None,
        **kwargs: Any,
    ) -> "DeepSeekChatClient":
        key = os.environ.get(env_var, "").strip()
        if not key:
            raise ValueError(f"environment variable {env_var} is not configured")
        return cls(key, model=model or "deepseek-v4-pro", **kwargs)

    async def complete(
        self,
        messages: Sequence[Mapping[str, Any]],
        *,
        json_output: bool = False,
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
        if json_output:
            payload["response_format"] = {"type": "json_object"}
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
                        "https://api.deepseek.com/chat/completions",
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
                    raise ModelProtocolError(
                        f"model request rejected with HTTP {response.status_code}"
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
        if choice.get("finish_reason") == "length":
            raise ModelProtocolError(
                "model output reached max_output_tokens and was not accepted"
            )
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
        )


__all__ = [
    "ChatModel",
    "DEFAULT_MAX_PAYLOAD_CHARS",
    "DeepSeekChatClient",
    "MessageCapacityError",
    "ModelAuthError",
    "ModelProtocolError",
    "ModelRateLimitError",
    "ModelReply",
    "ModelToolCall",
    "ModelUnavailableError",
    "ToolSpec",
    "compact_tool_loop_messages",
    "serialized_model_request_chars",
    "serialized_messages_chars",
]
