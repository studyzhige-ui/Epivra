from __future__ import annotations

import json
import unittest

import httpx

from deep_research_agent.adapters import (
    DeepSeek,
    IncompleteStream,
    JsonAPI,
    ProviderFailure,
    Tavily,
    rate_limit_delay,
)


def response(finish="tool_calls", arguments='{"value":"ok"}'):
    return {
        "http_status": 200,
        "data": {
            "choices": [
                {
                    "finish_reason": finish,
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "reasoning_content": "provider-private-continuation",
                        "tool_calls": [
                            {
                                "id": "call1",
                                "type": "function",
                                "function": {"name": "echo", "arguments": arguments},
                            }
                        ],
                    },
                }
            ],
            "usage": {"total_tokens": 12},
        },
    }


class AdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_fragmented_stream_reassembles_tools_and_usage(self):
        def chunk(delta, finish=None, usage=None):
            return (
                "data: "
                + json.dumps(
                    {
                        "choices": [
                            {"index": 0, "delta": delta, "finish_reason": finish}
                        ],
                        "usage": usage,
                    }
                )
                + "\n\n"
            )

        events = ": keepalive\n\n" + chunk(
            {"role": "assistant", "reasoning_content": "private"}
        )
        events += chunk(
            {
                "tool_calls": [
                    {
                        "index": 0,
                        "id": "call1",
                        "type": "function",
                        "function": {"name": "echo", "arguments": '{"value":'},
                    }
                ]
            }
        )
        events += chunk(
            {"tool_calls": [{"index": 0, "function": {"arguments": '"ok"}'}}]}
        )
        events += chunk({}, "tool_calls", {"total_tokens": 12}) + "data: [DONE]\n\n"

        class Fragmented(httpx.AsyncByteStream):
            async def __aiter__(self):
                data = events.encode()
                for i in range(0, len(data), 7):
                    yield data[i : i + 7]

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda r: httpx.Response(200, stream=Fragmented())
            )
        ) as client:
            model = DeepSeek(
                JsonAPI("https://fixture.test", "key", client), stream=True
            )
            raw = await model.complete({"wire": model.prepare(self.context, None)})
            self.assertEqual(
                [{"name": "echo", "arguments": {"value": "ok"}}],
                model.decode(raw)["calls"],
            )
            self.assertEqual(12, raw["data"]["usage"]["total_tokens"])
            self.assertEqual(
                "private", raw["data"]["choices"][0]["message"]["reasoning_content"]
            )

    async def test_stream_requires_both_terminators_and_valid_protocol(self):
        end = 'data: {"choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}\n\n'
        for events in [
            end,
            "data: [DONE]\n\n",
            "data: broken\n\n",
            end + end + "data: [DONE]\n\n",
        ]:
            with self.subTest(events=events):
                async with httpx.AsyncClient(
                    transport=httpx.MockTransport(
                        lambda r: httpx.Response(200, content=events.encode())
                    )
                ) as client:
                    api = JsonAPI("https://fixture.test", "key", client)
                    with self.assertRaises(IncompleteStream):
                        await api.chat_stream("/chat/completions", {})

    async def test_rejection_preserves_only_safe_retry_metadata(self):
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda r: httpx.Response(
                    429, headers={"retry-after": "120"}, text="private"
                )
            )
        ) as client:
            api = JsonAPI("https://fixture.test", "key", client)
            raw = await api.post("/search", {})
            self.assertEqual({"http_status": 429, "retry_after": 120.0}, raw)
            self.assertEqual(120, rate_limit_delay(raw, 0))
            self.assertIsNone(rate_limit_delay({"http_status": 503}, 0))

    async def test_invalid_response_shapes_are_repairable(self):
        for data in [
            None,
            {},
            {"choices": []},
            {"choices": [None]},
            {"choices": [{"message": [], "finish_reason": "stop"}]},
        ]:
            with self.subTest(data=data), self.assertRaises(ValueError):
                self.model.decode({"http_status": 200, "data": data})

    async def asyncSetUp(self):
        self.requests = []

        def handle(request):
            self.requests.append(request)
            return httpx.Response(200, json=response()["data"])

        self.client = httpx.AsyncClient(transport=httpx.MockTransport(handle))
        self.api = JsonAPI("https://api.deepseek.com", "test-key", self.client)
        self.model = DeepSeek(self.api)
        self.context = {"system": "Research", "tools": {}, "task": "Question"}

    async def asyncTearDown(self):
        await self.client.aclose()

    async def test_actual_payload_is_frozen_and_auth_is_transport_only(self):
        wire = self.model.prepare(self.context, None)
        raw = await self.model.complete({"wire": wire})
        self.assertEqual(200, raw["http_status"])
        self.assertNotIn("test-key", str(wire))
        self.assertEqual("Bearer test-key", self.requests[0].headers["Authorization"])
        self.assertEqual(1, len(self.requests))

    async def test_reasoning_and_tool_ids_are_preserved_on_continuation(self):
        first = self.model.prepare(self.context, None)
        second = self.model.prepare(
            self.context,
            {
                "request": first["payload"],
                "response": response(),
                "observations": [
                    {"index": 0, "result": {"value": "ok"}, "_ref": "obs"}
                ],
            },
        )
        messages = second["payload"]["messages"]
        self.assertEqual(
            "provider-private-continuation", messages[2]["reasoning_content"]
        )
        self.assertEqual("call1", messages[3]["tool_call_id"])
        self.assertEqual("continued", second["window_mode"])

    async def test_unpaired_tool_is_not_silently_dropped(self):
        with self.assertRaisesRegex(ValueError, "unpaired"):
            self.model.prepare(
                self.context,
                {
                    "request": self.model.prepare(self.context, None)["payload"],
                    "response": response(),
                    "observations": [],
                },
            )

    async def test_oversized_window_is_rebuilt_at_complete_tool_boundary(self):
        self.model.window_chars = 2000
        old = self.model.prepare(self.context, None)["payload"]
        old["messages"][1]["content"] = "x" * 10000
        wire = self.model.prepare(
            self.context,
            {
                "request": old,
                "response": response(),
                "observations": [{"index": 0, "result": "ok", "_ref": "obs"}],
            },
        )
        self.assertEqual("rebuilt", wire["window_mode"])
        self.assertEqual(2, len(wire["payload"]["messages"]))

    async def test_incomplete_or_malformed_model_output_cannot_execute_tools(self):
        self.assertFalse(self.model.decode(response("length"))["complete"])
        with self.assertRaises(ValueError):
            self.model.decode(response(arguments="{"))
        raw = response()
        raw["data"]["choices"][0]["message"]["tool_calls"] *= 2
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.model.decode(raw)

    async def test_provider_errors_do_not_echo_secret_response_bodies(self):
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(401, json={"error": "secret-echo"})
            )
        ) as client:
            api = JsonAPI("https://api.deepseek.com", "test-key", client)
            raw = await api.post("/chat/completions", {})
            self.assertEqual({"http_status": 401}, raw)
            with self.assertRaises(ProviderFailure) as error:
                self.model.decode(raw)
            self.assertNotIn("secret-echo", str(error.exception))

    async def test_transport_failure_has_no_hidden_retry(self):
        calls = 0

        def fail(request):
            nonlocal calls
            calls += 1
            raise httpx.ReadTimeout("fixture")

        async with httpx.AsyncClient(transport=httpx.MockTransport(fail)) as client:
            api = JsonAPI("https://api.deepseek.com", "test-key", client)
            with self.assertRaises(httpx.ReadTimeout):
                await api.post("/chat/completions", {})
        self.assertEqual(1, calls)

    async def test_tavily_does_not_follow_auth_redirect(self):
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    302, headers={"Location": "https://elsewhere.test"}
                )
            ),
            follow_redirects=False,
        ) as client:
            api = JsonAPI("https://api.tavily.com", "test", client)
            raw = await Tavily(api).search({"query": "public research"})
            self.assertEqual(302, raw["http_status"])

    async def test_private_extract_target_is_rejected_before_network(self):
        tavily = Tavily(self.api)
        for url in ["file:///etc/passwd", "http://127.0.0.1/a", "http://localhost/a"]:
            with self.assertRaises(ValueError):
                await tavily.extract({"url": url})
        self.assertEqual([], self.requests)
