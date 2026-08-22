from __future__ import annotations

import json
import unittest

import httpx

from deep_research_agent.model import (
    ModelAuthError,
    ModelProtocolError,
    OpenAICompatibleClient,
    TokenUsage,
    ToolSpec,
)


async def no_sleep(_seconds: float) -> None:
    return None


class DeepSeekTransportTest(unittest.IsolatedAsyncioTestCase):
    async def test_tool_calls_follow_the_openai_wire_format(self) -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            self.assertNotIn("response_format", payload)
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
                [{"role": "user", "content": "work"}]
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


class TokenUsageTest(unittest.TestCase):
    """Spend has to be readable from whatever shape a vendor happens to send.

    The distinction that matters is absent-versus-zero: a provider that reports
    no usage must not be recorded as a free call, or a spend report quietly
    under-counts and the resource budget it feeds is wrong in the safe-looking
    direction.
    """

    def test_the_openai_shape_is_read(self) -> None:
        usage = TokenUsage.from_payload(
            {"prompt_tokens": 900, "completion_tokens": 120, "total_tokens": 1020}
        )
        assert usage is not None
        self.assertEqual((900, 120), (usage.input_tokens, usage.output_tokens))
        self.assertEqual(1020, usage.total_tokens)

    def test_the_anthropic_shape_is_read(self) -> None:
        usage = TokenUsage.from_payload(
            {
                "input_tokens": 700,
                "output_tokens": 80,
                "cache_read_input_tokens": 640,
            }
        )
        assert usage is not None
        self.assertEqual((700, 80, 640), (
            usage.input_tokens,
            usage.output_tokens,
            usage.cached_input_tokens,
        ))

    def test_a_cache_hit_reported_inside_details_is_kept(self) -> None:
        usage = TokenUsage.from_payload(
            {
                "prompt_tokens": 5000,
                "completion_tokens": 200,
                "prompt_tokens_details": {"cached_tokens": 4096},
            }
        )
        assert usage is not None
        self.assertEqual(4096, usage.cached_input_tokens)

    def test_absent_usage_is_none_not_zero(self) -> None:
        for payload in (None, {}, {"prompt_tokens": 0, "completion_tokens": 0}, "x"):
            with self.subTest(payload=payload):
                self.assertIsNone(TokenUsage.from_payload(payload))  # type: ignore[arg-type]

    def test_a_negative_count_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            TokenUsage(input_tokens=-1)


if __name__ == "__main__":
    unittest.main()
