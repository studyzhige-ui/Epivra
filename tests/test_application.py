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
    async def test_actual_local_material_reaches_report_through_tools(self):
        corpus = Path(self.tmp.name) / "corpus"
        corpus.mkdir()
        (corpus / "evidence.txt").write_text(
            "Measured value: 17; limited sample.", encoding="utf-8"
        )
        store = self.store
        store.create("s", "Read user evidence", {"local_roots": [str(corpus)]})
        source_ref = None
        report_ref = None

        class LocalModel:
            identity = "offline-local-closed-loop"

            async def complete(inner, request):
                nonlocal source_ref, report_ref
                observations = [item.get("body", {}) for item in request["context"]]
                results = {o["tool"]: o["result"] for o in observations if "tool" in o}
                if "propose_plan" in request["tools"]:
                    call = Call(
                        "propose_plan", {"text": "Read and check the user material"}
                    )
                elif "submit_review" in request["tools"]:
                    if "read_artifact" not in results:
                        call = Call(
                            "read_artifact", {"ref": request["inputs"][0]["ref"]}
                        )
                    elif "read_source" not in results:
                        call = Call(
                            "read_source",
                            {"ref": source_ref, "offset": 0, "limit": 1000},
                        )
                    else:
                        self.assertIn("limited sample", results["read_source"]["text"])
                        call = Call(
                            "submit_review",
                            {
                                "accepted": True,
                                "reason": "Value and limitation match",
                                "checks": [
                                    {
                                        "claim": "The value is 17, with a limited sample.",
                                        "evidence": [source_ref],
                                        "assessment": "Matches measured value and limitation",
                                        "requires_revision": False,
                                    }
                                ],
                            },
                        )
                elif any("review_available" in o for o in observations):
                    review = next(o for o in observations if "review_available" in o)
                    call = Call(
                        "publish_report",
                        {"report": report_ref, "review": review["review_available"]},
                    )
                elif "discover_local" not in results:
                    call = Call("discover_local", {"root": str(corpus)})
                elif "read_catalog" not in results:
                    call = Call(
                        "read_catalog",
                        {
                            "ref": results["discover_local"]["ref"],
                            "offset": 0,
                            "limit": 10,
                        },
                    )
                elif "snapshot_local" not in results:
                    call = Call(
                        "snapshot_local",
                        {
                            "catalog": results["discover_local"]["ref"],
                            "path": results["read_catalog"]["entries"][0]["path"],
                        },
                    )
                elif "read_source" not in results:
                    source_ref = results["snapshot_local"]["ref"]
                    call = Call(
                        "read_source", {"ref": source_ref, "offset": 0, "limit": 1000}
                    )
                else:
                    self.assertIn("17", results["read_source"]["text"])
                    call = Call(
                        "draft_report",
                        {
                            "text": "The value is 17, with a limited sample.",
                            "evidence": [source_ref],
                        },
                    )
                if "draft_report" in results:
                    report_ref = results["draft_report"]["ref"]
                    if call.name == "publish_report":
                        call.arguments["report"] = report_ref
                return Reply("", (call,)).to_json()

        service = ResearchService(store, Harness(store, LocalModel()))
        await service.run("s")
        c = store.control("s")
        store.command(
            "s", "approve", c.ref, "approve", {"plan": store.list("s", "plan")[-1].ref}
        )
        await asyncio.wait_for(service.run("s"), 3)
        self.assertFalse(service.errors)
        self.assertEqual(1, len(store.list("s", "publication")))
        self.assertEqual(1, len(store.list("s", "source")))

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
                    call = Call(
                        "propose_plan", {"text": "Read sources and check claims"}
                    )
                elif "submit_review" in tools:
                    call = Call(
                        "submit_review",
                        {
                            "accepted": True,
                            "reason": "Checked",
                            "checks": [
                                {
                                    "claim": "Limited result supported by the observed source.",
                                    "evidence": [source.ref],
                                    "assessment": "One observation only",
                                    "requires_revision": False,
                                }
                            ],
                        },
                    )
                elif store.list("s", "review"):
                    report = store.list("s", "report")[-1]
                    review = store.list("s", "review")[-1]
                    call = Call(
                        "publish_report", {"report": report.ref, "review": review.ref}
                    )
                else:
                    call = Call(
                        "draft_report",
                        {
                            "text": "Limited result supported by the observed source.",
                            "evidence": [source.ref],
                        },
                    )
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
                    return Reply(
                        "", (Call("save_note", {"text": "old", "refs": []}),)
                    ).to_json()
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
        source = store.put(
            "s", "source", {"text": "x" * 30000 + "rare counterevidence"}
        )
        work = store.work("s", c.ref, "planner", "inspect")

        class Model:
            identity = "offline-range"

            async def complete(inner, request):
                return Reply(
                    "",
                    (
                        Call(
                            "read_source",
                            {
                                "ref": source.ref,
                                "offset": 30000,
                                "limit": 100,
                            },
                        ),
                    ),
                ).to_json()

        harness = Harness(store, Model(), context_chars=8000)
        await harness.step("s", work.ref)
        body = store.list("s", "observation")[-1].body["result"]
        self.assertEqual("rare counterevidence", body["text"])
        self.assertEqual(30000, body["offset"])


