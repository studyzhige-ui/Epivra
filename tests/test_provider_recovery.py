from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from epivra.adapters import (
    DeepSeek,
    IncompleteStream,
    ProviderFailure,
    Tavily,
)
from epivra.domain import Call, Conflict, Reply, UnknownOutcome
from epivra.harness import Harness, object_schema
from epivra.harness import Tool as BaseTool
from epivra.storage import Store


def Tool(*args, **kwargs):
    kwargs.setdefault("roles", ("lead", "investigator", "reviewer"))
    return BaseTool(*args, **kwargs)


class RecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_search_quota_repair_reuses_paid_model_response(self):
        class Model:
            identity = "quota-fixture"
            calls = 0

            async def complete(inner, request):
                inner.calls += 1
                return Reply("", (Call("lookup", {}),)).to_json()

        calls = 0

        async def lookup(args):
            nonlocal calls
            calls += 1
            return {"http_status": 432 if calls == 1 else 200}

        def observe(raw, acquisition):
            if raw["http_status"] != 200:
                raise ProviderFailure("tavily", raw["http_status"])
            return {"recovered": True}

        tool = Tool(
            "Lookup",
            object_schema({}),
            lookup,
            observe=observe,
            retry_on_resume=Tavily.retry_on_resume,
        )
        model = Model()
        with self.assertRaises(ProviderFailure):
            await Harness(self.store, model, {"lookup": tool}).step("s", self.work.ref)
        self.reopen()
        self.store.command("s", "resume-quota", self.c.ref, "resume")
        await Harness(self.store, model, {"lookup": tool}).step("s", self.work.ref)
        self.assertEqual(1, model.calls)
        self.assertEqual(2, calls)
        self.assertTrue(
            self.store.list("s", "observation")[0].body["result"]["recovered"]
        )

    async def test_balance_rejection_requires_new_user_control_before_retry(self):
        class Model:
            identity = "balance-fixture"
            calls = 0
            funded = False
            retry_on_resume = staticmethod(DeepSeek.retry_on_resume)

            async def complete(inner, request):
                inner.calls += 1
                return (
                    Reply("done", ()).to_json()
                    if inner.funded
                    else {"http_status": 402}
                )

            def decode(inner, raw):
                if raw.get("http_status") == 402:
                    raise ProviderFailure("deepseek", 402)
                return raw

        model = Model()
        for _ in range(2):
            with self.assertRaises(ProviderFailure):
                await Harness(self.store, model).step("s", self.work.ref)
        self.assertEqual(1, model.calls)
        model.funded = True
        self.reopen()
        with self.assertRaises(ProviderFailure):
            await Harness(self.store, model).step("s", self.work.ref)
        c = self.store.control("s")
        self.store.command("s", "resume-funded", c.ref, "resume")
        await Harness(self.store, model).step("s", self.work.ref)
        self.assertEqual(2, model.calls)
        self.assertEqual(1, len(self.store.list("s", "retry")))

    async def test_failed_balance_repair_does_not_loop(self):
        class Model:
            identity = "balance-fixture"
            calls = 0
            retry_on_resume = staticmethod(DeepSeek.retry_on_resume)

            async def complete(inner, request):
                inner.calls += 1
                return {"http_status": 402}

            def decode(inner, raw):
                raise ProviderFailure("deepseek", 402)

        model = Model()
        with self.assertRaises(ProviderFailure):
            await Harness(self.store, model).step("s", self.work.ref)
        self.store.command("s", "resume-unfunded", self.c.ref, "resume")
        with self.assertRaises(ProviderFailure):
            await Harness(self.store, model).step("s", self.work.ref)
        self.assertEqual(2, model.calls)
        self.assertEqual([], self.store.unsettled("s"))

    async def asyncSetUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = Path(self.folder.name) / "research.db"
        self.store = Store(self.path)
        c = self.store.create("s", "Research", {})
        plan = self.store.put("s", "plan", {"text": "Plan"}, (c.direction,))
        self.c = self.store.command(
            "s", "approve", c.ref, "approve", {"plan": plan.ref}
        )
        self.work = self.store.work("s", self.c.ref, "lead", "Investigate")

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
        # Keep the retry deadline in the future even if a durable write takes
        # longer than the fixture's delay. Test event order, not disk speed.
        with patch("epivra.harness.time", SimpleNamespace(time=lambda: 1000.0)):
            task = asyncio.create_task(
                Harness(self.store, model).step("s", self.work.ref)
            )
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
