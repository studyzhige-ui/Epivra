"""Offline regressions for control epochs and durable, joint send admission."""

import asyncio
import base64
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from epivra.agent_runtime import AgentRuntime
from epivra.application import ResearchService
from epivra.domain import Conflict, UnknownOutcome
from epivra.harness import Harness
from epivra.host import Host
from epivra.scheduling import Scheduler
from epivra.storage import Store


async def until(predicate):
    async with asyncio.timeout(2):
        while not predicate():
            await asyncio.sleep(0.001)


class OfflineModel:
    identity = "offline-model"
    max_tokens = 1
    context_tokens = 10000


class InvocationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.directory.name) / "research.db")
        self.now = 100.0
        self.runtime = AgentRuntime(1)
        self.scheduler = Scheduler(clock=lambda: self.now)
        self.harness = Harness(self.store, OfflineModel(), scheduler=self.scheduler)
        self.harness.agent_runtime = self.runtime

    def tearDown(self):
        self.store.close()
        self.directory.cleanup()

    def request(self, study):
        control = self.store.create(study, "offline test", {})
        work = self.store.work(study, control.ref, "lead", "route")
        request = {"wire": {"estimated_input_tokens": 1, "payload": {"model": "offline"}}}
        step = self.store.put(study, "step", {"request": request}, (work.ref,))
        return SimpleNamespace(study=study, control=control, work=work, request=request, step=step)

    async def invoke(self, request, send, *, epoch=None):
        return await self.harness._invoke(
            request.study, request.work.ref,
            request.control.epoch if epoch is None else epoch,
            request.step.ref, "operation-" + request.study, request.request, send,
            resource="limited", request_step=request.step.ref,
        )

    def resume(self, request):
        control = self.store.control(request.study)
        control = self.store.command(request.study, "pause", control.ref, "pause")
        return self.store.command(request.study, "resume", control.ref, "resume")

    async def assert_queued_rate(self, limit):
        self.scheduler.limits = {"limited": limit}
        requests = [self.request("one"), self.request("two")]
        sends = []

        async def send():
            sends.append(self.now)
            return {"http_status": 200, "data": {}}

        async with self.runtime.turn("unrelated", "slow", lambda: None):
            tasks = [asyncio.create_task(self.invoke(requests[0], send))]
            await until(lambda: len(self.runtime.pending) == 1)
            self.assertFalse(self.scheduler.history.get("limited"))
            self.assertEqual(self.store.admissions(), [])
            self.assertEqual(self.scheduler.active.get("limited", 0), 0)
            self.now = 161.0
            tasks.append(asyncio.create_task(self.invoke(requests[1], send)))
            await until(lambda: len(self.runtime.pending) == 2)
        await until(lambda: len(sends) == 1 and not self.runtime.active)
        self.assertEqual(sends, [161.0])
        # The second request must release its Agent turn while rate-limited.
        async with asyncio.timeout(1):
            async with self.runtime.turn("unrelated", "ready", lambda: None):
                self.assertEqual(len(sends), 1)
        self.now = 221.0
        await asyncio.wait_for(asyncio.gather(*tasks), 2)
        self.assertEqual(sends, [161.0, 221.0])
        self.assertEqual(
            [(row["at"], row["timing"]["invoked_at"]) for row in self.store.admissions()],
            [(161.0, 161.0), (221.0, 221.0)],
        )
        self.assertFalse(self.runtime.pending)
        self.assertFalse(self.runtime.active)

    async def test_rpm_is_committed_after_agent_queue(self):
        await self.assert_queued_rate({"rpm": 1})

    async def test_tpm_is_committed_after_agent_queue(self):
        await self.assert_queued_rate({"tpm": 2})

    async def test_paused_unsent_request_withdraws_without_other_study_finishing(self):
        request = self.request("paused")

        async def send():
            self.fail("paused queued request was sent")

        async with self.runtime.turn("other", "slow", lambda: None):
            task = asyncio.create_task(self.invoke(request, send))
            await until(lambda: bool(self.runtime.pending))
            self.store.command("paused", "pause", request.control.ref, "pause")
            with self.assertRaises(Conflict):
                await asyncio.wait_for(task, 1)
            self.assertFalse(self.runtime.pending)
            self.assertEqual(len(self.runtime.active), 1)
            self.assertEqual(self.store.admissions(), [])
            self.assertFalse(self.scheduler.history.get("limited"))

    async def test_cancellation_withdraws_repeated_queued_requests(self):
        request = self.request("cancelled")
        async with self.runtime.turn("other", "slow", lambda: None):
            for _ in range(4):
                task = asyncio.create_task(self.invoke(request, lambda: None))
                await until(lambda: bool(self.runtime.pending))
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task
                self.assertFalse(self.runtime.pending)
                self.assertEqual(self.scheduler.waiting["limited"], 0)
            self.assertEqual(self.store.admissions(), [])

    async def test_pause_settles_sent_result_and_resume_reuses_it(self):
        request = self.request("settled")
        entered, release = asyncio.Event(), asyncio.Event()
        calls = 0

        async def send():
            nonlocal calls
            calls += 1
            entered.set()
            await release.wait()
            return {"http_status": 200, "data": {"answer": "saved"}}

        task = asyncio.create_task(self.invoke(request, send))
        await entered.wait()
        resumed = self.resume(request)
        release.set()
        with self.assertRaises(Conflict):
            await task
        result = await self.invoke(request, send, epoch=resumed.epoch)
        self.assertEqual(result["data"]["answer"], "saved")
        self.assertEqual(calls, 1)
        self.assertEqual(len(self.store.admissions()), 1)

    async def test_unknown_sent_request_is_not_replayed_on_resume_or_restart(self):
        request = self.request("unknown")
        entered = asyncio.Event()
        calls = 0

        async def send():
            nonlocal calls
            calls += 1
            entered.set()
            await asyncio.Event().wait()

        task = asyncio.create_task(self.invoke(request, send))
        await entered.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        resumed = self.resume(request)
        with self.assertRaises(UnknownOutcome):
            await self.invoke(request, send, epoch=resumed.epoch)
        self.store.close()
        self.store = Store(Path(self.directory.name) / "research.db")
        self.scheduler = Scheduler(history=self.store.admissions(), clock=lambda: self.now)
        self.harness = Harness(self.store, OfflineModel(), scheduler=self.scheduler)
        self.harness.agent_runtime = self.runtime
        with self.assertRaises(UnknownOutcome):
            await self.invoke(request, send, epoch=resumed.epoch)
        self.assertEqual(calls, 1)
        self.assertEqual(len(self.store.unsettled(request.study)), 1)

    def test_restart_uses_actual_send_time_and_conservative_unknown_admission(self):
        scheduler = Scheduler(
            limits={"limited": {"rpm": 1}}, clock=lambda: 170.0,
            history=[{"at": 100.0, "resource": "limited", "tokens": 2,
                      "timing": {"invoked_at": 161.0}}],
        )
        self.assertEqual(scheduler.rate_delay("limited", 2), 51.0)
        scheduler = Scheduler(
            limits={"limited": {"tpm": 2}}, clock=lambda: 170.0,
            history=[{"at": 161.0, "resource": "limited", "tokens": 2}],
        )
        self.assertEqual(scheduler.rate_delay("limited", 1), 51.0)

    async def test_provider_capacity_is_rechecked_after_waiting_for_agent(self):
        self.scheduler.limits = {"limited": {"concurrency": 1}}
        self.runtime.capacity = 2
        first, second = self.request("first"), self.request("second")
        entered, release = asyncio.Event(), asyncio.Event()
        active = 0

        async def send():
            nonlocal active
            active += 1
            self.assertEqual(active, 1)
            entered.set()
            await release.wait()
            active -= 1
            return {"http_status": 200, "data": {}}

        tasks = [asyncio.create_task(self.invoke(request, send)) for request in (first, second)]
        await entered.wait()
        self.assertEqual(self.scheduler.active["limited"], 1)
        release.set()
        await asyncio.wait_for(asyncio.gather(*tasks), 2)
        self.assertEqual(self.scheduler.active["limited"], 0)

    async def test_pause_while_rate_limited_neither_spends_tokens_nor_holds_agent(self):
        self.scheduler.limits = {"limited": {"rpm": 1}}
        self.scheduler.history["limited"] = [(self.now, 2)]
        request = self.request("rate-wait")

        async def send():
            self.fail("rate-limited work was sent")

        task = asyncio.create_task(self.invoke(request, send))
        await until(lambda: self.scheduler.waiting.get("limited") == 1)
        self.assertFalse(self.runtime.pending)
        self.assertFalse(self.runtime.active)
        self.store.command(request.study, "pause", request.control.ref, "pause")
        with self.assertRaises(Conflict):
            await asyncio.wait_for(task, 1)
        self.assertEqual(self.scheduler.history["limited"], [(100.0, 2)])
        self.assertEqual(self.store.admissions(), [])
        self.assertEqual(self.scheduler.waiting["limited"], 0)

    async def test_oversize_token_request_fails_without_admission(self):
        self.scheduler.limits = {"limited": {"tpm": 1}}
        request = self.request("too-many-tokens")

        async def send():
            self.fail("oversize token request was sent")

        with self.assertRaisesRegex(ValueError, "exceeds configured TPM"):
            await self.invoke(request, send)
        self.assertEqual(self.store.admissions(), [])
        self.assertEqual(self.scheduler.waiting["limited"], 0)

    async def test_frozen_request_evidence_is_checked_before_send(self):
        request = self.request("changed-request")
        request.request = {"wire": {"estimated_input_tokens": 1, "payload": {"model": "changed"}}}

        async def send():
            self.fail("request that differs from its frozen evidence was sent")

        with self.assertRaisesRegex(Conflict, "frozen step"):
            await self.invoke(request, send)
        self.assertEqual(self.store.admissions(), [])


