"""Explicit DeepSeek and Tavily protocols. No Agent loop or hidden retries."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any

import httpx

from .domain import encode, identity

DEFAULT_MODEL = "deepseek-flash"


class ProviderFailure(RuntimeError):
    def __init__(self, provider: str, status: int):
        self.provider, self.status = provider, status
        super().__init__(f"{provider}: HTTP {status}")


class IncompleteStream(RuntimeError):
    """The provider may have charged; no executable response was received."""


def rate_limit_delay(raw: dict, attempt: int) -> float | None:
    """Only an explicit rejection permits an automatic new attempt."""
    if raw.get("http_status") == 429 and raw.get("error_kind") != "quota":
        return max(float(2 ** min(attempt + 1, 6)), raw.get("retry_after", 0))
    return None


class _ChatStream:
    def __init__(self):
        self.message = {"role": "assistant", "content": ""}
        self.calls = {}
        self.finish = None
        self.usage = None

    def add(self, chunk):
        if not isinstance(chunk, dict) or "error" in chunk:
            raise ValueError("invalid stream chunk")
        choices = chunk["choices"]
        if choices == [] and isinstance(chunk.get("usage"), dict):
            self.usage = chunk["usage"]
            return
        if not isinstance(choices, list) or len(choices) != 1:
            raise ValueError("expected one streamed choice")
        choice = choices[0]
        if choice["index"] != 0 or self.finish is not None:
            raise ValueError("unexpected streamed choice")
        delta = choice["delta"]
        if not isinstance(delta, dict) or delta.get("role", "assistant") != "assistant":
            raise ValueError("invalid stream delta")
        for field in ("content", "reasoning_content"):
            part = delta.get(field)
            if part is not None:
                if not isinstance(part, str):
                    raise ValueError("invalid text delta")
                self.message[field] = self.message.get(field, "") + part
        for part in delta.get("tool_calls") or []:
            index = part["index"]
            if type(index) is not int or index < 0:
                raise ValueError("invalid tool index")
            call = self.calls.setdefault(
                index, {"type": "function", "function": {"name": "", "arguments": ""}}
            )
            if part.get("type", "function") != "function":
                raise ValueError("unsupported tool type")
            if part.get("id") is not None:
                if "id" in call and call["id"] != part["id"]:
                    raise ValueError("tool ID changed during stream")
                call["id"] = part["id"]
            for field in ("name", "arguments"):
                value = part.get("function", {}).get(field)
                if value is not None:
                    if not isinstance(value, str):
                        raise ValueError("invalid function delta")
                    call["function"][field] += value
        self.finish = choice.get("finish_reason")
        if self.finish is not None and not isinstance(self.finish, str):
            raise ValueError("invalid finish reason")
        if chunk.get("usage") is not None:
            if not isinstance(chunk["usage"], dict):
                raise ValueError("invalid usage")
            self.usage = chunk["usage"]

    def result(self):
        if self.finish is None:
            raise ValueError("stream has no finish reason")
        if self.calls:
            if sorted(self.calls) != list(range(len(self.calls))):
                raise ValueError("missing tool index")
            self.message["tool_calls"] = [self.calls[i] for i in sorted(self.calls)]
        data = {"choices": [{"message": self.message, "finish_reason": self.finish}]}
        if self.usage is not None:
            data["usage"] = self.usage
        return {"http_status": 200, "data": data}


def credentials(path: Path) -> dict[str, str]:
    """Read only named credentials; callers never log this mapping."""
    names = {
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
        "XAI_API_KEY",
        "DEEPSEEK_API_KEY",
        "QWEN_API_KEY",
        "KIMI_API_KEY",
        "GLM_API_KEY",
        "DOUBAO_API_KEY",
        "MINIMAX_API_KEY",
        "HUNYUAN_API_KEY",
        "ERNIE_API_KEY",
        "TAVILY_API_KEY",
        "EXA_API_KEY",
        "BRAVE_API_KEY",
        "PERPLEXITY_API_KEY",
        "BOCHA_API_KEY",
        "JINA_API_KEY",
    }
    result = {}
    for line in (
        path.read_text(encoding="utf-8") if path.exists() else ""
    ).splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            if key.strip() in names:
                result[key.strip()] = value.strip().strip("\"'")
    result.update({key: os.environ[key] for key in names if key in os.environ})
    return result


class JsonAPI:
    def __init__(
        self,
        origin: str,
        key: str,
        client: httpx.AsyncClient | None = None,
        *,
        auth_header: str = "Authorization",
        auth_prefix: str = "Bearer ",
        headers: dict | None = None,
        credential_env: str | None = None,
    ):
        self.origin, self._key = origin, key
        self.auth_header, self.auth_prefix = auth_header, auth_prefix
        self.headers = dict(headers or {})
        self.credential_env = credential_env
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(180, connect=20),
            follow_redirects=False,
        )
        self._owns_client = client is None
        self.account = identity(origin, "default-account")[:16]

    def replace_key(self, key: str) -> None:
        if not isinstance(key, str) or not key.strip():
            raise ValueError("credential required")
        self._key = key

    def _headers(self):
        return {
            **self.headers,
            **({self.auth_header: self.auth_prefix + self._key} if self._key else {}),
        }

    @staticmethod
    def _rejection(response: httpx.Response) -> dict:
        result = {"http_status": response.status_code}
        # Keep only a known classification, never provider text that may echo secrets.
        try:
            error = response.json().get("error", {})
            quota_codes = {
                "insufficient_quota",
                "credit_balance_exhausted",
                "organization_spend_limit_exceeded",
                "project_spend_limit_exceeded",
                "billing_hard_limit_reached",
            }
            if isinstance(error, dict) and (
                error.get("code") in quota_codes or error.get("type") in quota_codes
            ):
                result["error_kind"] = "quota"
            if isinstance(error, dict) and any(
                isinstance(detail, dict)
                and detail.get("@type") == "type.googleapis.com/google.rpc.ErrorInfo"
                and detail.get("reason") == "API_KEY_INVALID"
                for detail in error.get("details", [])
            ):
                result["error_kind"] = "authentication"
        except (ValueError, AttributeError, TypeError):
            pass
        if response.status_code == 429:
            try:
                seconds = float(response.headers.get("retry-after", ""))
                if math.isfinite(seconds) and seconds >= 0:
                    result["retry_after"] = seconds
            except ValueError:
                pass
        return result

    async def post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        return await self.request("POST", path, body=body)

    async def request(self, method, path, *, body=None, params=None, text=False):
        response = await self._client.request(
            method,
            self.origin + path,
            json=body,
            params=params,
            headers=self._headers(),
        )
        # Error bodies can echo request data. Keep only safe status metadata.
        if response.status_code != 200:
            return self._rejection(response)
        if text:
            return {"http_status": 200, "data": {"html": response.text}}
        try:
            return {"http_status": 200, "data": response.json()}
        except ValueError:
            return {"http_status": 200, "malformed_json": True}

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def chat_stream(self, path: str, body: dict[str, Any]) -> dict:
        async with self._client.stream(
            "POST",
            self.origin + path,
            json=body,
            headers=self._headers(),
        ) as response:
            if response.status_code != 200:
                return self._rejection(response)
            state = _ChatStream()
            event = []
            try:
                async for line in response.aiter_lines():
                    if line == "":
                        if not event:
                            continue
                        value = "\n".join(event)
                        event = []
                        if value == "[DONE]":
                            return state.result()
                        state.add(json.loads(value))
                    elif line.startswith("data:"):
                        event.append(line[5:].removeprefix(" "))
                    # SSE comments/other fields carry no model content.
            except (ValueError, KeyError, TypeError, IndexError, AttributeError):
                raise IncompleteStream(
                    "invalid provider stream; outcome unknown"
                ) from None
            raise IncompleteStream("provider stream ended before DONE; outcome unknown")


class ChatCompletions:
    """Shared wire protocol, with explicit vendor parameters and model capacity."""

    retry_delay = staticmethod(rate_limit_delay)

    @staticmethod
    def retry_on_resume(raw: dict) -> bool:
        return (
            raw.get("http_status") in {401, 402, 403}
            or raw.get("error_kind") == "quota"
        )

    def __init__(
        self,
        api,
        model,
        *,
        provider,
        max_tokens,
        context_tokens,
        output_parameter="max_tokens",
        request_fields=None,
        stream=False,
    ):
        if type(max_tokens) is not int or max_tokens < 1:
            raise ValueError("positive output allowance required")
        if type(context_tokens) is not int or context_tokens <= max_tokens:
            raise ValueError("context tokens must exceed the output allowance")
        self.api, self.model = api, model
        self.max_tokens, self.context_tokens = max_tokens, context_tokens
        self.stream, self.resource = stream, provider
        self.output_parameter = output_parameter
        self.request_fields = dict(request_fields or {})
        self.identity = identity(
            "official-chat-v1",
            api.account,
            provider,
            model,
            max_tokens,
            context_tokens,
            output_parameter,
            self.request_fields,
            stream,
        )

    def _payload(self, messages, tools):
        return {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            self.output_parameter: self.max_tokens,
            "stream": self.stream,
            **self.request_fields,
            **({"stream_options": {"include_usage": True}} if self.stream else {}),
        }

    def prepare(self, context: dict[str, Any], previous: dict | None) -> dict:
        state = {
            k: v
            for k, v in context.items()
            if k not in {"system", "tools", "tool_versions", "provider"}
        }
        current = {"role": "user", "content": encode(state)}
        messages = [{"role": "system", "content": context["system"]}, current]
        mode = "new"
        if previous:
            try:
                usable = self.decode(previous["response"])["complete"]
            except (
                ProviderFailure,
                ValueError,
                KeyError,
                TypeError,
                IndexError,
                AttributeError,
            ):
                usable = False
            raw = previous["response"]
            if usable:
                choice = raw["data"]["choices"][0]
                if choice["finish_reason"] in {"stop", "tool_calls"}:
                    assistant = choice["message"]
                    outputs = []
                    observations = {
                        o["index"]: o for o in previous["observations"] if "index" in o
                    }
                    for index, call in enumerate(assistant.get("tool_calls") or []):
                        if index not in observations:
                            raise ValueError("cannot continue unpaired tool call")
                        observation = observations[index]
                        result = encode(observation["result"])
                        if len(result) > 12000:
                            result = encode(
                                {
                                    "observation_ref": observation["_ref"],
                                    "body_omitted": True,
                                    "instruction": "Use read_artifact_range",
                                }
                            )
                        else:
                            result = encode(
                                {
                                    "observation_ref": observation["_ref"],
                                    "result": observation["result"],
                                }
                            )
                        outputs.append(
                            {
                                "role": "tool",
                                "tool_call_id": call["id"],
                                "content": result,
                            }
                        )
                    seen = {
                        o["_ref"]
                        for o in previous["observations"]
                        if "_ref" in o
                        and "index" in o
                        and len(encode(o["result"])) <= 12000
                    }
                    prior_fields = {}
                    for message in previous["request"]["messages"]:
                        if message.get("role") not in {"user", "tool"}:
                            continue
                        try:
                            prior_state = json.loads(message["content"])
                        except (ValueError, TypeError):
                            continue
                        if isinstance(prior_state, dict):
                            if message["role"] == "tool":
                                if (
                                    "observation_ref" in prior_state
                                    and "result" in prior_state
                                ):
                                    seen.add(prior_state["observation_ref"])
                                continue
                            prior_fields.update(prior_state)
                            seen.update(
                                item["ref"]
                                for item in prior_state.get("context", [])
                                if isinstance(item, dict)
                                and "ref" in item
                                and "body" in item
                            )
                    current = {
                        "role": "user",
                        "content": encode(
                            {
                                **{
                                    key: value
                                    for key, value in state.items()
                                    if key != "context"
                                    and (
                                        key not in prior_fields
                                        or prior_fields[key] != value
                                    )
                                },
                                "context": [
                                    item
                                    for item in state.get("context", [])
                                    if item["ref"] not in seen
                                ],
                            }
                        ),
                    }
                    messages = [
                        *previous["request"]["messages"],
                        assistant,
                        *outputs,
                        current,
                    ]
                    mode = "continued"
        tools = [
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": spec["description"],
                    "parameters": spec["parameters"],
                },
            }
            for name, spec in context["tools"].items()
        ]
        payload = self._payload(messages, tools)
        estimated = self._input_tokens(
            payload, previous if mode == "continued" else None
        )
        if estimated + self.max_tokens > self.context_tokens:
            payload["messages"] = [
                {"role": "system", "content": context["system"]},
                {"role": "user", "content": encode(state)},
            ]
            mode = "rebuilt"
            estimated = self._input_tokens(payload, None)
        if estimated + self.max_tokens > self.context_tokens:
            raise ValueError("essential context exceeds provider window")
        return {
            "payload": payload,
            "window_mode": mode,
            "estimated_input_tokens": estimated,
        }

    @staticmethod
    def _input_tokens(payload: dict, previous: dict | None) -> int:
        # Reuse billed prompt usage for an unchanged prefix. Only the new tail
        # needs a byte estimate; this includes private continuation without
        # inspecting or summarizing it. JSON framing is counted conservatively.
        if previous:
            prior = previous["request"]
            messages = prior["messages"]
            usage = previous["response"].get("data", {}).get("usage", {}) or {}
            count = usage.get("prompt_tokens")
            if (
                type(count) is int
                and count > 0
                and payload["messages"][: len(messages)] == messages
                and payload["tools"] == prior.get("tools")
                and payload["model"] == prior.get("model")
            ):
                return count + len(
                    encode(payload["messages"][len(messages) :]).encode("utf-8")
                )
        return len(
            encode({k: payload[k] for k in ("messages", "tools")}).encode("utf-8")
        )

    async def complete(self, request: dict[str, Any]) -> dict[str, Any]:
        payload = request["wire"]["payload"]
        send = self.api.chat_stream if payload["stream"] else self.api.post
        return await send("/chat/completions", payload)

    def decode(self, raw: dict[str, Any]) -> dict[str, Any]:
        status = raw.get("http_status", 0)
        if status != 200:
            raise ProviderFailure(self.resource, status)
        if "data" not in raw:
            raise ValueError("invalid model response JSON")
        data = raw["data"]
        if not isinstance(data, dict) or not isinstance(data.get("choices"), list):
            raise ValueError("invalid model choices")
        if len(data["choices"]) != 1 or not isinstance(data["choices"][0], dict):
            raise ValueError("expected one model choice")
        choice = data["choices"][0]
        message = choice["message"]
        if not isinstance(message, dict):
            raise ValueError("invalid model message")
        if not isinstance(message.get("tool_calls") or [], list):
            raise ValueError("invalid model tool calls")
        calls = []
        ids = set()
        for call in message.get("tool_calls") or []:
            if not isinstance(call, dict) or not isinstance(call.get("function"), dict):
                raise ValueError("invalid model tool call")
            if (
                not isinstance(call.get("id"), str)
                or not call["id"]
                or call["id"] in ids
            ):
                raise ValueError("invalid or duplicate provider tool ID")
            ids.add(call["id"])
            arguments = json.loads(call["function"]["arguments"])
            if (
                not isinstance(call["function"].get("name"), str)
                or not call["function"]["name"]
            ):
                raise ValueError("tool name required")
            if not isinstance(arguments, dict):
                raise ValueError("tool arguments must be an object")
            calls.append({"name": call["function"]["name"], "arguments": arguments})
        return {
            "text": message.get("content") or "",
            "calls": calls,
            "complete": choice["finish_reason"] in {"stop", "tool_calls"},
        }


class DeepSeek(ChatCompletions):
    resource = "deepseek"
    retry_delay = staticmethod(rate_limit_delay)

    @staticmethod
    def retry_on_resume(raw: dict) -> bool:
        return raw.get("http_status") in {401, 402}

    def __init__(
        self,
        api: JsonAPI,
        model: str = DEFAULT_MODEL,
        thinking: bool = True,
        max_tokens: int | None = None,
        context_tokens: int = 1000000,
        stream: bool = False,
        reasoning_effort: str = "high",
    ):
        self.api, self.model = api, model
        self.thinking = thinking
        if reasoning_effort not in {"low", "high", "max"}:
            raise ValueError("DeepSeek reasoning effort must be low, high or max")
        self.reasoning_effort = reasoning_effort
        self.max_tokens = (
            max_tokens if max_tokens is not None else (65536 if thinking else 8192)
        )
        # DeepSeek Chat Completions contract, checked 2026-09-11; see ENGINEERING_REVIEW.md.
        if type(self.max_tokens) is not int or not 1 <= self.max_tokens <= 393216:
            raise ValueError("DeepSeek max_tokens must be an integer in 1..393216")
        if type(context_tokens) is not int or context_tokens <= self.max_tokens:
            raise ValueError("context tokens must exceed the output allowance")
        self.context_tokens = context_tokens
        self.stream = stream
        self.identity = identity(
            "deepseek-chat-v1",
            api.account,
            model,
            thinking,
            self.max_tokens,
            context_tokens,
            reasoning_effort,
        )
        if stream:
            self.identity = identity(self.identity, "sse-v1")

    def _payload(self, messages, tools):
        return {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "thinking": {"type": "enabled" if self.thinking else "disabled"},
            "reasoning_effort": self.reasoning_effort,
            "max_tokens": self.max_tokens,
            "stream": self.stream,
        }


class Tavily:
    resource = "tavily"
    retry_delay = staticmethod(rate_limit_delay)

    @staticmethod
    def retry_on_resume(raw: dict) -> bool:
        return raw.get("http_status") in {401, 432, 433}

    def __init__(self, api: JsonAPI):
        self.api = api
        self.identity = identity("tavily-v2-official-defaults", api.account)

    async def search(self, args: dict[str, Any]) -> dict:
        return await self.api.post(
            "/search",
            {
                "query": args["query"],
                "max_results": 10,
                "include_answer": False,
                "include_raw_content": False,
                "include_usage": True,
            },
        )

    @staticmethod
    def validate_extract(args: dict[str, Any]) -> None:
        import ipaddress
        from urllib.parse import urlsplit

        url = urlsplit(args["url"])
        if url.scheme not in {"http", "https"} or not url.hostname or url.username:
            raise ValueError("expected a public web URL")
        if url.hostname.lower() in {"localhost", "localhost.localdomain"}:
            raise ValueError("local targets are not web sources")
        try:
            address = ipaddress.ip_address(url.hostname)
        except ValueError:
            address = None
        if address is not None and not address.is_global:
            raise ValueError("private targets are not web sources")

    async def extract(self, args: dict[str, Any]) -> dict:
        self.validate_extract(args)
        return await self.api.post(
            "/extract",
            {"urls": [args["url"]], "format": "markdown", "include_usage": True},
        )

    @staticmethod
    def _data(raw: dict) -> dict:
        if raw.get("http_status") != 200:
            raise ProviderFailure("tavily", raw.get("http_status", 0))
        data = raw.get("data")
        if not isinstance(data, dict) or not isinstance(data.get("results"), list):
            raise ValueError("invalid Tavily response: expected results array")
        return data

    @classmethod
    def decode_search(cls, raw: dict) -> dict:
        results = []
        for item in cls._data(raw)["results"]:
            if not isinstance(item, dict) or not isinstance(item.get("url"), str):
                raise ValueError("invalid Tavily search result URL")
            if any(not isinstance(item.get(k, ""), str) for k in ("title", "content")):
                raise ValueError("invalid Tavily search title or content")
            results.append(
                {
                    "url": item["url"],
                    "title": item.get("title", ""),
                    "snippet": item.get("content", ""),
                    "content_type": "search_snippet",
                }
            )
        return {"results": results}

    @classmethod
    def decode_extract(cls, raw: dict) -> dict:
        data = cls._data(raw)
        failed = data.get("failed_results", [])
        if not isinstance(failed, list):
            raise ValueError("invalid Tavily extraction failures")
        sources, failures = [], []
        for item in failed:
            if not isinstance(item, dict):
                raise ValueError("invalid Tavily extraction failure")
            failures.append(
                {
                    "url": item.get("url", ""),
                    "reason": str(
                        item.get("error") or "Provider could not extract this URL"
                    ),
                    "action": "Check the URL or obtain an accessible original; no source was saved.",
                }
            )
        for item in data["results"]:
            if not isinstance(item, dict) or not isinstance(item.get("url"), str):
                raise ValueError("invalid Tavily extraction result URL")
            text = item.get("raw_content")
            if not isinstance(text, str) or not text.strip():
                failures.append(
                    {
                        "url": item["url"],
                        "reason": "Extraction returned no readable text",
                        "action": "Use another accessible original or an uploaded copy.",
                    }
                )
                continue
            sources.append(
                {
                    "origin": item["url"],
                    "text": text,
                    "parser": "tavily-extract-v1",
                    "coverage": "extracted_not_reviewed",
                }
            )
        return {"sources": sources, "failures": failures}
