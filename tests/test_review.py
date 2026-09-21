from __future__ import annotations

import unittest

from epivra.review import text_metrics, units


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
