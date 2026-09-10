"""Explicit DeepSeek and Tavily protocols. No Agent loop or hidden retries."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import httpx

from .domain import encode, identity

DEFAULT_MODEL = "deepseek-v4-flash"


class ProviderFailure(RuntimeError):
    def __init__(self, provider: str, status: int):
        self.provider, self.status = provider, status
        super().__init__(f"{provider}: HTTP {status}")


class IncompleteStream(RuntimeError):
    """The provider may have charged; no executable response was received."""


def rate_limit_delay(raw: dict, attempt: int) -> float | None:
    """Only an explicit rejection permits an automatic new attempt."""
    if raw.get("http_status") == 429:
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
    result = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            if key in {"DEEPSEEK_API_KEY", "TAVILY_API_KEY"}:
                result[key] = value.strip()
    return result


class JsonAPI:
    def __init__(self, origin: str, key: str, client: httpx.AsyncClient | None = None):
        self.origin, self._key = origin, key
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

    @staticmethod
    def _rejection(response: httpx.Response) -> dict:
        result = {"http_status": response.status_code}
        if response.status_code == 429:
            try:
                seconds = float(response.headers.get("retry-after", ""))
                if math.isfinite(seconds) and seconds >= 0:
                    result["retry_after"] = seconds
            except ValueError:
                pass
        return result

    async def post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        response = await self._client.post(
            self.origin + path,
            json=body,
            headers={"Authorization": "Bearer " + self._key},
        )
        # Error bodies can echo request data. Keep only safe status metadata.
        if response.status_code != 200:
            return self._rejection(response)
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
            headers={"Authorization": "Bearer " + self._key},
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


class DeepSeek:
    retry_delay = staticmethod(rate_limit_delay)

    @staticmethod
    def retry_on_resume(raw: dict) -> bool:
        return raw.get("http_status") in {401, 402}

    def __init__(
        self,
        api: JsonAPI,
        model: str = DEFAULT_MODEL,
        thinking: bool = True,
        max_tokens: int = 8192,
        window_chars: int = 120000,
        stream: bool = False,
    ):
        self.api, self.model = api, model
        self.thinking, self.max_tokens = thinking, max_tokens
        self.window_chars = window_chars
        self.stream = stream
        self.identity = identity(
            "deepseek-chat-v1", api.account, model, thinking, max_tokens, window_chars
        )
        if stream:
            self.identity = identity(self.identity, "sse-v1")

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
            raw = previous["response"]
            if raw.get("http_status") == 200 and "data" in raw:
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
                        outputs.append(
                            {
                                "role": "tool",
                                "tool_call_id": call["id"],
                                "content": result,
                            }
                        )
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
        payload = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "thinking": {"type": "enabled" if self.thinking else "disabled"},
            "max_tokens": self.max_tokens,
            "stream": self.stream,
        }
        if len(encode(payload)) > self.window_chars:
            payload["messages"] = [
                {"role": "system", "content": context["system"]},
                current,
            ]
            mode = "rebuilt"
        if len(encode(payload)) > self.window_chars:
            raise ValueError("essential context exceeds provider window")
        return {"payload": payload, "window_mode": mode}

    async def complete(self, request: dict[str, Any]) -> dict[str, Any]:
        payload = request["wire"]["payload"]
        send = self.api.chat_stream if payload["stream"] else self.api.post
        return await send("/chat/completions", payload)

    def decode(self, raw: dict[str, Any]) -> dict[str, Any]:
        status = raw.get("http_status", 0)
        if status != 200:
            raise ProviderFailure("deepseek", status)
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
            if not isinstance(call.get("id"), str) or call["id"] in ids:
                raise ValueError("invalid or duplicate provider tool ID")
            ids.add(call["id"])
            arguments = json.loads(call["function"]["arguments"])
            if not isinstance(arguments, dict):
                raise ValueError("tool arguments must be an object")
            calls.append({"name": call["function"]["name"], "arguments": arguments})
        return {
            "text": message.get("content") or "",
            "calls": calls,
            "complete": choice["finish_reason"] in {"stop", "tool_calls"},
        }


class Tavily:
    retry_delay = staticmethod(rate_limit_delay)

    @staticmethod
    def retry_on_resume(raw: dict) -> bool:
        return raw.get("http_status") in {401, 432, 433}

    def __init__(self, api: JsonAPI):
        self.api = api
        self.identity = identity("tavily-v1", api.account)

    async def search(self, args: dict[str, Any]) -> dict:
        return await self.api.post(
            "/search",
            {
                "query": args["query"],
                "max_results": 5,
                "include_answer": False,
                "include_raw_content": False,
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
            "/extract", {"urls": [args["url"]], "format": "text"}
        )
