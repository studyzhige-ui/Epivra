"""Actual Harness and scheduler outcomes for sequential manuscript ownership."""
import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from research_fixture import prepare_basis

from epivra.application import ResearchService
from epivra.domain import Call, NotAllowed, Reply
from epivra.harness import Harness
from epivra.storage import Store


class AuthoringRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "state.db"
        self.store = Store(self.path)
        c = self.store.create("s", "Explain the supplied record", {})
        plan = self.store.put("s", "plan", {"text": "Read original"}, (c.direction,))
        self.c = self.store.command("s", "approve", c.ref, "approve", {"plan": plan.ref})
        self.owner = self.store.work("s", self.c.ref, "lead", "Own the approved research", (plan.ref,))
        self.source = self.store.put("s", "source", {"text": "17 registered", "origin": "record.txt"})
        prepare_basis(self.store, self.owner)

    async def asyncTearDown(self):
        self.store.close()
        self.tmp.cleanup()

    async def test_cancelled_inflight_writer_settles_without_adopting_or_resending(self):
        started, release = asyncio.Event(), asyncio.Event()
        calls = []
        source = self.source.ref
        class Model:
            context_tokens = 49024
            max_tokens = 1024
            identity = "late-writer-fixture"
            owner_call = None
            async def complete(self, request):
                calls.append(request["work_ref"])
                if request["role"] == "writer":
                    started.set()
                    await release.wait()
                    return Reply("", (Call("draft_report", {"text": "Late draft", "evidence": [source]}),)).to_json()
                return Reply("", (self.owner_call,)).to_json()
        model = Model()
        h = Harness(self.store, model)
        model.owner_call = Call("delegate_work", {"role": "writer", "task": "Write the report", "refs": [source]})
        await h.step("s", self.owner.ref)
        writer = self.store.writing_author("s")
        service = ResearchService(self.store, h)
        pending = asyncio.create_task(service._run_child("s", writer))
        try:
            await asyncio.wait_for(started.wait(), 2)
            model.owner_call = Call("cancel_work", {"work": writer, "reason": "Owner will complete the manuscript"})
            await h.step("s", self.owner.ref)
            self.assertEqual(self.owner.ref, self.store.writing_author("s"))
        finally:
            release.set()
            await asyncio.wait_for(pending, 2)
        self.assertEqual({}, service.work_errors)
        self.assertEqual([], self.store.list("s", "report"))
        row = self.store.db.execute("SELECT status,result FROM operations WHERE work=?", (writer,)).fetchone()
        self.assertEqual("succeeded", row["status"])
        self.assertIn("Late draft", row["result"])
        self.store.close()
        self.store = Store(self.path)
        self.assertEqual(self.owner.ref, self.store.writing_author("s"))
        with self.assertRaises(NotAllowed):
            await Harness(self.store, model).step("s", writer)
        self.assertEqual(1, calls.count(writer))
        self.assertEqual("cancelled", self.store.matching("s", "work_result", {"producer": writer})[-1].body["status"])

    async def test_blocked_writer_cancellation_stops_error_delivery_and_preserves_history(self):
        writer = self.store.work("s", self.c.ref, "writer", "Write", (), self.owner.ref)
        cancelled, release = asyncio.Event(), asyncio.Event()
        store = self.store
        class Model:
            context_tokens = 49024
            max_tokens = 1024
            identity = "blocked-writer-cancellation"
            async def complete(inner, request):
                if request["role"] == "writer":
                    raise ValueError("Provider fixture failed")
                results = store.matching("s", "work_result", {"producer": writer.ref})
                if results:
                    cancelled.set()
                    await release.wait()
                    return Reply("", ()).to_json()
                if any(o.body.get("blocked") for o in store.list("s", "observation")):
                    return Reply("", (Call("cancel_work", {"work": writer.ref, "reason": "Owner takes over"}),)).to_json()
                return Reply("", (Call("wait_for_work", {"refs": [writer.ref]}),)).to_json()
        service = ResearchService(store, Harness(store, Model()), concurrency=2)
        pending = asyncio.create_task(service.run("s"))
        try:
            await asyncio.wait_for(cancelled.wait(), 3)
            self.assertNotIn(writer.ref, service.status("s")["work_errors"])
            self.assertNotIn(writer.ref, service.repeated_failures)
            result = store.matching("s", "work_result", {"producer": writer.ref})[-1]
            blocked = [o for o in store.list("s", "observation") if o.body.get("blocked")]
            self.assertTrue(blocked)
            self.assertTrue(all(o.seq < result.seq for o in blocked))
            self.assertTrue(any(o["work"] == writer.ref for o in store.unsettled("s")))
        finally:
            c = store.control("s")
            store.command("s", "pause-after-cancel", c.ref, "pause")
            release.set()
            await asyncio.wait_for(pending, 3)
        self.assertEqual({}, service.errors)

    async def test_late_failure_cannot_reblock_cancelled_writer(self):
        writer = self.store.work("s", self.c.ref, "writer", "Write", (), self.owner.ref)
        started, release = asyncio.Event(), asyncio.Event()
        class Model:
            context_tokens = 49024
            max_tokens = 1024
            identity = "late-provider-failure"
            async def complete(inner, request):
                started.set()
                await release.wait()
                raise ValueError("Late provider failure")
        service = ResearchService(self.store, Harness(self.store, Model()))
        pending = asyncio.create_task(service._run_child("s", writer.ref))
        try:
            await asyncio.wait_for(started.wait(), 2)
            self.store.cancel_work("s", self.owner.ref, writer.ref, self.c.epoch, "Reassign")
        finally:
            release.set()
            await asyncio.wait_for(pending, 2)
        self.assertEqual({}, service.work_errors)
        self.assertTrue(any(o["work"] == writer.ref for o in self.store.unsettled("s")))
        # Clearing terminal errors also clears the scheduler's repeated-failure gate.
        service.work_errors[writer.ref] = "RepeatedFailure"
        service.repeated_failures.add(writer.ref)
        self.assertEqual({}, service.status("s")["work_errors"])
        self.assertNotIn(writer.ref, service.repeated_failures)

    async def test_normal_completion_does_not_hide_an_inflight_failure(self):
        writer = self.store.work("s", self.c.ref, "writer", "Write", (), self.owner.ref)
        started, release = asyncio.Event(), asyncio.Event()
        class Model:
            context_tokens = 49024
            max_tokens = 1024
            identity = "completed-work-failure"
            async def complete(inner, request):
                started.set()
                await release.wait()
                raise ValueError("Unrelated failure remains visible")
        service = ResearchService(self.store, Harness(self.store, Model()))
        pending = asyncio.create_task(service._run_child("s", writer.ref))
        try:
            await asyncio.wait_for(started.wait(), 2)
            self.store.put("s", "work_result", {"producer": writer.ref, "text": "Done", "refs": []}, (writer.ref,))
        finally:
            release.set()
            await asyncio.wait_for(pending, 2)
        self.assertEqual("ValueError", service.status("s")["work_errors"][writer.ref])
        self.assertTrue(any(o["work"] == writer.ref for o in self.store.unsettled("s")))

    async def test_service_handoff_finish_owner_revision_review_and_publication(self):
        source, store = self.source.ref, self.store
        trace = []
        class Model:
            context_tokens = 49024
            max_tokens = 1024
            identity = "sequential-publication-fixture"
            async def complete(self, request):
                role = request["role"]
                trace.append((role, request["authoring"]["author"]))
                draft = request["draft"]
                if role == "writer":
                    if not draft:
                        call = Call("draft_report", {"text": "17 registered[[cite:" + source + "]]", "evidence": [source]})
                    else:
                        call = Call("finish_work", {"text": "Supported draft delivered", "refs": [draft["ref"]]})
                elif role == "reviewer":
                    call = Call("submit_review", {"reason": "Registration count matches the source", "defects": []})
                else:
                    writers = store.matching("s", "work", {"role": "writer"})
                    if not writers:
                        call = Call("delegate_work", {"role": "writer", "task": "Write from the supplied record", "refs": [source]})
                    elif request["authoring"]["delegated_writer"]:
                        call = Call("wait_for_work", {"refs": [writers[0].ref]})
                    elif "Seventeen" not in store.get("s", draft["ref"]).body["manuscript"]:
                        call = Call("patch_draft", {"base": draft["ref"], "edits": [{"old": "17 registered", "new": "Seventeen registered"}]})
                    else:
                        reviewers = store.matching("s", "work", {"role": "reviewer"})
                        reviews = store.list("s", "review")
                        if not reviewers:
                            call = Call("delegate_work", {"role": "reviewer", "task": "Check exact report", "refs": [draft["ref"]]})
                        elif not reviews:
                            call = Call("wait_for_work", {"refs": [reviewers[0].ref]})
                        else:
                            call = Call("publish_report", {"report": draft["ref"], "review": reviews[-1].ref})
                return Reply("", (call,)).to_json()
        service = ResearchService(self.store, Harness(self.store, Model()), concurrency=2)
        await asyncio.wait_for(service.run("s"), 10)
        self.assertEqual({}, service.errors)
        self.assertEqual({}, service.work_errors)
        reports = self.store.list("s", "report")
        self.assertEqual(2, len(reports))
        self.assertEqual("writer", self.store.get("s", reports[0].body["producer"]).body["role"])
        self.assertEqual(self.owner.ref, reports[1].body["producer"])
        publication = self.store.list("s", "publication")[-1]
        self.assertEqual(reports[1].ref, publication.body["report"])
        self.assertEqual(1, len(self.store.matching("s", "work", {"role": "lead"})))
        self.assertTrue(any(role == "writer" for role, _ in trace))
        self.assertFalse(any(o.body.get("failure") for o in self.store.list("s", "observation")))
        self.assertNotIn("cancelled", json.dumps(publication.body))