class AgentQueueTests(unittest.IsolatedAsyncioTestCase):
    async def test_cancel_between_grant_and_continuation_releases_turn(self):
        runtime = AgentRuntime(1)

        async def waiter():
            async with runtime.turn("next", "cancel-at-grant", lambda: None):
                self.fail("cancelled continuation entered its turn")

        async with runtime.turn("busy", "holder", lambda: None):
            task = asyncio.create_task(waiter())
            await until(lambda: bool(runtime.pending))
        # Releasing the holder grants the future synchronously. Cancel before
        # the waiter runs again, which exercises a different cleanup path.
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertFalse(runtime.active)
        self.assertFalse(runtime.pending)
        self.assertFalse(runtime.queues)
        async with runtime.turn("ready", "new-turn", lambda: None):
            self.assertEqual(len(runtime.active), 1)

    async def test_cancelled_waiter_does_not_disturb_round_robin_studies(self):
        runtime = AgentRuntime(1)
        order = []

        async def run(study, work):
            async with runtime.turn(study, work, lambda: None):
                order.append(work)

        async with runtime.turn("busy", "holder", lambda: None):
            tasks = [asyncio.create_task(run(*key)) for key in
                     [("A", "cancel"), ("A", "A1"), ("A", "A2"), ("B", "B1")]]
            await until(lambda: len(runtime.pending) == 4)
            tasks[0].cancel()
            with self.assertRaises(asyncio.CancelledError):
                await tasks[0]
            self.assertEqual(len(runtime.pending), 3)
        await asyncio.wait_for(asyncio.gather(*tasks[1:]), 1)
        self.assertEqual(order, ["A1", "B1", "A2"])
        self.assertFalse(runtime.active)
        self.assertFalse(runtime.pending)
        self.assertFalse(runtime.queues)


