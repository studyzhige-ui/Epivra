"""Deterministic durable timing diagnostics; no provider calls."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from epivra.storage import Store


class OperationTimingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / "state.db")
        control = self.store.create("s", "test", {})
        plan = self.store.put("s", "plan", {"text": "test"}, (control.direction,))
        control = self.store.command(
            "s", "approve", control.ref, "approve", {"plan": plan.ref}
        )
        self.work = self.store.work("s", control.ref, "lead", "test")
        self.epoch = control.epoch

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def admit(self, operation="op"):
        self.assertIsNone(
            self.store.admit(
                "s",
                self.work.ref,
                self.epoch,
                operation,
                {"tool": "fixture"},
                admission={
                    "queued_at": 10.0,
                    "at": 12.0,
                    "resource": "fixture",
                },
            )
        )

    def test_timing_is_persisted_and_projected(self):
        self.admit()
        self.assertIsNone(self.store.usage_records("s")[0]["invoked_at"])
        self.store.mark_invoked("op", 13.0)
        inflight = self.store.usage_records("s")[0]
        self.assertEqual(2.0, inflight["queue_seconds"])
        self.assertEqual(1.0, inflight["admission_to_invoke_seconds"])
        self.assertIsNone(inflight["external_seconds"])

        result = {"value": {"http_status": 200}}
        self.store.settle("op", result, settled_at=17.0)
        done = self.store.usage_records("s")[0]
        self.assertEqual(4.0, done["external_seconds"])
        self.assertEqual("succeeded", done["status"])

        self.store.settle("op", result, settled_at=99.0)
        self.assertEqual(17.0, self.store.usage_records("s")[0]["settled_at"])

    def test_unknown_after_send_has_no_fake_settlement(self):
        self.admit("unknown-op")
        self.store.mark_invoked("unknown-op", 15.0)
        row = next(
            item
            for item in self.store.usage_records("s")
            if item["operation"] == "unknown-op"
        )
        self.assertEqual("unknown", row["status"])
        self.assertEqual(15.0, row["invoked_at"])
        self.assertIsNone(row["settled_at"])
        self.assertIsNone(row["external_seconds"])

    def test_legacy_operation_without_admission_stays_out_of_scheduler_history(self):
        self.assertIsNone(
            self.store.admit(
                "s",
                self.work.ref,
                self.epoch,
                "legacy",
                {"tool": "fixture"},
            )
        )
        self.store.mark_invoked("legacy", 13.0)
        self.store.settle(
            "legacy", {"value": {"http_status": 200}}, settled_at=17.0
        )
        self.assertEqual([], self.store.admissions())
        row = next(
            item
            for item in self.store.usage_records("s")
            if item["operation"] == "legacy"
        )
        self.assertIsNone(row["admitted_at"])
        self.assertIsNone(row["invoked_at"])
        self.assertIsNone(row["settled_at"])

    def test_invalid_timestamps_do_not_mutate_ledger(self):
        self.admit()
        for value in (float("nan"), float("inf"), True, "13"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.store.mark_invoked("op", value)
        self.assertIsNone(self.store.usage_records("s")[0]["invoked_at"])


if __name__ == "__main__":
    unittest.main()
