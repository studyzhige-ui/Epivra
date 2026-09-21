"""Language affects presentation, not user content or collaboration contracts."""

import asyncio
import re
import tempfile
import unittest
from pathlib import Path

from epivra.cli import stage, strategy
from epivra.locale import MESSAGES, set_language, tr


class LocaleTests(unittest.TestCase):
    def tearDown(self):
        set_language("zh-CN")

    def test_translated_templates_preserve_placeholders_and_user_text(self):
        for source, translated in MESSAGES.items():
            self.assertEqual(
                set(re.findall(r"\{\d+\}", source)),
                set(re.findall(r"\{\d+\}", translated)),
                source,
            )
        set_language("en")
        self.assertEqual(stage({"paused": True}), "Paused")
        user_text = "原始资料 {0} Research 研究"
        rendered = strategy({"text": user_text, "brief": {"subject": user_text}})
        self.assertEqual(rendered.count(user_text), 2)
        self.assertIn("Research scope and questions", rendered)
        self.assertEqual(tr("已选择：") + user_text, "Selected: " + user_text)
        set_language("zh-CN")
        self.assertEqual(stage({"paused": True}), "已暂停")

    def test_language_is_isolated_between_tasks(self):
        async def render(language):
            set_language(language)
            await asyncio.sleep(0)
            return tr("研究")

        async def run():
            return await asyncio.gather(render("en"), render("zh-CN"))

        self.assertEqual(asyncio.run(run()), ["Research", "研究"])

    def test_mcp_descriptions_change_but_contracts_and_results_do_not(self):
        try:
            from mcp import Client
        except ImportError:
            self.skipTest("Install the mcp extension")
        from epivra.mcp_server import build

        async def sender(root, request):
            return {"text": "原始报告 {0}", "sources": []}

        async def inspect(root, language):
            async with Client(build(root, sender=sender, language=language)) as client:
                tools = (await client.list_tools()).tools
                report = await client.call_tool("read_report", {"study": "sample"})
                return tools, report.structured_content

        with tempfile.TemporaryDirectory() as folder:
            en, en_report = asyncio.run(inspect(Path(folder), "en"))
            zh, zh_report = asyncio.run(inspect(Path(folder), "zh-CN"))
        self.assertEqual(en_report, zh_report)
        self.assertIn("原始报告", str(en_report))
        self.assertEqual([t.name for t in en], [t.name for t in zh])
        for english, chinese in zip(en, zh, strict=True):
            self.assertEqual(english.input_schema, chinese.input_schema)
            self.assertNotEqual(english.description, chinese.description)
