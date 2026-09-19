"""Offline selection and truthful-completion gates; no paid providers."""
import asyncio
import tempfile
import time
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

from tools.run_open_web_eval import (
    drive,
    evaluation_active_seconds,
    execution_gate,
    run,
    selection,
)

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

    def test_evaluation_active_window_is_diagnostic_only_and_bounded(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(1500, evaluation_active_seconds())
        with patch.dict("os.environ", {"EPIVRA_EVAL_ACTIVE_SECONDS": "900"}):
            self.assertEqual(900, evaluation_active_seconds())
        for value in ("x", "299", "1801"):
            with self.subTest(value=value), patch.dict(
                "os.environ", {"EPIVRA_EVAL_ACTIVE_SECONDS": value}
            ):
                with self.assertRaises(ValueError):
                    evaluation_active_seconds()

    def test_drive_pauses_before_hard_runner_timeout_without_cancelling_inflight_work(self):
        class Rows:
            def fetchall(self):
                return []

        class Store:
            def __init__(self):
                self.state = SimpleNamespace(
                    ref="control-1", paused=False, cancelled=False
                )
                self.db = self
                self.commands = []

            def execute(self, *args):
                return Rows()

            def control(self, study):
                return self.state

            def command(self, study, command_id, expected, action):
                self.commands.append((study, command_id, expected, action))
                self.state = SimpleNamespace(
                    ref="control-2", paused=True, cancelled=False
                )
                return self.state

        class Service:
            def __init__(self, store):
                self.store = store
                self.cancelled = False

            async def run(self, study):
                try:
                    while not self.store.state.paused:
                        await asyncio.sleep(0)
                except asyncio.CancelledError:
                    self.cancelled = True
                    raise

        async def scenario():
            with tempfile.TemporaryDirectory() as d:
                store = Store()
                service = Service(store)
                summary = {"run_id": "deadline-test", "stage": "research"}
                await drive(
                    service,
                    store,
                    "study",
                    Path(d),
                    summary,
                    (),
                    stop_at=time.monotonic() - 1,
                )
                self.assertEqual(1, len(store.commands))
                self.assertEqual("pause", store.commands[0][3])
                self.assertTrue(summary["evaluation_deadline_reached"])
                self.assertEqual("evaluation_deadline_paused", summary["stage"])
                self.assertFalse(service.cancelled)

        asyncio.run(scenario())

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
