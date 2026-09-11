"""Evaluation admission checks: hidden rubrics and trace privacy boundaries."""

import json
import tempfile
import unittest
from pathlib import Path

from deep_research_agent.storage import Store
from evals.mechanism_cases import CASES
from tools.run_closed_loop_eval import export


class EvaluationContractTests(unittest.TestCase):
    def test_every_mechanism_has_distinct_reports_and_behavior_checks(self):
        self.assertEqual([f"M{i:02}" for i in range(1, 19)], [c["id"] for c in CASES])
        for case in CASES:
            self.assertTrue(case["requires_trace"])
            self.assertNotEqual(case["positive"]["report"], case["negative"]["report"])
            self.assertNotEqual(
                case["positive"]["behavior"], case["negative"]["behavior"]
            )

    def test_export_does_not_release_provider_private_steps_or_claim_semantic_pass(
        self,
    ):
        with tempfile.TemporaryDirectory() as name:
            folder = Path(name)
            store = Store(folder / "research.db")
            try:
                store.create("s", "Question", {})
                store.put("s", "step", {"request": {"secret_reasoning": "PRIVATE"}})
                store.put("s", "note", {"text": "Public evidence interpretation"})
                result = export(store, "s", folder, {}, running=True)
                trace = (folder / "trace.json").read_text(encoding="utf-8")
                self.assertNotIn("PRIVATE", trace)
                self.assertEqual(["note"], [r["kind"] for r in json.loads(trace)])
                self.assertTrue(result["running"])
                self.assertEqual(
                    "pending_primary_review", result["semantic_acceptance"]
                )
            finally:
                store.close()
