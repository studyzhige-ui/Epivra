from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

from research_fixture import save_report

from epivra.domain import (
    Call,
    Conflict,
    NotAllowed,
    OwnershipError,
    Reply,
    UnknownOutcome,
)
from epivra.harness import Harness, object_schema
from epivra.harness import Tool as BaseTool
from epivra.storage import Store


def Tool(*args, **kwargs):
    kwargs.setdefault("roles", ("lead", "investigator", "reviewer"))
    return BaseTool(*args, **kwargs)


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "research.db"
        self.store = Store(self.path)
        c = self.store.create("s", "Compare sources", {"network": False})
        plan = self.store.put(
            "s", "plan", {"text": "Check primary evidence"}, (c.direction,)
        )
        self.c = self.store.command(
            "s", "approve", c.ref, "approve", {"plan": plan.ref}
        )
        self.work = self.store.work("s", self.c.ref, "lead", "Investigate")

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def command(self, action, payload=None):
        c = self.store.control("s")
        return self.store.command("s", action + str(c.epoch), c.ref, action, payload)


class StorageTests(Fixture):
    def test_existing_unversioned_database_is_rejected_without_schema_changes(self):
        import sqlite3
        from contextlib import closing

        path = Path(self.tmp.name) / "old.db"
        with closing(sqlite3.connect(path)) as db:
            db.execute("CREATE TABLE old_data(value TEXT)")
        with self.assertRaisesRegex(ValueError, "incompatible"):
            Store(path)
        with closing(sqlite3.connect(path)) as db:
            names = [
                r[0]
                for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")
            ]
        self.assertEqual(["old_data"], names)

    def test_corrupted_artifact_is_not_returned_as_valid_evidence(self):
        source = self.store.put("s", "source", {"text": "original"})
        self.store.db.execute(
            "UPDATE artifacts SET body=? WHERE ref=?",
            ('{"text":"corrupted"}', source.ref),
        )
        with self.assertRaisesRegex(ValueError, "integrity"):
            self.store.get("s", source.ref)

    def test_source_cursor_does_not_hide_later_pages(self):
        expected = [
            self.store.put("s", "source", {"text": f"item-{i}"}).ref for i in range(105)
        ]
        found, cursor = [], 0
        while True:
            page = self.store.search("s", "source", "", cursor, 20)
            if not page:
                break
            found.extend(a.ref for a in page)
            cursor = page[-1].seq
        self.assertEqual(expected, found)

    def test_command_replay_and_identity_collision(self):
        old = self.c
        new = self.store.command("s", "pause1", old.ref, "pause")
        self.assertEqual(new, self.store.command("s", "pause1", old.ref, "pause"))
        with self.assertRaises(Conflict):
            self.store.command("s", "pause1", old.ref, "resume")
        with self.assertRaises(Conflict):
            self.store.command("s", "pause2", old.ref, "pause")

    def test_single_host_ownership(self):
        with self.assertRaises(OwnershipError):
            Store(self.path)

    def test_unknown_survives_restart(self):
        self.store.admit("s", self.work.ref, self.c.epoch, "paid", {"q": "x"})
        self.store.close()
        self.store = Store(self.path)
        with self.assertRaises(UnknownOutcome):
            self.store.admit("s", self.work.ref, self.c.epoch, "paid", {"q": "x"})

    def test_settled_receipt_preserves_json_types_and_unicode(self):
        for i, (old, new) in enumerate(((True, 1), (1, 1.0), (False, 0))):
            operation = "typed-" + str(i)
            self.store.admit("s", self.work.ref, self.c.epoch, operation, {})
            self.store.settle(operation, {"value": old})
            with self.assertRaises(Conflict):
                self.store.settle(operation, {"value": new})
            replay = self.store.admit("s", self.work.ref, self.c.epoch, operation, {})
            self.assertIs(type(old), type(replay["value"]))
        self.store.admit("s", self.work.ref, self.c.epoch, "unicode", {})
        self.store.settle("unicode", {"text": "中文"})
        self.store.db.execute("UPDATE operations SET result=? WHERE id=?", ('{"text":"中文"}', "unicode"))
        self.store.settle("unicode", {"text": "中文"})
        self.assertEqual({"text": "中文"}, self.store.admit("s", self.work.ref, self.c.epoch, "unicode", {}))

    def test_completed_call_replays_without_new_operation(self):
        self.store.admit("s", self.work.ref, self.c.epoch, "paid", {"q": "x"})
        self.store.settle("paid", {"answer": 42})
        self.store.close()
        self.store = Store(self.path)
        self.assertEqual(
            {"answer": 42},
            self.store.admit("s", self.work.ref, self.c.epoch, "paid", {"q": "x"}),
        )
        self.assertEqual(
            1, self.store.db.execute("SELECT count(*) FROM operations").fetchone()[0]
        )
        with self.assertRaises(Conflict):
            self.store.settle("paid", {"answer": 43})

    def test_pause_fences_new_calls_but_preserves_late_results(self):
        self.store.admit("s", self.work.ref, self.c.epoch, "paid", {})
        self.command("pause")
        self.store.settle("paid", {"answer": 42})
        with self.assertRaises(Conflict):
            self.store.observation("s", self.work.ref, self.c.epoch, {})
        resumed = self.command("resume")
        self.assertEqual(
            {"answer": 42},
            self.store.admit("s", self.work.ref, resumed.epoch, "paid", {}),
        )

    def test_steer_while_paused_does_not_resume(self):
        self.command("pause")
        revised = self.command("steer", {"request": "New question"})
        self.assertTrue(revised.paused)
        resumed = self.command("resume")
        with self.assertRaises(Conflict):
            self.store.admit("s", self.work.ref, resumed.epoch, "new", {})

    def test_cross_study_reference_rejected(self):
        self.store.create("other", "x", {})
        with self.assertRaises(ValueError):
            self.store.put("other", "note", {}, (self.work.ref,))

    def test_plan_version_is_required(self):
        # Initial route approval must name a current plan. Steering an already
        # approved study retains authority and no longer allows reapproval.
        old = self.store.create("pending", "Original question", {})
        plan = self.store.put("pending", "plan", {"text": "old"}, (old.direction,))
        revised = self.store.command(
            "pending", "steer", old.ref, "steer", {"request": "new"}
        )
        with self.assertRaises(Conflict):
            self.store.command(
                "pending", "wrong-plan", revised.ref, "approve", {"plan": plan.ref}
            )

    def test_publication_needs_bound_independent_review(self):
        inv = self.store.work(
            "s", self.c.ref, "investigator", "Find", owner=self.work.ref
        )
        findings = self.store.put(
            "s",
            "work_result",
            {"text": "Found", "refs": [], "producer": inv.ref},
            (inv.ref,),
        )
        syn = self.store.work(
            "s", self.c.ref, "synthesizer", "Combine", (findings.ref,), self.work.ref
        )
        synthesis = self.store.put(
            "s",
            "work_result",
            {"text": "Combined", "refs": [], "producer": syn.ref},
            (syn.ref,),
        )
        writer = self.store.work(
            "s", self.c.ref, "writer", "Write", (synthesis.ref,), self.work.ref
        )
        source = self.store.put("s", "source", {"text": "Evidence"})
        report = save_report(self.store, writer, "Result", [source.ref])
        completion = Harness(self.store, FakeModel([]))
        finish = self.store.put("s", "step", {"fixture": "finish"}, (writer.ref,))
        result = completion._builtin("s", writer, self.c.epoch, finish.ref, 0,
                                     Call("finish_work", {"text": "Ready for review", "refs": [report.ref]}))
        self.assertIn("ref", result)
        self.assertTrue(completion.finished("s", writer.ref))
        review_work = self.store.work(
            "s",
            self.c.ref,
            "reviewer",
            "Check",
            (report.ref,),
            self.work.ref,
        )
        review = self.store.put(
            "s",
            "review",
            {
                "accepted": True,
                "work": review_work.ref,
            },
            (report.ref, review_work.ref),
        )
        with self.assertRaisesRegex(ValueError, "has not reached"):
            self.store.publish("s", self.work.ref, self.c.epoch, report.ref, review.ref)
        request = {
            "context": [{"ref": report.ref, "kind": "report", "body": report.body}]
        }
        step = self.store.put("s", "step", {"request": request}, (review_work.ref,))
        self.store.admit(
            "s",
            review_work.ref,
            self.c.epoch,
            "review-input",
            request,
            request_step=step.ref,
        )
        self.store.settle(
            "review-input", {"complete": True, "text": "checked", "calls": []}
        )
        published = self.store.publish(
            "s", self.work.ref, self.c.epoch, report.ref, review.ref
        )
        self.assertEqual(report.ref, published.body["report"])
        self.assertEqual(
            published.ref,
            self.store.publish(
                "s", self.work.ref, self.c.epoch, report.ref, review.ref
            ).ref,
        )
        self.store.put(
            "s",
            "review",
            {"accepted": False, "work": review_work.ref},
            (report.ref, review_work.ref),
        )
        with self.assertRaisesRegex(Conflict, "latest review"):
            self.store.publish("s", self.work.ref, self.c.epoch, report.ref, review.ref)
        changed = self.command("steer", {"request": "Different scope"})
        new_work = self.store.work("s", changed.ref, "lead", "Revisit")
        with self.assertRaises(Conflict):
            self.store.publish("s", new_work.ref, changed.epoch, report.ref, review.ref)

    def test_failed_transaction_has_no_partial_artifact(self):
        before = self.store.db.execute("SELECT count(*) FROM artifacts").fetchone()[0]
        with self.assertRaises(ValueError):
            with self.store.transaction():
                self.store._put("s", "note", {"text": "temporary"})
                raise ValueError("injected crash")
        self.assertEqual(
            before,
            self.store.db.execute("SELECT count(*) FROM artifacts").fetchone()[0],
        )

    def test_cancel_is_terminal(self):
        c = self.command("cancel")
        with self.assertRaises(NotAllowed):
            self.store.command("s", "restart", c.ref, "resume")


