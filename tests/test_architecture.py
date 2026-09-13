import runpy
import tempfile
import unittest
from pathlib import Path

GATE = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "tools/check_architecture.py")
)


class ArchitectureTests(unittest.TestCase):
    def test_gate_rejects_unregistered_and_wrong_direction_dependencies(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in GATE["ALLOWED"]:
                (root / f"{name}.py").write_text("", encoding="utf-8")
            self.assertEqual([], GATE["check"](root))
            (root / "domain.py").write_text(
                "from epivra import application\n", encoding="utf-8"
            )
            (root / "prompts.py").write_text(
                "def hidden():\n    import httpx\n", encoding="utf-8"
            )
            (root / "unregistered.py").write_text("", encoding="utf-8")
            problems = GATE["check"](root)
            self.assertTrue(any("forbidden local dependency" in p for p in problems))
            self.assertTrue(any("imports I/O" in p for p in problems))
            self.assertTrue(any("not registered" in p for p in problems))
