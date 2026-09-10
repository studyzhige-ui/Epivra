from __future__ import annotations

import asyncio
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from deep_research_agent.application import ResearchService
from deep_research_agent.domain import Call, Reply
from deep_research_agent.harness import Harness
from deep_research_agent.host import Host, send, start
from deep_research_agent.storage import Store


class HostTests(unittest.IsolatedAsyncioTestCase):
    async def test_start_checks_readiness_and_reuses_running_host(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            children = []
            popen = subprocess.Popen

            def launch(*args, **kwargs):
                child = popen(*args, **kwargs)
                children.append(child)
                return child

            try:
                with patch("subprocess.Popen", side_effect=launch):
                    result = await start(root)
                self.assertTrue(result["ready"])
                self.assertEqual({"already_running": True}, await start(root))
                self.assertEqual({"studies": []}, await send(root, {"action": "list"}))
            finally:
                await send(root, {"action": "shutdown"})
                for child in children:
                    await asyncio.to_thread(child.wait, timeout=5)

    async def test_startup_failure_releases_database_ownership(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            host = Host(root)
            with patch(
                "asyncio.start_server", new=AsyncMock(side_effect=OSError("fixture"))
            ):
                with self.assertRaises(OSError):
                    await host.serve()
            store = Store(root / ".deep-research-agent/research.db")
            store.close()

    async def test_previous_direction_report_is_not_current_delivery(self):
        with tempfile.TemporaryDirectory() as folder:
            host = Host(Path(folder))
            try:
                c = host.store.create("s", "Old question", {})
                report = host.store.put(
                    "s",
                    "report",
                    {"text": "Old result", "evidence": []},
                    (c.direction,),
                )
                host.store._put(
                    "s",
                    "publication",
                    {"report": report.ref},
                    (c.direction, report.ref),
                )
                request = {"token": host.token, "action": "report", "study": "s"}
                self.assertEqual("Old result", (await host.dispatch(request))["text"])
                host.store.command(
                    "s", "steer", c.ref, "steer", {"request": "New question"}
                )
                self.assertEqual({"report": None}, await host.dispatch(request))
            finally:
                host.store.close()

    async def test_disconnect_and_pause_do_not_destroy_research(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            entered, release = asyncio.Event(), asyncio.Event()

            class Model:
                identity = "host-fixture"
                calls = 0

                async def complete(inner, request):
                    inner.calls += 1
                    entered.set()
                    await release.wait()
                    return Reply(
                        "", (Call("propose_plan", {"text": "Plan"}),)
                    ).to_json()

            model = Model()

            def factory(store, study):
                return ResearchService(store, Harness(store, model)), []

            host = Host(root, factory)
            task = asyncio.create_task(host.serve())
            pointer = root / ".deep-research-agent/host.json"
            for _ in range(100):
                if pointer.exists():
                    break
                await asyncio.sleep(0.01)
            try:
                created = await send(root, {"action": "create", "request": "Research"})
                study = created["study"]
                await entered.wait()
                status = await send(root, {"action": "status", "study": study})
                self.assertTrue(status["running"])
                paused = await send(
                    root,
                    {
                        "action": "control",
                        "study": study,
                        "command": "pause",
                        "command_id": "pause1",
                        "expected": status["control"],
                    },
                )
                self.assertTrue(paused["paused"])
                release.set()
                await asyncio.sleep(0.05)
                paused_status = await send(root, {"action": "status", "study": study})
                self.assertTrue(paused_status["paused"])
                self.assertEqual([], paused_status["plans"])
                resumed = await send(
                    root,
                    {
                        "action": "control",
                        "study": study,
                        "command": "resume",
                        "command_id": "resume1",
                        "expected": paused_status["control"],
                    },
                )
                self.assertFalse(resumed["paused"])
                for _ in range(100):
                    status = await send(root, {"action": "status", "study": study})
                    if status["plans"]:
                        break
                    await asyncio.sleep(0.01)
                self.assertEqual(1, len(status["plans"]))
                self.assertEqual(1, model.calls)
                info = json.loads(pointer.read_text())
                reader, writer = await asyncio.open_connection(
                    "127.0.0.1", info["port"]
                )
                writer.write(b'{"action":"shutdown","token":"wrong"}\n')
                await writer.drain()
                self.assertEqual(
                    {"error": "unauthorized"}, json.loads(await reader.readline())
                )
                writer.close()
                await writer.wait_closed()
                self.assertFalse(task.done())
            finally:
                release.set()
                await send(root, {"action": "shutdown"})
                await asyncio.wait_for(task, 2)
            self.assertFalse(pointer.exists())
