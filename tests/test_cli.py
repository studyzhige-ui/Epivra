import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput

from deep_research_agent import cli_settings
from deep_research_agent.cli import Workbench, stage, strategy
from deep_research_agent.host import Host
from deep_research_agent.terminal import Terminal, clean, native_path


class UI:
    def __init__(self, choices=(), texts=(), confirms=(), paths=()):
        self.choices, self.texts = iter(choices), iter(texts)
        self.confirms, self.paths = iter(confirms), iter(paths)
        self.messages = []

    async def choose(self, *args, **kwargs):
        return next(self.choices)

    async def text(self, *args, **kwargs):
        return next(self.texts)

    async def confirm(self, *args, **kwargs):
        return next(self.confirms)

    async def path(self, *args, **kwargs):
        return next(self.paths)

    def show(self, text="", **kwargs):
        self.messages.append(text)

    def page(self, text):
        self.messages.append(text)


class CLITests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.host = Host(self.root)
        self.host.start_study = lambda study: None

    async def asyncTearDown(self):
        for service in self.host.services.values():
            await service.close()
        for clients in self.host.clients.values():
            for client in clients:
                await client.close()
        self.host.store.close()
        self.temp.cleanup()

    async def send(self, root, request):
        return await self.host.dispatch({**request, "token": self.host.token})

    async def test_new_imports_exact_file_before_resuming_no_directory_grant(self):
        path = self.root / "中文资料.txt"
        path.write_text("用户提供的完整材料", encoding="utf-8")
        ui = UI(
            choices=["local", "file", "done", None],
            texts=["研究这个材料"],
            confirms=[True],
            paths=[path],
        )
        with patch(
            "deep_research_agent.cli.cli_settings.configured",
            return_value={"DEEPSEEK_API_KEY"},
        ):
            await Workbench(self.root, ui, self.send).new()
        study = (await self.send(self.root, {"action": "list"}))["studies"][0]
        c = self.host.store.control(study)
        self.assertFalse(c.paused)
        self.assertFalse(c.approved)
        self.assertEqual(
            [], self.host.store.get(study, c.direction).body["policy"]["local_roots"]
        )
        self.assertEqual(1, len(self.host.store.list(study, "source")))
        self.assertEqual([], self.host.store.list(study, "operation"))

    async def test_failed_import_leaves_recoverable_paused_draft(self):
        path = self.root / "input.txt"
        path.write_text("data", encoding="utf-8")

        async def fail(root, request):
            if request["action"] == "import_file":
                raise ValueError("parse failure")
            return await self.send(root, request)

        ui = UI(
            choices=["local", "file", "done"],
            texts=["question"],
            confirms=[True],
            paths=[path],
        )
        with patch(
            "deep_research_agent.cli.cli_settings.configured",
            return_value={"DEEPSEEK_API_KEY"},
        ):
            with self.assertRaises(ValueError):
                await Workbench(self.root, ui, fail).new()
        study = (await self.send(self.root, {"action": "list"}))["studies"][0]
        self.assertTrue(self.host.store.control(study).paused)

    async def test_cancel_picker_never_creates_study(self):
        ui = UI(choices=["local", "folder", None], texts=["question"], paths=[None])
        with patch(
            "deep_research_agent.cli.cli_settings.configured",
            return_value={"DEEPSEEK_API_KEY"},
        ):
            await Workbench(self.root, ui, self.send).new()
        self.assertEqual(
            [], (await self.send(self.root, {"action": "list"}))["studies"]
        )

    async def test_exact_displayed_approval_conflict_is_not_retried(self):
        calls = []
        status = {
            "control": "old-control",
            "plans": [{"ref": "exact-plan", "body": {"text": "displayed original"}}],
        }

        async def send(root, request):
            calls.append(request)
            return status if request["action"] == "status" else {"error": "Conflict"}

        ui = UI(choices=["approve"], confirms=[True])
        with self.assertRaisesRegex(ValueError, "状态已变化"):
            await Workbench(self.root, ui, send).study("s")
        self.assertIn("displayed original", ui.messages)
        self.assertEqual(2, len(calls))
        self.assertEqual("old-control", calls[1]["expected"])
        self.assertEqual({"plan": "exact-plan"}, calls[1]["payload"])

    async def test_overview_filters_old_plans_and_never_needs_credentials(self):
        c = self.host.store.create("s", "旧方向", {})
        self.host.store.put("s", "plan", {"text": "old"}, (c.direction,))
        self.host.store.command("s", "steer", c.ref, "steer", {"request": "新的方向"})
        summary = (await self.send(self.root, {"action": "overview"}))["studies"][0]
        self.assertEqual("新的方向", summary["request"])
        self.assertEqual([], summary["plans"])

    async def test_leave_watch_does_not_send_control(self):
        send = AsyncMock(return_value={"approved": True, "running": True})
        ui = UI(texts=[""])
        await Workbench(self.root, ui, send).watch("s")
        self.assertTrue(
            all(call.args[1]["action"] == "status" for call in send.call_args_list)
        )

    async def test_stale_report_returns_to_study(self):
        async def send(root, request):
            return (
                {"published": True, "cancelled": True}
                if request["action"] == "status"
                else {"report": None}
            )

        ui = UI(choices=["report", None])
        await Workbench(self.root, ui, send).study("s")
        self.assertTrue(any("正在刷新" in text for text in ui.messages))

    async def test_keyboard_select_text_escape_and_password(self):
        # Real prompt toolkit input, no paid backend and no fake selection implementation.
        with (
            create_pipe_input() as pipe,
            create_app_session(input=pipe, output=DummyOutput()),
        ):
            ui = Terminal()
            task = asyncio.create_task(
                ui.choose("选择", [("one", "第一项"), ("two", "第二项")])
            )
            await asyncio.sleep(0.02)
            pipe.send_text("\x1b[B\r")
            self.assertEqual("two", await asyncio.wait_for(task, 2))
            task = asyncio.create_task(ui.choose("选择", [("one", "第一项")]))
            await asyncio.sleep(0.02)
            pipe.send_text("\x1b")
            self.assertIsNone(await asyncio.wait_for(task, 3))
            task = asyncio.create_task(ui.choose("选择", [("one", "第一项")]))
            await asyncio.sleep(0.02)
            pipe.send_text("\x1b[B\r")
            self.assertIsNone(await asyncio.wait_for(task, 2))
            task = asyncio.create_task(ui.text("输入"))
            await asyncio.sleep(0.02)
            pipe.send_text("中文研究\r")
            self.assertEqual("中文研究", await asyncio.wait_for(task, 2))


