from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from epivra.adapters import ChatCompletions, credentials, rate_limit_delay
from epivra.application import online_service
from epivra.domain import encode
from epivra.model_catalog import OFFICIAL_PROVIDERS
from epivra.models import (
    create_model,
    freeze_model_settings,
    model_settings,
)
from epivra.storage import Store

CONTEXT = {
    "system": "Complete the assigned research task using original evidence.",
    "task": "Investigate",
    "context": [],
    "tools": {
        "read_artifact_range": {
            "description": "Read an original artifact",
            "parameters": {
                "type": "object",
                "properties": {"ref": {"type": "string"}},
                "required": ["ref"],
                "additionalProperties": False,
            },
        }
    },
}


def raw_call(protocol):
    if protocol == "anthropic":
        return {
            "stop_reason": "tool_use",
            "content": [
                {
                    "type": "tool_use",
                    "id": "c1",
                    "name": "read_artifact_range",
                    "input": {"ref": "original"},
                }
            ],
            "usage": {"input_tokens": 55, "output_tokens": 20},
        }
    if protocol == "gemini":
        return {
            "candidates": [
                {
                    "finishReason": "STOP",
                    "content": {
                        "role": "model",
                        "parts": [
                            {
                                "thoughtSignature": "signed-original",
                                "functionCall": {
                                    "id": "c1",
                                    "name": "read_artifact_range",
                                    "args": {"ref": "original"},
                                },
                            }
                        ],
                    },
                }
            ],
            "usageMetadata": {"promptTokenCount": 55, "candidatesTokenCount": 20},
        }
    return {
        "choices": [
            {
                "finish_reason": "tool_calls",
                "message": {
                    "role": "assistant",
                    "content": None,
                    "reasoning_content": "private-continuation",
                    "reasoning_details": [{"type": "reasoning.text", "text": "opaque"}],
                    "tool_calls": [
                        {
                            "id": "c1",
                            "type": "function",
                            "function": {
                                "name": "read_artifact_range",
                                "arguments": '{"ref":"original"}',
                            },
                        }
                    ],
                },
            }
        ],
        "usage": {"prompt_tokens": 55, "completion_tokens": 20},
    }


