"""The architecture gate must actually fail, not merely run.

A gate that cannot be shown to reject a violation is decoration.  Each test here
injects one real violation into a temporary package and asserts the checker
catches it -- including the docstring exemption, whose first implementation
silently exempted any line containing a string literal.
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "check_architecture", ROOT / "tools" / "check_architecture.py"
)
assert _spec is not None and _spec.loader is not None
gate = importlib.util.module_from_spec(_spec)
sys.modules["check_architecture"] = gate
_spec.loader.exec_module(gate)


class GateFixture(unittest.TestCase):
    def check(self, filename: str, source: str) -> list[str]:
        """Run the gate over one synthetic module and return its messages."""

        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "deep_research_agent"
            package.mkdir()
            path = package / filename
            path.write_text(source, encoding="utf-8")

            original = gate.PACKAGE
            gate.PACKAGE = package
            try:
                violations = [
                    *gate.check_domain_purity(path, __import__("ast").parse(source)),
                    *gate.check_layer_direction(path, __import__("ast").parse(source)),
                    *gate.check_legacy_symbols(path, source),
                ]
            finally:
                gate.PACKAGE = original
            return [violation.message for violation in violations]


class DomainPurityTest(GateFixture):
    def test_a_domain_module_importing_a_driver_is_rejected(self) -> None:
        messages = self.check("artifacts.py", "import aiosqlite\n")
        self.assertTrue(any("infrastructure" in m for m in messages))

    def test_domain_modules_may_import_each_other(self) -> None:
        messages = self.check("artifacts.py", "from .sources import BodyRef\n")
        self.assertEqual([], messages)

    def test_a_trust_module_may_import_a_driver(self) -> None:
        messages = self.check("artifact_store.py", "import aiosqlite\n")
        self.assertEqual([], messages)


class LayerDirectionTest(GateFixture):
    def test_domain_importing_trust_is_rejected(self) -> None:
        messages = self.check("artifacts.py", "from .operations import run_once\n")
        self.assertTrue(any("dependencies point downward" in m for m in messages))

    def test_trust_importing_agents_is_rejected(self) -> None:
        messages = self.check("citations.py", "from .agents import author\n")
        self.assertTrue(any("dependencies point downward" in m for m in messages))

    def test_trust_importing_domain_is_allowed(self) -> None:
        messages = self.check("citations.py", "from .sources import MaterialBody\n")
        self.assertEqual([], messages)


class LegacySymbolTest(GateFixture):
    def test_a_legacy_symbol_in_code_is_rejected(self) -> None:
        messages = self.check("contract.py", 'branch_id = "b1"\n')
        self.assertTrue(any("branch_id" in m for m in messages))

    def test_a_legacy_symbol_inside_a_string_is_still_rejected(self) -> None:
        """The first implementation exempted any line holding a string."""

        messages = self.check("contract.py", 'route = payload["stage"]\nx = Supervisor\n')
        self.assertTrue(any("Supervisor" in m for m in messages))

    def test_a_docstring_may_record_that_a_concept_was_removed(self) -> None:
        source = '"""The legacy Supervisor control plane has been removed."""\n'
        self.assertEqual([], self.check("contract.py", source))

    def test_a_comment_may_reference_a_removed_concept(self) -> None:
        self.assertEqual([], self.check("contract.py", "# no branch_id here\n"))

    def test_a_function_docstring_is_exempt_but_its_body_is_not(self) -> None:
        source = (
            "def f():\n"
            '    """Replaces the old ResearchState blob."""\n'
            "    return ResearchState\n"
        )
        messages = self.check("contract.py", source)
        self.assertEqual(1, len(messages))
        self.assertIn("ResearchState", messages[0])


class RealPackageTest(unittest.TestCase):
    def test_the_current_package_passes_its_own_gate(self) -> None:
        self.assertEqual([], [v.render() for v in gate.run()])


if __name__ == "__main__":
    unittest.main()
