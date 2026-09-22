from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from epivra.application import ResearchService
from epivra.domain import Call, Conflict, NotAllowed, Reply
from epivra.harness import Harness
from epivra.storage import Store


class Model:
    identity = "clarification-fixture"

    def __init__(self, *calls):
        self.calls = calls
        self.requests = []

    async def complete(self, request):
        self.requests.append(request)
        return Reply("", self.calls).to_json()


class ClarificationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = Path(self.folder.name) / "state.db"
        self.store = Store(self.path)
        c = self.store.create("s", "Compare the supplied findings", {})
        plan = self.store.put("s", "plan", {"text": "Compare"}, (c.direction,))
        self.c = self.store.command(
            "s", "approve", c.ref, "approve", {"plan": plan.ref}
        )
        self.lead = self.store.work("s", self.c.ref, "lead", "Coordinate")
        self.work = self.store.work(
            "s", self.c.ref, "investigator", "Investigate", owner=self.lead.ref
        )
        self.source = self.store.put("s", "source", {"text": "Original observation"})

    async def asyncTearDown(self):
        self.store.close()
        self.folder.cleanup()

    async def ask(self, *following):
        model = Model(
            Call(
                "request_clarification",
                {
                    "text": "The populations differ; which comparison is intended?",
                    "refs": [self.source.ref],
                },
            ),
            *following,
        )
        harness = Harness(self.store, model)
        await harness.step("s", self.work.ref)
        return model, harness, self.store.list("s", "clarification")[-1]

    def restart(self):
        self.store.close()
        self.store = Store(self.path)

    async def test_wait_does_not_sample_and_answer_resumes_same_work_with_original_result(
        self,
    ):
        model, harness, question = await self.ask()
        count = len(self.store.list("s", "work"))
        self.assertFalse(harness.finished("s", self.work.ref))
        self.assertEqual([], self.store.list("s", "work_result"))
        self.assertEqual("waiting", await harness.step("s", self.work.ref))
        self.assertEqual(1, len(model.requests))
        self.restart()
        harness = Harness(self.store, model)
        self.assertEqual("waiting", await harness.step("s", self.work.ref))
        self.assertEqual(1, len(model.requests))
        producer = self.store.work(
            "s", self.c.ref, "investigator", "Clarify population", owner=self.lead.ref
        )
        text = "生产者原成果：17人；限定为登记人群。"
        result = self.store.put(
            "s",
            "work_result",
            {"text": text, "refs": [self.source.ref], "producer": producer.ref},
            (producer.ref, self.c.direction, self.source.ref),
        )
        answer = self.store.answer(
            "s",
            self.lead.ref,
            self.c.epoch,
            question.ref,
            "Use the registered population",
            [result.ref],
        )
        self.assertFalse(harness.waiting("s", self.work.ref))
        request = harness._request("s", self.work)
        contextual = {a["ref"]: a for a in request["context"]}
        self.assertEqual(text, contextual[result.ref]["body"]["text"])
        self.assertEqual([result.ref], contextual[answer.ref]["body"]["refs"])
        self.assertEqual(question.ref, request["clarifications"][0]["question"])
        self.assertEqual(answer.ref, request["clarifications"][0]["answer"])
        model.calls = (
            Call(
                "finish_work",
                {"text": "Answer using registered population", "refs": [result.ref]},
            ),
        )
        self.assertEqual("finished", await harness.step("s", self.work.ref))
        self.assertEqual(2, len(model.requests))
        self.assertEqual(count + 1, len(self.store.list("s", "work")))
        own = [
            a
            for a in self.store.list("s", "work_result")
            if a.body["producer"] == self.work.ref
        ]
        self.assertEqual(1, len(own))

    async def test_ask_stops_remaining_batch_and_pairs_every_call(self):
        _, _, _ = await self.ask(
            Call("save_note", {"text": "Should not execute", "refs": []}),
            Call("finish_work", {"text": "Premature answer", "refs": []}),
        )
        self.assertEqual([], self.store.list("s", "note"))
        self.assertEqual([], self.store.list("s", "work_result"))
        observations = self.store.list("s", "observation")
        self.assertEqual([0, 1, 2], [o.body["index"] for o in observations])
        self.assertTrue(observations[0].body["result"]["waiting"])
        self.assertTrue(
            all("not_executed" in o.body["result"] for o in observations[1:])
        )

    async def test_all_delegated_roles_can_ask_but_only_lead_can_answer(self):
        result = self.store.put(
            "s",
            "work_result",
            {"text": "Finding", "refs": [], "producer": self.work.ref},
            (self.work.ref, self.c.direction),
        )
        report = self.store.put(
            "s", "report", {"text": "Report", "evidence": []}, (self.c.direction,)
        )
        for role in ("investigator", "synthesizer", "writer", "reviewer"):
            with self.subTest(role=role):
                refs = (report.ref,) if role == "reviewer" else (result.ref,)
                work = self.store.work(
                    "s", self.c.ref, role, "Task", refs, self.lead.ref
                )
                model = Model(
                    Call(
                        "request_clarification",
                        {"text": "Which population is in scope?", "refs": [result.ref]},
                    )
                )
                harness = Harness(self.store, model)
                self.assertIn(
                    "request_clarification", harness._request("s", work)["tools"]
                )
                self.assertNotIn(
                    "answer_clarification", harness._request("s", work)["tools"]
                )
                await harness.step("s", work.ref)
                self.assertTrue(harness.waiting("s", work.ref))
        schema = Harness(self.store, Model())._request("s", self.lead)["tools"]
        self.assertNotIn("request_clarification", schema)
        self.assertIn("answer_clarification", schema)
        c = self.store.create("unapproved", "Plan first", {})
        lead = self.store.work("unapproved", c.ref, "lead", "Plan")
        schema = Harness(self.store, Model())._request("unapproved", lead)["tools"]
        self.assertNotIn("request_clarification", schema)
        self.assertNotIn("answer_clarification", schema)

    async def test_owner_and_direction_boundaries_cannot_release_question(self):
        _, _, question = await self.ask()
        other = self.store.work("s", self.c.ref, "investigator", "Unrelated helper", (), self.lead.ref)
        for work in (other, self.work):
            with self.subTest(work=work.ref):
                with self.assertRaises(NotAllowed):
                    self.store.answer(
                        "s", work.ref, self.c.epoch, question.ref, "Override", []
                    )
        self.assertEqual([], self.store.list("s", "clarification_answer"))
        c = self.store.command(
            "s", "steer", self.c.ref, "steer", {"request": "A different question"}
        )
        lead = self.store.work("s", c.ref, "lead", "New direction")
        with self.assertRaises((NotAllowed, Conflict)):
            self.store.answer(
                "s", lead.ref, c.epoch, question.ref, "Use old question", []
            )
        self.assertEqual([], self.store.clarifications("s", open_only=True))
        self.assertEqual(1, len(self.store.list("s", "clarification")))

    async def test_answer_is_idempotent_across_restart_and_cannot_be_rewritten(self):
        _, _, question = await self.ask()
        args = (
            "s",
            self.lead.ref,
            self.c.epoch,
            question.ref,
            "Use the first population",
            [self.source.ref],
        )
        answer = self.store.answer(*args)
        self.restart()
        self.assertEqual(answer.ref, self.store.answer(*args).ref)
        with self.assertRaises(Conflict):
            self.store.answer(
                "s",
                self.lead.ref,
                self.c.epoch,
                question.ref,
                "Use a different population",
                [],
            )
        self.assertEqual(1, len(self.store.list("s", "clarification_answer")))

    async def test_replay_after_question_saved_before_observation_reuses_question(self):
        model = Model(
            Call("request_clarification", {"text": "Which population?", "refs": []})
        )
        with patch.object(
            self.store, "observation", side_effect=OSError("disk failure")
        ):
            with self.assertRaises(OSError):
                await Harness(self.store, model).step("s", self.work.ref)
        self.assertEqual(1, len(self.store.list("s", "clarification")))
        self.restart()
        harness = Harness(self.store, model)
        await harness.step("s", self.work.ref)
        self.assertEqual(1, len(model.requests))
        self.assertEqual(1, len(self.store.list("s", "clarification")))
        self.assertEqual(1, len(self.store.list("s", "observation")))
        self.assertTrue(harness.waiting("s", self.work.ref))

    async def test_replay_after_ask_observation_does_not_execute_unpaired_later_call(
        self,
    ):
        model = Model(
            Call("request_clarification", {"text": "Which population?", "refs": []}),
            Call("finish_work", {"text": "Premature answer", "refs": []}),
        )
        original = self.store.observation

        def fail_second(study, work, epoch, body, parents):
            if body.get("index") == 1:
                raise OSError("disk failure during skipped receipt")
            return original(study, work, epoch, body, parents)

        with patch.object(self.store, "observation", side_effect=fail_second):
            with self.assertRaises(OSError):
                await Harness(self.store, model).step("s", self.work.ref)
        self.restart()
        harness = Harness(self.store, model)
        await harness.step("s", self.work.ref)
        self.assertEqual(1, len(model.requests))
        self.assertEqual([], self.store.list("s", "work_result"))
        observations = self.store.list("s", "observation")
        self.assertEqual([0, 1], [o.body["index"] for o in observations])
        self.assertIn("not_executed", observations[1].body["result"])
        self.assertTrue(harness.waiting("s", self.work.ref))

    async def test_answer_tool_releases_child_and_rejects_foreign_owner(self):
        _, _, question = await self.ask()
        other = self.store.work("s", self.c.ref, "investigator", "Other helper", (), self.lead.ref)
        model = Model(
            Call(
                "answer_clarification",
                {
                    "question": question.ref,
                    "text": "Use the original scope",
                    "refs": [self.source.ref],
                },
            )
        )
        harness = Harness(self.store, model)
        await harness.step("s", other.ref)
        self.assertIn("error", self.store.list("s", "observation")[-1].body["result"])
        self.assertTrue(harness.waiting("s", self.work.ref))
        await harness.step("s", self.lead.ref)
        receipt = self.store.list("s", "observation")[-1].body["result"]
        self.assertEqual(self.work.ref, receipt["resumed_work"])
        self.assertEqual(1, len(self.store.list("s", "clarification_answer")))
        self.assertFalse(harness.waiting("s", self.work.ref))

    async def test_open_question_cannot_be_overwritten_or_asked_by_lead(self):
        _, _, question = await self.ask()
        step = self.store.put(
            "s", "step", {"number": 99, "request": {}}, (self.work.ref,)
        )
        with self.assertRaises(Conflict):
            self.store.ask(
                "s", self.work.ref, self.c.epoch, "Replacement question", [], step.ref
            )
        with self.assertRaises(NotAllowed):
            self.store.ask(
                "s", self.lead.ref, self.c.epoch, "Owner asks itself", [], step.ref
            )
        self.assertEqual([question], self.store.clarifications("s", open_only=True))

    async def test_replay_preserves_barrier_even_if_owner_answered_during_interruption(
        self,
    ):
        model = Model(
            Call("request_clarification", {"text": "Which population?", "refs": []}),
            Call("save_note", {"text": "Prepared before answer", "refs": []}),
        )
        original = self.store.observation

        def fail_second(study, work, epoch, body, parents):
            if body.get("index") == 1:
                raise OSError("receipt interrupted")
            return original(study, work, epoch, body, parents)

        with patch.object(self.store, "observation", side_effect=fail_second):
            with self.assertRaises(OSError):
                await Harness(self.store, model).step("s", self.work.ref)
        question = self.store.list("s", "clarification")[0]
        self.store.answer(
            "s", self.lead.ref, self.c.epoch, question.ref, "Updated comparison", []
        )
        self.restart()
        await Harness(self.store, model).step("s", self.work.ref)
        self.assertEqual(1, len(model.requests))
        self.assertEqual([], self.store.list("s", "note"))
        self.assertIn(
            "not_executed", self.store.list("s", "observation")[-1].body["result"]
        )

    def test_ask_rejects_nonstep_and_other_work_step(self):
        foreign = self.store.put("s", "step", {"request": {}}, (self.lead.ref,))
        for ref in (self.source.ref, foreign.ref):
            with self.subTest(ref=ref), self.assertRaises(Conflict):
                self.store.ask(
                    "s", self.work.ref, self.c.epoch, "Which population?", [], ref
                )
        self.assertEqual([], self.store.list("s", "clarification"))

    async def test_service_wakes_owner_waits_for_supplement_and_resumes_original_work(
        self,
    ):
        store = self.store
        c = store.create("flow", "Compare supplied populations", {})
        plan = store.put(
            "flow", "plan", {"text": "Investigate and compare"}, (c.direction,)
        )
        store.command("flow", "approve", c.ref, "approve", {"plan": plan.ref})
        events = []
        original_ref = None
        original_calls = 0
        supplement_calls = 0
        original_text = "Direct producer finding: registration defines the comparison."
        test = self

        class FlowModel:
            identity = "clarification-flow"

            async def complete(inner, request):
                nonlocal original_ref, original_calls, supplement_calls
                task = request["task"]
                if request["role"] == "lead":
                    children = {w["task"]: w for w in request["delegated_work"]}
                    if "original" not in children:
                        events.append("delegate original")
                        calls = [
                            Call(
                                "delegate_work",
                                {
                                    "role": "investigator",
                                    "task": "original",
                                    "refs": [],
                                },
                            )
                        ]
                    else:
                        original = children["original"]
                        original_ref = original["ref"]
                        questions = store.clarifications(
                            "flow", work=original_ref, open_only=True
                        )
                        if questions:
                            if "supplement" not in children:
                                events.append("question wakes owner")
                                calls = [
                                    Call(
                                        "delegate_work",
                                        {
                                            "role": "investigator",
                                            "task": "supplement",
                                            "refs": [],
                                        },
                                    )
                                ]
                            elif not children["supplement"]["finished"]:
                                events.append("wait supplement")
                                calls = [
                                    Call(
                                        "wait_for_work",
                                        {"refs": [children["supplement"]["ref"]]},
                                    )
                                ]
                            else:
                                events.append("answer original")
                                calls = [
                                    Call(
                                        "answer_clarification",
                                        {
                                            "question": questions[0].ref,
                                            "text": "Use the registered population",
                                            "refs": children["supplement"]["results"],
                                        },
                                    )
                                ]
                        elif not original["finished"]:
                            events.append("wait original")
                            calls = [Call("wait_for_work", {"refs": [original_ref]})]
                        else:
                            events.append("original delivered")
                            control = store.control("flow")
                            store.command("flow", "test-stop", control.ref, "pause")
                            calls = []
                elif task == "original":
                    original_calls += 1
                    work = next(
                        w
                        for w in store.list("flow", "work")
                        if w.body["task"] == "original"
                    )
                    test.assertEqual(
                        [],
                        store.clarifications("flow", work=work.ref, open_only=True),
                        "waiting child must not sample",
                    )
                    if original_calls == 1:
                        events.append("original starts")
                        calls = [
                            Call(
                                "save_note",
                                {"text": "Comparison needs scope decision", "refs": []},
                            )
                        ]
                    elif original_calls == 2:
                        events.append("original asks")
                        calls = [
                            Call(
                                "request_clarification",
                                {
                                    "text": "Population boundaries differ; which should the comparison cover?",
                                    "refs": [],
                                },
                            )
                        ]
                    else:
                        events.append("original resumes")
                        test.assertEqual(original_ref, work.ref)
                        bodies = [a.get("body", {}) for a in request["context"]]
                        test.assertTrue(
                            any(b.get("text") == original_text for b in bodies)
                        )
                        answers = store.list("flow", "clarification_answer")
                        test.assertEqual(1, len(answers))
                        calls = [
                            Call(
                                "finish_work",
                                {
                                    "text": "Comparison uses the registered population",
                                    "refs": answers[0].body["refs"],
                                },
                            )
                        ]
                else:
                    test.assertEqual("supplement", task)
                    supplement_calls += 1
                    if supplement_calls == 1:
                        events.append("supplement starts")
                        calls = [
                            Call(
                                "save_note",
                                {
                                    "text": "Reading the population definition",
                                    "refs": [],
                                },
                            )
                        ]
                    else:
                        events.append("supplement completes")
                        calls = [
                            Call("finish_work", {"text": original_text, "refs": []})
                        ]
                return Reply("", tuple(calls)).to_json()

        service = ResearchService(store, Harness(store, FlowModel()), concurrency=1)
        await asyncio.wait_for(service.run("flow"), 60)
        self.assertEqual({}, service.errors)
        self.assertEqual({}, service.work_errors)
        self.assertLess(events.index("wait original"), events.index("original asks"))
        sequence = [
            "original asks",
            "question wakes owner",
            "supplement starts",
            "wait supplement",
            "supplement completes",
            "answer original",
            "original resumes",
            "original delivered",
        ]
        self.assertEqual(
            sorted(events.index(e) for e in sequence),
            [events.index(e) for e in sequence],
        )
        self.assertEqual(
            ["wait supplement", "supplement completes"],
            events[events.index("wait supplement") : events.index("answer original")],
        )
        self.assertEqual(
            1, sum(w.body["task"] == "original" for w in store.list("flow", "work"))
        )
        self.assertEqual(
            1,
            sum(
                a.body.get("producer") == original_ref
                for a in store.list("flow", "work_result")
            ),
        )
