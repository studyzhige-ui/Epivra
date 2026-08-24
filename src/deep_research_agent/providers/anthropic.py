"""Native Anthropic Messages API transport.

Anthropic is the one registered vendor that does not speak the OpenAI protocol,
and the differences are not cosmetic: ``system`` is a top-level parameter rather
than a message, ``max_tokens`` is required, tools declare ``input_schema``
instead of ``parameters``, tool calls come back as ``tool_use`` content blocks
instead of ``tool_calls``, and ``tool_choice`` is an object whose "must call
something" value is ``{"type": "any"}`` -- not the string ``"required"``.
Pointing an OpenAI client at this endpoint yields 404s and 400s, so it gets its
own transport rather than a shim.

Two further constraints are enforced here because they are 400s rather than
degraded output, and both mirror failures this project has already hit live:

* Current Claude models **reject** ``temperature``, ``top_p``, and ``top_k``.
  This module never sends them.
* A ``tool_use`` block must be answered by a ``tool_result`` carrying the same
  ``tool_use_id``.  The agent runner's correction turn is plain text, so it is
  translated into an error tool result -- which is what it actually is.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

import httpx

from ..model import (
    STREAMING_THRESHOLD_TOKENS,
    ModelAuthError,
    ModelContextOverflow,
    ModelOutputTruncated,
    ModelProtocolError,
    ModelRateLimitError,
    ModelReply,
    ModelRequestRejected,
    ModelToolCall,
    ModelUnavailableError,
    TokenUsage,
    ToolSpec,
    context_overflow_problem,
    truncation_problem,
)

#: Required on every request; the API rejects calls without it.
ANTHROPIC_VERSION = "2023-06-01"

_TOOL_CHOICE: Mapping[str, Mapping[str, str]] = {
    # OpenAI's "required" is Anthropic's "any"; sending "required" is a 400.
    "auto": {"type": "auto"},
    "required": {"type": "any"},
    "none": {"type": "none"},
}


def _tool_payload(tool: ToolSpec) -> dict[str, Any]:
    """Translate a neutral ToolSpec into Anthropic's tool shape."""

    return {
        "name": tool.name,
        "description": tool.description,
        "input_schema": dict(tool.parameters),
    }


def _split_system(
    messages: Sequence[Mapping[str, Any]],
) -> tuple[str, list[Mapping[str, Any]]]:
    """Lift system turns out of the message list into the top-level parameter."""

    system_parts: list[str] = []
    conversation: list[Mapping[str, Any]] = []
    for message in messages:
        if message.get("role") == "system":
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                system_parts.append(content)
            continue
        conversation.append(message)
    return "\n\n".join(system_parts), conversation


