"""Admission and truthful completeness for the fixed-source full task."""
import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.run_read_delivery_eval import execution_gate, run, validate_request

REQUEST = {"version": 1, "request_id": "one-task", "case": "wal-checkpoint-snapshot"}


class ReadDeliveryEvalTests(unittest.TestCase):
    def test_exact_small_selection_only(self):
        self.assertEqual(REQUEST, validate_request(REQUEST))
        for value in ({**REQUEST, "version": True}, {**REQUEST, "case": "benchmark10"},
                      {**REQUEST, "cases": []}, {**REQUEST, "request_id": "../escape"}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_request(value)

    def test_completed_report_is_not_semantic_acceptance(self):
        summary = {"published": True, "unknown_operations": 0}
        self.assertTrue(execution_gate(summary))
        for update in ({"published": False}, {"unknown_operations": 1}, {"errors": {"s": "blocked"}},
                       {"work_errors": {"w": "unknown"}}, {"export_error_type": "ValueError"},
                       {"cleanup_error_type": "OSError"}, {"error_type": "TimeoutError"}):
            self.assertFalse(execution_gate({**summary, **update}))

    def test_repeated_paid_attempt_stops_before_reading_material_or_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "evals").mkdir()
            (root / "evals/read-delivery-request.json").write_text(json.dumps(REQUEST))
            with patch.dict("os.environ", {"GITHUB_RUN_ATTEMPT": "2"}), patch(
                "tools.run_read_delivery_eval.fixture", side_effect=AssertionError("no fixture access")
            ), self.assertRaisesRegex(ValueError, "original paid attempt"):
                asyncio.run(run(root, "candidate", "new-run", root / "unread.zip"))


if __name__ == "__main__":
    unittest.main()
