"""Durable, exclusive writing handoffs and recovery contracts."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from research_fixture import prepare_basis

from epivra.domain import Conflict, NotAllowed
from epivra.storage import Store
from epivra.writing import WritingWorkspace


class WritingOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "research.db"
        self.store = Store(self.path)
        c = self.store.create("s", "Explain the supplied source", {})
        self.route = self.store.work("s", c.ref, "lead", "Plan research")
        plan = self.store.put("s", "plan", {"text": "Read the source"}, (c.direction,))
        self.c = self.store.command("s", "approve", c.ref, "approve", {"plan": plan.ref})
        self.owner = self.store.work("s", self.c.ref, "lead", "Own research")
        self.source = self.store.put("s", "source", {"text": "The source reports 12 attendees", "origin": "source.txt"})
        self.basis = prepare_basis(self.store, self.owner)
        self.writing = WritingWorkspace(self.store)
        self.index = 0

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def save(self, actor, text="12 attendees", base=None):
        self.index += 1
        step = self.store.put("s", "step", {"fixture": self.index}, (actor.ref,))
        return self.writing.save("s", actor.ref, self.c.epoch, step.ref, 0,
                                 text=text, base=base, basis=self.basis.ref,
                                 evidence=[self.source.ref])

    def writer(self, task="Revise", inputs=()):
        return self.store.work("s", self.c.ref, "writer", task, inputs, self.owner.ref)

    def finish(self, writer, report=None):
        return self.store.put("s", "work_result", {"producer": writer.ref, "text": "Done", "refs": [report] if report else []}, (writer.ref,))

    def test_one_research_owner_and_route_is_not_author(self):
        self.assertEqual(self.store.writing_author("s"), self.owner.ref)
        self.assertEqual(self.store.work("s", self.c.ref, "lead", "Own research").ref, self.owner.ref)
        before = len(self.store.list("s", "work"))
        with self.assertRaises(NotAllowed):
            self.store.work("s", self.c.ref, "lead", "Another owner")
        self.assertEqual(len(self.store.list("s", "work")), before)
        with self.assertRaises(NotAllowed):
            self.save(self.route)
        with self.assertRaises(NotAllowed):
            self.store.require_work("s", self.route.ref, self.c.epoch)
        with self.assertRaises(NotAllowed):
            self.store.work("s", self.c.ref, "investigator", "Old route delegation", (), self.route.ref)

    def test_research_helpers_cannot_write_even_first_manuscript(self):
        for role in ("investigator", "synthesizer"):
            helper = self.store.work("s", self.c.ref, role, "Read evidence", (), self.owner.ref)
            with self.assertRaises(NotAllowed):
                self.save(helper)
        self.assertEqual(self.store.list("s", "report"), [])

    def test_sequential_handoff_survives_restart_and_replay(self):
        first = self.save(self.owner)
        writer = self.writer(inputs=(first["ref"],))
        self.assertFalse(self.store.authoring_state("s", self.owner.ref)["can_write"])
        with self.assertRaises(NotAllowed):
            self.save(self.owner, "Owner cannot interleave", first["ref"])
        before = len(self.store.list("s", "work"))
        with self.assertRaises(NotAllowed):
            self.writer("Second writer", (first["ref"],))
        self.assertEqual(len(self.store.list("s", "work")), before)
        self.store.close()
        self.store = Store(self.path)
        self.writing = WritingWorkspace(self.store)
        self.assertEqual(self.store.writing_author("s"), writer.ref)
        second = self.save(writer, "12 registered attendees", first["ref"])
        saved_step = self.store.list("s", "step")[-1]
        self.finish(writer, second["ref"])
        third = self.save(self.owner, "12 registered attendees in scope", second["ref"])
        self.assertEqual(self.writer(inputs=(first["ref"],)).ref, writer.ref)
        self.assertEqual(self.store.writing_author("s"), self.owner.ref)
        replay = self.writing.save("s", writer.ref, self.c.epoch, saved_step.ref, 0,
                                  text="12 registered attendees", base=first["ref"],
                                  basis=self.basis.ref, evidence=[self.source.ref])
        self.assertEqual(replay, second)
        self.assertEqual(self.writing.current("s").ref, third["ref"])
        with self.assertRaises(NotAllowed):
            self.save(writer, "Late new write", third["ref"])

    def test_handoff_requires_current_manuscript_and_owner(self):
        first = self.save(self.owner)
        with self.assertRaises(NotAllowed):
            self.writer()
        with self.assertRaises(NotAllowed):
            self.store.work("s", self.c.ref, "writer", "Orphan", (first["ref"],))
        with self.assertRaises(NotAllowed):
            self.store.work("s", self.c.ref, "writer", "Route writer", (first["ref"],), self.route.ref)
        self.assertEqual(self.store.writing_author("s"), self.owner.ref)

    def test_cancel_returns_partial_draft_and_fences_future_writes(self):
        writer = self.writer()
        draft = self.save(writer)
        result = self.store.cancel_work("s", self.owner.ref, writer.ref, self.c.epoch, "Reassign remaining work")
        self.assertEqual(result.body["refs"], [draft["ref"]])
        self.assertEqual(self.store.writing_author("s"), self.owner.ref)
        self.assertEqual(self.store.cancel_work("s", self.owner.ref, writer.ref, self.c.epoch, "Repeated cancellation").ref, result.ref)
        with self.assertRaises(NotAllowed):
            self.store.require_work("s", writer.ref, self.c.epoch)
        self.save(self.owner, "Continued without discarding draft", draft["ref"])

    def test_cancel_closes_questions_without_erasing_history_or_answer_replays(self):
        from epivra.presentation import progress

        writer = self.writer()
        step = self.store.put("s", "step", {"request": {}}, (writer.ref,))
        question = self.store.ask("s", writer.ref, self.c.epoch, "Which scope?", [], step.ref)
        self.store.cancel_work("s", self.owner.ref, writer.ref, self.c.epoch, "Scope changed")
        self.store.close()
        self.store = Store(self.path)
        self.assertEqual([], self.store.clarifications("s", open_only=True))
        self.assertEqual([question.ref], [q.ref for q in self.store.clarifications("s")])
        with self.assertRaisesRegex(NotAllowed, "finished work"):
            self.store.answer("s", self.owner.ref, self.c.epoch, question.ref, "Resume", [])
        view = next(w for w in progress(self.store, "s")["work"] if w["ref"] == writer.ref)
        self.assertEqual("cancelled", view["state"])
        self.assertIsNone(view["question"])

        other = self.writer("Different scope")
        step = self.store.put("s", "step", {"request": {}}, (other.ref,))
        question = self.store.ask("s", other.ref, self.c.epoch, "Confirm scope", [], step.ref)
        answer = self.store.answer("s", self.owner.ref, self.c.epoch, question.ref, "Confirmed", [])
        self.store.cancel_work("s", self.owner.ref, other.ref, self.c.epoch, "No longer needed")
        self.assertEqual(answer.ref, self.store.answer("s", self.owner.ref, self.c.epoch,
                                                     question.ref, "Confirmed", []).ref)

    def test_cancel_finished_child_preserves_original_result(self):
        writer = self.writer()
        result = self.finish(writer)
        self.assertEqual(self.store.cancel_work("s", self.owner.ref, writer.ref, self.c.epoch, "Already done").ref, result.ref)
        self.assertNotIn("status", result.body)

    def test_receipt_failure_rolls_back_writer_save_without_releasing_turn(self):
        writer = self.writer()
        original = self.store._put
        def fail_receipt(study, kind, body, parents=()):
            if kind == "draft_saved":
                raise OSError("Receipt disk failure")
            return original(study, kind, body, parents)
        with patch.object(self.store, "_put", side_effect=fail_receipt):
            with self.assertRaises(OSError):
                self.save(writer)
        self.assertEqual(self.store.list("s", "report"), [])
        self.assertEqual(self.store.list("s", "draft_saved"), [])
        self.assertEqual(self.store.writing_author("s"), writer.ref)
        self.save(writer)

    def test_stale_base_still_rejected_with_single_author(self):
        first = self.save(self.owner)
        self.save(self.owner, "Updated", first["ref"])
        with self.assertRaises(Conflict):
            self.save(self.owner, "Stale replacement", first["ref"])

    def test_active_writer_prevents_publication_before_artifact_validation(self):
        writer = self.writer()
        with self.assertRaises(NotAllowed):
            self.store.publish("s", self.owner.ref, self.c.epoch, "missing-report", "missing-review")
        self.assertEqual(self.store.writing_author("s"), writer.ref)
