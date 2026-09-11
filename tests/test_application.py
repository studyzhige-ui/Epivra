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
    async def test_root_progresses_before_child_finishes_and_wait_survives_restart(
        self,
    ):
        store = self.store
        c = store.create("s", "Investigate", {})
        plan = store.put("s", "plan", {"text": "Investigate"}, (c.direction,))
        store.command("s", "approve", c.ref, "approve", {"plan": plan.ref})
        parent_calls = 0
        child_calls = 0
        interrupted = False

        class Model:
            identity = "cooperative-scheduling"

            async def complete(inner, request):
                nonlocal parent_calls, child_calls, interrupted
                if "finish_work" in request["tools"]:
                    child_calls += 1
                    if store.list("s", "work_wait") and not interrupted:
                        interrupted = True
                        control = store.control("s")
                        store.command("s", "pause", control.ref, "pause")
                    call = (
                        Call("finish_work", {"text": "Evidence", "refs": []})
                        if child_calls >= 5
                        else Call(
                            "save_note", {"text": f"progress {child_calls}", "refs": []}
                        )
                    )
                else:
                    parent_calls += 1
                    if parent_calls == 1:
                        call = Call(
                            "delegate_work",
                            {
                                "role": "investigator",
                                "task": "Long investigation",
                                "refs": [],
                            },
                        )
                    elif parent_calls == 2:
                        self.assertLess(child_calls, 5)
                        call = Call(
                            "wait_for_work",
                            {"refs": [request["delegated_work"][0]["ref"]]},
                        )
                    else:
                        self.assertEqual(3, parent_calls)
                        self.assertTrue(request["delegated_work"][0]["finished"])
                        self.assertTrue(
                            any(
                                "work_result" in x.get("body", {})
                                for x in request["context"]
                            )
                        )
                        control = store.control("s")
                        store.command("s", "done", control.ref, "pause")
                        return Reply("", ()).to_json()
                return Reply("", (call,)).to_json()

        model = Model()
        service = ResearchService(store, Harness(store, model), concurrency=1)
        await asyncio.wait_for(service.run("s"), 3)
        self.assertFalse(service.errors)
        self.assertTrue(interrupted)
        self.assertEqual(2, parent_calls)
        path = store.path
        store.close()
        self.store = store = Store(path)
        control = store.control("s")
        store.command("s", "resume", control.ref, "resume")
        service = ResearchService(store, Harness(store, model), concurrency=1)
        await asyncio.wait_for(service.run("s"), 3)
        self.assertFalse(service.errors)
        self.assertEqual(3, parent_calls)
        self.assertTrue(store.list("s", "work_wait"))

    async def test_actual_local_material_reaches_report_through_tools(self):
        await self._mainline(False)

    async def test_complete_investigation_can_go_directly_to_writer_and_revise(self):
        await self._mainline(True, direct=True)

    async def _mainline(self, reject_once, direct=False):
        answer_role = "investigator" if direct else "synthesizer"
        corpus = Path(self.tmp.name) / "corpus"
        corpus.mkdir()
        (corpus / "evidence.txt").write_text(
            "Measured value: 17; limited sample.", encoding="utf-8"
        )
        store = self.store
        store.create("s", "Read user evidence", {"local_roots": [str(corpus)]})
        source_ref = None

        class LocalModel:
            identity = "offline-mainline"

            async def complete(inner, request):
                nonlocal source_ref
                obs = [x.get("body", {}) for x in request["context"]]
                results = {o["tool"]: o["result"] for o in obs if "tool" in o}
                role = request["role"]
                if "propose_plan" in request["tools"]:
                    calls = [
                        Call(
                            "propose_plan",
                            {
                                "text": "Read and check user evidence",
                                "brief": {
                                    "subject": "User evidence",
                                    "given_context": ["User supplied evidence"],
                                    "questions": ["What does the evidence establish?"],
                                    "material_scope": {
                                        "mode": "case_materials",
                                        "basis": "User supplied case",
                                    },
                                },
                            },
                        )
                    ]
                elif role == "lead":
                    children = request["delegated_work"]
                    unfinished = [w["ref"] for w in children if not w["finished"]]
                    if unfinished:
                        calls = [Call("wait_for_work", {"refs": unfinished})]
                    else:
                        child_results = {
                            store.get("s", o["work"]).body["role"]: o
                            for o in obs
                            if "work_result" in o
                        }
                        next_role, refs, task = "investigator", [], "Measure evidence"
                        if (
                            "reviewer" in child_results
                            and child_results["reviewer"]["work_result"]
                            == max(
                                (o for o in obs if "work_result" in o),
                                key=lambda o: store.get("s", o["work_result"]).seq,
                            )["work_result"]
                        ):
                            review = store.get(
                                "s", child_results["reviewer"]["result"]["ref"]
                            )
                            report = next(
                                ref
                                for ref in review.parents
                                if store.get("s", ref).kind == "report"
                            )
                            if review.body["accepted"]:
                                return Reply(
                                    "",
                                    (
                                        Call(
                                            "publish_report",
                                            {"report": report, "review": review.ref},
                                        ),
                                    ),
                                ).to_json()
                            next_role, refs, task = (
                                "writer",
                                [
                                    child_results[answer_role]["work_result"],
                                    report,
                                    review.ref,
                                ],
                                "Revise wording",
                            )
                        elif "writer" in child_results:
                            next_role, refs = (
                                "reviewer",
                                [child_results["writer"]["result"]["ref"]],
                            )
                        elif "synthesizer" in child_results:
                            next_role, refs = (
                                "writer",
                                [child_results["synthesizer"]["work_result"]],
                            )
                        elif "investigator" in child_results:
                            next_role, refs = (
                                "writer" if direct else "synthesizer",
                                [child_results["investigator"]["work_result"]],
                            )
                        calls = [
                            Call(
                                "delegate_work",
                                {"role": next_role, "task": task, "refs": refs},
                            )
                        ]
                        # Pending work becomes visible on next model step; wait then.
                elif role == "investigator":
                    if "discover_local" not in results:
                        calls = [Call("discover_local", {"root": str(corpus)})]
                    elif "snapshot_local" not in results:
                        calls = [
                            Call(
                                "snapshot_local",
                                {
                                    "catalog": results["discover_local"]["ref"],
                                    "path": "evidence.txt",
                                },
                            )
                        ]
                    elif "read_source" not in results:
                        source_ref = results["snapshot_local"]["ref"]
                        calls = [
                            Call(
                                "read_source",
                                {"ref": source_ref, "offset": 0, "limit": 1000},
                            )
                        ]
                    elif "record_evidence" not in results:
                        calls = [
                            Call(
                                "record_evidence",
                                {
                                    "text": "Observed 17",
                                    "source": source_ref,
                                    "offset": 0,
                                    "quote": "Measured value: 17; limited sample.",
                                    "limits": "limited sample",
                                },
                            )
                        ]
                    else:
                        calls = [
                            Call(
                                "finish_work",
                                {
                                    "text": "17 in a limited sample",
                                    "refs": [
                                        source_ref,
                                        results["record_evidence"]["ref"],
                                    ],
                                },
                            )
                        ]
                elif role == "synthesizer":
                    result = store.get("s", request["inputs"][0]["ref"])
                    self.assertIn("limited sample", result.body["text"])
                    calls = [
                        Call(
                            "finish_work",
                            {
                                "text": "The sample measured 17; no population extrapolation",
                                "refs": [result.ref, source_ref],
                            },
                        )
                    ]
                elif role == "writer":
                    answer = store.get("s", request["inputs"][0]["ref"])
                    self.assertIn("17", answer.body["text"])
                    self.assertIn("sample", answer.body["text"])
                    calls = [
                        Call(
                            "draft_report",
                            {
                                "text": "Measured 17 in a limited sample.",
                                "evidence": [source_ref],
                            },
                        )
                    ]
                else:
                    reject = reject_once and not store.list("s", "review")
                    calls = [
                        Call(
                            "record_review",
                            {
                                "checks": [
                                    {
                                        "unit": 0,
                                        "evidence": [source_ref],
                                        "assessment": "Bounded observation",
                                        "defects": ["Clarify wording"]
                                        if reject
                                        else [],
                                    }
                                ]
                            },
                        ),
                        Call("submit_review", {"reason": "Checked", "defects": []}),
                    ]
                return Reply("", tuple(calls)).to_json()

        service = ResearchService(store, Harness(store, LocalModel()), concurrency=2)
        await asyncio.wait_for(service.run("s"), 3)
        c = store.control("s")
        store.command(
            "s", "approve", c.ref, "approve", {"plan": store.list("s", "plan")[-1].ref}
        )
        await asyncio.wait_for(service.run("s"), 5)
        self.assertFalse(service.errors)
        self.assertEqual(1, len(store.list("s", "publication")))
        self.assertEqual(1, len(store.list("s", "source")))
        roles = [w.body["role"] for w in store.list("s", "work")]
        self.assertEqual(1, roles.count("investigator"))
        self.assertEqual(0 if direct else 1, roles.count("synthesizer"))
        self.assertEqual(2 if reject_once else 1, roles.count("writer"))
        note = store.list("s", "note")[0]
        self.assertEqual("limited sample", note.body["limits"])
        calls_before = len(store.list("s", "step"))
        await service.run("s")
        self.assertEqual(calls_before, len(store.list("s", "step")))

    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / "research.db")

    async def asyncTearDown(self):
        self.store.close()
        self.tmp.cleanup()

    async def test_plan_approval_report_independent_review_and_publication(self):
        await self._mainline(True)

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
        plan = store.put("s", "plan", {"text": "Read"}, (c.direction,))
        c = store.command("s", "approve", c.ref, "approve", {"plan": plan.ref})
        work = store.work("s", c.ref, "investigator", "inspect")

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
                        if "finish_work" in request["tools"]:
                            active += 1
                            peak = max(peak, active)
                            seen.append(request)
                            await asyncio.sleep(0.01)
                            active -= 1
                            return Reply(
                                "",
                                (
                                    Call(
                                        "finish_work",
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
                                        "delegate_work",
                                        {
                                            "role": "investigator",
                                            "task": f"Independent question {i}",
                                            "refs": [],
                                        },
                                    )
                                    for i in range(5)
                                ),
                            ).to_json()
                        if any(not w["finished"] for w in request["delegated_work"]):
                            return Reply(
                                "",
                                (
                                    Call(
                                        "wait_for_work",
                                        {
                                            "refs": [
                                                w["ref"]
                                                for w in request["delegated_work"]
                                                if not w["finished"]
                                            ]
                                        },
                                    ),
                                ),
                            ).to_json()
                        results = [
                            x
                            for x in request["context"]
                            if "work_result" in x.get("body", {})
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
                self.assertTrue(all("delegate_work" not in r["tools"] for r in seen))
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
