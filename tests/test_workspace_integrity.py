"""Published evidence is sealed; incomplete internal draft actions replay once."""
import tempfile
import unittest
from pathlib import Path

from research_fixture import basis_arguments

from epivra.domain import Conflict, NotAllowed
from epivra.research import ResearchLedger
from epivra.storage import Store
from epivra.writing import WritingWorkspace


class WorkspaceIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / "state.db")
        self.addCleanup(self.store.close)
        c = self.store.create("s", "Explain the supplied record", {})
        p = self.store.put("s", "plan", {"text": "Read the supplied record"}, (c.direction,))
        self.c = self.store.command("s", "approve", c.ref, "approve", {"plan": p.ref})
        self.owner = self.store.work("s", self.c.ref, "lead", "Complete research", (p.ref,))
        self.source = self.store.put("s", "source", {"text": "12 attended", "origin": "record"})
        self.ledger = ResearchLedger(self.store)
        self.finding = self.ledger.record_finding("s", self.owner.ref, self.c.epoch, statement="12 attended", status="source_statement", support=[self.source.ref])
        self.basis = self.ledger.prepare_writing("s", self.owner.ref, self.c.epoch, **basis_arguments(self.ledger.store, {'findings': [self.finding.ref], 'coverage': [{"question": 0, "findings": [self.finding.ref]}], 'rationale': "The supplied record covers the requested count"}))
        self.writing = WritingWorkspace(self.store)

    def test_publication_fences_late_evidence_mutations(self):
        # Isolate the publication-state fence. The full service test separately
        # exercises the complete, independently reviewed publication path.
        with self.store.transaction():
            self.store._put("s", "publication", {"fixture": "published-state"}, (self.c.direction,))
        operations = [
            lambda: self.ledger.record_finding("s", self.owner.ref, self.c.epoch, statement="changed", status="inference", support=[self.source.ref]),
            lambda: self.ledger.record_conflict("s", self.owner.ref, self.c.epoch, question="late question", findings=[self.finding.ref]),
            lambda: self.ledger.prepare_writing("s", self.owner.ref, self.c.epoch, **basis_arguments(self.ledger.store, {'findings': [], 'coverage': [{"question": 0, "findings": [], "limitation": "late"}], 'rationale': "late", 'replaces': self.basis.ref})),
        ]
        for operation in operations:
            with self.assertRaisesRegex(NotAllowed, "published"):
                operation()
        self.assertEqual(self.basis.ref, self.ledger.require_basis("s", self.basis.ref).ref)
        self.assertEqual(1, self.store.count("s", "finding"))

    def test_lost_patch_receipt_replays_without_duplicate_revision(self):
        step = self.store.put("s", "step", {"fixture": "initial"}, (self.owner.ref,))
        first = self.writing.save("s", self.owner.ref, self.c.epoch, step.ref, 0, text="12 attended.", evidence=[])
        edit_step = self.store.put("s", "step", {"fixture": "edit"}, (self.owner.ref,))
        args = {"base": first["ref"], "edits": [{"old": "12 attended.", "new": "The record states that 12 attended."}]}
        changed = self.writing.save("s", self.owner.ref, self.c.epoch, edit_step.ref, 0, **args)
        replay = self.writing.save("s", self.owner.ref, self.c.epoch, edit_step.ref, 0, **args)
        self.assertEqual(changed, replay)
        self.assertEqual(2, self.store.count("s", "report"))
        with self.assertRaises(Conflict):
            self.writing.save("s", self.owner.ref, self.c.epoch, edit_step.ref, 0, base=first["ref"], edits=[{"old": "12 attended.", "new": "Another edit"}])


if __name__ == "__main__":
    unittest.main()
