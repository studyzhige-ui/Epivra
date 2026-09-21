from __future__ import annotations

import unittest

from epivra.review import text_metrics, units


class ReviewTests(unittest.TestCase):
    def test_units_preserve_tables_code_and_unicode_without_gaps(self):
        text = "# 标题\n\n第一段。\n\n| 值 |\n|---|\n| 17 |\n\n最后的建议。"
        parts = units(text)
        self.assertEqual(list(range(4)), [p["unit"] for p in parts])
        self.assertEqual("| 值 |\n|---|\n| 17 |\n\n", parts[2]["text"])
        self.assertEqual(text, "".join(p["text"] for p in parts))
        for p in parts:
            self.assertEqual(p["text"], text[p["offset"]:p["end"]])
        self.assertEqual("最后的建议。", parts[-1]["text"])

    def test_formula_boundaries_preserve_original_indentation_and_following_prose(self):
        from markdown_it import MarkdownIt

        from epivra.markdown_rules import math_plugin
        parser = math_plugin(MarkdownIt("default"))
        raw = "$$\n x\n\n  y\n$$"
        self.assertEqual(raw, parser.parse(raw)[0].content)
        tokens = parser.parse("$$x$$ after\n\nnext\n\n$$y$$")
        self.assertEqual(["$$y$$"], [t.content for t in tokens if t.type == "math_block"])
        self.assertTrue(any(t.type == "inline" and t.content == "next" for t in tokens))

    def test_metrics_count_original_unicode_without_normalizing_whitespace(self):
        self.assertEqual(
            {"characters": 6, "non_whitespace_characters": 3},
            text_metrics("中 a\n😀\t"),
        )
