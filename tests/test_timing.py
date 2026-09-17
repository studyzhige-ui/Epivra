"""Clock metadata and indexed display reads; no model calls or quality claims."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from epivra.storage import Store


class TimingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "research.db"
        self.store = Store(self.path)
        self.control = self.store.create("s", "Research", {})
        self.plan = self.store.put(
            "s", "plan", {"text": "Research"}, (self.control.direction,)
        )

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def command(self, name, at, payload=None):
        with patch("epivra.storage.time.time", return_value=at):
            self.control = self.store.command(
                "s", name, self.control.ref, name, payload
            )

    def test_elapsed_includes_pauses_and_survives_restart(self):
        self.assertIsNone(self.store.timing("s", now=99)["elapsed_seconds"])
        self.command("approve", 100, {"plan": self.plan.ref})
        self.command("pause", 120)
        self.assertEqual(40, self.store.timing("s", now=140)["elapsed_seconds"])
        self.command("resume", 150)
        self.command("steer", 160, {"request": "Revised research"})
        with patch("epivra.storage.time.time", return_value=200):
            # Publication fact fixture only; this test does not bypass a real review.
            publication = self.store._put(
                "s", "publication", {"report": "fixture"}, (self.control.direction,)
            )
        self.store.close()
        self.store = Store(self.path)
        timing = self.store.timing("s", now=900)
        self.assertEqual(
            (100, 200, 100),
            (timing["started_at"], timing["ended_at"], timing["elapsed_seconds"]),
        )
        with patch("epivra.storage.time.time", return_value=1000):
            same = self.store._put(
                "s", "publication", publication.body, publication.parents
            )
        self.assertEqual(publication.ref, same.ref)
        self.assertEqual(200, self.store.timing("s")["ended_at"])

    def test_cancel_and_backward_clock(self):
        self.command("approve", 100, {"plan": self.plan.ref})
        self.assertIsNone(self.store.timing("s", now=90)["elapsed_seconds"])
        self.command("cancel", 130)
        self.assertEqual(30, self.store.timing("s", now=500)["elapsed_seconds"])

    def test_legacy_migration_preserves_originals_without_invented_times(self):
        self.command("approve", 100, {"plan": self.plan.ref})
        before = [
            tuple(row)
            for row in self.store.db.execute("SELECT ref,body,parents FROM artifacts")
        ]
        self.store.db.execute("ALTER TABLE artifacts DROP COLUMN created_at")
        self.store.db.execute("PRAGMA user_version=2003")
        self.store.close()
        self.store = Store(self.path)
        self.assertEqual(
            before,
            [
                tuple(row)
                for row in self.store.db.execute(
                    "SELECT ref,body,parents FROM artifacts"
                )
            ],
        )
        self.assertIsNone(self.store.timing("s", now=200)["elapsed_seconds"])

    def test_current_control_reads_only_latest_and_operations_are_indexed(self):
        self.command("approve", 100, {"plan": self.plan.ref})
        self.command("pause", 120)
        with patch.object(
            self.store, "list", side_effect=AssertionError("must not load history")
        ):
            self.assertEqual(self.control, self.store.control("s"))
        plan = self.store.db.execute(
            "EXPLAIN QUERY PLAN SELECT id FROM operations WHERE study=? AND status=?",
            ("s", "unknown"),
        ).fetchall()
        self.assertTrue(any("operation_study_status" in row[3] for row in plan))


if __name__ == "__main__":
    unittest.main()
