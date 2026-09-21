"""The smoke driver cannot substitute publication for semantic quality."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.run_refactor_smoke import REQUEST, admit, execution_gate


class RefactorSmokeTests(unittest.TestCase):
    def test_only_fixed_request_and_fresh_state(self):
        with tempfile.TemporaryDirectory() as name:
            state, output = Path(name) / "state", Path(name) / "out"
            admit(REQUEST, "test-run", state, output)
            for value in (None, {**REQUEST, "version": True}, {**REQUEST, "case": "benchmark10"}):
                with self.assertRaises(ValueError):
                    admit(value, "test-run", state, output)
            state.mkdir()
            with self.assertRaises(ValueError):
                admit(REQUEST, "test-run", state, output)

    def test_no_paid_rerun_or_ambiguous_identity(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "new"
            with patch.dict(os.environ, {"GITHUB_RUN_ATTEMPT": "2"}), self.assertRaises(ValueError):
                admit(REQUEST, "test-run", path, path)
            with self.assertRaises(ValueError):
                admit(REQUEST, "../path", path, path)

    def test_execution_is_not_quality_acceptance(self):
        good = {"published": True, "unknown_operations": 0}
        self.assertTrue(execution_gate(good))
        for field, value in (("published", False), ("unknown_operations", 1), ("errors", {"study": "x"}),
                             ("work_errors", {"work": "x"}), ("export_error_type", "ValueError"),
                             ("cleanup_error_type", "OSError")):
            self.assertFalse(execution_gate({**good, field: value}))


if __name__ == "__main__":
    unittest.main()
