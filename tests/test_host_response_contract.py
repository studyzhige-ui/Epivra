"""Every interface distinguishes a blocked study from a failed status read."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from mcp import Client

from epivra.cli import Workbench
from epivra.host import response_failed
from epivra.mcp_server import build
from epivra.webui import App, WebError

BLOCKED = {"control": "observed-control", "error": "RepeatedFailure", "paused": True}
MISSING = {"error": "ValueError"}


class InterfaceResponseTests(unittest.IsolatedAsyncioTestCase):
    async def test_deleted_selected_cli_study_does_not_offer_controls(self):
        ui = SimpleNamespace(show=Mock(), choose=AsyncMock(return_value="pause"))
        sender = AsyncMock(return_value=MISSING)
        workbench = Workbench(Path("."), ui, sender)
        with self.assertRaises(ValueError):
            await workbench.study("deleted-study")
        ui.choose.assert_not_awaited()
        self.assertEqual(sender.await_count, 1)

    async def test_cli_preserves_real_blocked_status(self):
        ui = SimpleNamespace(show=Mock(), choose=AsyncMock(return_value=None))
        workbench = Workbench(Path("."), ui, AsyncMock(return_value=BLOCKED))
        self.assertEqual(await workbench.call("status", study="blocked"), BLOCKED)
        await workbench.study("blocked")
        ui.choose.assert_awaited_once()

    async def test_mcp_error_only_and_blocked_status_are_distinct(self):
        for response, failed in ((MISSING, True), (BLOCKED, False)):
            with self.subTest(response=response):
                server = build(Path("."), sender=AsyncMock(return_value=response))
                async with Client(server) as client:
                    result = await client.call_tool("research_status", {"study": "fixture"})
                self.assertEqual(bool(result.is_error), failed)
                if not failed:
                    self.assertEqual(result.structured_content, BLOCKED)


class WebResponseTests(unittest.TestCase):
    def test_web_preserves_same_status_contract(self):
        with tempfile.TemporaryDirectory() as folder:
            app = App(Path(folder), sender=AsyncMock(return_value=MISSING))
            with self.assertRaises(WebError):
                app.send({"action": "status", "study": "deleted"})
            app.sender = AsyncMock(return_value=BLOCKED)
            self.assertEqual(app.send({"action": "status", "study": "blocked"}), BLOCKED)

    def test_only_status_can_contain_a_nonfatal_blocker(self):
        self.assertFalse(response_failed("status", BLOCKED))
        self.assertTrue(response_failed("status", MISSING))
        self.assertTrue(response_failed("control", BLOCKED))
        self.assertFalse(response_failed("status", {"control": "ok"}))
