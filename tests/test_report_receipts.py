"""The report handoff describes committed text, never a stale preflight estimate."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from epivra.domain import Call, Reply
from epivra.harness import Harness
from epivra.review import report_metrics, text_metrics
from epivra.storage import Store


class ScriptedModel:
    identity = "report-receipt-test"

    async def complete(self, request):
        return Reply("", (self.call,)).to_json()


class ReportReceiptTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = Path(self.folder.name) / "research.db"
        self.store = Store(self.path)
        c = self.store.create("s", "Produce a short factual answer.", {})
        p = self.store.put("s", "plan", {"text": "Read evidence"}, (c.direction,))
        self.c = self.store.command("s", "approval", c.ref, "approve", {"plan": p.ref})
        self.lead = self.store.work("s", self.c.ref, "lead", "Coordinate")
        self.model = ScriptedModel()
        self.harness = Harness(self.store, self.model)
        investigator = self.store.work("s", self.c.ref, "investigator", "Investigate", (), self.lead.ref)
        result = await self.execute("finish_work", {"text": "A supported finding", "refs": []}, investigator)
        self.finding_ref = result["ref"]
        self.writer = self.store.work("s", self.c.ref, "writer", "Write", (self.finding_ref,), self.lead.ref)

    async def asyncTearDown(self):
        self.store.close()
        self.folder.cleanup()

    async def execute(self, name, args, work=None):
        self.model.call = Call(name, args)
        await self.harness.step("s", (work or self.writer).ref)
        return self.store.list("s", "observation")[-1].body["result"]

    async def test_stale_preflight_not_copied_into_committed_handoff(self):
        measured = await self.execute("measure_text", {"text": "Draft", "evidence": []})
        text = "Draft\n\nAppendix with additional author content."
        receipt = await self.execute("draft_report", {"text": text, "evidence": [], "handoff": "Old draft had 5 characters"})
        report = self.store.get("s", receipt["ref"])
        result = self.harness._steps("s", "work_result", self.writer.ref)[-1]
        self.assertEqual(report_metrics(report.body), receipt["report_metrics"])
        self.assertEqual(receipt["report_metrics"], result.body["report_metrics"])
        self.assertEqual(report.ref, result.body["ref"])
        self.assertNotEqual(measured["body"], result.body["report_metrics"]["body"])
        self.assertEqual(text_metrics(text), result.body["report_metrics"]["body"])
        self.assertNotIn("Old draft", report.body["text"])
        self.assertTrue(self.harness.finished("s", self.writer.ref))

    async def test_rendered_citations_match_reviewer_receipt(self):
        source = self.store.put("s", "source", {"origin": "source.txt", "text": "Count: 17."})
        args = {"text": "17 entries[[cite:" + source.ref + "]].", "evidence": [source.ref]}
        before = await self.execute("measure_text", args)
        receipt = await self.execute("draft_report", args)
        reviewer = self.store.work("s", self.c.ref, "reviewer", "Review", (receipt["ref"],), self.lead.ref)
        read = await self.execute("read_report", {"offset": 0, "limit": 20}, reviewer)
        self.assertEqual(before, receipt["report_metrics"])
        self.assertEqual(receipt["report_metrics"], read["report_metrics"])
        self.assertLess(before["body"]["characters"], before["characters"])

    async def test_unmeasured_unicode_and_author_notes_are_not_stripped(self):
        text = "# 标题\n\n| A | B |\n|---|---|\n| 😀 | e\u0301 |\n\nAuthor note\t "
        receipt = await self.execute("draft_report", {"text": text, "evidence": []})
        report = self.store.get("s", receipt["ref"])
        self.assertEqual(text, report.body["text"])
        self.assertEqual(text_metrics(text), receipt["report_metrics"]["body"])
        self.assertEqual(1, len(self.store.list("s", "report")))

    async def test_no_automatic_length_gate_or_model_supplied_metrics(self):
        text = "Long report " * 100
        receipt = await self.execute("draft_report", {"text": text, "evidence": []})
        self.assertEqual(len(text), receipt["report_metrics"]["characters"])
        self.assertEqual(2, len(self.store.list("s", "work_result")))
        other = self.store.work("s", self.c.ref, "writer", "Other", (self.finding_ref,), self.lead.ref)
        error = await self.execute("draft_report", {"text": "x", "evidence": [], "report_metrics": {}}, other)
        self.assertIn("error", error)
        self.assertEqual(1, len(self.store.list("s", "report")))

    async def test_invalid_citation_creates_no_report_or_receipt(self):
        error = await self.execute("draft_report", {"text": "Claim[[cite:" + "0" * 64 + "]].", "evidence": []})
        self.assertIn("error", error)
        self.assertEqual([], self.store.list("s", "report"))
        self.assertEqual([], self.harness._steps("s", "work_result", self.writer.ref))

    async def test_handoff_survives_reopen_and_reaches_owner(self):
        receipt = await self.execute("draft_report", {"text": "Bounded finding", "evidence": []})
        result = self.harness._steps("s", "work_result", self.writer.ref)[-1]
        self.store.close()
        self.store = Store(self.path)
        saved = self.store.get("s", result.ref)
        self.assertEqual(receipt["report_metrics"], saved.body["report_metrics"])
        harness = Harness(self.store, self.model)
        receiver = self.store.work("s", self.c.ref, "lead", "Use the delivered report", (saved.ref,))
        request = harness._request("s", receiver)
        bodies = [x.get("body") for x in request["context"]]
        self.assertIn(saved.body, bodies)


if __name__ == "__main__":
    unittest.main()
