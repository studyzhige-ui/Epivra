"""Actual model-bound input and read delivery, with offline provider responses."""

import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from research_fixture import prepare_basis
from test_native_models import anthropic_response, gemini_response

from epivra.adapters import DeepSeek
from epivra.domain import Call, encode, identity, input_capacity
from epivra.harness import Harness
from epivra.native_models import Anthropic, Gemini
from epivra.review import public_inputs
from epivra.storage import Store


def model_fixture(protocol, source, capacity):
    api = SimpleNamespace(account="capacity-offline")
    if protocol == "chat":
        model = DeepSeek(api, context_tokens=capacity, max_tokens=1024)
        raw = {"http_status": 200, "data": {
            "choices": [{"finish_reason": "tool_calls", "message": {
                "role": "assistant", "content": "", "tool_calls": [{
                    "id": "read", "type": "function", "function": {
                        "name": "read_source", "arguments": encode({"ref": source}),
                    },
                }],
            }}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 10},
        }}
    elif protocol == "anthropic":
        model = Anthropic(api, "fixture", context_tokens=capacity, max_tokens=1024)
        raw = anthropic_response()
        raw["data"]["content"][-1]["input"] = {"ref": source}
    else:
        model = Gemini(api, "fixture", context_tokens=capacity, max_tokens=1024)
        raw = gemini_response()
        raw["data"]["candidates"][0]["content"]["parts"][-1]["functionCall"]["args"] = {"ref": source}
    model.complete = AsyncMock(return_value=raw)
    return model


def delivered(request, ref):
    for value in public_inputs(request):
        if value.get("observation_ref") == ref and "result" in value:
            return value["result"]
        for item in value.get("context", []):
            if item["ref"] == ref and "body" in item:
                return item["body"]["result"]
    return None


class ModelCapacityTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = Path(self.folder.name) / "state.db"
        self.store = Store(self.path)
        c = self.store.create("s", "Inspect original evidence", {})
        plan = self.store.put("s", "plan", {"text": "Read"}, (c.direction,))
        self.c = self.store.command("s", "approve", c.ref, "approve", {"plan": plan.ref})
        self.lead = self.store.work("s", self.c.ref, "lead", "Coordinate")
        self.text = '汉字😀\\"\n' * 20000
        self.source = self.store.put("s", "source", {"text": self.text})

    async def asyncTearDown(self):
        self.store.close()
        self.folder.cleanup()

    async def test_large_pages_survive_each_protocol_and_forced_history_rebuild(self):
        for protocol in ("chat", "anthropic", "gemini"):
            with self.subTest(protocol=protocol):
                model = model_fixture(protocol, self.source.ref, 1000000)
                h = Harness(self.store, model)
                work = self.store.work("s", self.c.ref, "investigator", protocol, owner=self.lead.ref)
                await h.step("s", work.ref)
                observation = h._steps("s", "observation", work.ref)[-1]
                result = observation.body["result"]
                self.assertNotIn("error", result)
                self.assertGreater(len(result["text"]), 12000)
                self.assertEqual(self.text[:result["end"]], result["text"])
                continued = h._request("s", work)
                self.assertEqual(result, delivered(continued, observation.ref))
                # Make only the old private history too large. The source page and
                # essential public request still fit, so rebuilding must retain it.
                step = h._steps("s", "step", work.ref)[-1]
                original_get = h._result
                raw = original_get("s", identity("model", work.ref, step.ref))
                if protocol == "chat":
                    raw["data"]["choices"][0]["message"]["content"] = "old" * 1000000
                elif protocol == "anthropic":
                    raw["data"]["content"][0]["thinking"] = "old" * 1000000
                else:
                    raw["data"]["candidates"][0]["content"]["parts"][0]["text"] = "old" * 1000000
                h._result = lambda *args: raw
                rebuilt = h._request("s", work)
                self.assertEqual("rebuilt", rebuilt["wire"]["window_mode"])
                self.assertEqual(result, delivered(rebuilt, observation.ref))
                self.assertLessEqual(rebuilt["wire"]["estimated_input_tokens"], input_capacity(model))

    async def test_parallel_roles_and_long_task_fit_actual_remaining_wire_capacity(self):
        small = model_fixture("chat", self.source.ref, 80000)
        large = model_fixture("chat", self.source.ref, 1000000)
        h = Harness(self.store, large, role_models={"investigator": small})
        small_work = self.store.work("s", self.c.ref, "investigator", "t" * 18000, owner=self.lead.ref)
        large_work = self.store.work("s", self.c.ref, "synthesizer", "Inspect", owner=self.lead.ref)
        await asyncio.gather(h.step("s", small_work.ref), h.step("s", large_work.ref))
        pages = []
        for model, work in ((small, small_work), (large, large_work)):
            obs = h._steps("s", "observation", work.ref)[-1]
            result = obs.body["result"]
            self.assertNotIn("error", result)
            request = h._request("s", work)
            self.assertEqual(result, delivered(request, obs.ref))
            self.assertLessEqual(request["wire"]["estimated_input_tokens"], input_capacity(model))
            self.assertGreater(result["end"], 0)
            pages.append(result["end"])
        self.assertGreater(pages[1], pages[0])
        self.assertEqual(1000000, large.context_tokens)
        # Reopening preserves already-paid/read receipts without new model calls.
        self.store.close()
        self.store = Store(self.path)
        restored = Harness(self.store, large, role_models={"investigator": small})
        obs = restored._steps("s", "observation", small_work.ref)[-1]
        self.assertEqual(obs.body["result"], delivered(restored._request("s", small_work), obs.ref))
        self.assertEqual(1, small.complete.await_count)

    async def test_large_memory_uses_complete_model_budget_not_old_quarter_cap(self):
        model = model_fixture("chat", self.source.ref, 1000000)
        h = Harness(self.store, model)
        memory = "working evidence " * 3000
        step = self.store.put("s", "step", {"request": {}, "number": 0}, (self.lead.ref,))
        h._builtin("s", self.lead, self.c.epoch, step.ref, 0,
                   Call("save_memory", {"text": memory, "refs": []}))
        request = h._request("s", self.lead)
        self.assertEqual(memory, request["memory"]["body"]["text"])
        self.assertGreater(len(encode(request)), 48000)
        self.assertLessEqual(request["wire"]["estimated_input_tokens"], input_capacity(model))

    async def test_shared_state_growth_recovers_pending_page_without_handle_loop(self):
        source = self.store.put("s", "source", {"text": "x" * 500000})
        model = model_fixture("chat", source.ref, 80000)
        h = Harness(self.store, model)
        await h.step("s", self.lead.ref)
        original = h._steps("s", "observation", self.lead.ref)[-1]
        self.assertEqual(original.body["result"], delivered(h._request("s", self.lead), original.ref))
        prepare_basis(self.store, self.lead)
        changed = h._request("s", self.lead, prepare_wire=False)
        self.assertIsNone(delivered(changed, original.ref))
        self.assertTrue(any(item["ref"] == original.ref and item.get("body_omitted")
                            for item in changed["context"]))
        raw = model.complete.return_value
        function = raw["data"]["choices"][0]["message"]["tool_calls"][0]["function"]
        function["name"] = "read_artifact_range"
        function["arguments"] = encode({"ref": original.ref})
        await h.step("s", self.lead.ref)
        recovered = h._steps("s", "observation", self.lead.ref)[-1]
        result = recovered.body["result"]
        self.assertNotIn("error", result)
        self.assertGreater(result["end"], 0)
        self.assertEqual(result, delivered(h._request("s", self.lead), recovered.ref))
        # Force history rebuilding after the recovery: the new body still fits.
        raw["data"]["choices"][0]["message"]["content"] = "old" * 1000000
        h._result = lambda *args: raw
        rebuilt = h._request("s", self.lead)
        self.assertEqual("rebuilt", rebuilt["wire"]["window_mode"])
        self.assertEqual(result, delivered(rebuilt, recovered.ref))
        self.assertLessEqual(rebuilt["wire"]["estimated_input_tokens"], input_capacity(model))
        self.assertEqual(2, model.complete.await_count)