class ProviderQueueTests(unittest.IsolatedAsyncioTestCase):
    async def test_existing_waiter_precedes_repeated_fast_new_requests(self):
        scheduler = Scheduler(capacity=1)
        order = []

        async def waiter():
            async with scheduler.slot("shared", lambda: None):
                order.append("waiting")

        async with scheduler.slot("shared", lambda: None):
            task = asyncio.create_task(waiter())
            await until(lambda: scheduler.waiting.get("shared") == 1)
        for _ in range(5):
            async with scheduler.slot("shared", lambda: None):
                order.append("new")
                await asyncio.sleep(0)
        await asyncio.wait_for(task, 1)
        self.assertEqual(order, ["waiting", *(["new"] * 5)])
        self.assertFalse(scheduler.queues["shared"])
        self.assertEqual(scheduler.active["shared"], 0)
        self.assertEqual(scheduler.waiting["shared"], 0)

    async def test_cancelled_queue_head_does_not_block_next_waiter(self):
        scheduler = Scheduler(capacity=1)
        order = []

        async def waiter(name):
            async with scheduler.slot("shared", lambda: None):
                order.append(name)

        async with scheduler.slot("shared", lambda: None):
            first = asyncio.create_task(waiter("cancelled"))
            second = asyncio.create_task(waiter("waiting"))
            await until(lambda: scheduler.waiting.get("shared") == 2)
            first.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await first
        async with scheduler.slot("shared", lambda: None):
            order.append("new")
        await asyncio.wait_for(second, 1)
        self.assertEqual(order, ["waiting", "new"])
        self.assertFalse(scheduler.queues["shared"])
        self.assertEqual(scheduler.waiting["shared"], 0)

    async def test_agent_wait_neither_reserves_nor_heads_provider_queue(self):
        scheduler, runtime = Scheduler(capacity=1), AgentRuntime(1)

        async def model():
            async with scheduler.slot(
                "shared", lambda: None,
                turn=lambda: runtime.turn("queued", "model", lambda: None),
            ):
                self.fail("model should remain queued until cancelled")

        async with runtime.turn("other", "slow-model", lambda: None):
            task = asyncio.create_task(model())
            await until(lambda: bool(runtime.pending))
            async with asyncio.timeout(1):
                async with scheduler.slot("shared", lambda: None):
                    self.assertEqual(scheduler.active["shared"], 1)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertFalse(runtime.pending)
        self.assertFalse(runtime.active)
        self.assertFalse(scheduler.queues["shared"])
        self.assertEqual(scheduler.active["shared"], 0)
        self.assertEqual(scheduler.waiting["shared"], 0)


