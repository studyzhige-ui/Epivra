"""Offline selection and truthful-completion gates; no paid providers."""
import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.run_open_web_eval import execution_gate, run, selection

ROOT = Path(__file__).resolve().parents[1]
REQUEST = {"version": 1, "request_id": "test-once", "case": "asyncio-timeouts"}


class OnlineEvalTests(unittest.TestCase):
    def test_only_task_and_date_enter_case(self):
        _, case = selection(ROOT, REQUEST)
        self.assertEqual(set(case), {"task", "as_of_date"})
        self.assertNotIn("expected", case)

    def test_bad_requests_rejected_before_credentials(self):
        for request in ({**REQUEST, "case": "benchmark10"}, {**REQUEST, "cases": [1, 2]},
                        {**REQUEST, "version": True}, {**REQUEST, "request_id": "../x"}):
            with self.subTest(request=request), patch("tools.run_open_web_eval.credentials") as keys:
                with self.assertRaises(ValueError):
                    asyncio.run(run(ROOT, request, "test-once"))
                keys.assert_not_called()

    def test_attempt_not_blindly_repeated(self):
        with patch.dict("os.environ", {"GITHUB_RUN_ATTEMPT": "2"}), patch("tools.run_open_web_eval.credentials") as keys:
            with self.assertRaises(ValueError):
                asyncio.run(run(ROOT, REQUEST, "test-once"))
            keys.assert_not_called()

    def test_fresh_identity_required_before_credentials(self):
        with tempfile.TemporaryDirectory() as d, patch("tools.run_open_web_eval.selection", return_value=(REQUEST, {})), patch("tools.run_open_web_eval.credentials") as keys:
            root = Path(d)
            (root / ".epivra/open-web-test-once").mkdir(parents=True)
            with self.assertRaises(ValueError):
                asyncio.run(run(root, REQUEST, "test-once"))
            keys.assert_not_called()

    def test_completion_requires_actual_search_and_read(self):
        summary = {"published": True, "unknown_operations": 0}
        calls = [{"tool": t, "status": "succeeded", "http_status": 200} for t in ("web_search", "fetch_web")]
        self.assertTrue(execution_gate(summary, calls))
        self.assertFalse(execution_gate(summary, calls[:1]))
        self.assertFalse(execution_gate(summary, [{**c, "http_status": 429} for c in calls]))
        for update in ({"published": False}, {"unknown_operations": 1}, {"errors": {"x": "blocked"}}, {"error_type": "ValueError"}, {"work_errors": {"x": "unknown"}}):
            self.assertFalse(execution_gate({**summary, **update}, calls))


if __name__ == "__main__":
    unittest.main()
