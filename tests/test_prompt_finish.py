"""Shared policy, focused inputs and source-to-manuscript revision contracts.

No vendor API calls or semantic keyword scoring. Scripted models exercise the
same Harness that transports provider requests; prose quality is assessed apart.
"""

from __future__ import annotations

import ast
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from epivra import prompts
from epivra.domain import Call, Conflict, NotAllowed, Reply, encode
from epivra.harness import BUILTINS, Harness, validate
from epivra.research import ResearchLedger
from epivra.storage import Store
from epivra.writing import WritingWorkspace


class Scripted:
    identity = "offline-shared-policy-contract"
    call = None

    async def complete(self, request):
        return Reply("", (self.call,)).to_json()


class PromptFinishTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "research.db"
        self.store = Store(self.db)
        c = self.store.create(
            "s", "Explain the licensed scope and recorded observations.", {}
        )
        p = self.store.put(
            "s",
            "plan",
            {"text": "Examine the original terms and records."},
            (c.direction,),
        )
        self.c = self.store.command("s", "approve", c.ref, "approve", {"plan": p.ref})
        self.owner = self.store.work(
            "s", self.c.ref, "lead", "Complete research", (p.ref,)
        )
        self.source = self.store.put(
            "s",
            "source",
            {
                "origin": "terms.txt",
                "text": "Use indoors. Four observations; follow-up duration unspecified.",
            },
        )
        self.ledger = ResearchLedger(self.store)
        self.writer = WritingWorkspace(self.store)
        self.model = Scripted()
        self.h = Harness(self.store, self.model)
        self.f = self.finding("Indoor use; four observations, duration unspecified.")
        self.b = self.basis([self.f])

    async def asyncTearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def finding(self, statement, **kw):
        return self.ledger.record_finding(
            "s",
            self.owner.ref,
            self.c.epoch,
            statement=statement,
            status="source_statement",
            support=[self.source.ref],
            **kw,
        )

    def basis(self, findings):
        old = self.ledger.current_basis("s")
        refs = [f.ref for f in findings]
        return self.ledger.prepare_writing(
            "s",
            self.owner.ref,
            self.c.epoch,
            findings=refs,
            coverage=[{"question": 0, "findings": refs}],
            rationale="The supplied original covers the declared question with limitations.",
            replaces=old.ref if old else None,
        )

    def save(self, *, key="initial", **kw):
        step = self.store.put("s", "note", {"fixture": key}, (self.owner.ref,))
        return self.writer.save("s", self.owner.ref, self.c.epoch, step.ref, 0, **kw)

    async def call(self, name, args, work=None):
        work = work or self.owner
        self.model.call = Call(name, args)
        await self.h.step("s", work.ref)
        return self.h._steps("s", "observation", work.ref)[-1].body

    async def accept(self, ref):
        editor = self.child("reviewer", "Check final", [ref])
        read = await self.call("read_report", {}, editor)
        self.assertIsNone(read.get("failure"), read)
        result = await self.call(
            "submit_review",
            {
                "reason": "This scripted fixture matches its original terms.",
                "defects": [],
            },
            editor,
        )
        self.assertIsNone(result.get("failure"), result)
        return result["result"]["ref"]

    def child(self, role, task, refs, **kw):
        return self.store.work(
            "s", self.c.ref, role, task, tuple(refs), self.owner.ref, **kw
        )

    async def test_basis_only_revision_preserves_all_text_and_requires_new_review(self):
        text = (
            "# 范围😀\r\n\r\nIndoor only[[cite:"
            + self.source.ref
            + "]].\n\nDuration unspecified."
        )
        saved = self.save(text=text)
        accepted = await self.accept(saved["ref"])
        updated = self.finding(
            "Indoor scope; four observations with unspecified follow-up.",
            replaces=self.f.ref,
            reason="Make the observation limitation explicit.",
        )
        with self.assertRaises(Conflict):
            self.ledger.require_basis("s", self.b.ref)
        new_basis = self.basis([updated])
        request = {"base": saved["ref"], "basis": new_basis.ref, "edits": []}
        validate(request, BUILTINS["patch_draft"][1])
        result = await self.call("patch_draft", request)
        self.assertIsNone(result.get("failure"), result)
        revised = self.store.get("s", result["result"]["ref"])
        old = self.store.get("s", saved["ref"])
        self.assertEqual(text, revised.body["manuscript"])
        self.assertEqual(old.body["text"], revised.body["text"])
        self.assertEqual(old.body["citations"], revised.body["citations"])
        self.assertEqual("basis_rebind", result["result"]["mode"])
        self.assertEqual(0, result["result"]["edit_count"])
        self.assertEqual(new_basis.ref, revised.body["basis"])
        self.assertNotEqual(old.ref, revised.ref)
        with self.assertRaises((Conflict, NotAllowed, ValueError)):
            self.store.publish("s", self.owner.ref, self.c.epoch, revised.ref, accepted)
        review = await self.accept(revised.ref)
        self.store.publish("s", self.owner.ref, self.c.epoch, revised.ref, review)
        self.assertEqual(1, len(self.store.list("s", "publication")))

    async def test_empty_edit_rejects_noop_missing_basis_or_stale_base(self):
        saved = self.save(text="Indoor scope.")
        for kw in (
            {"base": saved["ref"], "edits": []},
            {"base": saved["ref"], "basis": self.b.ref, "edits": []},
            {"edits": [], "basis": self.b.ref},
        ):
            with self.subTest(kw=kw), self.assertRaises((Conflict, ValueError)):
                self.save(key=encode(kw), **kw)
        self.assertEqual(1, len(self.store.list("s", "report")))

    async def test_basis_rebind_replay_does_not_overwrite_newer_draft(self):
        first = self.save(text="Indoor scope.")
        f = self.finding(
            "Four observations only.", replaces=self.f.ref, reason="Correction"
        )
        b = self.basis([f])
        rebound = self.save(key="binding", base=first["ref"], basis=b.ref, edits=[])
        latest = self.save(
            key="patch",
            base=rebound["ref"],
            edits=[
                {"old": "Indoor scope.", "new": "Indoor scope, limited observations."}
            ],
        )
        replay = self.save(key="binding", base=first["ref"], basis=b.ref, edits=[])
        self.assertEqual(rebound, replay)
        self.assertEqual(latest["ref"], self.writer.current("s").ref)
        with self.assertRaises(Conflict):
            self.save(
                key="binding",
                base=first["ref"],
                basis=b.ref,
                edits=[],
                handoff="different request",
            )

    async def test_no_silent_binding_to_invalid_basis_and_no_citation_loss(self):
        saved = self.save(text="Terms[[cite:" + self.source.ref + "]].")
        f = self.finding("Better wording", replaces=self.f.ref, reason="Correction")
        b = self.basis([f])
        with self.assertRaises(ValueError):
            self.save(
                key="uncited", base=saved["ref"], basis=b.ref, evidence=[], edits=[]
            )
        with self.assertRaises((ValueError, NotAllowed)):
            self.save(
                key="not-basis", base=saved["ref"], basis=self.source.ref, edits=[]
            )
        self.assertEqual(saved["ref"], self.writer.current("s").ref)

    async def test_binding_receipt_failure_rolls_back_and_reopen_recovers(self):
        first = self.save(text="Indoor only.")
        b = self.basis([self.f])
        original = self.store._put

        def fail(study, kind, *args, **kw):
            if kind == "draft_saved":
                raise ValueError("simulated durable receipt failure")
            return original(study, kind, *args, **kw)

        with (
            patch.object(self.store, "_put", side_effect=fail),
            self.assertRaises(ValueError),
        ):
            self.save(key="fail", base=first["ref"], basis=b.ref, edits=[])
        self.assertEqual(first["ref"], self.writer.current("s").ref)
        saved = self.save(key="success", base=first["ref"], basis=b.ref, edits=[])
        self.store.close()
        self.store = Store(self.db)
        self.writer = WritingWorkspace(self.store)
        self.assertEqual(saved["ref"], self.writer.current("s").ref)
        self.assertEqual(b.ref, self.writer.current("s").body["basis"])

    async def test_semantic_correction_updates_finding_conflict_basis_and_batch(self):
        # Deliberately wrong seeded interpretation; deterministic test does not
        # claim a real model would detect it. Source snapshots remain unchanged.
        wrong = self.finding(
            "Any location is licensed.",
            replaces=self.f.ref,
            reason="Injected test fault",
        )
        conflict = self.ledger.record_conflict(
            "s",
            self.owner.ref,
            self.c.epoch,
            question="Which environment?",
            findings=[wrong.ref],
            disposition="no_conflict",
            explanation="Injected incorrect interpretation",
            evidence=[self.source.ref],
        )
        self.basis([wrong])
        first = self.save(
            text="# Summary\nAny location.\n\n| Location | All |\n\nRecommendation: outdoors allowed."
        )
        obs = await self.call(
            "record_finding",
            {
                "statement": "Only indoor scope is licensed.",
                "status": "source_statement",
                "support": [self.source.ref],
                "conditions": ["indoors"],
                "replaces": wrong.ref,
                "reason": "Scope omitted; restore the exact condition.",
            },
        )
        self.assertIsNone(obs.get("failure"), obs)
        corrected = self.store.get("s", obs["result"]["ref"])
        self.assertEqual(wrong.ref, obs["result"]["replaces"])
        self.assertIn("does not edit prose", obs["result"]["follow_up"])
        with self.assertRaises(Conflict):
            self.basis([corrected])
        self.ledger.record_conflict(
            "s",
            self.owner.ref,
            self.c.epoch,
            question="Which environment?",
            findings=[corrected.ref],
            disposition="transcription_error",
            explanation="The original explicitly limits use to indoors.",
            evidence=[self.source.ref],
            replaces=conflict.ref,
        )
        b = self.basis([corrected])
        revised = self.save(
            key="batch",
            base=first["ref"],
            basis=b.ref,
            edits=[
                {"old": "Any location.", "new": "Indoor only."},
                {"old": "| Location | All |", "new": "| Location | Indoors |"},
                {"old": "outdoors allowed.", "new": "outdoor use not established."},
            ],
        )
        self.assertEqual(3, revised["edit_count"])
        report = self.writer.current("s")
        self.assertTrue(report.body["manuscript"].startswith("# Summary\n"))
        self.assertEqual(
            [corrected.ref], self.ledger.current_basis("s").body["findings"]
        )
        self.assertEqual(self.source.body, self.store.get("s", self.source.ref).body)
        self.assertEqual(2, len(self.store.list("s", "report")))

    async def test_cosmetic_patch_does_not_mutate_knowledge(self):
        first = self.save(text="# Scope\nIndoor only.")
        second = self.save(
            key="title",
            base=first["ref"],
            edits=[{"old": "# Scope", "new": "# Licensed scope"}],
        )
        self.assertEqual(self.b.ref, second["basis"])
        self.assertEqual(1, len(self.store.list("s", "finding")))

    async def test_task_focus_excludes_unassigned_conclusions_but_lookup_is_complete(
        self,
    ):
        other = self.finding("UNRELATED_GLOBAL_CONCLUSION")
        b = self.basis([self.f, other])
        for role in ("investigator", "synthesizer"):
            child = self.child(
                role, "Check original licensed scope", [self.f.ref, self.source.ref]
            )
            request = self.h._request("s", child)
            self.assertEqual("task_focused_with_full_lookup", request["context_scope"])
            self.assertNotIn("UNRELATED_GLOBAL_CONCLUSION", encode(request))
            self.assertEqual([], request["research_findings"])
            self.assertEqual(2, request["navigation"]["research_findings"]["total"])
            self.assertEqual(
                0, request["navigation"]["research_findings"]["next_offset"]
            )
            result = await self.call(
                "read_context",
                {"section": "research_findings", "offset": 0, "limit": 20},
                child,
            )
            self.assertIsNone(result.get("failure"), result)
            self.assertIn("UNRELATED_GLOBAL_CONCLUSION", encode(result["result"]))
            read = await self.call("read_source", {"ref": self.source.ref}, child)
            self.assertEqual(self.source.body["text"], read["result"]["text"])
        self.assertEqual(b.ref, self.ledger.current_basis("s").ref)
        self.assertIn(
            "UNRELATED_GLOBAL_CONCLUSION", encode(self.h._request("s", self.owner))
        )

    async def test_final_editor_retains_full_basis_focused_check_does_not_preload_it(
        self,
    ):
        other = self.finding("EXTRA_VALID_FINDING")
        self.basis([self.f, other])
        saved = self.save(text="Indoor only.")
        final = self.child("reviewer", "Review entire manuscript", [saved["ref"]])
        check = self.child(
            "reviewer",
            "Check indoor scope only",
            [saved["ref"], self.source.ref],
            review_mode="check",
        )
        self.assertIn("EXTRA_VALID_FINDING", encode(self.h._request("s", final)))
        self.assertNotIn("EXTRA_VALID_FINDING", encode(self.h._request("s", check)))
        self.assertIn("read_source", self.h._request("s", check)["tools"])
        self.assertNotIn("submit_review", self.h._request("s", check)["tools"])

    async def test_plan_and_research_prompts_align_with_tools_and_never_vendor_branch(
        self,
    ):
        c = self.store.create("new", "Research the supplied materials.", {})
        planner = self.store.work("new", c.ref, "lead", "Propose a route")
        before = self.h._request("new", planner)
        self.assertEqual(prompts.ROUTE, before["system"])
        self.assertEqual("route_approval", before["research_stage"])
        self.assertNotIn("read_source", before["tools"])
        self.assertIn("propose_plan", before["tools"])
        after = self.h._request("s", self.owner)
        self.assertEqual(prompts.ROLES["lead"], after["system"])
        self.assertNotIn("request_clarification", after["tools"])
        self.assertNotIn("propose_plan", after["tools"])
        for vendor in ("openai", "anthropic", "google", "deepseek"):
            with patch.object(self.model, "identity", vendor):
                self.assertEqual(
                    after["system"], self.h._request("s", self.owner)["system"]
                )

    async def test_prompt_definitions_are_single_source_not_overridden_or_model_tuned(
        self,
    ):
        tree = ast.parse(Path(prompts.__file__).read_text(encoding="utf-8"))
        assignments = [n for n in tree.body if isinstance(n, ast.Assign)]
        for name in ("TOOLS", "ROLES"):
            definitions = [
                n.value
                for n in assignments
                if any(isinstance(t, ast.Name) and t.id == name for t in n.targets)
            ]
            self.assertEqual(1, len(definitions))
            keys = [k.value for k in definitions[0].keys]
            self.assertEqual(len(keys), len(set(keys)))
        self.assertFalse(
            any(
                isinstance(n, ast.Call)
                and isinstance(n.func, ast.Attribute)
                and n.func.attr == "update"
                for n in ast.walk(tree)
            )
        )
        self.assertEqual(set(BUILTINS), set(prompts.TOOLS))


if __name__ == "__main__":
    unittest.main()