class EpochHarness:
    def __init__(self, store, root, child):
        self.store, self.root, self.child = store, root, child
        self.scheduler = Scheduler()
        self.first_root = asyncio.Event()
        self.release_old = asyncio.Event()
        self.second_root = asyncio.Event()
        self.child_retried = asyncio.Event()
        self.root_calls = 0
        self.child_calls = 0
        self.old_root_error = None

    def finished(self, *args):
        return False

    def waiting(self, *args):
        return False

    def _steps(self, *args, **kwargs):
        return []

    async def step(self, study, work):
        if work == self.child:
            self.child_calls += 1
            if self.child_calls == 1:
                raise ValueError("recoverable child blocker")
            self.child_retried.set()
            await asyncio.Event().wait()
        self.root_calls += 1
        epoch = self.store.control(study).epoch
        if self.root_calls == 1:
            self.first_root.set()
            await self.release_old.wait()
            if self.old_root_error is not None:
                raise self.old_root_error
        else:
            self.second_root.set()
            await asyncio.Event().wait()
        self.store.require_work(study, work, epoch)


class ServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.directory.name) / "research.db")
        self.control = self.store.create("study", "test", {})
        plan = self.store.put("study", "plan", {}, (self.control.direction,))
        self.control = self.store.command("study", "approve", self.control.ref, "approve", {"plan": plan.ref})
        self.root = self.store.work("study", self.control.ref, "lead", "owner", (plan.ref,))
        self.child = self.store.work("study", self.control.ref, "investigator", "child", owner=self.root.ref)
        self.harness = EpochHarness(self.store, self.root.ref, self.child.ref)
        self.service = ResearchService(self.store, self.harness)

    async def asyncTearDown(self):
        await self.service.close()
        self.store.close()
        self.directory.cleanup()

    async def assert_resume(self, quick):
        self.service.start("study")
        await self.harness.first_root.wait()
        await until(lambda: self.child.ref in self.service.work_errors)
        control = self.store.command("study", "pause", self.control.ref, "pause")
        if not quick:
            self.harness.release_old.set()
            await asyncio.wait_for(self.service.tasks["study"], 1)
        self.store.command("study", "resume", control.ref, "resume")
        self.service.start("study")
        self.harness.release_old.set()
        await asyncio.wait_for(self.harness.child_retried.wait(), 1)
        await asyncio.wait_for(self.harness.second_root.wait(), 1)
        self.assertEqual(self.harness.child_calls, 2)
        self.assertNotIn(self.child.ref, self.service.work_errors)

    async def test_quick_resume_retries_blocked_child_after_old_turn_settles(self):
        await self.assert_resume(quick=True)

    async def test_resume_after_driver_stops_has_identical_recovery(self):
        await self.assert_resume(quick=False)

    async def test_quick_resume_survives_old_root_non_conflict_failure(self):
        self.harness.old_root_error = ValueError("old provider failed")
        driver_waiting = asyncio.Event()
        original_wait = asyncio.wait

        async def observe_wait(futures, **kwargs):
            # The failed child has been removed; only the old root and control
            # wake remain. Fence this boundary without timing-based sleeps.
            if len(futures) == 2 and self.child.ref in self.service.work_errors:
                driver_waiting.set()
            return await original_wait(futures, **kwargs)

        with patch("epivra.application.asyncio.wait", observe_wait):
            self.service.start("study")
            await asyncio.wait_for(driver_waiting.wait(), 1)
            self.harness.release_old.set()
            control = self.store.command("study", "pause", self.control.ref, "pause")
            self.store.command("study", "resume", control.ref, "resume")
            self.service.start("study")
            await asyncio.wait_for(self.harness.child_retried.wait(), 1)
            await asyncio.wait_for(self.harness.second_root.wait(), 1)
        self.assertEqual(self.harness.root_calls, 2)
        self.assertEqual(self.harness.child_calls, 2)
        self.assertNotIn("study", self.service.errors)

    async def test_duplicate_start_does_not_reset_same_epoch_errors(self):
        self.service.start("study")
        await self.harness.first_root.wait()
        await until(lambda: self.child.ref in self.service.work_errors)
        self.service.start("study")
        await asyncio.sleep(0)
        self.assertIn(self.child.ref, self.service.work_errors)
        self.assertEqual(self.harness.child_calls, 1)

    async def test_paused_queued_service_releases_upload_and_reload_guards(self):
        class QueuedHarness(Harness):
            async def step(inner, study, work):
                epoch = inner.store.control(study).epoch
                request = {"wire": {"estimated_input_tokens": 1, "payload": {}}}
                step = inner.store.put(study, "step", {"request": request}, (work,))

                async def send():
                    raise AssertionError("unsent study must remain unsent")

                await inner._invoke(study, work, epoch, step.ref, "op-" + work,
                                    request, send, request_step=step.ref)

        self.service = ResearchService(self.store, QueuedHarness(self.store, OfflineModel()), runtime=AgentRuntime(1))
        host = SimpleNamespace(store=self.store, services={"study": self.service}, token="local",
                               root=Path(self.directory.name), clients={})
        async with self.service.runtime.turn("unrelated", "slow", lambda: None):
            self.service.start("study")
            await until(lambda: bool(self.service.runtime.pending))
            control = self.store.command("study", "pause", self.control.ref, "pause")
            await asyncio.wait_for(self.service.tasks["study"], 1)
            self.assertFalse(self.service.status("study")["running"])
            self.assertEqual(self.store.unsettled("study"), [])
            self.assertEqual(await Host._dispatch(host, {"action": "reload", "study": "study", "token": "local"}), {"reloaded": True})
            result = await Host._dispatch(host, {
                "action": "upload", "study": "study", "expected": control.ref, "token": "local",
                "name": "extra.txt", "data": base64.b64encode(b"extra source").decode(),
            })
            self.assertIn("source", result)
            self.assertEqual(len(self.service.runtime.active), 1)


if __name__ == "__main__":
    unittest.main()
