from __future__ import annotations

import asyncio
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from deep_research_agent.domain import Call, Conflict, Reply, UnknownOutcome
from deep_research_agent.harness import STRING, Harness, Tool, object_schema
from deep_research_agent.scheduling import Scheduler
from deep_research_agent.storage import Store


class Model:
    identity = "fixture"

    def __init__(self, calls=()):
        self.calls = calls
        self.count = 0

    async def complete(self, request):
        self.count += 1
        return Reply("", self.calls).to_json()


class BoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_planner_can_discover_authorized_inventory_before_approval(self):
        root = Path(self.folder.name) / "documents"
        root.mkdir()
        (root / "paper.txt").write_text("Evidence", encoding="utf-8")
        control = self.store.create("p", "Plan", {"local_roots": [str(root)]})
        work = self.store.work("p", control.ref, "planner", "Plan")
        model = Model((Call("discover_local", {"root": str(root)}),))
        harness = Harness(self.store, model)
        self.assertNotIn("snapshot_local", harness._request("p", work)["tools"])
        await harness.step("p", work.ref)
        self.assertEqual(1, len(self.store.list("p", "catalog")))
        self.assertEqual([], self.store.list("p", "source"))
        self.assertFalse(self.store.control("p").approved)

    async def test_pending_builtin_contract_change_is_rejected_before_model_call(self):
        model = Model()
        harness = Harness(self.store, model)
        self.store.put(
            "s",
            "step",
            {"number": 0, "request": harness._request("s", self.work)},
            (self.work.ref,),
        )
        with patch.dict(
            "deep_research_agent.harness.TOOLS", {"read_source": "changed contract"}
        ):
            with self.assertRaisesRegex(Exception, "original tool contracts"):
                await harness.step("s", self.work.ref)
        self.assertEqual(0, model.count)

    async def test_review_cannot_accept_required_changes_or_unbound_claims(self):
        source = self.store.put("s", "source", {"text": "Uncertain effect"})
        report = self.store.put(
            "s",
            "report",
            {"text": "Effect is proven.", "evidence": [source.ref]},
            (self.c.direction, self.work.ref),
        )
        reviewer = self.store.work(
            "s", self.c.ref, "reviewer", "Check", (report.ref,), self.work.ref
        )
        check = {
            "claim": "Effect is proven.",
            "evidence": [source.ref],
            "assessment": "Source is uncertain",
            "requires_revision": True,
        }
        model = Model(
            (
                Call(
                    "submit_review",
                    {"accepted": True, "reason": "Revise", "checks": [check]},
                ),
            )
        )
        harness = Harness(self.store, model)
        await harness.step("s", reviewer.ref)
        self.assertEqual([], self.store.list("s", "review"))
        self.assertIn(
            "cannot accept",
            self.store.list("s", "observation")[-1].body["result"]["error"],
        )
        model.calls = (
            Call(
                "submit_review",
                {
                    "accepted": False,
                    "reason": "Revise",
                    "checks": [{**check, "claim": "Invented quote"}],
                },
            ),
        )
        await harness.step("s", reviewer.ref)
        self.assertEqual([], self.store.list("s", "review"))
        model.calls = (
            Call(
                "submit_review",
                {"accepted": False, "reason": "Revise", "checks": [check]},
            ),
        )
        await harness.step("s", reviewer.ref)
        self.assertFalse(self.store.list("s", "review")[-1].body["accepted"])

    async def test_reading_progress_survives_restart_but_is_work_local(self):
        source = self.store.put(
            "s", "source", {"origin": "paper", "text": "abcdefghij"}
        )
        model = Model(
            tuple(
                Call("read_source", {"ref": source.ref, "offset": start, "limit": 4})
                for start in (0, 2, 8)
            )
        )
        await Harness(self.store, model).step("s", self.work.ref)
        self.store.close()
        self.store = Store(self.path)
        self.assertEqual(
            [source], self.store.search("s", "source", source.ref[:16], 0, 10)
        )
        self.assertEqual(
            [], self.store.search("another-study", "source", source.ref[:16], 0, 10)
        )
        lookup = Model(
            (
                Call(
                    "find_artifacts",
                    {"kind": "source", "query": "", "after": 0, "limit": 10},
                ),
            )
        )
        harness = Harness(self.store, lookup)
        await harness.step("s", self.work.ref)
        items = self.store.list("s", "observation")[-1].body["result"]["items"]
        self.assertEqual([[0, 6], [8, 10]], items[0]["read_ranges"])
        child = self.store.work(
            "s",
            self.c.ref,
            "investigator",
            "Independent check",
            (source.ref,),
            self.work.ref,
        )
        await harness.step("s", child.ref)
        self.assertEqual(
            [],
            self.store.list("s", "observation")[-1].body["result"]["items"][0][
                "read_ranges"
            ],
        )

    async def test_reference_types_and_latest_catalog_survive_reconstruction(self):
        source = self.store.put("s", "source", {"text": "evidence"})
        work = self.store.work(
            "s", self.c.ref, "investigator", "Check", (source.ref,), self.work.ref
        )
        self.store.put("s", "catalog", {"root": "authorized", "entries": []})
        latest = self.store.put(
            "s", "catalog", {"root": "authorized", "entries": [{"path": "new"}]}
        )
        request = Harness(self.store, Model())._request("s", work)
        self.assertEqual([{"ref": source.ref, "kind": "source"}], request["inputs"])
        self.assertEqual(
            [
                {
                    "ref": latest.ref,
                    "kind": "catalog",
                    "root": "authorized",
                    "entries": 1,
                }
            ],
            request["catalogs"],
        )
        self.store.close()
        self.store = Store(self.path)
        self.assertEqual(request, Harness(self.store, Model())._request("s", work))

    async def test_reconciliation_receipt_failure_rolls_back_result(self):
        self.store.admit("s", self.work.ref, self.c.epoch, "lost", {"fixture": True})
        c = self.store.command("s", "pause", self.c.ref, "pause")
        with patch.object(self.store, "_put", side_effect=OSError("disk failure")):
            with self.assertRaises(OSError):
                self.store.reconcile(
                    "s",
                    c.ref,
                    "lost",
                    "receipt",
                    {"text": "verified"},
                    "provider record",
                )
        with self.assertRaises(UnknownOutcome):
            self.store.result("s", "lost")
        self.assertEqual([], self.store.list("s", "reconciliation"))

    async def asyncSetUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = Path(self.folder.name) / "state.db"
        self.store = Store(self.path)
        self.c, self.work = self.study("s")

    def study(self, study):
        c = self.store.create(study, "Research", {})
        plan = self.store.put(study, "plan", {"text": "Plan"}, (c.direction,))
        c = self.store.command(study, "approve", c.ref, "approve", {"plan": plan.ref})
        return c, self.store.work(study, c.ref, "researcher", "Research")

    async def asyncTearDown(self):
        self.store.close()
        self.folder.cleanup()

    async def test_safe_batch_is_concurrent_but_observations_remain_ordered(self):
        entered = asyncio.Event()
        active = 0
        completed = []

        async def read(args):
            nonlocal active
            active += 1
            if active == 2:
                entered.set()
            await asyncio.wait_for(entered.wait(), 1)
            if args["name"] == "first":
                await asyncio.sleep(0.01)
            completed.append(args["name"])
            return args["name"]

        model = Model(tuple(Call("read", {"name": n}) for n in ("first", "second")))
        tool = Tool("Read", object_schema({"name": STRING}), read, parallel_safe=True)
        await Harness(self.store, model, {"read": tool}).step("s", self.work.ref)
        self.assertEqual(["second", "first"], completed)
        observations = self.store.list("s", "observation")
        self.assertEqual(
            ["first", "second"], [o.body["result"]["value"] for o in observations]
        )
        self.assertEqual(2, active)

    async def test_failed_parallel_call_does_not_cancel_successful_sibling(self):
        completed = []

        async def read(args):
            if args["name"] == "bad":
                raise OSError("lost response")
            await asyncio.sleep(0.01)
            completed.append("saved")
            return "paid result"

        model = Model((Call("read", {"name": "bad"}), Call("read", {"name": "good"})))
        tools = {
            "read": Tool(
                "Read", object_schema({"name": STRING}), read, parallel_safe=True
            )
        }
        with self.assertRaises(OSError):
            await Harness(self.store, model, tools).step("s", self.work.ref)
        self.assertEqual(["saved"], completed)
        with self.assertRaises(UnknownOutcome):
            await Harness(self.store, model, tools).step("s", self.work.ref)
        self.assertEqual(["saved"], completed)
        self.assertEqual(1, model.count)

    async def test_internal_write_is_a_parallel_batch_barrier(self):
        seen = []

        async def read(args):
            seen.append(len(self.store.list("s", "note")))
            return "ok"

        model = Model(
            (
                Call("read", {}),
                Call("save_note", {"text": "checkpoint", "refs": []}),
                Call("read", {}),
            )
        )
        tool = Tool("Read", object_schema({}), read, parallel_safe=True)
        await Harness(self.store, model, {"read": tool}).step("s", self.work.ref)
        self.assertEqual([0, 1], seen)

    async def test_shared_capacity_applies_across_researches(self):
        _, work2 = self.study("second")
        active = peak = 0

        class Slow(Model):
            async def complete(inner, request):
                nonlocal active, peak
                active += 1
                peak = max(peak, active)
                await asyncio.sleep(0.01)
                active -= 1
                return Reply("done", ()).to_json()

        scheduler = Scheduler(1)
        await asyncio.gather(
            Harness(self.store, Slow(), scheduler=scheduler).step("s", self.work.ref),
            Harness(self.store, Slow(), scheduler=scheduler).step("second", work2.ref),
        )
        self.assertEqual(1, peak)

    async def test_pause_while_waiting_capacity_prevents_admission(self):
        scheduler = Scheduler(1)
        model = Model()
        async with scheduler.slot("model", lambda: None):
            task = asyncio.create_task(
                Harness(self.store, model, scheduler=scheduler).step("s", self.work.ref)
            )
            await asyncio.sleep(0.01)
            self.store.command("s", "pause", self.c.ref, "pause")
        with self.assertRaises(Conflict):
            await task
        self.assertEqual(0, model.count)
        self.assertEqual([], self.store.unsettled("s"))

    async def test_shared_cooldown_delays_new_admission(self):
        scheduler = Scheduler(1)
        deadline = time.time() + 0.04
        scheduler.defer("model", deadline)
        model = Model()
        await Harness(self.store, model, scheduler=scheduler).step("s", self.work.ref)
        self.assertGreaterEqual(time.time(), deadline)
        self.assertEqual(1, model.count)

    async def test_reconciliation_is_atomic_idempotent_and_never_sends(self):
        self.store.admit("s", self.work.ref, self.c.epoch, "lost", {"model": "fixture"})
        raw = Reply("verified", ()).to_json()
        with self.assertRaises(Conflict):
            self.store.reconcile(
                "s", self.c.ref, "lost", "receipt", raw, "provider record"
            )
        c = self.store.command("s", "pause", self.c.ref, "pause")
        receipt = self.store.reconcile(
            "s", c.ref, "lost", "receipt", raw, "provider record"
        )
        self.store.close()
        self.store = Store(self.path)
        self.assertEqual(
            receipt.ref,
            self.store.reconcile(
                "s", c.ref, "lost", "receipt", raw, "provider record"
            ).ref,
        )
        self.assertEqual(raw, self.store.result("s", "lost"))
        self.assertEqual([], self.store.unsettled("s"))
        self.assertTrue(self.store.control("s").paused)
        with self.assertRaises(Conflict):
            self.store.reconcile(
                "s", c.ref, "lost", "receipt", {"changed": True}, "provider record"
            )

    async def test_rare_evidence_anchor_survives_context_pressure_and_restart(self):
        source = self.store.put("s", "source", {"text": "Rare contradictory evidence"})
        model = Model((Call("pin_evidence", {"refs": [source.ref]}),))
        harness = Harness(self.store, model, context_chars=16000)
        await harness.step("s", self.work.ref)
        for i in range(1000):
            self.store.put("s", "note", {"text": str(i) + "x" * 100}, (self.work.ref,))
        before = harness._request("s", self.work)
        self.assertEqual([source.ref], before["pinned_evidence"])
        self.assertGreater(before["omitted_count"], 0)
        self.store.close()
        self.store = Store(self.path)
        after = Harness(self.store, model, context_chars=16000)._request("s", self.work)
        self.assertEqual(before, after)
        self.assertEqual(
            "Rare contradictory evidence", self.store.get("s", source.ref).body["text"]
        )
