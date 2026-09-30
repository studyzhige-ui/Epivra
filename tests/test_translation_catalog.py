"""Presentation templates remain complete without translating research data."""

import ast
import re
import unittest
from pathlib import Path

from epivra import locale


class TranslationCatalogTests(unittest.TestCase):
    def test_chinese_python_templates_have_english_entries(self):
        root = Path(locale.__file__).parent
        missing = []
        for path in root.glob("*.py"):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "tr"
                    and node.args
                    and isinstance(node.args[0], ast.Constant)
                    and isinstance(node.args[0].value, str)
                ):
                    message = node.args[0].value
                    if re.search(r"[\u4e00-\u9fff]", message) and message not in locale.MESSAGES:
                        missing.append((path.name, node.lineno, message))
        self.assertEqual(missing, [])

    def test_translation_preserves_placeholder_contract(self):
        for source, translated in locale.MESSAGES.items():
            with self.subTest(source=source):
                self.assertIsInstance(translated, str)
                self.assertEqual(
                    sorted(re.findall(r"\{\d+\}", source)),
                    sorted(re.findall(r"\{\d+\}", translated)),
                )

    def test_missing_privacy_disclosure_is_now_english(self):
        message = "Jev 会将选定原文发送至 TypeSafe，包括本地资料。"
        self.assertEqual(locale.tr(message, language="zh-CN"), message)
        self.assertEqual(
            locale.tr(message, language="en"),
            "Jev sends selected original text, including local materials, to TypeSafe.",
        )
