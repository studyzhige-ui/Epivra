from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

from deep_research_agent.adapters import IncompleteStream
from deep_research_agent.domain import Call, Conflict, Reply, UnknownOutcome
from deep_research_agent.harness import Harness, Tool, object_schema
from deep_research_agent.storage import Store


class RecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = Path(self.folder.name) / "research.db"
        self.store = Store(self.path)
        c = self.store.create("s", "Research", {})
        plan = self.store.put("s", "plan", {"text": "Plan"}, (c.direction,))
        self.c = self.store.command(
            "s", "approve", c.ref, "approve", {"plan": plan.ref}
        )
        self.work = self.store.work("s", self.c.ref, "researcher", "Investigate")

    async def asyncTearDown(self):
        self.store.close()
        self.folder.cleanup()

    def reopen(self):
        self.store.close()
        self.store = Store(self.path)

    async def test_successful_retry_replays_after_crash_before_observation(self):
        class Model:
            identity = "retry-fixture"
            calls = 0

            @staticmethod
            def retry_delay(raw, attempt):
                return 0 if raw.get("http_status") == 429 else None

            async def complete(inner, request):
                inner.calls += 1
                return (
                    {"http_status": 429}
                    if inner.calls == 1
                    else Reply("done", ()).to_json()
                )

        model = Model()
        harness = Harness(self.store, model)
        original = self.store.observation

        def crash(*args, **kwargs):
            raise RuntimeError("crash before adoption")

        self.store.observation = crash
        with self.assertRaisesRegex(RuntimeError, "crash"):
            await harness.step("s", self.work.ref)
        self.store.observation = original
        self.reopen()
        harness = Harness(self.store, model)
        await harness.step("s", self.work.ref)
        self.assertEqual(2, model.calls)
        self.assertEqual(1, len(self.store.list("s", "retry")))
        self.assertEqual([], self.store.unsettled("s"))
        retry = self.store.list("s", "retry")[0]
        self.assertEqual("done", harness._result("s", retry.body["operation"])["text"])

    async def test_pause_during_backoff_then_restart(self):
        entered = asyncio.Event()

        class Model:
            identity = "retry-fixture"
            calls = 0

            @staticmethod
            def retry_delay(raw, attempt):
                entered.set()
                return 0.3 if raw.get("http_status") == 429 else None

            async def complete(inner, request):
                inner.calls += 1
                return (
                    {"http_status": 429}
                    if inner.calls == 1
                    else Reply("done", ()).to_json()
                )

        model = Model()
        task = asyncio.create_task(Harness(self.store, model).step("s", self.work.ref))
        await entered.wait()
        c = self.store.command("s", "pause", self.c.ref, "pause")
        with self.assertRaises(Conflict):
            await asyncio.wait_for(task, 1)
        self.assertEqual(1, model.calls)
        self.reopen()
        self.store.command("s", "resume", c.ref, "resume")
        await Harness(self.store, model).step("s", self.work.ref)
        self.assertEqual(2, model.calls)

    async def test_unknown_retry_attempt_is_never_reissued(self):
        class Model:
            identity = "retry-fixture"
            calls = 0

            @staticmethod
            def retry_delay(raw, attempt):
                return 0 if raw.get("http_status") == 429 else None

            async def complete(inner, request):
                inner.calls += 1
                if inner.calls == 1:
                    return {"http_status": 429}
                raise IncompleteStream("fixture disconnect")

        model = Model()
        with self.assertRaises(IncompleteStream):
            await Harness(self.store, model).step("s", self.work.ref)
        self.reopen()
        with self.assertRaises(UnknownOutcome):
            await Harness(self.store, model).step("s", self.work.ref)
        self.assertEqual(2, model.calls)
        self.assertEqual(1, len(self.store.unsettled("s")))
        self.assertEqual([], self.store.list("s", "observation"))

    async def test_tool_retry_does_not_repeat_model_or_successful_tool(self):
        class Model:
            identity = "tool-retry-fixture"
            calls = 0

            async def complete(inner, request):
                inner.calls += 1
                return Reply("", (Call("lookup", {}),)).to_json()

        count = 0

        async def lookup(args):
            nonlocal count
            count += 1
            return {"http_status": 429 if count == 1 else 200}

        tool = Tool(
            "Lookup",
            object_schema({}),
            lookup,
            retry_delay=lambda raw, n: 0 if raw["http_status"] == 429 else None,
        )
        model = Model()
        await Harness(self.store, model, {"lookup": tool}).step("s", self.work.ref)
        self.assertEqual(1, model.calls)
        self.assertEqual(2, count)
        self.assertEqual(
            200,
            self.store.list("s", "observation")[0].body["result"]["value"][
                "http_status"
            ],
        )
