import tempfile
import unittest
from pathlib import Path

from epivra.application import ResearchService
from epivra.domain import Call, RepeatedFailure, Reply
from epivra.harness import Harness
from epivra.storage import Store


class RepeatedTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "store.db")
        c = self.store.create("s", "Question", {})
        self.work = self.store.work("s", c.ref, "lead", "Plan")
        self.calls = 0
        self.reply = Reply("", (Call("nonexistent", {"x": 1}),)).to_json()
        test = self

        class Model:
            identity = "failure-test"

            async def complete(self, request):
                test.calls += 1
                return test.reply

        self.model = Model()
        self.h = Harness(self.store, self.model)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    async def rounds(self, n):
        for _ in range(n):
            await self.h.step("s", self.work.ref)

    async def test_repeated_tool_rejected_before_fourth_model_call_after_restart(self):
        await self.rounds(3)
        self.h = Harness(self.store, self.model)
        with self.assertRaises(RepeatedFailure):
            await self.rounds(1)
        self.assertEqual(3, self.calls)
        self.assertEqual(3, len(self.store.list("s", "step")))

    async def test_repeated_protocol_failure(self):
        self.reply = {"unexpected": True}
        await self.rounds(3)
        with self.assertRaises(RepeatedFailure):
            await self.rounds(1)
        self.assertEqual(3, self.calls)

    async def test_changed_operation_and_success_do_not_trigger(self):
        await self.rounds(2)
        self.reply = Reply("", (Call("nonexistent", {"x": 2}),)).to_json()
        await self.rounds(2)
        self.reply = Reply("", (Call("calculate", {"expression": "1+1"}),)).to_json()
        await self.rounds(1)
        self.reply = Reply("", (Call("nonexistent", {"x": 2}),)).to_json()
        await self.rounds(3)
        self.assertEqual(8, self.calls)

    async def test_new_source_and_explicit_resume_allow_fresh_attempt(self):
        await self.rounds(3)
        self.store.put("s", "source", {"text": "New evidence"})
        await self.rounds(3)
        with self.assertRaises(RepeatedFailure):
            await self.rounds(1)
        c = self.store.control("s")
        c = self.store.command("s", "pause-1", c.ref, "pause", {})
        self.store.command("s", "resume-1", c.ref, "resume", {})
        await self.rounds(1)
        self.assertEqual(7, self.calls)

    async def test_failed_child_is_reported_without_repeating_paid_calls(self):
        service = ResearchService(self.store, self.h)
        await self.rounds(3)
        await service._run_child("s", self.work.ref)
        self.assertIn(self.work.ref, service.repeated_failures)
        self.assertEqual("RepeatedFailure", service.work_errors[self.work.ref])
        self.assertEqual(3, self.calls)

    async def test_service_releases_only_repeated_failure_after_new_material(self):
        c = self.store.control("s")
        plan = self.store.put("s", "plan", {"text": "Plan"}, (c.direction,))
        c = self.store.command("s", "approve", c.ref, "approve", {"plan": plan.ref})
        lead = self.store.work(
            "s",
            c.ref,
            "lead",
            "依据当前方向自主研究并交付经过核查的报告。",
            (plan.ref,),
        )
        self.work = self.store.work(
            "s", c.ref, "investigator", "Investigate", (), lead.ref
        )
        unknown = self.store.work(
            "s", c.ref, "investigator", "Unknown paid work", (), lead.ref
        )
        service = ResearchService(self.store, self.h)
        await self.rounds(3)
        await service._run_child("s", self.work.ref)
        service.work_errors[unknown.ref] = "UnknownOutcome"
        self.store.put("s", "source", {"text": "Additional original"})
        step = self.h.step

        async def stop_after_selection(study, ref):
            if ref == lead.ref:
                raise RuntimeError("End this scheduler fixture")
            return await step(study, ref)

        self.h.step = stop_after_selection
        await service._drive("s")
        self.assertEqual(4, self.calls)
        self.assertNotIn(self.work.ref, service.work_errors)
        self.assertEqual("UnknownOutcome", service.work_errors[unknown.ref])