class OfficialModelTests(unittest.IsolatedAsyncioTestCase):
    async def test_gemini_http400_bad_key_can_resume_after_credential_repair(self):
        async with httpx.AsyncClient(transport=httpx.MockTransport(
            lambda request: httpx.Response(400, json={"error": {
                "code": 400, "message": "secret-echo", "details": [{
                    "@type": "type.googleapis.com/google.rpc.ErrorInfo",
                    "reason": "API_KEY_INVALID"}]}})
        )) as client:
            model, _ = create_model({"provider": "gemini"}, {"GEMINI_API_KEY": "fixture"}, client=client)
            raw = await model.complete({"wire": model.prepare(CONTEXT, None)})
            self.assertEqual({"http_status": 400, "error_kind": "authentication"}, raw)
            self.assertTrue(model.retry_on_resume(raw))
            self.assertFalse(model.retry_on_resume({"http_status": 400}))

    async def test_three_protocols_run_real_harness_and_resume_exact_history(self):
        from epivra.harness import Harness, Tool

        for name in ("openai", "claude", "gemini"):
            with (
                self.subTest(provider=name),
                tempfile.TemporaryDirectory() as directory,
            ):
                spec = OFFICIAL_PROVIDERS[name]
                requests, executed = [], []

                def respond(request):
                    requests.append(json.loads(request.content))
                    body = encode(raw_call(spec.protocol)).replace(
                        "read_artifact_range", "inspect_original"
                    )
                    return httpx.Response(200, json=json.loads(body))

                async def inspect(args):
                    executed.append(args)
                    return {"text": "Original evidence"}

                async with httpx.AsyncClient(
                    transport=httpx.MockTransport(respond)
                ) as client:
                    policy = freeze_model_settings(
                        {"provider": name, "stream_model": False}
                    )
                    model, _ = create_model(
                        policy, {spec.credential_env: "fixture"}, client=client
                    )
                    store = Store(Path(directory) / "research.db")
                    try:
                        c = store.create("s", "Investigate", policy)
                        plan = store.put(
                            "s", "plan", {"text": "Investigate"}, (c.direction,)
                        )
                        c = store.command(
                            "s", "approve", c.ref, "approve", {"plan": plan.ref}
                        )
                        work = store.work("s", c.ref, "lead", "Investigate")
                        tools = {
                            "inspect_original": Tool(
                                "Read original evidence",
                                CONTEXT["tools"]["read_artifact_range"]["parameters"],
                                inspect,
                                roles=("lead",),
                                identity="fixture-original",
                            )
                        }
                        await Harness(store, model, tools).step("s", work.ref)
                        path = store.path
                        store.close()
                        store = Store(path)
                        restored, _ = create_model(
                            policy, {spec.credential_env: "fixture"}, client=client
                        )
                        await Harness(store, restored, tools).step("s", work.ref)
                        self.assertEqual(2, len(requests))
                        self.assertEqual(2, len(executed))
                        self.assertIn("Original evidence", encode(requests[1]))
                        self.assertEqual(2, len(store.list("s", "step")))
                    finally:
                        store.close()

    async def test_chat_malformed_previous_reply_recovers_from_public_context(self):
        async with httpx.AsyncClient() as client:
            model, _ = create_model(
                {"provider": "openai"}, {"OPENAI_API_KEY": "fixture"}, client=client
            )
            first = model.prepare(CONTEXT, None)
            for data in ({}, {"choices": []}, {"choices": [None]}):
                with self.subTest(data=data):
                    wire = model.prepare(
                        CONTEXT,
                        {
                            "request": first["payload"],
                            "response": {"http_status": 200, "data": data},
                            "observations": [],
                        },
                    )
                    self.assertEqual("new", wire["window_mode"])

    async def test_freeze_defaults_respects_protocol_and_original_deepseek_binding(
        self,
    ):
        from epivra.adapters import DeepSeek, JsonAPI

        policy = freeze_model_settings({"provider": "minimax"})
        self.assertFalse(policy["stream_model"])
        self.assertEqual(131072, policy["max_tokens"])
        self.assertTrue(policy["model_profile"]["request_fields"]["reasoning_split"])
        with self.assertRaises(ValueError):
            model_settings({"provider": "minimax", "stream_model": True})
        client = httpx.AsyncClient()
        api = JsonAPI("https://api.deepseek.com", "fixture", client)
        expected = DeepSeek(api).identity
        actual, _ = create_model({}, {"DEEPSEEK_API_KEY": "fixture"}, client=client)
        self.assertEqual(expected, actual.identity)
        await client.aclose()

    async def test_all_official_connections_execute_and_continue_tool_exchange(self):
        self.assertEqual(12, len(OFFICIAL_PROVIDERS))
        for name, spec in OFFICIAL_PROVIDERS.items():
            with self.subTest(provider=name):
                captured = []

                def respond(request):
                    captured.append(request)
                    return httpx.Response(200, json=raw_call(spec.protocol))

                async with httpx.AsyncClient(
                    transport=httpx.MockTransport(respond)
                ) as client:
                    # Every shipped preset must work with only its official credential.
                    policy = {"provider": name}
                    model, api = create_model(
                        policy, {spec.credential_env: "fixture-secret"}, client=client
                    )
                    first = model.prepare(CONTEXT, None)
                    raw = await model.complete({"wire": first})
                    decoded = model.decode(raw)
                    self.assertTrue(decoded["complete"])
                    self.assertEqual(
                        [
                            {
                                "name": "read_artifact_range",
                                "arguments": {"ref": "original"},
                            }
                        ],
                        decoded["calls"],
                    )
                    next_wire = model.prepare(
                        CONTEXT,
                        {
                            "request": first["payload"],
                            "response": raw,
                            "observations": [
                                {
                                    "index": 0,
                                    "_ref": "obs-original",
                                    "result": {"text": "原件内容"},
                                }
                            ],
                        },
                    )
                    self.assertEqual("continued", next_wire["window_mode"])
                    wire = encode(next_wire)
                    self.assertIn("obs-original", wire)
                    self.assertIn("原件内容", wire)
                    self.assertNotIn("fixture-secret", wire + model.identity)
                    self.assertEqual(
                        spec.auth_prefix + "fixture-secret",
                        captured[0].headers[spec.auth_header],
                    )
                    self.assertTrue(str(captured[0].url).startswith(api.origin + "/"))
                    if spec.protocol == "chat" and name != "deepseek":
                        self.assertNotIn(
                            "thinking",
                            first["payload"] if name not in {"kimi", "glm"} else {},
                        )
                        self.assertIn("reasoning_details", wire)

    async def test_quota_rejection_does_not_spin_or_expose_body(self):
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    429,
                    json={
                        "error": {
                            "code": "credit_balance_exhausted",
                            "message": "fixture-secret",
                        }
                    },
                )
            )
        ) as client:
            model, api = create_model(
                {"provider": "openai"},
                {"OPENAI_API_KEY": "fixture-secret"},
                client=client,
            )
            raw = await model.complete({"wire": model.prepare(CONTEXT, None)})
            self.assertEqual("quota", raw["error_kind"])
            self.assertNotIn("fixture-secret", encode(raw))
            self.assertIsNone(rate_limit_delay(raw, 1))
            self.assertTrue(model.retry_on_resume(raw))
            self.assertEqual(4, rate_limit_delay({"http_status": 429}, 1))
            await api.close()

    async def test_offline_study_needs_only_selected_model_key(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / "research.db")
            try:
                store.create("s", "Read local papers", {"provider": "deepseek"})
                service, clients = online_service(
                    store, "s", {"DEEPSEEK_API_KEY": "fixture"}
                )
                self.assertEqual("deepseek-flash", service.harness.model.model)
                await service.close()
                for client in clients:
                    await client.close()
            finally:
                store.close()

    def test_unknown_model_needs_explicit_capacities_and_no_gateway(self):
        with self.assertRaises(ValueError):
            model_settings({"provider": "openai", "model": "unregistered"})
        with self.assertRaises((ValueError, KeyError)):
            model_settings({"provider": "gateway"})
        with self.assertRaises(ValueError):
            model_settings({"provider": "openai", "region": "unregistered"})
        settings = model_settings(
            {
                "provider": "openai",
                "model": "account-model",
                "context_tokens": 200000,
                "max_tokens": 10000,
            }
        )
        self.assertEqual("account-model", settings[1])

    def test_credentials_missing_file_and_environment_precedence(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.dict(
                "os.environ", {"OPENAI_API_KEY": "environment-fixture"}, clear=True
            ),
        ):
            path = Path(directory) / ".env"
            self.assertEqual(
                {"OPENAI_API_KEY": "environment-fixture"}, credentials(path)
            )
            path.write_text(
                'OPENAI_API_KEY="file-fixture"\nOTHER_SECRET=ignored', encoding="utf-8"
            )
            self.assertEqual(
                {"OPENAI_API_KEY": "environment-fixture"}, credentials(path)
            )

    async def test_chat_usage_only_chunk_and_tool_reassembly(self):
        from epivra.adapters import JsonAPI

        chunks = [
            {
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "tool_calls": [
                                {
                                    "index": 0,
                                    "id": "c1",
                                    "function": {
                                        "name": "read_artifact_range",
                                        "arguments": "{",
                                    },
                                }
                            ]
                        },
                    }
                ]
            },
            {
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "tool_calls": [
                                {
                                    "index": 0,
                                    "function": {"arguments": '"ref":"original"}'},
                                }
                            ]
                        },
                        "finish_reason": "tool_calls",
                    }
                ]
            },
            {"choices": [], "usage": {"prompt_tokens": 55, "completion_tokens": 20}},
        ]
        events = "".join("data: " + json.dumps(chunk) + "\n\n" for chunk in chunks)
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, text=events + "data: [DONE]\n\n")
            )
        ) as client:
            api = JsonAPI("https://api.openai.com/v1", "fixture", client)
            model = ChatCompletions(
                api,
                "fixture-model",
                provider="openai",
                context_tokens=200000,
                max_tokens=10000,
                stream=True,
            )
            raw = await model.complete({"wire": model.prepare(CONTEXT, None)})
            self.assertEqual(55, raw["data"]["usage"]["prompt_tokens"])
            self.assertEqual(
                {"ref": "original"}, model.decode(raw)["calls"][0]["arguments"]
            )
