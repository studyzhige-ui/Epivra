"""Frozen requests retain their identity across additive storage migration."""

from __future__ import annotations

import unittest

from test_execution import FakeModel, Fixture

from epivra.domain import Conflict, Reply, UnknownOutcome, identity
from epivra.harness import Harness
from epivra.storage import Store


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
            2004, self.store.db.execute("PRAGMA user_version").fetchone()[0]
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
                "s",
                self.work.ref,
                self.c.epoch,
                "cross-study",
                {},
                request_step=step.ref,
            )
        self.assertEqual(
            0, self.store.db.execute("SELECT count(*) FROM operations").fetchone()[0]
        )


class CompletedImportTests(Fixture):
    def published(self):
        investigator = self.store.work(
            "s", self.c.ref, "investigator", "Find", owner=self.work.ref
        )
        finding = self.store.put(
            "s",
            "work_result",
            {"text": "Finding", "refs": [], "producer": investigator.ref},
            (investigator.ref,),
        )
        writer = self.store.work(
            "s", self.c.ref, "writer", "Write", (finding.ref,), self.work.ref
        )
        report = self.store.put(
            "s",
            "report",
            {"text": "Result", "producer": writer.ref, "evidence": []},
            (self.c.direction, writer.ref),
        )
        reviewer = self.store.work(
            "s", self.c.ref, "reviewer", "Check", (report.ref,), self.work.ref
        )
        request = {"context": [{"ref": report.ref, "kind": "report", "body": report.body}]}
        step = self.store.put("s", "step", {"request": request}, (reviewer.ref,))
        self.store.admit("s", reviewer.ref, self.c.epoch, "review-input", request, request_step=step.ref)
        self.store.settle("review-input", {"complete": True, "text": "checked", "calls": []})
        review = self.store.put(
            "s",
            "review",
            {"accepted": True, "work": reviewer.ref},
            (report.ref, reviewer.ref),
        )
        self.store.publish("s", self.work.ref, self.c.epoch, report.ref, review.ref)
        self.store.admit("s", self.work.ref, self.c.epoch, "paid", {"input": "saved"})
        self.store.settle("paid", {"output": "already paid"})

    def test_import_preserves_ledger_and_rejects_partial_existing_copy(self):
        self.published()
        target = Store(self.path.with_name("target.db"))
        try:
            self.assertTrue(target.import_completed(self.path, "s")["imported"])
            self.assertTrue(target.import_completed(self.path, "s")["already_imported"])
            self.assertEqual("succeeded", target.operation_status("s", "paid"))
            target.db.execute("DELETE FROM operations WHERE id='paid'")
            with self.assertRaisesRegex(Conflict, "ledger differ"):
                target.import_completed(self.path, "s")
        finally:
            target.close()

    def test_historical_publication_does_not_complete_new_direction(self):
        self.published()
        self.command("steer", {"request": "Changed scope"})
        target = Store(self.path.with_name("target.db"))
        try:
            with self.assertRaisesRegex(ValueError, "completed"):
                target.import_completed(self.path, "s")
            self.assertEqual(0, target.latest_sequence("s", ("control",)))
        finally:
            target.close()

    def test_foreign_ledger_reference_rolls_back_whole_import(self):
        self.published()
        other = self.store.create("other", "different study", {})
        self.store.db.execute(
            "UPDATE operations SET direction=? WHERE id='paid'", (other.direction,)
        )
        target = Store(self.path.with_name("target.db"))
        try:
            with self.assertRaisesRegex(ValueError, "ledger references"):
                target.import_completed(self.path, "s")
            self.assertEqual(0, target.latest_sequence("s", ("control",)))
        finally:
            target.close()
