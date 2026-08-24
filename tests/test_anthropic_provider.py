"""The Anthropic transport must match the Messages API, not the OpenAI shape.

Every assertion here pins a difference that would otherwise reach a user as an
opaque 404 or 400: system as a top-level parameter, required max_tokens,
input_schema instead of parameters, tool_use blocks instead of tool_calls,
{"type": "any"} instead of "required", and sampling parameters that current
Claude models reject outright.
"""

from __future__ import annotations

import json
import unittest

import httpx

from deep_research_agent.model import (
    ModelAuthError,
    ModelOutputTruncated,
    ModelRateLimitError,
    ModelRequestRejected,
    ModelUnavailableError,
    ToolSpec,
)
from deep_research_agent.providers import build_chat_model, resolve_llm_provider
from deep_research_agent.providers.anthropic import (
    ANTHROPIC_VERSION,
    AnthropicClient,
    parse_reply,
    translate_messages,
)

TOOL = ToolSpec(
    name="submit_report",
    description="Submit the finished report.",
    parameters={
        "type": "object",
        "properties": {"report_markdown": {"type": "string"}},
        "required": ["report_markdown"],
    },
)


def capture(handler) -> tuple[AnthropicClient, dict]:
    seen: dict = {}

    async def wrapped(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["headers"] = dict(request.headers)
        seen["payload"] = json.loads(request.content)
        return handler(request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(wrapped))
    return AnthropicClient("secret", client=client), seen


def text_response(_request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "content": [{"type": "text", "text": "An answer."}],
            "stop_reason": "end_turn",
        },
    )


class RequestShapeTest(unittest.IsolatedAsyncioTestCase):
    async def test_system_is_a_top_level_parameter_not_a_message(self) -> None:
        client, seen = capture(text_response)
        try:
            await client.complete(
                [
                    {"role": "system", "content": "You are an Evidence Analyst."},
                    {"role": "user", "content": "Analyse."},
                ]
            )
        finally:
            await client.client.aclose()

        self.assertEqual("You are an Evidence Analyst.", seen["payload"]["system"])
        self.assertEqual(
            [{"role": "user", "content": "Analyse."}], seen["payload"]["messages"]
        )

    async def test_required_headers_and_endpoint(self) -> None:
        client, seen = capture(text_response)
        try:
            await client.complete([{"role": "user", "content": "Hello."}])
        finally:
            await client.client.aclose()

        self.assertEqual("https://api.anthropic.com/v1/messages", seen["url"])
        self.assertEqual(ANTHROPIC_VERSION, seen["headers"]["anthropic-version"])
        self.assertEqual("secret", seen["headers"]["x-api-key"])
        # An OpenAI-style bearer header is not how this API authenticates.
        self.assertNotIn("authorization", seen["headers"])

    async def test_max_tokens_is_always_sent(self) -> None:
        client, seen = capture(text_response)
        try:
            await client.complete([{"role": "user", "content": "Hello."}])
        finally:
            await client.client.aclose()

        self.assertGreater(seen["payload"]["max_tokens"], 0)

    async def test_sampling_parameters_are_never_sent(self) -> None:
        """Current Claude models reject temperature/top_p/top_k with a 400."""

        client, seen = capture(text_response)
        try:
            await client.complete([{"role": "user", "content": "Hello."}])
        finally:
            await client.client.aclose()

        for forbidden in ("temperature", "top_p", "top_k"):
            self.assertNotIn(forbidden, seen["payload"])

    async def test_tools_use_input_schema_not_parameters(self) -> None:
        client, seen = capture(text_response)
        try:
            await client.complete(
                [{"role": "user", "content": "Write it."}], tools=(TOOL,)
            )
        finally:
            await client.client.aclose()

        tool = seen["payload"]["tools"][0]
        self.assertEqual("submit_report", tool["name"])
        self.assertIn("input_schema", tool)
        self.assertNotIn("parameters", tool)
        self.assertNotIn("function", tool)

    async def test_required_tool_choice_becomes_any(self) -> None:
        """OpenAI's "required" is a 400 here; the wire value is {"type": "any"}."""

        for neutral, expected in (
            ("required", "any"),
            ("auto", "auto"),
            ("none", "none"),
        ):
            with self.subTest(tool_choice=neutral):
                client, seen = capture(text_response)
                try:
                    await client.complete(
                        [{"role": "user", "content": "Write it."}],
                        tools=(TOOL,),
                        tool_choice=neutral,  # type: ignore[arg-type]
                    )
                finally:
                    await client.client.aclose()
                self.assertEqual({"type": expected}, seen["payload"]["tool_choice"])


