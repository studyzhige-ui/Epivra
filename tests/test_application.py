from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

from deep_research_agent.application import ResearchService
from deep_research_agent.domain import Call, Reply
from deep_research_agent.harness import Harness
from deep_research_agent.storage import Store


class WorkflowTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / "research.db")

    async def asyncTearDown(self):
        self.store.close()
        self.tmp.cleanup()

    async def test_plan_approval_report_independent_review_and_publication(self):
        store = self.store
        store.create("s", "Compare the evidence", {"network": False})
        source = store.put("s", "source", {"text": "One measured observation"})

        class ScriptedResearcher:
            identity = "offline-integration"
            calls = 0

            async def complete(inner, request):
                inner.calls += 1
                tools = request["tools"]
                if "propose_plan" in tools:
                    call = Call("propose_plan", {"text": "Read sources and check claims"})
                elif "submit_review" in tools:
                    call = Call("submit_review", {"accepted": True, "reason": "Checked"})
                elif store.list("s", "review"):
                    report = store.list("s", "report")[-1]
                    review = store.list("s", "review")[-1]
                    call = Call("publish_report", {"report": report.ref, "review": review.ref})
                else:
                    call = Call("draft_report", {
                        "text": "Limited result supported by the observed source.",
                        "evidence": [source.ref],
                    })
                return Reply("", (call,)).to_json()

        model = ScriptedResearcher()
        harness = Harness(store, model)
        service = ResearchService(store, harness)
        await service.run("s")
        self.assertEqual(1, model.calls)
        self.assertFalse(store.control("s").approved)
        self.assertEqual([], store.list("s", "publication"))
        plan = store.list("s", "plan")[-1]
        c = store.control("s")
        store.command("s", "approve", c.ref, "approve", {"plan": plan.ref})
        await service.run("s")
        self.assertEqual(4, model.calls)
        self.assertEqual(1, len(store.list("s", "publication")))
        self.assertEqual(3, len(store.list("s", "work")))
        await service.run("s")
        self.assertEqual(4, model.calls)

    async def test_user_steering_during_call_continues_without_extra_resume(self):
        store = self.store
        c = store.create("s", "Original", {})
        plan = store.put("s", "plan", {"text": "plan"}, (c.direction,))
        store.command("s", "approve", c.ref, "approve", {"plan": plan.ref})
        entered, release = asyncio.Event(), asyncio.Event()

        class Model:
            identity = "offline-steer"
            seen = []

            async def complete(inner, request):
                inner.seen.append(request["direction"]["request"])
                if len(inner.seen) == 1:
                    entered.set()
                    await release.wait()
                    return Reply("", (Call("save_note", {"text": "old", "refs": []}),)).to_json()
                current = store.control("s")
                store.command("s", "pause-end", current.ref, "pause")
                return Reply("", ()).to_json()

        model = Model()
        service = ResearchService(store, Harness(store, model))
        service.start("s")
        await entered.wait()
        c = store.control("s")
        store.command("s", "steer", c.ref, "steer", {"request": "Revised"})
        release.set()
        await asyncio.wait_for(service.tasks["s"], 2)
        self.assertEqual(["Original", "Revised"], model.seen)
        self.assertEqual([], store.list("s", "note"))

    async def test_oversize_source_can_be_read_in_bounded_ranges(self):
        store = self.store
        c = store.create("s", "Read", {})
        source = store.put("s", "source", {"text": "x" * 30000 + "rare counterevidence"})
        work = store.work("s", c.ref, "planner", "inspect")

        class Model:
            identity = "offline-range"

            async def complete(inner, request):
                return Reply("", (Call("read_source", {
                    "ref": source.ref, "offset": 30000, "limit": 100,
                }),)).to_json()

        harness = Harness(store, Model(), context_chars=8000)
        await harness.step("s", work.ref)
        body = store.list("s", "observation")[-1].body["result"]
        self.assertEqual("rare counterevidence", body["text"])
        self.assertEqual(30000, body["offset"])
