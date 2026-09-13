from __future__ import annotations

import json
import unittest
from copy import deepcopy

import httpx

from epivra.adapters import JsonAPI, ProviderFailure
from epivra.native_models import Anthropic, Gemini


def context():
    return {
        "system": "Research only the supplied task",
        "provider": "fixture",
        "role": "investigator",
        "task": "Read evidence",
        "context": [{"ref": "source-1", "body": {"text": "Original evidence"}}],
        "tools": {
            "read_source": {
                "description": "Read source",
                "parameters": {
                    "type": "object",
                    "properties": {"ref": {"type": "string"}},
                    "required": ["ref"],
                    "additionalProperties": False,
                },
            }
        },
    }


def anthropic_response(stop="tool_use"):
    return {
        "http_status": 200,
        "data": {
            "id": "msg-one",
            "role": "assistant",
            "content": [
                {
                    "type": "thinking",
                    "thinking": "synthetic private fixture",
                    "signature": "opaque-signature",
                },
                {"type": "redacted_thinking", "data": "opaque-redaction"},
                {
                    "type": "tool_use",
                    "id": "tool-123",
                    "name": "read_source",
                    "input": {"ref": "source-1"},
                },
            ],
            "stop_reason": stop,
            "usage": {
                "input_tokens": 100,
                "cache_read_input_tokens": 200,
                "cache_creation_input_tokens": 50,
                "output_tokens": 25,
            },
        },
    }


def gemini_response(finish="STOP"):
    return {
        "http_status": 200,
        "data": {
            "candidates": [
                {
                    "content": {
                        "role": "model",
                        "parts": [
                            {"text": "synthetic private fixture", "thought": True},
                            {
                                "functionCall": {
                                    "id": "fc-123",
                                    "name": "read_source",
                                    "args": {"ref": "source-1"},
                                },
                                "thoughtSignature": "opaque-signature",
                            },
                        ],
                    },
                    "finishReason": finish,
                }
            ],
            "usageMetadata": {
                "promptTokenCount": 350,
                "cachedContentTokenCount": 200,
                "candidatesTokenCount": 25,
            },
        },
    }


class NativeModelTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = httpx.AsyncClient(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json={}))
        )
        self.api = JsonAPI("https://example.invalid/v1", "test-secret", self.client)

    async def asyncTearDown(self):
        await self.client.aclose()

    def models(self):
        return (
            Anthropic(
                self.api, "claude-fixture", max_tokens=4096, context_tokens=200000
            ),
            Gemini(self.api, "gemini-fixture", max_tokens=4096, context_tokens=200000),
        )

    def test_native_protocols_preserve_signed_blocks_and_pair_tool_ids(self):
        for model, response in zip(
            self.models(), (anthropic_response(), gemini_response())
        ):
            with self.subTest(provider=model.resource):
                original = deepcopy(response)
                first = model.prepare(context(), None)
                next_context = context()
                next_context["context"].append(
                    {"ref": "observation-1", "body": {"result": "evidence"}}
                )
                previous = {
                    "request": first["payload"],
                    "response": response,
                    "observations": [
                        {
                            "index": 0,
                            "_ref": "observation-1",
                            "result": {"text": "Evidence result"},
                        }
                    ],
                }
                continued = model.prepare(next_context, previous)
                self.assertEqual("continued", continued["window_mode"])
                history = continued["payload"][model.history_key]
                if model.resource == "anthropic":
                    self.assertEqual(
                        response["data"]["content"], history[-2]["content"]
                    )
                    blocks = history[-1]["content"]
                    self.assertEqual("tool-123", blocks[0]["tool_use_id"])
                    result = json.loads(blocks[0]["content"])
                    delta = json.loads(blocks[-1]["text"])
                    self.assertEqual(350, model._prompt_tokens(response))
                else:
                    self.assertEqual(
                        response["data"]["candidates"][0]["content"], history[-2]
                    )
                    parts = history[-1]["parts"]
                    self.assertEqual("fc-123", parts[0]["functionResponse"]["id"])
                    self.assertEqual(
                        "read_source", parts[0]["functionResponse"]["name"]
                    )
                    result = parts[0]["functionResponse"]["response"]
                    delta = json.loads(parts[-1]["text"])
                self.assertEqual({"text": "Evidence result"}, result["result"])
                self.assertEqual([], delta["context"])
                self.assertEqual(
                    original, response, "prepare must not mutate saved response"
                )
                decoded = model.decode(response)
                self.assertEqual("", decoded["text"])
                self.assertEqual(
                    [{"name": "read_source", "arguments": {"ref": "source-1"}}],
                    decoded["calls"],
                )
                self.assertTrue(decoded["complete"])
                with self.assertRaisesRegex(ValueError, "unpaired"):
                    model.prepare(context(), {**previous, "observations": []})

    def test_truncation_and_safety_do_not_authorize_execution(self):
        a, g = self.models()
        self.assertFalse(a.decode(anthropic_response("max_tokens"))["complete"])
        self.assertFalse(g.decode(gemini_response("MAX_TOKENS"))["complete"])
        self.assertFalse(
            g.decode(
                {
                    "http_status": 200,
                    "data": {"promptFeedback": {"blockReason": "SAFETY"}},
                }
            )["complete"]
        )
        for model in (a, g):
            with self.assertRaises(ProviderFailure):
                model.decode({"http_status": 429})
            with self.assertRaises(ValueError):
                model.decode({"http_status": 200, "malformed_json": True})

    def test_duplicate_native_ids_and_invalid_arguments_are_rejected(self):
        a, g = self.models()
        raw = anthropic_response()
        raw["data"]["content"].append(deepcopy(raw["data"]["content"][-1]))
        with self.assertRaises(ValueError):
            a.decode(raw)
        raw = gemini_response()
        raw["data"]["candidates"][0]["content"]["parts"].append(
            deepcopy(raw["data"]["candidates"][0]["content"]["parts"][-1])
        )
        with self.assertRaises(ValueError):
            g.decode(raw)
        raw = gemini_response()
        raw["data"]["candidates"][0]["content"]["parts"][-1]["functionCall"]["args"] = (
            "not an object"
        )
        with self.assertRaises(ValueError):
            g.decode(raw)

    def test_large_tool_result_keeps_retrievable_receipt_and_signature(self):
        for model, raw in zip(self.models(), (anthropic_response(), gemini_response())):
            first = model.prepare(context(), None)
            previous = {
                "request": first["payload"],
                "response": raw,
                "observations": [
                    {
                        "index": 0,
                        "_ref": "large-result",
                        "result": {"text": "x" * 15000},
                    }
                ],
            }
            prepared = model.prepare(context(), previous)
            payload_text = json.dumps(prepared["payload"])
            self.assertIn("large-result", payload_text)
            self.assertIn("body_omitted", payload_text)
            self.assertIn("opaque-signature", payload_text)
            self.assertNotIn("x" * 15000, payload_text)

    def test_paired_tool_exchange_rebuilds_as_complete_public_state_on_pressure(self):
        model = Anthropic(
            self.api, "claude-fixture", max_tokens=1024, context_tokens=10000
        )
        current = context()
        current["context"].append(
            {"ref": "result", "body": {"text": "Preserved evidence"}}
        )
        first = model.prepare(context(), None)
        raw = anthropic_response()
        original = deepcopy(raw)
        raw["data"]["usage"]["input_tokens"] = 9990
        rebuilt = model.prepare(
            current,
            {
                "request": first["payload"],
                "response": raw,
                "observations": [
                    {
                        "index": 0,
                        "_ref": "result",
                        "result": {"text": "Preserved evidence"},
                    }
                ],
            },
        )
        self.assertEqual("rebuilt", rebuilt["window_mode"])
        messages = rebuilt["payload"]["messages"]
        self.assertEqual(1, len(messages))
        self.assertIn("Preserved evidence", messages[0]["content"][0]["text"])
        self.assertNotIn("opaque-signature", json.dumps(messages))
        self.assertEqual(original["data"]["content"], raw["data"]["content"])

    def test_failed_or_incomplete_previous_response_starts_from_public_feedback(self):
        for model in self.models():
            first = model.prepare(context(), None)
            for raw in (
                {"http_status": 429},
                {"http_status": 200, "malformed_json": True},
                {"http_status": 200, "data": {}},
                anthropic_response("max_tokens")
                if model.resource == "anthropic"
                else gemini_response("MAX_TOKENS"),
            ):
                with self.subTest(provider=model.resource, raw=raw.get("http_status")):
                    fresh = model.prepare(
                        context(),
                        {
                            "request": first["payload"],
                            "response": raw,
                            "observations": [],
                        },
                    )
                    self.assertEqual("new", fresh["window_mode"])
                    self.assertEqual(first["payload"], fresh["payload"])

    def test_configuration_is_explicit_and_no_deepseek_fields_leak(self):
        a = Anthropic(
            self.api,
            "claude-fixture",
            max_tokens=4096,
            context_tokens=200000,
            thinking={"type": "adaptive"},
            effort="high",
        )
        g = Gemini(
            self.api,
            "gemini-fixture",
            max_tokens=4096,
            context_tokens=200000,
            thinking_level="high",
        )
        ap, gp = (
            a.prepare(context(), None)["payload"],
            g.prepare(context(), None)["payload"],
        )
        self.assertEqual({"type": "adaptive"}, ap["thinking"])
        self.assertEqual({"effort": "high"}, ap["output_config"])
        self.assertEqual(
            {"thinkingLevel": "high"}, gp["generationConfig"]["thinkingConfig"]
        )
        self.assertIn("input_schema", ap["tools"][0])
        self.assertIn("parametersJsonSchema", gp["tools"][0]["functionDeclarations"][0])
        for payload in (ap, gp):
            self.assertNotIn("reasoning_effort", payload)
            self.assertNotIn("test-secret", json.dumps(payload))
        for cls in (Anthropic, Gemini):
            with self.assertRaisesRegex(ValueError, "streaming"):
                cls(
                    self.api,
                    "fixture",
                    max_tokens=4096,
                    context_tokens=200000,
                    stream=True,
                )

    async def test_mock_transport_uses_native_endpoint_headers_and_preserves_usage(
        self,
    ):
        for cls, origin, header, suffix, response in (
            (
                Anthropic,
                "https://example.invalid/v1",
                "x-api-key",
                "/v1/messages",
                anthropic_response(),
            ),
            (
                Gemini,
                "https://example.invalid/v1beta",
                "x-goog-api-key",
                "/v1beta/models/native-fixture:generateContent",
                gemini_response(),
            ),
        ):
            with self.subTest(provider=cls.resource):
                requests = []

                def handler(request):
                    requests.append(request)
                    return httpx.Response(200, json=response["data"])

                async with httpx.AsyncClient(
                    transport=httpx.MockTransport(handler)
                ) as client:
                    api = JsonAPI(
                        origin,
                        "test-secret",
                        client,
                        auth_header=header,
                        auth_prefix="",
                        headers={"anthropic-version": "2023-06-01"}
                        if cls is Anthropic
                        else {},
                    )
                    model = cls(
                        api, "native-fixture", max_tokens=4096, context_tokens=200000
                    )
                    wire = model.prepare(context(), None)
                    raw = await model.complete({"wire": wire})
                self.assertEqual(response, raw)
                self.assertEqual(suffix, requests[0].url.path)
                self.assertEqual("test-secret", requests[0].headers[header])
                self.assertNotIn("authorization", requests[0].headers)
                self.assertEqual(wire["payload"], json.loads(requests[0].content))
                self.assertTrue(model.decode(raw)["complete"])