class TranslationTest(unittest.TestCase):
    def test_a_correction_turn_becomes_an_error_tool_result(self) -> None:
        """A tool_use must be answered by a tool_result with the same id."""

        system, messages = translate_messages(
            [
                {"role": "system", "content": "S"},
                {"role": "user", "content": "Write it."},
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "toolu_1",
                            "type": "function",
                            "function": {
                                "name": "submit_report",
                                "arguments": '{"report_markdown": ""}',
                            },
                        }
                    ],
                },
                {"role": "user", "content": "动作无效：报告过短"},
            ]
        )

        self.assertEqual("S", system)
        assistant = messages[1]
        self.assertEqual("tool_use", assistant["content"][0]["type"])
        self.assertEqual("toolu_1", assistant["content"][0]["id"])

        correction = messages[2]["content"][0]
        self.assertEqual("tool_result", correction["type"])
        self.assertEqual("toolu_1", correction["tool_use_id"])
        self.assertTrue(correction["is_error"])
        self.assertIn("报告过短", correction["content"])

    def test_a_plain_user_turn_stays_plain(self) -> None:
        _system, messages = translate_messages(
            [{"role": "user", "content": "Just a question."}]
        )
        self.assertEqual([{"role": "user", "content": "Just a question."}], messages)

    def test_tool_use_blocks_parse_into_neutral_tool_calls(self) -> None:
        reply = parse_reply(
            {
                "content": [
                    {"type": "text", "text": "Submitting."},
                    {
                        "type": "tool_use",
                        "id": "toolu_9",
                        "name": "submit_report",
                        "input": {"report_markdown": "# 报告"},
                    },
                ],
                "stop_reason": "tool_use",
            }
        )

        self.assertEqual("Submitting.", reply.content)
        self.assertEqual("submit_report", reply.tool_calls[0].name)
        self.assertEqual(
            {"report_markdown": "# 报告"},
            json.loads(reply.tool_calls[0].arguments),
        )


class FailureMappingTest(unittest.IsolatedAsyncioTestCase):
    async def run_status(self, status: int) -> None:
        client, _ = capture(lambda _r: httpx.Response(status, json={}))
        try:
            await client.complete([{"role": "user", "content": "Hello."}])
        finally:
            await client.client.aclose()

    async def test_status_codes_map_to_billing_relevant_failures(self) -> None:
        for status, expected in (
            (401, ModelAuthError),
            (429, ModelRateLimitError),
            (503, ModelUnavailableError),
            # A 4xx is refused before generation, so it is provably unbilled.
            (400, ModelRequestRejected),
        ):
            with self.subTest(status=status), self.assertRaises(expected):
                await self.run_status(status)

    async def test_a_refusal_is_detected_before_content_is_read(self) -> None:
        """A refusal is HTTP 200 with empty content, not an error status."""

        client, _ = capture(
            lambda _r: httpx.Response(
                200, json={"content": [], "stop_reason": "refusal"}
            )
        )
        try:
            with self.assertRaisesRegex(ModelRequestRejected, "refusal"):
                await client.complete([{"role": "user", "content": "..."}])
        finally:
            await client.client.aclose()

    async def test_truncation_is_detected_before_content_is_read(self) -> None:
        """Truncation is HTTP 200 with usable-looking content, which is the trap.

        This transport checked only ``refusal``, so a report cut off at the output
        ceiling came back as an ordinary reply: it passed the Author's validator,
        became a report artifact, went through review, and could publish.  The
        OpenAI transport raised on the same event, so the two vendors disagreed
        about whether a half-written report was publishable.
        """

        client, _ = capture(
            lambda _r: httpx.Response(
                200,
                json={
                    "content": [{"type": "text", "text": "报告写到一半就断了"}],
                    "stop_reason": "max_tokens",
                },
            )
        )
        try:
            with self.assertRaises(ModelOutputTruncated) as raised:
                await client.complete([{"role": "user", "content": "..."}])
        finally:
            await client.client.aclose()
        # The message has to name the setting, because raising it is the only fix.
        self.assertIn("输出上限", str(raised.exception))

    async def test_the_api_key_never_appears_in_the_repr(self) -> None:
        self.assertNotIn("secret", repr(AnthropicClient("secret")))


class ProtocolRoutingTest(unittest.TestCase):
    def test_each_vendor_gets_the_transport_its_protocol_declares(self) -> None:
        anthropic = resolve_llm_provider("anthropic")
        deepseek = resolve_llm_provider("deepseek")

        self.assertEqual("anthropic", anthropic.protocol)
        self.assertEqual("openai_compatible", deepseek.protocol)
        self.assertIsInstance(
            build_chat_model(anthropic, anthropic.reasoning_model, api_key="k"),
            AnthropicClient,
        )
        self.assertNotIsInstance(
            build_chat_model(deepseek, deepseek.reasoning_model, api_key="k"),
            AnthropicClient,
        )

    def test_claude_model_ids_carry_no_date_suffix(self) -> None:
        """Appending a date suffix to a Claude alias 404s."""

        spec = resolve_llm_provider("anthropic")
        for model_id in (spec.reasoning_model, spec.fast_model):
            with self.subTest(model=model_id):
                self.assertNotRegex(model_id, r"-\d{8}$")

    def test_a_gateway_reaching_claude_stays_openai_compatible(self) -> None:
        """OpenRouter re-exposes Claude behind the OpenAI protocol."""

        spec = resolve_llm_provider("openrouter")
        self.assertEqual("openai_compatible", spec.protocol)
        self.assertIn("claude", spec.reasoning_model)


if __name__ == "__main__":
    unittest.main()