class FakeModel:
    context_tokens = 49024
    max_tokens = 1024
    identity = "offline-fixture-v1"

    def __init__(self, replies):
        self.replies = iter(replies)
        self.calls = 0

    async def complete(self, request):
        self.calls += 1
        return next(self.replies).to_json()


class HarnessTests(Fixture, unittest.IsolatedAsyncioTestCase):
    async def test_ungranted_network_tool_cannot_execute(self):
        async def search(args):
            self.fail("network tool executed despite missing grant")

        model = FakeModel([Reply("", (Call("search", {}),))])
        h = Harness(
            self.store,
            model,
            {
                "search": Tool(
                    "Search",
                    object_schema({}),
                    search,
                    permission="network",
                )
            },
        )
        await h.step("s", self.work.ref)
        self.assertIn("error", self.store.list("s", "observation")[-1].body["result"])

    async def test_incomplete_response_never_executes_tool(self):
        count = 0

        async def search(args):
            nonlocal count
            count += 1
            return "data"

        model = FakeModel([Reply("", (Call("search", {}),), False)])
        h = Harness(
            self.store,
            model,
            {
                "search": Tool(
                    "Search",
                    object_schema({}),
                    search,
                )
            },
        )
        await h.step("s", self.work.ref)
        self.assertEqual(0, count)
        self.assertIn(
            "incomplete", self.store.list("s", "observation")[0].body["error"]
        )

    async def test_resume_after_model_result_does_not_resample(self):
        model = FakeModel(
            [Reply("", (Call("save_note", {"text": "Keep", "refs": []}),))]
        )
        h = Harness(self.store, model)
        original = self.store.observation

        def crash(*args, **kwargs):
            raise OSError("injected disk failure")

        self.store.observation = crash
        with self.assertRaises(OSError):
            await h.step("s", self.work.ref)
        self.store.observation = original
        await h.step("s", self.work.ref)
        self.assertEqual(1, model.calls)
        self.assertEqual(1, len(self.store.list("s", "note")))

    async def test_resume_after_tool_result_does_not_recall_tool(self):
        count = 0

        async def search(args):
            nonlocal count
            count += 1
            return {"found": "evidence"}

        model = FakeModel([Reply("", (Call("search", {}),))])
        h = Harness(
            self.store,
            model,
            {
                "search": Tool(
                    "Search",
                    object_schema({}),
                    search,
                )
            },
        )
        original = self.store.observation
        self.store.observation = lambda *a, **kw: (_ for _ in ()).throw(
            OSError("crash")
        )
        with self.assertRaises(OSError):
            await h.step("s", self.work.ref)
        self.store.observation = original
        await h.step("s", self.work.ref)
        self.assertEqual((1, 1), (model.calls, count))

    async def test_partial_multi_tool_replay_uses_frozen_request(self):
        model = FakeModel(
            [
                Reply(
                    "",
                    (
                        Call("save_note", {"text": "one", "refs": []}),
                        Call("save_note", {"text": "two", "refs": []}),
                    ),
                )
            ]
        )
        h = Harness(self.store, model)
        original = self.store.observation
        calls = 0

        def crash_second(*a, **kw):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("crash")
            return original(*a, **kw)

        self.store.observation = crash_second
        with self.assertRaises(OSError):
            await h.step("s", self.work.ref)
        self.store.observation = original
        await h.step("s", self.work.ref)
        self.assertEqual(1, model.calls)
        self.assertEqual(2, len(self.store.list("s", "note")))

    async def test_inflight_pause_keeps_result_without_adoption(self):
        started, release = asyncio.Event(), asyncio.Event()

        class SlowModel:
            context_tokens = 49024
            max_tokens = 1024
            identity = "slow"
            calls = 0

            async def complete(inner, request):
                inner.calls += 1
                started.set()
                await release.wait()
                return Reply(
                    "",
                    (
                        Call(
                            "save_note",
                            {
                                "text": "late",
                                "refs": [],
                            },
                        ),
                    ),
                ).to_json()

        model = SlowModel()
        h = Harness(self.store, model)
        task = asyncio.create_task(h.step("s", self.work.ref))
        await started.wait()
        self.command("pause")
        release.set()
        with self.assertRaises(Conflict):
            await task
        self.assertEqual([], self.store.list("s", "note"))
        self.command("resume")
        await h.step("s", self.work.ref)
        self.assertEqual(1, model.calls)
        self.assertEqual(1, len(self.store.list("s", "note")))

    async def test_invalid_tool_is_observation_not_control(self):
        model = FakeModel([Reply("", (Call("resume", {}),))])
        h = Harness(self.store, model)
        await h.step("s", self.work.ref)
        self.assertEqual(self.c, self.store.control("s"))
        self.assertIn("error", self.store.list("s", "observation")[0].body["result"])

    async def test_concurrent_step_does_not_duplicate_model_call(self):
        model = FakeModel(
            [
                Reply(
                    "",
                    (
                        Call(
                            "propose_plan",
                            {
                                "text": "Plan",
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
                        ),
                    ),
                )
            ]
        )
        other = self.store.create("planning", "Question", {})
        planner = self.store.work("planning", other.ref, "lead", "Plan")
        h = Harness(self.store, model)
        await asyncio.gather(
            h.step("planning", planner.ref), h.step("planning", planner.ref)
        )
        self.assertEqual(1, model.calls)

    async def test_model_binding_change_cannot_reuse_pending_request(self):
        model = FakeModel([Reply("", ())])
        h = Harness(self.store, model)
        original = self.store.settle
        self.store.settle = lambda *a, **kw: (_ for _ in ()).throw(OSError("disk"))
        with self.assertRaises(OSError):
            await h.step("s", self.work.ref)
        self.store.settle = original
        model.identity = "different-provider"
        with self.assertRaises(NotAllowed):
            await h.step("s", self.work.ref)
