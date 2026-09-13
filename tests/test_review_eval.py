"""Review experiment identity checks never call a provider."""

import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from tools.run_review_eval import CASES, bind_run, run, source_snapshot


class ReviewIdentityTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.src = self.root / "src/epivra"
        self.src.mkdir(parents=True)
        (self.src / "example.py").write_text("version = 1", encoding="utf-8")
        self.folder = self.root / ".epivra/review-test"

    def test_same_configuration_replays_but_drift_is_rejected(self):
        cases = [{"id": "one", "report": "Original", "accept": True}]
        bound = bind_run(self.root, self.folder, cases, "high")
        (self.folder / "research.db").write_bytes(b"finished database")
        self.assertEqual(bound, bind_run(self.root, self.folder, cases, "high"))
        for changed, effort in [
            (cases, "max"),
            ([{**cases[0], "report": "Changed"}], "high"),
            ([{**cases[0], "accept": False}], "high"),
        ]:
            with self.assertRaisesRegex(ValueError, "new run ID"):
                bind_run(self.root, self.folder, changed, effort)
        (self.src / "example.py").write_text("version = 2", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "new run ID"):
            bind_run(self.root, self.folder, cases, "high")
        self.assertEqual(bound, json.loads((self.folder / "fixture.json").read_text()))

    def test_unbound_existing_run_is_not_adopted(self):
        self.folder.mkdir(parents=True)
        database = self.folder / "research.db"
        database.write_bytes(b"old run")
        with self.assertRaisesRegex(ValueError, "audit-only"):
            bind_run(self.root, self.folder, [], "high")
        self.assertEqual(b"old run", database.read_bytes())
        self.assertFalse((self.folder / "fixture.json").exists())

    def test_source_content_is_bound_not_just_report_name(self):
        database = self.root / "source.db"
        with closing(sqlite3.connect(database)) as db:
            db.execute(
                "CREATE TABLE artifacts(seq INTEGER,ref TEXT,study TEXT,kind TEXT,body TEXT)"
            )
            db.execute(
                "INSERT INTO artifacts VALUES(1,'publication','s','publication',?)",
                (json.dumps({"report": "r"}),),
            )
            db.execute(
                "INSERT INTO artifacts VALUES(2,'evidence-v1','s','source','{}')"
            )
            db.commit()
        snapshot = source_snapshot(database)
        bound = bind_run(self.root, self.folder, [], "high", snapshot)
        with closing(sqlite3.connect(database)) as db:
            db.execute("UPDATE artifacts SET ref='evidence-v2' WHERE kind='source'")
            db.commit()
        self.assertNotEqual(snapshot, source_snapshot(database))
        with self.assertRaisesRegex(ValueError, "new run ID"):
            bind_run(self.root, self.folder, [], "high", source_snapshot(database))
        self.assertEqual(bound["source"]["report"], "r")

    async def test_completed_effort_change_stops_before_credentials_or_database(self):
        case = CASES[0]
        bind_run(self.root, self.folder, [case], "high")
        # Even a completed legacy result cannot bypass validation via finished().
        (self.folder / "research.db").write_bytes(b"completed run must not open")
        with patch(
            "tools.run_review_eval.credentials",
            side_effect=AssertionError("no credential access"),
        ):
            with self.assertRaisesRegex(ValueError, "configuration changed"):
                await run(self.root, "test", only=[case["id"]], effort="max")
