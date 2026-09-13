import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from epivra.scheduling import Scheduler
from epivra.storage import Store
from epivra.usage import counters, summarize


class UsageTests(unittest.TestCase):
    def test_native_and_chat_counts_do_not_double_count_cache_or_reasoning(self):
        claude = counters(
            {
                "data": {
                    "usage": {
                        "input_tokens": 10,
                        "output_tokens": 20,
                        "cache_read_input_tokens": 80,
                        "cache_creation_input_tokens": 5,
                    }
                }
            }
        )
        self.assertEqual((95, 115), (claude["input_tokens"], claude["total_tokens"]))
        chat = counters(
            {
                "data": {
                    "usage": {
                        "prompt_tokens": 95,
                        "completion_tokens": 20,
                        "total_tokens": 115,
                        "prompt_cache_hit_tokens": 80,
                        "completion_tokens_details": {"reasoning_tokens": 12},
                    }
                }
            }
        )
        self.assertEqual(
            (115, 80, 12),
            (chat["total_tokens"], chat["cache_read_tokens"], chat["reasoning_tokens"]),
        )
        gemini = counters(
            {
                "data": {
                    "usageMetadata": {
                        "promptTokenCount": 95,
                        "candidatesTokenCount": 8,
                        "thoughtsTokenCount": 12,
                        "totalTokenCount": 115,
                    }
                }
            }
        )
        self.assertEqual((20, 115), (gemini["output_tokens"], gemini["total_tokens"]))
        self.assertEqual(
            0, counters({"data": {"usage": {"credits": 0}}})["search_credits"]
        )
        self.assertTrue(all(v is None for v in counters({}).values()))

    def test_replay_reopen_and_reconciliation_have_one_usage_entry(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "research.db"
            store = Store(path)
            c = store.create("s", "Research", {})
            work = store.work("s", c.ref, "lead", "Investigate")
            request = {"wire": {"payload": {"model": "test"}}}
            receipt = {"data": {"usage": {"prompt_tokens": 10, "completion_tokens": 3}}}
            store.admit(
                "s",
                work.ref,
                c.epoch,
                "one",
                request,
                admission={
                    "at": 100,
                    "tokens": 20,
                    "resource": "account",
                    "model": "test",
                },
            )
            store.settle("one", receipt)
            self.assertEqual(
                receipt, store.admit("s", work.ref, c.epoch, "one", request)
            )
            store.admit("s", work.ref, c.epoch, "unknown", request)
            store.close()
            store = Store(path)
            try:
                rows = store.usage_records("s")
                self.assertEqual(2, len(rows))
                self.assertEqual(13, rows[0]["usage"]["total_tokens"])
                self.assertIsNone(rows[1]["usage"]["total_tokens"])
                self.assertEqual(1, len(store.admissions()))
                self.assertEqual(13, summarize(rows)[0]["totals"]["total_tokens"])
                c = store.command("s", "pause", c.ref, "pause")
                store.reconcile(
                    "s", c.ref, "unknown", "receipt", receipt, "official receipt"
                )
                rows = store.usage_records("s")
                self.assertEqual(2, len(rows))
                self.assertEqual(26, sum(r["usage"]["total_tokens"] for r in rows))
            finally:
                store.close()


class RateTests(unittest.IsolatedAsyncioTestCase):
    async def test_shared_sliding_window_and_restart(self):
        now = [100.0]
        scheduler = Scheduler(
            limits={"account": {"rpm": 2, "tpm": 30}}, clock=lambda: now[0]
        )
        async with scheduler.slot("account", lambda: None, 20):
            pass
        now[0] += 10
        async with scheduler.slot("account", lambda: None, 10):
            pass
        self.assertEqual(50, scheduler.rate_delay("account", 1))
        self.assertEqual(60, scheduler.rate_delay("account", 25))
        self.assertEqual(0, scheduler.rate_delay("other", 30))
        restored = Scheduler(
            limits=scheduler.limits,
            clock=lambda: now[0],
            history=[
                {"resource": "account", "at": t, "tokens": n}
                for t, n in scheduler.history["account"]
            ],
        )
        self.assertEqual(60, restored.rate_delay("account", 25))
        now[0] = 170
        self.assertEqual(0, restored.rate_delay("account", 25))

    async def test_wait_rechecks_pause_and_releases_capacity(self):
        scheduler = Scheduler(
            limits={"p": {"rpm": 1, "concurrency": 1}}, clock=lambda: 100
        )
        async with scheduler.slot("p", lambda: None):
            pass
        checks = []

        def check():
            checks.append(1)
            if len(checks) > 2:
                raise ValueError("paused")

        with self.assertRaisesRegex(ValueError, "paused"):
            async with scheduler.slot("p", check):
                self.fail("must not send")
        self.assertEqual(0, scheduler.waiting["p"])
        self.assertEqual(1, scheduler.semaphores["p"]._value)
        self.assertEqual(1, len(scheduler.history["p"]))

    async def test_oversized_request_fails_without_admission_or_hanging(self):
        scheduler = Scheduler(limits={"p": {"tpm": 20}})
        with self.assertRaisesRegex(ValueError, "exceeds"):
            async with scheduler.slot("p", lambda: None, 21):
                self.fail("must not send")
        self.assertFalse(scheduler.history.get("p"))

    async def test_rate_wait_actually_delays_send_until_capacity_returns(self):
        now = [100.0]
        scheduler = Scheduler(limits={"p": {"rpm": 1}}, clock=lambda: now[0])
        async with scheduler.slot("p", lambda: None):
            pass

        async def advance(delay):
            now[0] += delay

        with patch("epivra.scheduling.asyncio.sleep", advance):
            async with scheduler.slot("p", lambda: None):
                self.assertGreaterEqual(now[0], 160)

    async def test_concurrency_is_shared(self):
        scheduler = Scheduler(limits={"p": {"concurrency": 1}})
        entered = asyncio.Event()

        async def second():
            async with scheduler.slot("p", lambda: None):
                entered.set()

        async with scheduler.slot("p", lambda: None):
            task = asyncio.create_task(second())
            await asyncio.sleep(0.01)
            self.assertFalse(entered.is_set())
        await task
        self.assertTrue(entered.is_set())
