from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from research_fixture import prepare_basis

from epivra.domain import Call, Conflict, Reply
from epivra.harness import Harness
from epivra.storage import Store


class Model:
    context_tokens = 49024
    max_tokens = 1024
    identity = "argument-check-fixture"

    def __init__(self):
        self.calls = ()
        self.count = 0

    async def complete(self, request):
        self.count += 1
        return Reply("", self.calls).to_json()


class ArgumentCheckTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = Path(self.folder.name) / "state.db"
        self.store = Store(self.path)
        c = self.store.create("s", "Explain the supplied findings", {})
        plan = self.store.put("s", "plan", {"text": "Investigate"}, (c.direction,))
        self.c = self.store.command(
            "s", "approve", c.ref, "approve", {"plan": plan.ref}
        )
        self.lead = self.store.work("s", self.c.ref, "lead", "Coordinate")
        self.model = Model()
        self.harness = Harness(self.store, self.model)
        inv = self.child("investigator", "Find evidence")
        await self.execute(
            inv, "finish_work", {"text": "Supported finding", "refs": []}
        )
        self.finding = self.harness._steps("s", "work_result", inv.ref)[0]
        writer = self.child("writer", "Write findings", (self.finding.ref,))
        await self.execute(
            writer,
            "draft_report",
            {"text": "Finding with appropriate limits.", "evidence": []},
        )
        self.report = self.store.list("s", "report")[-1]
        completed = await self.execute(writer, "finish_work", {"text": "Ready for review", "refs": [self.report.ref]})
        self.assertIn("ref", completed)

    async def asyncTearDown(self):
        self.store.close()
        self.folder.cleanup()

    def child(self, role, task, refs=(), mode="final"):
        return self.store.work(
            "s", self.c.ref, role, task, refs, self.lead.ref, review_mode=mode
        )

    async def execute(self, work, name, args):
        if name == "draft_report":
            prepare_basis(self.store, work)
        self.model.calls = (Call(name, args),)
        await self.harness.step("s", work.ref)
        return self.harness._steps("s", "observation", work.ref)[-1].body["result"]

    async def completed_check(self):
        check = self.child(
            "reviewer",
            "Check the relationship between evidence and conclusion",
            (self.report.ref,),
            "check",
        )
        result = await self.execute(
            check,
            "finish_work",
            {"text": "核查原成果：该限定与证据范围一致。", "refs": [self.report.ref]},
        )
        return check, self.store.get("s", result["ref"])

    async def test_check_finishes_with_host_report_binding_but_cannot_submit_review(
        self,
    ):
        check = self.child(
            "reviewer", "Check one argument", (self.report.ref,), "check"
        )
        request = self.harness._request("s", check)
        self.assertEqual("check", request["review_mode"])
        self.assertIn("finish_work", request["tools"])
        self.assertNotIn("submit_review", request["tools"])
        denied = await self.execute(
            check, "submit_review", {"reason": "Looks correct", "defects": []}
        )
        self.assertIn("error", denied)
        self.assertFalse(self.harness.finished("s", check.ref))
        result = await self.execute(
            check,
            "finish_work",
            {"text": "The specified argument is supported", "refs": []},
        )
        finding = self.store.get("s", result["ref"])
        self.assertEqual(self.report.ref, finding.body["report"])
        self.assertEqual(check.ref, finding.body["producer"])
        self.assertIn(self.report.ref, finding.parents)
        self.assertTrue(self.harness.finished("s", check.ref))
        self.assertEqual([], self.store.list("s", "review"))
        self.assertEqual([], self.store.list("s", "publication"))

    async def test_final_receives_original_check_and_task_after_restart_then_can_publish(
        self,
    ):
        check, finding = await self.completed_check()
        final = self.child(
            "reviewer", "Evaluate complete report", (self.report.ref, finding.ref)
        )
        self.store.close()
        self.store = Store(self.path)
        self.harness = Harness(self.store, self.model)
        request = self.harness._request("s", final)
        bodies = {a["ref"]: a["body"] for a in request["context"] if "body" in a}
        self.assertEqual(finding.body, bodies[finding.ref])
        self.assertEqual(check.body, bodies[check.ref])
        self.assertIn("submit_review", request["tools"])
        self.assertNotIn("finish_work", request["tools"])
        await self.execute(
            final,
            "submit_review",
            {"reason": "Whole report is supported", "defects": []},
        )
        review = self.store.list("s", "review")[-1]
        await self.execute(
            self.lead,
            "publish_report",
            {"report": self.report.ref, "review": review.ref},
        )
        publication = self.store.list("s", "publication")[-1]
        self.assertEqual(self.report.ref, publication.body["report"])
        self.assertEqual(review.ref, publication.body["review"])

    async def test_check_cannot_transfer_acceptance_but_can_be_revision_input(
        self,
    ):
        _, finding = await self.completed_check()
        other = self.store.put(
            "s",
            "report",
            {"text": "Changed conclusion", "evidence": []},
            (self.c.direction,),
        )
        with self.assertRaises(Conflict):
            self.child("reviewer", "Check revised report", (other.ref, finding.ref))
        writer = self.child(
            "writer", "Inspect this check and its bound source report", (finding.ref, self.report.ref)
        )
        self.assertEqual([finding.ref, self.report.ref], list(writer.body["inputs"]))
        self.assertFalse(self.harness.finished("s", writer.ref))
        self.assertEqual([], self.store.list("s", "review"))
        self.assertEqual([], self.store.list("s", "publication"))

    async def test_forged_accepted_review_from_check_work_cannot_publish(self):
        check, _ = await self.completed_check()
        forged = self.store.put(
            "s",
            "review",
            {
                "accepted": True,
                "work": check.ref,
                "report": self.report.ref,
                "defects": [],
                "reason": "Counterfeit whole-report approval",
            },
            (check.ref, self.report.ref, self.c.direction),
        )
        with self.assertRaises(Conflict):
            self.store.publish(
                "s", self.lead.ref, self.c.epoch, self.report.ref, forged.ref
            )
        self.assertEqual([], self.store.list("s", "publication"))

    async def test_clarification_resumes_same_check_and_keeps_report_version(self):
        check = self.child(
            "reviewer", "Check one unresolved argument", (self.report.ref,), "check"
        )
        await self.execute(
            check,
            "request_clarification",
            {
                "text": "Which population does the conclusion concern?",
                "refs": [self.report.ref],
            },
        )
        question = self.store.clarifications("s", work=check.ref, open_only=True)[0]
        calls = self.model.count
        self.assertEqual("waiting", await self.harness.step("s", check.ref))
        self.assertEqual(calls, self.model.count)
        await self.execute(
            self.lead,
            "answer_clarification",
            {
                "question": question.ref,
                "text": "Use the population in the original task",
                "refs": [self.finding.ref],
            },
        )
        self.store.close()
        self.store = Store(self.path)
        self.harness = Harness(self.store, self.model)
        request = self.harness._request("s", check)
        self.assertEqual("check", request["review_mode"])
        self.assertEqual(self.report.ref, request["review_progress"]["report"])
        result = await self.execute(
            check,
            "finish_work",
            {"text": "The scoped conclusion is supported", "refs": [self.finding.ref]},
        )
        finding = self.store.get("s", result["ref"])
        self.assertEqual(check.ref, finding.body["producer"])
        self.assertEqual(self.report.ref, finding.body["report"])
