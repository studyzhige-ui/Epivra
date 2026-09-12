from __future__ import annotations

import unittest

from deep_research_agent.review import text_metrics, units
from evals.review_cases import CASES


class ReviewTests(unittest.TestCase):
    def test_units_preserve_tables_code_and_unicode_without_gaps(self):
        text = "# 标题\n\n第一段。\n\n| 值 |\n|---|\n| 17 |\n\n最后的建议。"
        parts = units(text)
        self.assertEqual(list(range(4)), [p["unit"] for p in parts])
        self.assertEqual("| 值 |\n|---|\n| 17 |", parts[2]["text"])
        self.assertEqual("最后的建议。", parts[-1]["text"])

    def test_metrics_count_original_unicode_without_normalizing_whitespace(self):
        self.assertEqual(
            {"characters": 6, "non_whitespace_characters": 3},
            text_metrics("中 a\n😀\t"),
        )

    def test_suite_has_positive_controls_and_full_coverage_transfer_pair(self):
        self.assertEqual(5, sum(c["accept"] for c in CASES))
        transfer = next(c for c in CASES if c["id"] == "coverage_transfer")
        self.assertGreater(len(units(transfer["report"])), 5)
        self.assertFalse(transfer["accept"])
