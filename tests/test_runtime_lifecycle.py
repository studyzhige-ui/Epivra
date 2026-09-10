from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from deep_research_agent.domain import Conflict, UnknownOutcome, identity
from deep_research_agent.harness import Harness
from deep_research_agent.materials import parse_isolated
from deep_research_agent.scheduling import Scheduler
from deep_research_agent.storage import Store


class LifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_parser_timeout_and_cancellation_reap_real_child(self):
        launch = asyncio.create_subprocess_exec
        for cancel in (False, True):
            children = []
            ready = asyncio.Event()

            async def slow(*args, **kwargs):
                child = await launch(
                    sys.executable, "-c", "import time; time.sleep(30)", **kwargs
                )
                children.append(child)
                ready.set()
                return child

            with patch("asyncio.create_subprocess_exec", side_effect=slow):
                task = asyncio.create_task(
                    parse_isolated("file.txt", b"text", 0.1 if not cancel else 30)
                )
                await ready.wait()
                if cancel:
                    task.cancel()
                with self.assertRaises(
                    asyncio.CancelledError if cancel else ValueError
                ):
                    await task
            self.assertIsNotNone(children[0].returncode)

    async def test_parser_environment_does_not_inherit_credentials(self):
        launch = asyncio.create_subprocess_exec

        async def inspected(*args, **kwargs):
            self.assertNotIn("DEEPSEEK_API_KEY", kwargs["env"])
            self.assertNotIn("TAVILY_API_KEY", kwargs["env"])
            return await launch(*args, **kwargs)

        with (
            patch.dict(
                os.environ, {"DEEPSEEK_API_KEY": "fixture", "TAVILY_API_KEY": "fixture"}
            ),
            patch("asyncio.create_subprocess_exec", side_effect=inspected),
        ):
            result = await parse_isolated("中文.txt", "证据".encode())
        self.assertEqual("证据", result["text"])

    async def test_paused_queue_leaves_without_waiting_for_active_call(self):
        scheduler = Scheduler(1)
        paused = False

        def check():
            if paused:
                raise Conflict("paused")

        async def queued():
            async with scheduler.slot("provider", check):
                self.fail("paused work entered slot")

        async with scheduler.slot("provider", lambda: None):
            task = asyncio.create_task(queued())
            await asyncio.sleep(0.01)
            self.assertEqual(1, scheduler.snapshot()["provider"]["waiting"])
            paused = True
            with self.assertRaises(Conflict):
                await asyncio.wait_for(task, 1)
            self.assertEqual(1, scheduler.snapshot()["provider"]["active"])
            self.assertEqual(0, scheduler.snapshot()["provider"]["waiting"])
        self.assertEqual(0, scheduler.snapshot()["provider"]["active"])

    async def test_late_rate_limit_is_durable_and_shared_after_pause(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder) / "state.db")
            try:
                c = store.create("s", "Research", {})
                work = store.work("s", c.ref, "planner", "Plan")
                entered, release = asyncio.Event(), asyncio.Event()

                class Model:
                    identity = "fixture"
                    resource = "provider"

                    async def complete(self, request):
                        entered.set()
                        await release.wait()
                        return {"http_status": 429}

                    def retry_delay(self, raw, attempt):
                        return 30

                harness = Harness(store, Model())
                task = asyncio.create_task(harness.step("s", work.ref))
                await entered.wait()
                store.command("s", "pause", c.ref, "pause")
                release.set()
                with self.assertRaises(Conflict):
                    await task
                retry = store.list("s", "retry")[0]
                self.assertEqual(
                    retry.body["not_before"], harness.scheduler.deadlines["provider"]
                )
                self.assertEqual([], store.unsettled("s"))
            finally:
                store.close()

    async def test_unknown_does_not_enter_busy_provider_queue(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder) / "state.db")
            try:
                c = store.create("s", "Research", {})
                work = store.work("s", c.ref, "planner", "Plan")

                class Model:
                    identity = "fixture"

                    async def complete(self, request):
                        raise AssertionError("must not send")

                scheduler = Scheduler(1)
                harness = Harness(store, Model(), scheduler=scheduler)
                request = harness._request("s", work)
                step = store.put(
                    "s", "step", {"number": 0, "request": request}, (work.ref,)
                )
                store.admit(
                    "s",
                    work.ref,
                    c.epoch,
                    identity("model", work.ref, step.ref),
                    request,
                )
                async with scheduler.slot("model", lambda: None):
                    with self.assertRaises(UnknownOutcome):
                        await asyncio.wait_for(harness.step("s", work.ref), 0.5)
            finally:
                store.close()
