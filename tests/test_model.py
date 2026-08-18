from __future__ import annotations

import json
import unittest

import httpx

from deep_research_agent.model import (
    ModelAuthError,
    ModelProtocolError,
    OpenAICompatibleClient,
    ToolSpec,
)


async def no_sleep(_seconds: float) -> None:
    return None


class DeepSeekTransportTest(unittest.IsolatedAsyncioTestCase):
    async def test_json_mode_and_tool_calls_follow_openai_wire_format(self) -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            self.assertEqual({"type": "json_object"}, payload["response_format"])
            self.assertEqual(65_536, payload["max_tokens"])
            self.assertEqual("auto", payload["tool_choice"])
            self.assertEqual("search", payload["tools"][0]["function"]["name"])
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [
                                    {
                                        "id": "call-1",
                                        "type": "function",
                                        "function": {
                                            "name": "search",
                                            "arguments": '{"query":"q"}',
                                        },
                                    }
                                ],
                            }
                        }
                    ]
                },
            )

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        model = OpenAICompatibleClient("secret", client=client)
        try:
            reply = await model.complete(
                [
                    {"role": "system", "content": "Return JSON."},
                    {"role": "user", "content": "work"},
                ],
                json_output=True,
                tools=(
                    ToolSpec(
                        "search",
                        "Search",
                        {
                            "type": "object",
                            "properties": {"query": {"type": "string"}},
                            "required": ["query"],
                        },
                    ),
                ),
            )
        finally:
            await client.aclose()

        self.assertEqual("search", reply.tool_calls[0].name)
        self.assertEqual({"query": "q"}, reply.tool_calls[0].parsed_arguments())
        self.assertNotIn("secret", repr(model))

    async def test_transient_rate_limit_is_retried_finitely(self) -> None:
        calls = 0

        async def handler(_request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            if calls == 1:
                return httpx.Response(429, text="provider detail")
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": "{}"}}]},
            )

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        model = OpenAICompatibleClient(
            "secret", client=client, transient_retries=1, sleep=no_sleep
        )
        try:
            reply = await model.complete(
                [{"role": "user", "content": "Return JSON."}], json_output=True
            )
        finally:
            await client.aclose()

        self.assertEqual("{}", reply.content)
        self.assertEqual(2, calls)

    async def test_auth_error_never_includes_upstream_body_or_key(self) -> None:
        async def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, text="sensitive upstream body")

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        model = OpenAICompatibleClient("secret-key", client=client)
        try:
            with self.assertRaises(ModelAuthError) as raised:
                await model.complete([{"role": "user", "content": "hello"}])
        finally:
            await client.aclose()

        message = str(raised.exception)
        self.assertNotIn("sensitive", message)
        self.assertNotIn("secret-key", message)

    async def test_truncated_output_is_never_committed_as_a_role_result(self) -> None:
        async def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "finish_reason": "length",
                            "message": {"content": "partial report"},
                        }
                    ]
                },
            )

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        model = OpenAICompatibleClient("secret", client=client)
        try:
            with self.assertRaisesRegex(ModelProtocolError, "not accepted"):
                await model.complete([{"role": "user", "content": "write"}])
        finally:
            await client.aclose()


if __name__ == "__main__":
    unittest.main()
