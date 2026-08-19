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
    ModelAuthError,
    ModelProtocolError,
    ModelRateLimitError,
    ModelReply,
    ModelRequestRejected,
    ModelToolCall,
    ModelUnavailableError,
    TokenUsage,
    ToolSpec,
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
    """Turn a Messages API response into the runtime's neutral reply."""

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


@dataclass(slots=True)
class AnthropicClient:
    """ChatModel over the native Messages API."""

    api_key: str = field(repr=False)
    model: str = "claude-opus-5"
    api_base: str = "https://api.anthropic.com"
    max_output_tokens: int = 16_000
    timeout_seconds: float = 180.0
    client: httpx.AsyncClient | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not self.api_key.strip():
            raise ValueError("api_key must not be empty")
        if not self.model.strip():
            raise ValueError("model must not be empty")
        if not self.api_base.startswith("https://"):
            raise ValueError("api_base must be an HTTPS origin")
        if self.max_output_tokens < 1:
            raise ValueError("max_output_tokens must be positive")

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

        system, conversation = translate_messages(messages)
        payload: dict[str, Any] = {
            "model": self.model,
            # Required by this API; omitting it is a 400.
            "max_tokens": self.max_output_tokens,
            "messages": conversation,
        }
        if system:
            payload["system"] = system
        if tools:
            payload["tools"] = [_tool_payload(tool) for tool in tools]
            if tool_choice is not None:
                payload["tool_choice"] = _TOOL_CHOICE[tool_choice]
        # temperature / top_p / top_k are deliberately never sent: current Claude
        # models reject them outright rather than ignoring them.

        owns_client = self.client is None
        transport = self.client or httpx.AsyncClient(timeout=self.timeout_seconds)
        try:
            try:
                response = await transport.post(
                    f"{self.api_base.rstrip('/')}/v1/messages",
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": ANTHROPIC_VERSION,
                        "content-type": "application/json",
                    },
                    json=payload,
                )
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                raise ModelUnavailableError("anthropic request unavailable") from exc
        finally:
            if owns_client:
                await transport.aclose()

        _raise_for_status(response.status_code)
        try:
            body = response.json()
        except ValueError as exc:
            raise ModelProtocolError("anthropic returned invalid JSON") from exc
        if not isinstance(body, dict):
            raise ModelProtocolError("anthropic response is not an object")

        # A refusal is a successful HTTP 200 with an empty or partial content
        # list, so it must be checked before the content is read.
        if body.get("stop_reason") == "refusal":
            raise ModelRequestRejected(
                "anthropic declined the request (stop_reason=refusal)"
            )
        return parse_reply(body)


def _raise_for_status(status_code: int) -> None:
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
    # A 4xx here means the request was refused before any generation ran, so it
    # is provably unbilled and the ledger may retry it on the same key.
    raise ModelRequestRejected(message)


__all__ = [
    "ANTHROPIC_VERSION",
    "AnthropicClient",
    "parse_reply",
    "translate_messages",
]