class CollaborationTests(unittest.IsolatedAsyncioTestCase):
    async def test_delegated_work_uses_independent_context_and_bounded_concurrency(
        self,
    ):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder) / "study.db")
            try:
                c = store.create("s", "Compare two explanations", {})
                plan = store.put(
                    "s", "plan", {"text": "Investigate both"}, (c.direction,)
                )
                store.command("s", "approve", c.ref, "approve", {"plan": plan.ref})
                seen = []
                active = 0
                peak = 0
                root_calls = 0

                class Model:
                    identity = "offline-collaboration"

                    async def complete(inner, request):
                        nonlocal active, peak, root_calls
                        if "finish_investigation" in request["tools"]:
                            active += 1
                            peak = max(peak, active)
                            seen.append(request)
                            await asyncio.sleep(0.01)
                            active -= 1
                            return Reply(
                                "",
                                (
                                    Call(
                                        "finish_investigation",
                                        {
                                            "text": request["task"] + " result",
                                            "refs": [],
                                        },
                                    ),
                                ),
                            ).to_json()
                        root_calls += 1
                        if root_calls == 1:
                            return Reply(
                                "",
                                tuple(
                                    Call(
                                        "delegate_research",
                                        {
                                            "task": f"Independent question {i}",
                                            "refs": [],
                                        },
                                    )
                                    for i in range(5)
                                ),
                            ).to_json()
                        results = [
                            x
                            for x in request["context"]
                            if "investigation_result" in x.get("body", {})
                        ]
                        self.assertEqual(5, len(results))
                        c = store.control("s")
                        store.command("s", "pause-done", c.ref, "pause")
                        return Reply("", ()).to_json()

                service = ResearchService(store, Harness(store, Model()), concurrency=2)
                await asyncio.wait_for(service.run("s"), 3)
                self.assertEqual(2, peak)
                self.assertEqual(5, len(seen))
                self.assertEqual(5, len({r["task"] for r in seen}))
                self.assertTrue(all(r["memory"] is None for r in seen))
                self.assertTrue(
                    all("delegate_research" not in r["tools"] for r in seen)
                )
                self.assertEqual(5, len(store.list("s", "work_result")))
            finally:
                store.close()

    async def test_same_epoch_conflict_is_not_retried_forever(self):
        from deep_research_agent.domain import Conflict

        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder) / "study.db")
            try:
                store.create("s", "Plan", {})

                class Model:
                    identity = "conflict-fixture"

                    async def complete(inner, request):
                        raise Conflict("deterministic identity conflict")

                service = ResearchService(store, Harness(store, Model()))
                await asyncio.wait_for(service.run("s"), 1)
                self.assertEqual("Conflict", service.errors["s"])
            finally:
                store.close()
