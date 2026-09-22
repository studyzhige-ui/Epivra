"""Lossless read delivery and rollback regressions. No provider requests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from research_fixture import prepare_basis

from epivra.adapters import DeepSeek
from epivra.context import fit_read_result
from epivra.domain import Call, ContextCapacity, encode
from epivra.harness import BUILTINS, Harness
from epivra.native_models import _result as native_result
from epivra.review import public_inputs
from epivra.storage import Store


class NoNetwork:
    account = "read-delivery-no-network"


class WireModel(DeepSeek):
    def __init__(self):
        super().__init__(NoNetwork(), max_tokens=2048, context_tokens=1000000)
        self.call = None
        self.requests = []

    async def complete(self, request):
        self.requests.append(request)
        calls = (
            []
            if self.call is None
            else [
                {
                    "id": "call-" + str(len(self.requests)),
                    "type": "function",
                    "function": {
                        "name": self.call.name,
                        "arguments": encode(self.call.arguments),
                    },
                }
            ]
        )
        return {
            "http_status": 200,
            "data": {
                "choices": [
                    {
                        "finish_reason": "tool_calls" if calls else "stop",
                        "message": {
                            "role": "assistant",
                            "content": "",
                            "tool_calls": calls,
                        },
                    }
                ],
                "usage": {
                    "prompt_tokens": 1,
                    "completion_tokens": 1,
                    "total_tokens": 2,
                },
            },
        }


class FitTests(unittest.TestCase):
    def test_exact_encoded_envelope_and_terminal_cursor(self):
        text = '\\"\n😀汉e\u0301' * 3000

        def page(n):
            return {
                "text": text[:n],
                "end": n,
                "next_offset": n if n < len(text) else None,
            }

        for capacity in (200, 1000, 12000, 100000):
            result = fit_read_result(page, len(text), capacity)
            self.assertLessEqual(len(encode(result)), capacity)
            self.assertEqual(text[: result["end"]], result["text"])
            self.assertGreater(result["end"], 0)
        self.assertEqual(page(len(text)), fit_read_result(page, len(text), 100000))

    def test_impossible_metadata_does_not_return_nonadvancing_page(self):
        with self.assertRaises(ContextCapacity):
            fit_read_result(
                lambda n: {"essential": "x" * 300, "text": "a" * n}, 50, 200
            )
        self.assertEqual(
            {"text": "", "next_offset": None},
            fit_read_result(lambda n: {"text": "", "next_offset": None}, 0, 100),
        )


class DeliveryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.db = Path(self.folder.name) / "research.db"
        self.store = Store(self.db)
        c = self.store.create(
            "s",
            "Answer the original question with evidence; no default length requirement.",
            {},
        )
        plan = self.store.put(
            "s", "plan", {"text": "Use original evidence."}, (c.direction,)
        )
        self.control = self.store.command(
            "s", "approve", c.ref, "approve", {"plan": plan.ref}
        )
        self.lead = self.store.work("s", self.control.ref, "lead", "Coordinate")
        self.inv = self.child("investigator", "Investigate")
        self.model = WireModel()
        self.h = Harness(self.store, self.model)

    async def asyncTearDown(self):
        self.store.close()
        self.folder.cleanup()

    def child(self, role, task, refs=()):
        return self.store.work(
            "s", self.control.ref, role, task, tuple(refs), self.lead.ref
        )

    async def call(self, work, tool, args):
        if tool == "draft_report":
            prepare_basis(self.store, work)
        self.model.call = Call(tool, args)
        await self.h.step("s", work.ref)
        return self.h._steps("s", "observation", work.ref)[-1]

    def assert_public_delivery(self, work, observation):
        public = list(public_inputs(self.h._request("s", work)))
        delivered = [
            v["result"]
            for v in public
            if v.get("observation_ref") == observation.ref and "result" in v
        ]
        self.assertEqual([observation.body["result"]], delivered)
        self.assertLessEqual(len(encode(delivered[0])), self.model.context_tokens - self.model.max_tokens)
        self.assertEqual(
            delivered[0],
            native_result({**observation.body, "_ref": observation.ref})["result"],
        )

    async def test_default_source_pages_arrive_verbatim_with_exact_selections(self):
        text = ('甲"\\\n\n' + "证据与条件😀e\u0301\r\n\r\n") * 900
        source = self.store.put(
            "s",
            "source",
            {"text": text, "origin": "fixture.txt", "coverage": "partial"},
        )
        offset, collected = 0, []
        while offset is not None:
            obs = await self.call(
                self.inv, "read_source", {"ref": source.ref, "offset": offset}
            )
            self.assertIsNone(obs.body["failure"])
            result = obs.body["result"]
            self.assert_public_delivery(self.inv, obs)
            self.assertEqual(text[result["offset"] : result["end"]], result["text"])
            self.assertEqual("partial", result["coverage"])
            for item in result["selections"]:
                ref, start, end = item["selection"].split(":")
                self.assertEqual(source.ref, ref)
                self.assertTrue(offset <= int(start) < int(end) <= result["end"])
            collected.append(result["text"])
            self.assertTrue(
                result["next_offset"] is None or result["next_offset"] > offset
            )
            offset = result["next_offset"]
        self.assertEqual(text, "".join(collected))

    async def test_artifact_reader_never_returns_another_pointer_for_its_own_page(self):
        self.model.context_tokens = 60000
        body = {
            "text": '\\"\n资料😀' * 4000,
            "conditions": ["retain", "counterevidence"],
        }
        note = self.store.put("s", "note", body)
        obs = await self.call(self.inv, "read_artifact", {"ref": note.ref})
        result = obs.body["result"]
        self.assertEqual("canonical-json", result["encoding"])
        self.assert_public_delivery(self.inv, obs)
        collected = [result["text"]]
        offset = result["next_offset"]
        while offset is not None:
            obs = await self.call(
                self.inv, "read_artifact_range", {"ref": note.ref, "offset": offset}
            )
            result = obs.body["result"]
            self.assert_public_delivery(self.inv, obs)
            self.assertGreater(result["end"], offset)
            collected.append(result["text"])
            offset = result["next_offset"]
        self.assertEqual(encode(body), "".join(collected))

    async def test_saved_oversized_observation_can_be_recovered_without_nested_redirect(
        self,
    ):
        old = self.store.observation(
            "s",
            self.inv.ref,
            self.control.epoch,
            {"tool": "read_source", "result": {"ref": "a" * 64, "text": '"' * 20000}},
        )
        obs = await self.call(self.inv, "read_artifact_range", {"ref": old.ref})
        self.assert_public_delivery(self.inv, obs)
        self.assertEqual(old.ref, obs.body["result"]["ref"])
        self.assertGreater(obs.body["result"]["end"], 0)

    async def test_small_reads_keep_exact_content_and_requested_upper_bound(self):
        source = self.store.put("s", "source", {"text": "abcdefg", "origin": "small"})
        obs = await self.call(
            self.inv, "read_source", {"ref": source.ref, "offset": 2, "limit": 3}
        )
        self.assertEqual("cde", obs.body["result"]["text"])
        self.assertEqual(5, obs.body["result"]["next_offset"])
        self.assert_public_delivery(self.inv, obs)
        eof = await self.call(
            self.inv, "read_source", {"ref": source.ref, "offset": 999}
        )
        self.assertEqual("", eof.body["result"]["text"])
        self.assertIsNone(eof.body["result"]["next_offset"])

    async def test_large_draft_page_reaches_model_and_honors_explicit_limit(self):
        await self.call(self.inv, "finish_work", {"text": "Investigation complete", "refs": []})
        writer = self.child("writer", "Write")
        text = "Original author text.\n" * 3000
        saved = await self.call(writer, "draft_report", {"text": text, "evidence": []})
        self.assertIsNone(saved.body["failure"])
        page = await self.call(writer, "read_draft", {})
        self.assertEqual(text, page.body["result"]["text"])
        self.assertGreater(len(page.body["result"]["text"]), 12000)
        self.assert_public_delivery(writer, page)
        small = await self.call(writer, "read_draft", {"offset": 2, "limit": 7})
        self.assertEqual(text[2:9], small.body["result"]["text"])
        self.assertEqual(9, small.body["result"]["next_offset"])

    async def test_role_permissions_and_removed_optional_actions(self):
        for name in ("search_sources", "read_manuscript", "revise_report"):
            self.assertNotIn(name, BUILTINS)
        source = self.store.put(
            "s", "source", {"text": "private to source-reading roles"}
        )
        denied = await self.call(self.lead, "read_artifact", {"ref": source.ref})
        self.assertIsNone(denied.body["failure"])
        self.assertEqual(source.body["text"], denied.body["result"]["body"]["text"])

    async def test_real_read_selection_remains_savable_as_exact_quote(self):
        source = self.store.put(
            "s",
            "source",
            {"text": "Known condition.\n\nPossible counterexample.", "origin": "q.txt"},
        )
        result = (await self.call(self.inv, "read_source", {"ref": source.ref})).body[
            "result"
        ]
        chosen = result["selections"][1]
        saved = await self.call(
            self.inv,
            "record_evidence",
            {"selection": chosen["selection"], "text": "counterexample"},
        )
        self.assertIsNone(saved.body["failure"])
        note = self.store.get("s", saved.body["result"]["ref"])
        self.assertEqual("Possible counterexample.", note.body["quote"])

    async def test_delivered_receipt_survives_reopen(self):
        source = self.store.put("s", "source", {"text": "original " * 3000})
        obs = await self.call(self.inv, "read_source", {"ref": source.ref})
        self.store.close()
        self.store = Store(self.db)
        self.h = Harness(self.store, self.model)
        self.assert_public_delivery(self.inv, obs)

    async def test_report_page_does_not_imply_acceptance_before_actual_delivery(self):
        self.model.context_tokens = 100000
        text = "事实与限制" * 12000
        report = self.store.put(
            "s", "report", {"text": text, "evidence": []}, (self.control.direction,)
        )
        reviewer = self.child("reviewer", "Review all", [report.ref])
        bad = await self.call(
            reviewer, "submit_review", {"reason": "claim", "defects": []}
        )
        self.assertIsNotNone(bad.body["failure"])
        page = await self.call(reviewer, "read_report", {})
        self.assert_public_delivery(reviewer, page)
        with self.assertRaisesRegex(ValueError, "has not reached"):
            self.store.require_report_delivery("s", reviewer.ref, report.ref)
        self.assertEqual([], self.store.list("s", "publication"))

    async def test_atomic_report_and_receipt_fix_is_retained(self):
        finding = self.store.put(
            "s",
            "work_result",
            {"text": "Finding", "producer": self.inv.ref},
            (self.inv.ref,),
        )
        writer = self.child("writer", "Write original task", [finding.ref])
        real_put = self.store._put

        def faulty(study, kind, *args, **kwargs):
            if kind == "draft_saved":
                raise ValueError("receipt persistence failed")
            return real_put(study, kind, *args, **kwargs)

        with patch.object(self.store, "_put", side_effect=faulty):
            obs = await self.call(
                writer, "draft_report", {"text": "A supported report", "evidence": []}
            )
        self.assertIsNotNone(obs.body["failure"])
        self.assertEqual([], self.store.list("s", "report"))
        self.assertFalse(self.h.finished("s", writer.ref))


if __name__ == "__main__":
    unittest.main()
