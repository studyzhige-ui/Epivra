from __future__ import annotations

import asyncio
import json
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx

from deep_research_agent.adapters import DeepSeek, JsonAPI
from deep_research_agent.application import ResearchService
from deep_research_agent.domain import Call, Reply
from deep_research_agent.harness import Harness
from deep_research_agent.host import Host, send, start
from deep_research_agent.storage import Store


class HostTests(unittest.IsolatedAsyncioTestCase):
    async def test_shared_cooldown_is_restored_from_durable_retry(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            host = Host(root)
            deadline = time.time() + 120
            host.store.create("s", "Research", {})
            host.store.put(
                "s", "retry", {"resource": "deepseek", "not_before": deadline}
            )
            host.store.close()
            restored = Host(root)
            try:
                self.assertEqual(deadline, restored.scheduler.deadlines["deepseek"])
            finally:
                restored.store.close()

    async def test_boot_failure_is_isolated_and_large_reconciliation_uses_ipc(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)

            class Model:
                identity = "fixture"

                async def complete(self, request):
                    return Reply(
                        "", (Call("propose_plan", {"text": "Plan"}),)
                    ).to_json()

            def factory(store, study):
                if study == "bad":
                    raise ValueError("configuration unavailable")
                return ResearchService(store, Harness(store, Model())), []

            host = Host(root, factory)
            c = host.store.create("bad", "Research", {})
            work = host.store.work("bad", c.ref, "lead", "Plan")
            host.store.admit("bad", work.ref, c.epoch, "lost", {"fixture": True})
            host.store.create("good", "Research", {})
            task = asyncio.create_task(host.serve())
            for _ in range(100):
                if (root / ".deep-research-agent/host.json").exists():
                    break
                await asyncio.sleep(0.01)
            try:
                status = await send(root, {"action": "status", "study": "bad"})
                self.assertEqual("ValueError", status["error"])
                for _ in range(100):
                    good = await send(root, {"action": "status", "study": "good"})
                    if good["plans"]:
                        break
                    await asyncio.sleep(0.01)
                self.assertTrue(good["plans"])
                c = host.store.command("bad", "pause", c.ref, "pause")
                raw = Reply("x" * 100000, ()).to_json()
                result = await send(
                    root,
                    {
                        "action": "reconcile",
                        "study": "bad",
                        "expected": c.ref,
                        "operation": "lost",
                        "receipt_id": "verified",
                        "result": raw,
                        "evidence": "provider receipt fixture",
                    },
                )
                self.assertTrue(result["paused"])
                self.assertEqual(raw, host.store.result("bad", "lost"))
                self.assertFalse(task.done())
            finally:
                await send(root, {"action": "shutdown"})
                await task

    async def test_reload_credentials_requires_paused_and_drained_work(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            root.joinpath(".env").write_text(
                "DEEPSEEK_API_KEY=new-fixture-key\n", encoding="utf-8"
            )
            async with httpx.AsyncClient(
                transport=httpx.MockTransport(lambda r: httpx.Response(200, json={}))
            ) as transport:
                api = JsonAPI("https://api.deepseek.com", "old-fixture-key", transport)

                def factory(store, study):
                    return ResearchService(store, Harness(store, DeepSeek(api))), [api]

                host = Host(root, factory)
                try:
                    c = host.store.create("s", "Research", {})
                    service = host.service("s")
                    request = {"token": host.token, "action": "reload", "study": "s"}
                    with self.assertRaises(ValueError):
                        await host.dispatch(request)
                    host.store.command("s", "pause", c.ref, "pause")
                    task = asyncio.create_task(asyncio.sleep(0.01))
                    service.tasks["s"] = task
                    with self.assertRaises(ValueError):
                        await host.dispatch(request)
                    await task
                    self.assertEqual({"reloaded": True}, await host.dispatch(request))
                    self.assertEqual("new-fixture-key", api._key)
                    self.assertTrue(host.store.control("s").paused)
                finally:
                    host.store.close()

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
