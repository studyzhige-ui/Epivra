import tempfile
import unittest
from pathlib import Path

from epivra.domain import Call, Reply, encode
from epivra.harness import Harness
from epivra.storage import Store


class Model:
    context_tokens = 49024
    max_tokens = 1024
    identity = "long-runtime-fixture"
    calls = ()

    async def complete(self, request):
        return Reply("", self.calls).to_json()


class LongContextTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = Path(self.folder.name) / "research.db"
        self.store = Store(self.path)
        c = self.store.create(
            "s", "Compare flood adaptation, not insurance pricing", {}
        )
        self.brief = {"subject": "flood adaptation", "questions": ["Which measures?"]}
        p = self.store.put(
            "s",
            "plan",
            {"text": "Compare measures", "brief": self.brief},
            (c.direction,),
        )
        self.c = self.store.command("s", "approve", c.ref, "approve", {"plan": p.ref})
        self.lead = self.store.work("s", self.c.ref, "lead", "Coordinate", (p.ref,))
        self.model = Model()
        self.harness = Harness(self.store, self.model)

    async def asyncTearDown(self):
        self.store.close()
        self.folder.cleanup()

    async def test_growing_completed_work_is_pageable_and_scope_survives_restart(self):
        children = []
        for i in range(150):
            child = self.store.work(
                "s",
                self.c.ref,
                "investigator",
                f"{i} " + "detail " * 50,
                (),
                self.lead.ref,
            )
            children.append(child)
            self.store.put(
                "s",
                "work_result",
                {"text": "Done", "refs": [], "producer": child.ref},
                (child.ref, self.c.direction),
            )
        seen, offset = [], 0
        while offset is not None:
            result = self.harness._request(
                "s", self.lead, section="delegated_work", offset=offset, limit=100
            )
            seen.extend(row["ref"] for row in result["items"])
            offset = result["next_offset"]
        self.assertEqual([child.ref for child in children], seen)
        request = self.harness._request("s", self.lead)
        self.assertEqual(150, request["navigation"]["delegated_work"]["total"])
        self.assertLessEqual(len(encode(request)), self.model.context_tokens - self.model.max_tokens)
        self.assertEqual(self.brief, request["research_scope"]["brief"])
        self.assertEqual(self.c.direction, request["direction_ref"])
        self.store.close()
        self.store = Store(self.path)
        self.harness = Harness(self.store, self.model)
        self.assertEqual(request, self.harness._request("s", self.lead))
        new = self.store.command(
            "s", "steer", self.c.ref, "steer", {"request": "Compare drought adaptation"}
        )
        root = self.store.work("s", new.ref, "lead", "Plan")
        current = self.harness._request("s", root)
        self.assertEqual("Compare drought adaptation", current["direction"]["request"])
        self.assertIsNone(current["research_scope"]["brief"])
        self.assertNotEqual(request["direction_ref"], current["direction_ref"])

    async def test_rejected_memory_keeps_previous_and_allows_next_step(self):
        work = self.store.work(
            "s", self.c.ref, "investigator", "t" * 30000, (), self.lead.ref
        )
        self.model.calls = (
            Call(
                "save_memory",
                {"text": "still investigating flood adaptation", "refs": []},
            ),
        )
        await self.harness.step("s", work.ref)
        old = self.harness._request("s", work)["memory"]
        self.model.calls = (Call("save_memory", {"text": "m" * 11900, "refs": []}),)
        await self.harness.step("s", work.ref)
        self.assertEqual(old, self.harness._request("s", work)["memory"])
        self.model.calls = (Call("finish_work", {"text": "Done", "refs": []}),)
        await self.harness.step("s", work.ref)
        self.assertTrue(self.harness.finished("s", work.ref))

    async def test_navigation_cannot_crowd_out_task_or_accepted_memory(self):
        # Keep this a near-capacity navigation test when the advertised capability
        # surface changes; do not assume a particular prompt/schema byte count.
        base = self.harness._request("s", self.lead)
        task_chars = (self.harness.model.context_tokens - self.harness.model.max_tokens) - len(encode(base)) - 9000
        self.c = self.store.command(
            "s", "long-task-direction", self.c.ref, "steer",
            {"request": "Compare flood adaptation with detailed instructions"},
        )
        self.lead = self.store.work("s", self.c.ref, "lead", "t" * task_chars)
        self.model.calls = (
            Call("save_memory", {"text": "remember " * 850, "refs": []}),
        )
        await self.harness.step("s", self.lead.ref)
        before = self.harness._request("s", self.lead)
        self.assertIsNotNone(before["memory"])
        for i in range(100):
            self.store.work(
                "s",
                self.c.ref,
                "investigator",
                f"{i} " + "task " * 100,
                (),
                self.lead.ref,
            )
        after = self.harness._request("s", self.lead)
        self.assertEqual(before["memory"], after["memory"])
        self.assertEqual(before["task"], after["task"])
        self.assertLessEqual(len(encode(after)), self.model.context_tokens - self.model.max_tokens)

    async def test_old_frozen_request_can_replay_after_readonly_tool_added(self):
        original = self.harness._request("s", self.lead)
        original["tools"].pop("read_context")
        step = self.store.put(
            "s",
            "step",
            {"number": 0, "epoch": self.c.epoch, "request": original},
            (self.lead.ref,),
        )
        from epivra.domain import identity

        operation = identity("model", self.lead.ref, step.ref)
        self.store.admit(
            "s", self.lead.ref, self.c.epoch, operation, original, request_step=step.ref
        )
        self.store.settle(
            operation,
            Reply(
                "",
                (Call("save_memory", {"text": "continue original task", "refs": []}),),
            ).to_json(),
        )

        class NoCall(Model):
            async def complete(self, request):
                raise AssertionError("paid response must replay")

        await Harness(self.store, NoCall()).step("s", self.lead.ref)
        self.assertEqual(
            "continue original task",
            self.harness._request("s", self.lead)["memory"]["body"]["text"],
        )

    async def test_small_preview_allocation_does_not_block_clarifications(self):
        base = self.harness._request("s", self.lead)
        task_chars = (self.harness.model.context_tokens - self.harness.model.max_tokens) - len(encode(base)) - 1000
        self.c = self.store.command(
            "s", "long-task-direction", self.c.ref, "steer",
            {"request": "Compare flood adaptation with detailed instructions"},
        )
        self.lead = self.store.work("s", self.c.ref, "lead", "t" * task_chars)
        child = self.store.work(
            "s", self.c.ref, "investigator", "inspect", (), self.lead.ref
        )
        step = self.store.put(
            "s",
            "step",
            {"number": 0, "epoch": self.c.epoch, "request": {}},
            (child.ref,),
        )
        question = self.store.ask(
            "s", child.ref, self.c.epoch, "Clarify scope", [], step.ref
        )
        self.store.answer(
            "s", self.lead.ref, self.c.epoch, question.ref, "Use original scope", []
        )
        request = self.harness._request("s", self.lead)
        self.assertLessEqual(len(encode(request)), self.model.context_tokens - self.model.max_tokens)
        page = self.harness._request("s", self.lead, section="clarifications")
        self.assertEqual(question.ref, page["items"][0]["question"])

    async def test_all_direct_inputs_keep_priority_after_navigation_paging(self):
        notes = [
            self.store.put("s", "note", {"text": str(i) + "e" * 1000})
            for i in range(25)
        ]
        work = self.store.work(
            "s",
            self.c.ref,
            "investigator",
            "Analyze originals",
            tuple(n.ref for n in notes),
            self.lead.ref,
        )
        for i in range(40):
            self.store.observation(
                "s", work.ref, self.c.epoch, {"text": str(i) + "o" * 1000}, ()
            )
        request = self.harness._request("s", work)
        bodies = {x["ref"] for x in request["context"] if "body" in x}
        self.assertTrue({n.ref for n in notes} <= bodies)
        self.assertLess(len(request["inputs"]), len(notes))

    async def test_provider_budget_rejects_memory_before_persisting(self):
        from epivra.adapters import DeepSeek

        class API:
            account = "offline"

        class WireModel(DeepSeek):
            async def complete(inner, request):
                return {
                    "http_status": 200,
                    "data": {
                        "choices": [
                            {
                                "finish_reason": "tool_calls",
                                "message": {
                                    "role": "assistant",
                                    "content": None,
                                    "tool_calls": [
                                        {
                                            "id": "save",
                                            "type": "function",
                                            "function": {
                                                "name": "save_memory",
                                                "arguments": encode(
                                                    {"text": "m" * 11900, "refs": []}
                                                ),
                                            },
                                        }
                                    ],
                                },
                            }
                        ]
                    },
                }

        model = WireModel(API(), context_tokens=1000000, max_tokens=8192)
        harness = Harness(self.store, model)
        # Budget the current essential schema, then allow a small margin. This
        # still rejects the same oversized memory rather than disabling checks.
        essential = harness._request("s", self.lead)["wire"]["estimated_input_tokens"]
        model.context_tokens = essential + model.max_tokens + 2000
        await harness.step("s", self.lead.ref)
        self.assertFalse(self.store.list("s", "memory"))
        request = harness._request("s", self.lead)
        self.assertLessEqual(
            request["wire"]["estimated_input_tokens"] + 8192, model.context_tokens
        )

    async def test_finished_slot_refills_while_slow_work_is_running(self):
        import asyncio

        from epivra.application import ResearchService

        root = self.lead
        slow = self.store.work("s", self.c.ref, "investigator", "slow", (), root.ref)
        fast = self.store.work("s", self.c.ref, "investigator", "fast", (), root.ref)
        entered, release, advanced = asyncio.Event(), asyncio.Event(), asyncio.Event()
        counts, active, peak = {}, set(), 0

        class ConcurrentModel(Model):
            async def complete(inner, request):
                nonlocal peak
                ref = request["work_ref"]
                self.assertNotIn(ref, active)
                active.add(ref)
                peak = max(peak, len(active))
                counts[ref] = counts.get(ref, 0) + 1
                try:
                    if ref == slow.ref:
                        entered.set()
                        await release.wait()
                        call = Call(
                            "finish_work", {"text": "slow complete", "refs": []}
                        )
                    elif ref == fast.ref:
                        await entered.wait()
                        if counts[ref] == 2:
                            advanced.set()
                        call = Call("save_note", {"text": str(counts[ref]), "refs": []})
                    else:
                        call = Call("wait_for_work", {"refs": [slow.ref, fast.ref]})
                    return Reply("", (call,)).to_json()
                finally:
                    active.remove(ref)

        service = ResearchService(
            self.store, Harness(self.store, ConcurrentModel()), concurrency=2
        )
        service.start("s")
        try:
            await asyncio.wait_for(advanced.wait(), 2)
            self.assertFalse(release.is_set())
            current = self.store.control("s")
            self.store.command("s", "pause-running", current.ref, "pause")
            release.set()
            await asyncio.wait_for(service.tasks["s"], 2)
            self.assertLessEqual(peak, 2)
            self.assertFalse(self.store.unsettled("s"))
            self.assertFalse(service.errors)
        finally:
            release.set()
            await service.close()

    async def test_legacy_oversized_memory_reopens_without_losing_original(self):
        work = self.store.work(
            "s", self.c.ref, "investigator", "t" * 30000, (), self.lead.ref
        )
        memory = self.store.put(
            "s",
            "memory",
            {"text": "legacy " * 1700, "refs": [], "producer": work.ref},
            (work.ref, self.c.direction),
        )
        self.store.close()
        self.store = Store(self.path)
        self.harness = Harness(self.store, self.model)
        request = self.harness._request("s", work)
        self.assertEqual(memory.ref, request["memory"]["ref"])
        self.assertTrue(request["memory"]["body_omitted"])
        self.assertEqual(memory.body, self.store.get("s", memory.ref).body)
        self.model.calls = (
            Call(
                "save_memory",
                {"text": "Restored flood adaptation task", "refs": [memory.ref]},
            ),
        )
        await self.harness.step("s", work.ref)
        self.assertEqual(
            "Restored flood adaptation task",
            self.harness._request("s", work)["memory"]["body"]["text"],
        )

    async def test_legacy_pins_recover_as_original_reference(self):
        work = self.store.work(
            "s", self.c.ref, "investigator", "t" * 30000, (), self.lead.ref
        )
        refs = [self.store.put("s", "source", {"text": str(i)}).ref for i in range(170)]
        anchor = self.store.put(
            "s",
            "evidence_anchor",
            {"refs": refs, "producer": work.ref},
            (work.ref, *refs),
        )
        request = self.harness._request("s", work)
        self.assertTrue(request["pinned_evidence"]["body_omitted"])
        self.assertEqual(anchor.ref, request["pinned_evidence"]["ref"])
        self.assertEqual(refs, self.store.get("s", anchor.ref).body["refs"])
        self.model.calls = (
            Call(
                "save_memory",
                {"text": "Preserve the original flood task", "refs": [anchor.ref]},
            ),
        )
        await self.harness.step("s", work.ref)
        self.assertTrue(self.store.list("s", "memory"))
        self.model.calls = (Call("pin_evidence", {"refs": refs}),)
        await self.harness.step("s", work.ref)
        self.assertEqual(1, len(self.store.list("s", "evidence_anchor")))
        self.model.calls = (Call("pin_evidence", {"refs": refs[:2]}),)
        await self.harness.step("s", work.ref)
        self.assertEqual(refs[:2], self.harness._request("s", work)["pinned_evidence"])

    async def test_observation_lookup_does_not_assume_parent_order(self):
        step = self.store.put(
            "s", "step", {"number": 0, "request": {}}, (self.lead.ref,)
        )
        observation = self.store.observation(
            "s",
            self.lead.ref,
            self.c.epoch,
            {"text": "progress"},
            (step.ref, self.c.direction),
        )
        self.assertEqual(tuple(sorted(observation.parents)), observation.parents)
        self.assertIn(
            observation.ref,
            {x.ref for x in self.harness._steps("s", "observation", self.lead.ref)},
        )
        self.assertEqual(step.seq, self.store.step_sequence("s", self.lead.ref))
