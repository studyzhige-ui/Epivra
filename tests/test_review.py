from __future__ import annotations

import unittest

from deep_research_agent.domain import Artifact
from deep_research_agent.review import checked, units
from evals.review_cases import CASES


class ReviewTests(unittest.TestCase):
    def test_units_preserve_tables_code_and_unicode_without_gaps(self):
        text = "# 标题\n\n第一段。\n\n| 值 |\n|---|\n| 17 |\n\n最后的建议。"
        parts = units(text)
        self.assertEqual(list(range(4)), [p["unit"] for p in parts])
        self.assertEqual("| 值 |\n|---|\n| 17 |", parts[2]["text"])
        self.assertEqual("最后的建议。", parts[-1]["text"])

    def test_latest_check_replaces_judgment_without_losing_other_units(self):
        def record(seq, values):
            return Artifact(str(seq), "s", "review_check", {"checks": values}, (), seq)

        old = {"unit": 0, "defects": ["Unsupported assertion"], "assessment": "Initial"}
        corrected = {
            **old,
            "defects": [],
            "assessment": "Rechecked source",
        }
        other = {"unit": 1, "defects": ["Unsupported assertion"]}
        result = checked([record(2, [corrected]), record(1, [old, other])])
        self.assertEqual({0: corrected, 1: other}, result)

    def test_suite_has_positive_controls_and_full_coverage_transfer_pair(self):
        self.assertEqual(5, sum(c["accept"] for c in CASES))
        transfer = next(c for c in CASES if c["id"] == "coverage_transfer")
        self.assertGreater(len(units(transfer["report"])), 5)
        self.assertFalse(transfer["accept"])