class CLISettingsTests(unittest.TestCase):
    def test_secret_update_preserves_other_keys_and_comments(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".env").write_text(
                "# 用户配置\nTAVILY_API_KEY=fixture\nDEEPSEEK_API_KEY=old\n",
                encoding="utf-8",
            )
            cli_settings.save_key(root, "DEEPSEEK_API_KEY", "new-test-value")
            content = (root / ".env").read_text(encoding="utf-8")
            self.assertIn("# 用户配置", content)
            self.assertIn("TAVILY_API_KEY=fixture", content)
            self.assertNotIn("=old", content)
            with self.assertRaises(ValueError):
                cli_settings.save_key(root, "DEEPSEEK_API_KEY", "value\nEVIL=x")
            self.assertEqual([], list(root.glob(".settings-*.tmp")))

    def test_native_cancel_and_cleanup(self):
        with (
            patch("tkinter.Tk") as tk,
            patch("tkinter.filedialog.askdirectory", return_value=""),
        ):
            self.assertIsNone(native_path(directory=True))
            tk.return_value.destroy.assert_called_once()

    def test_rendered_input_has_no_terminal_escape(self):
        self.assertNotIn("\x1b", clean("test\x1b[2J"))
        self.assertEqual("已完成", stage({"published": True}))
        plan = strategy(
            {
                "text": "方法",
                "brief": {
                    "subject": "对象",
                    "given_context": ["背景"],
                    "questions": ["问题"],
                    "material_scope": {"mode": "library", "basis": "依据"},
                },
            }
        )
        for text in ("方法", "对象", "背景", "问题", "待检索的资料库", "依据"):
            self.assertIn(text, plan)
