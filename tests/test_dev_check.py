"""Developer execution recovery checks; no Epivra or provider dependencies."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import dev_check as dev


class DevCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "repo"
        (self.root / "src").mkdir(parents=True)
        (self.root / "src/a.py").write_text("answer = 1\n", encoding="utf-8")
        self.output = Path(self.temp.name) / "evidence"
        self.head = patch.object(dev.subprocess, "check_output", return_value="a" * 40)
        self.head.start()
        self.addCleanup(self.head.stop)
        self.ready = patch.object(dev, "preflight", return_value={"ready": True, "missing_modules": []})
        self.ready.start()
        self.addCleanup(self.ready.stop)

    def execute(self, command, cwd, log, timeout):
        log.write_text("offline fixture\n", encoding="utf-8")
        return 0

    def test_success_is_bound_to_inputs_and_log_hashes(self):
        with patch.object(dev, "execute", side_effect=self.execute):
            self.assertEqual(0, dev.run_checks(self.root, self.output, "smoke"))
        self.assertTrue(dev.inspect_result(self.root, self.output)["verified_success"])
        (self.root / "src/a.py").write_text("answer = 2\n")
        self.assertFalse(dev.inspect_result(self.root, self.output)["verified_success"])

    def test_failure_stops_before_later_commands(self):
        def fail(*args):
            self.execute(*args)
            return 7
        with patch.object(dev, "execute", side_effect=fail) as run:
            self.assertEqual(1, dev.run_checks(self.root, self.output, "full"))
            self.assertEqual(1, run.call_count)
        state = json.loads((self.output / "summary.json").read_text())
        self.assertEqual(7, state["steps"][0]["returncode"])
        self.assertFalse(dev.inspect_result(self.root, self.output)["verified_success"])

    def test_interrupt_persists_unknown_without_automatic_replay(self):
        with patch.object(dev, "execute", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                dev.run_checks(self.root, self.output, "smoke")
        self.assertEqual("interrupted", dev.inspect_result(self.root, self.output)["state"])
        with patch.object(dev, "execute") as replay, self.assertRaises(FileExistsError):
            dev.run_checks(self.root, self.output, "smoke")
        replay.assert_not_called()

    def test_missing_dependencies_are_blocked_not_passed(self):
        with patch.object(dev, "preflight", return_value={"ready": False, "missing_modules": ["ruff"]}), patch.object(dev, "execute") as run:
            self.assertEqual(2, dev.run_checks(self.root, self.output, "full"))
            run.assert_not_called()
        self.assertEqual("blocked_environment", dev.inspect_result(self.root, self.output)["state"])

    def test_mutation_during_checks_invalidates_success(self):
        def mutate(*args):
            self.execute(*args)
            (self.root / "src/a.py").write_text("answer = 3\n")
            return 0
        with patch.object(dev, "execute", side_effect=mutate):
            self.assertEqual(1, dev.run_checks(self.root, self.output, "smoke"))
        self.assertEqual("stale_inputs", dev.inspect_result(self.root, self.output)["state"])

    def test_tampered_log_invalidates_receipt(self):
        with patch.object(dev, "execute", side_effect=self.execute):
            dev.run_checks(self.root, self.output, "smoke")
        (self.output / "execution_tests.log").write_text("different\n")
        self.assertFalse(dev.inspect_result(self.root, self.output)["verified_success"])

    def test_timeout_is_not_success(self):
        def timeout(*args):
            self.execute(*args)
            raise subprocess.TimeoutExpired(args[0], args[3])
        with patch.object(dev, "execute", side_effect=timeout):
            self.assertEqual(1, dev.run_checks(self.root, self.output, "smoke"))
        self.assertEqual("timeout", dev.inspect_result(self.root, self.output)["state"])

    def test_does_not_inherit_provider_credentials(self):
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "never-export", "TAVILY_API_KEY_4": "numbered", "GITHUB_TOKEN": "no", "PATH": "safe"}):
            env = dev.check_environment()
            self.assertNotIn("DEEPSEEK_API_KEY", env)
            self.assertNotIn("GITHUB_TOKEN", env)
            self.assertNotIn("TAVILY_API_KEY_4", env)
            self.assertEqual("safe", env["PATH"])

    def test_atomic_checkpoint_does_not_destroy_old_on_replace_failure(self):
        self.output.mkdir()
        path = self.output / "summary.json"
        dev.write_json(path, {"old": True})
        with patch.object(dev.os, "replace", side_effect=OSError("simulated disk error")), self.assertRaises(OSError):
            dev.write_json(path, {"new": True})
        self.assertEqual({"old": True}, json.loads(path.read_text()))
        self.assertEqual(["summary.json"], [p.name for p in self.output.iterdir()])

    def test_real_process_logs_and_exit_code(self):
        log = Path(self.temp.name) / "child.log"
        code = dev.execute([sys.executable, "-c", "print('fixture'); raise SystemExit(3)"], self.root, log, 5)
        self.assertEqual(3, code)
        self.assertIn("fixture", log.read_text())

    def test_real_timeout_terminates_the_validation_process(self):
        log = Path(self.temp.name) / "timeout.log"
        with self.assertRaises(subprocess.TimeoutExpired):
            dev.execute([sys.executable, "-c", "import time; time.sleep(30)"], self.root, log, 0.2)

    def test_passed_label_cannot_hide_a_failed_step(self):
        with patch.object(dev, "execute", side_effect=self.execute):
            dev.run_checks(self.root, self.output, "smoke")
        path = self.output / "summary.json"
        state = json.loads(path.read_text())
        state["steps"][0]["returncode"] = 1
        dev.write_json(path, state)
        self.assertFalse(dev.inspect_result(self.root, self.output)["verified_success"])

    def test_partial_steps_cannot_count_as_a_full_validation(self):
        with patch.object(dev, "execute", side_effect=self.execute):
            dev.run_checks(self.root, self.output, "smoke")
        path = self.output / "summary.json"
        state = json.loads(path.read_text())
        state["profile"] = "full"
        dev.write_json(path, state)
        self.assertFalse(dev.inspect_result(self.root, self.output)["verified_success"])

    def test_output_cannot_invalidate_its_own_inputs(self):
        with self.assertRaisesRegex(ValueError, "watched"):
            dev.run_checks(self.root, self.root / "src/evidence", "smoke")


if __name__ == "__main__":
    unittest.main()
