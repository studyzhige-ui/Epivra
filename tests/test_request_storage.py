"""Frozen requests retain their identity across additive storage migration."""

from __future__ import annotations

import unittest

from test_execution import FakeModel, Fixture

from deep_research_agent.domain import Conflict, Reply, UnknownOutcome, identity
from deep_research_agent.harness import Harness
from deep_research_agent.storage import Store


class RequestStorageTests(Fixture, unittest.IsolatedAsyncioTestCase):
    def frozen_step(self, model):
        harness = Harness(self.store, model)
        step = self.store.put(
            "s",
            "step",
            {"number": 0, "request": harness._request("s", self.work)},
            (self.work.ref,),
        )
        return step, identity("model", self.work.ref, step.ref)

    def restart(self, *, legacy=False):
        if legacy:
            # Only this test's temporary database is converted to the old schema.
            self.store.db.execute("ALTER TABLE operations DROP COLUMN request_step")
            self.store.db.execute("PRAGMA user_version=2001")
        self.store.close()
        self.store = Store(self.path)

    async def test_legacy_success_migrates_and_replays_without_model_call(self):
        model = FakeModel([])
        step, operation = self.frozen_step(model)
        self.store.admit(
            "s", self.work.ref, self.c.epoch, operation, step.body["request"]
        )
        self.store.settle(operation, Reply("Saved response", ()).to_json())
        before = tuple(
            self.store.db.execute(
                "SELECT request,result FROM operations WHERE id=?", (operation,)
            ).fetchone()
        )
        self.restart(legacy=True)
        self.assertEqual(
            2003, self.store.db.execute("PRAGMA user_version").fetchone()[0]
        )
        await Harness(self.store, model).step("s", self.work.ref)
        self.assertEqual(0, model.calls)
        row = self.store.db.execute(
            "SELECT request,result,request_step FROM operations WHERE id=?",
            (operation,),
        ).fetchone()
        self.assertEqual(before, tuple(row[:2]))
        self.assertIsNone(row[2])
        self.assertEqual(
            1, self.store.db.execute("SELECT count(*) FROM operations").fetchone()[0]
        )

    async def test_legacy_unknown_stays_blocked_after_migration(self):
        model = FakeModel([])
        step, operation = self.frozen_step(model)
        self.store.admit(
            "s", self.work.ref, self.c.epoch, operation, step.body["request"]
        )
        self.restart(legacy=True)
        with self.assertRaises(UnknownOutcome):
            await Harness(self.store, model).step("s", self.work.ref)
        self.assertEqual(0, model.calls)

    async def test_new_model_request_is_stored_once_and_replays_after_restart(self):
        model = FakeModel([Reply("Saved response", ())])
        await Harness(self.store, model).step("s", self.work.ref)
        row = self.store.db.execute(
            "SELECT id,request,request_step FROM operations"
        ).fetchone()
        self.assertEqual("", row["request"])
        step = self.store.get("s", row["request_step"])
        self.assertEqual("step", step.kind)
        self.assertEqual(1, model.calls)
        self.restart()
        result = self.store.admit(
            "s",
            self.work.ref,
            self.c.epoch,
            row["id"],
            step.body["request"],
            request_step=step.ref,
        )
        self.assertEqual(Reply("Saved response", ()).to_json(), result)
        # Inline and referenced representations compare by the same request.
        self.assertEqual(
            result,
            self.store.admit(
                "s", self.work.ref, self.c.epoch, row["id"], step.body["request"]
            ),
        )

    def test_invalid_request_references_are_rejected_before_admission(self):
        request = {"q": "evidence"}
        other = self.store.work("s", self.c.ref, "lead", "Other work")
        wrong_work = self.store.put("s", "step", {"request": request}, (other.ref,))
        wrong_kind = self.store.put("s", "note", {"request": request}, (self.work.ref,))
        step = self.store.put("s", "step", {"request": request}, (self.work.ref,))
        for ref, submitted in [
            (wrong_work.ref, request),
            (wrong_kind.ref, request),
            (step.ref, {"q": "changed"}),
        ]:
            with self.subTest(ref=ref), self.assertRaises(Conflict):
                self.store.admit(
                    "s",
                    self.work.ref,
                    self.c.epoch,
                    "invalid",
                    submitted,
                    request_step=ref,
                )
        self.assertEqual(
            0, self.store.db.execute("SELECT count(*) FROM operations").fetchone()[0]
        )

    def test_referenced_unknown_survives_restart_and_request_change_conflicts(self):
        step, operation = self.frozen_step(FakeModel([]))
        self.store.admit(
            "s",
            self.work.ref,
            self.c.epoch,
            operation,
            step.body["request"],
            request_step=step.ref,
        )
        self.restart()
        with self.assertRaises(UnknownOutcome):
            self.store.admit(
                "s",
                self.work.ref,
                self.c.epoch,
                operation,
                step.body["request"],
                request_step=step.ref,
            )
        with self.assertRaises(Conflict):
            self.store.admit(
                "s", self.work.ref, self.c.epoch, operation, {"changed": True}
            )

    def test_cross_study_request_step_is_rejected(self):
        control = self.store.create("other", "Other study", {})
        work = self.store.work("other", control.ref, "lead", "Plan")
        step = self.store.put("other", "step", {"request": {}}, (work.ref,))
        with self.assertRaises(ValueError):
            self.store.admit(
                "s", self.work.ref, self.c.epoch, "cross-study", {}, request_step=step.ref
            )
        self.assertEqual(
            0, self.store.db.execute("SELECT count(*) FROM operations").fetchone()[0]
        )