def _assistant_content(message: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Rebuild an assistant turn, including any tool calls, as content blocks."""

    blocks: list[dict[str, Any]] = []
    text = message.get("content")
    if isinstance(text, str) and text.strip():
        blocks.append({"type": "text", "text": text})
    for call in message.get("tool_calls", ()) or ():
        function = call.get("function", {})
        try:
            arguments = json.loads(function.get("arguments") or "{}")
        except json.JSONDecodeError:
            arguments = {}
        blocks.append(
            {
                "type": "tool_use",
                "id": call.get("id", ""),
                "name": function.get("name", ""),
                "input": arguments,
            }
        )
    return blocks


def translate_messages(
    messages: Sequence[Mapping[str, Any]],
) -> tuple[str, list[dict[str, Any]]]:
    """Translate neutral messages into ``(system, messages)`` for this API.

    A plain user turn that follows tool calls is emitted as an error
    ``tool_result`` for each open ``tool_use``.  The runner only sends such a
    turn to correct an invalid action, so representing it as a failed tool
    result is both what the API requires and what the turn means.
    """

    system, conversation = _split_system(messages)
    translated: list[dict[str, Any]] = []
    pending_tool_ids: list[str] = []

    for message in conversation:
        role = message.get("role")
        if role == "assistant":
            blocks = _assistant_content(message)
            pending_tool_ids = [
                str(block["id"]) for block in blocks if block["type"] == "tool_use"
            ]
            translated.append({"role": "assistant", "content": blocks})
            continue

        content = message.get("content")
        text = content if isinstance(content, str) else json.dumps(content)

        if role == "tool":
            # A tool turn already names the call it answers, so it maps
            # one-to-one onto a tool_result block.
            tool_id = str(message.get("tool_call_id", ""))
            pending_tool_ids = [
                item for item in pending_tool_ids if item != tool_id
            ]
            translated.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": text,
                            "is_error": True,
                        }
                    ],
                }
            )
            continue

        if pending_tool_ids:
            translated.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": text,
                            "is_error": True,
                        }
                        for tool_id in pending_tool_ids
                    ],
                }
            )
            pending_tool_ids = []
            continue
        translated.append({"role": "user", "content": text})

    return system, translated


def parse_reply(payload: Mapping[str, Any]) -> ModelReply:
    """Turn a Messages API response into the runtime's neutral reply.

    ``stop_reason`` is inspected before the content, because two of its values
    mean the content must not be used at all.  A refusal arrives as a successful
    HTTP 200, and so does a truncation -- this transport used to check only the
    first, so a report cut off at the output ceiling came back looking like a
    finished one.
    """

    stop = str(payload.get("stop_reason") or "")
    if stop == "refusal":
        raise ModelRequestRejected(
            "anthropic declined the request (stop_reason=refusal)"
        )
    truncated = truncation_problem(stop)
    if truncated:
        raise ModelOutputTruncated(truncated)

    blocks = payload.get("content", ())
    if not isinstance(blocks, list):
        raise ModelProtocolError("anthropic response has no content list")

    texts: list[str] = []
    calls: list[ModelToolCall] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        kind = block.get("type")
        if kind == "text":
            texts.append(str(block.get("text", "")))
        elif kind == "tool_use":
            calls.append(
                ModelToolCall(
                    call_id=str(block.get("id", "")),
                    name=str(block.get("name", "")),
                    arguments=json.dumps(
                        block.get("input", {}), ensure_ascii=False
                    ),
                )
            )
    return ModelReply(
        content="\n".join(texts),
        tool_calls=tuple(calls),
        usage=TokenUsage.from_payload(payload.get("usage")),
    )


def _assemble_stream(lines: Sequence[str]) -> dict[str, Any]:
    """Rebuild a whole Messages response from its server-sent event lines.

    The result is the same object shape a non-streaming POST returns, so exactly
    one parser interprets stop reasons, content blocks and usage.  Two transports
    already disagreed once about what a stop reason meant; a second parser here
    would be the same mistake in a new place.
    """

    message: dict[str, Any] = {"content": [], "stop_reason": "", "usage": {}}
    blocks: list[dict[str, Any]] = []
    partials: dict[int, list[str]] = {}

    for line in lines:
        if not line.startswith("data:"):
            continue
        raw = line[len("data:") :].strip()
        if not raw or raw == "[DONE]":
            continue
        try:
            event = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ModelProtocolError("anthropic stream sent invalid JSON") from exc
        if not isinstance(event, dict):
            continue
        kind = event.get("type")

        if kind == "message_start":
            start = event.get("message")
            if isinstance(start, dict):
                message["stop_reason"] = start.get("stop_reason") or ""
                usage = start.get("usage")
                if isinstance(usage, dict):
                    message["usage"] = dict(usage)
        elif kind == "content_block_start":
            block = event.get("content_block")
            index = event.get("index")
            if isinstance(block, dict) and isinstance(index, int):
                while len(blocks) <= index:
                    blocks.append({})
                blocks[index] = dict(block)
                partials.setdefault(index, [])
        elif kind == "content_block_delta":
            delta = event.get("delta")
            index = event.get("index")
            if not isinstance(delta, dict) or not isinstance(index, int):
                continue
            partials.setdefault(index, [])
            # Text arrives as text_delta; a tool call's arguments arrive as
            # input_json_delta, one JSON fragment at a time.
            for key in ("text", "partial_json"):
                piece = delta.get(key)
                if isinstance(piece, str):
                    partials[index].append(piece)
        elif kind == "message_delta":
            delta = event.get("delta")
            if isinstance(delta, dict) and delta.get("stop_reason"):
                message["stop_reason"] = delta["stop_reason"]
            usage = event.get("usage")
            if isinstance(usage, dict):
                message["usage"] = {**message["usage"], **usage}
        elif kind == "error":
            detail = event.get("error")
            reason = ""
            if isinstance(detail, dict):
                reason = str(detail.get("message", ""))
            raise ModelUnavailableError(
                f"anthropic stream ended with an error: {reason or 'no reason given'}"
            )

    for index, block in enumerate(blocks):
        joined = "".join(partials.get(index, ()))
        if block.get("type") == "text":
            message["content"].append({"type": "text", "text": joined or block.get("text", "")})
        elif block.get("type") == "tool_use":
            try:
                arguments = json.loads(joined) if joined.strip() else {}
            except json.JSONDecodeError as exc:
                raise ModelProtocolError(
                    "anthropic stream sent an unparseable tool call"
                ) from exc
            message["content"].append({**block, "input": arguments})
    return message


@dataclass(slots=True)
class AnthropicClient:
    """ChatModel over the native Messages API."""

    api_key: str = field(repr=False)
    model: str = "claude-opus-5"
    api_base: str = "https://api.anthropic.com"
    #: Kept at a value that is safe to send without streaming, because a direct
    #: construction should never be a trap.  The composition root raises it and
    #: turns ``stream`` on together -- the two belong to one decision.
    max_output_tokens: int = 16_000
    timeout_seconds: float = 600.0
    client: httpx.AsyncClient | None = field(default=None, repr=False)
    #: How much thinking to spend.  Sent as ``output_config.effort``; the fixed
    #: thinking-budget parameter it replaced is rejected outright by current
    #: models, so it must never be reintroduced here.
    effort: str = "high"
    #: Whether to stream.  A large non-streaming completion holds one connection
    #: for minutes and eventually trips the read timeout -- and a timeout is an
    #: *unknown* outcome, so §8.2 can only freeze it.  Streaming is what keeps a
    #: long report from becoming an operation a human has to adjudicate.
    stream: bool = False
    #: Cache the stable prefix (tools, then system) so the parts that are
    #: byte-identical across every call of one role are not re-charged in full.
    #: Billing only -- it changes nothing the model sees, which is why it stays
    #: out of the operation fingerprint.
    cache_prompt: bool = True

    def __post_init__(self) -> None:
        if not self.api_key.strip():
            raise ValueError("api_key must not be empty")
        if not self.model.strip():
            raise ValueError("model must not be empty")
        if not self.api_base.startswith("https://"):
            raise ValueError("api_base must be an HTTPS origin")
        if self.max_output_tokens < 1:
            raise ValueError("max_output_tokens must be positive")
        if self.max_output_tokens > STREAMING_THRESHOLD_TOKENS and not self.stream:
            # Refused rather than silently downgraded: the failure it produces is
            # a timeout, which the ledger can only read as an unknown outcome.
            raise ValueError(
                f"max_output_tokens={self.max_output_tokens} requires stream=True; "
                f"a non-streaming request above {STREAMING_THRESHOLD_TOKENS} tokens "
                "trips the read timeout, which freezes the operation"
            )

    def _payload(
        self,
        messages: Sequence[Mapping[str, Any]],
        tools: Sequence[ToolSpec],
        tool_choice: Literal["auto", "none", "required"] | None,
    ) -> dict[str, Any]:
        system, conversation = translate_messages(messages)
        payload: dict[str, Any] = {
            "model": self.model,
            # Required by this API; omitting it is a 400.
            "max_tokens": self.max_output_tokens,
            "messages": conversation,
            # Adaptive thinking is the only supported on-mode on current models,
            # and effort is what controls its depth.  A fixed token budget is
            # rejected with a 400, so it is deliberately absent.
            "output_config": {"effort": self.effort},
        }
        if system:
            block: dict[str, Any] = {"type": "text", "text": system}
            if self.cache_prompt:
                block["cache_control"] = {"type": "ephemeral"}
            payload["system"] = [block]
        if tools:
            payload["tools"] = [_tool_payload(tool) for tool in tools]
            if tool_choice is not None:
                payload["tool_choice"] = _TOOL_CHOICE[tool_choice]
        # temperature / top_p / top_k are deliberately never sent: current Claude
        # models reject them outright rather than ignoring them.
        return payload

    async def complete(
        self,
        messages: Sequence[Mapping[str, Any]],
        *,
        tools: Sequence[ToolSpec] = (),
        tool_choice: Literal["auto", "none", "required"] | None = None,
    ) -> ModelReply:
        if not messages:
            raise ValueError("messages must not be empty")

        payload = self._payload(messages, tools, tool_choice)
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }

        owns_client = self.client is None
        transport = self.client or httpx.AsyncClient(timeout=self.timeout_seconds)
        url = f"{self.api_base.rstrip('/')}/v1/messages"
        try:
            if self.stream:
                return await self._stream_reply(transport, url, headers, payload)
            try:
                response = await transport.post(url, headers=headers, json=payload)
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                raise ModelUnavailableError("anthropic request unavailable") from exc
        finally:
            if owns_client:
                await transport.aclose()

        _raise_for_status(response.status_code, _error_reason(response))
        try:
            body = response.json()
        except ValueError as exc:
            raise ModelProtocolError("anthropic returned invalid JSON") from exc
        if not isinstance(body, dict):
            raise ModelProtocolError("anthropic response is not an object")
        # Refusal and truncation are both successful HTTP 200s whose content must
        # not be used; parse_reply checks stop_reason before reading it.
        return parse_reply(body)

    async def _stream_reply(
        self,
        transport: httpx.AsyncClient,
        url: str,
        headers: Mapping[str, str],
        payload: Mapping[str, Any],
    ) -> ModelReply:
        """Accumulate a streamed response into the same reply a POST would give.

        Streaming is a transport concern only.  The assembled message goes through
        :func:`parse_reply` exactly as the non-streaming body does, so the ledger,
        replay, and every stop-reason check stay in one place.
        """

        body = {**payload, "stream": True}
        try:
            async with transport.stream(
                "POST", url, headers=dict(headers), json=body
            ) as response:
                if response.status_code >= 400:
                    await response.aread()
                    _raise_for_status(response.status_code, _error_reason(response))
                return parse_reply(
                    _assemble_stream(
                        [line async for line in response.aiter_lines()]
                    )
                )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise ModelUnavailableError("anthropic stream unavailable") from exc


def _error_reason(response: httpx.Response) -> str:
    """The vendor's own explanation, without echoing the payload it refused."""

    try:
        detail = response.json().get("error", {})
    except ValueError:
        return ""
    return str(detail.get("message", ""))[:200] if isinstance(detail, dict) else ""


def _raise_for_status(status_code: int, reason: str = "") -> None:
    """Map HTTP status onto the runtime's billing-relevant failure vocabulary."""

    if status_code < 400:
        return
    message = f"anthropic request failed with HTTP {status_code}"
    if status_code in {401, 403}:
        raise ModelAuthError(message)
    if status_code == 429:
        raise ModelRateLimitError(message)
    if status_code >= 500:
        raise ModelUnavailableError(message)
    # A too-large request and a malformed one are both 400, so the vendor's own
    # text is what tells them apart.  Left unrecognised, an overflow would be
    # retried as "provably not executed" until the budget ran out.
    overflow = context_overflow_problem(reason)
    if overflow:
        raise ModelContextOverflow(overflow)
    # A 4xx here means the request was refused before any generation ran, so it
    # is provably unbilled and the ledger may retry it on the same key.
    raise ModelRequestRejected(message)


__all__ = [
    "ANTHROPIC_VERSION",
    "AnthropicClient",
    "parse_reply",
    "translate_messages",
]
