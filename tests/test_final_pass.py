"""Provider-neutral prompt contracts, focused inputs and atomic basis rebinding.

These tests validate mechanisms, not model judgment or release quality.
"""
from __future__ import annotations

import ast
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from epivra.domain import Call, Conflict, NotAllowed, Reply
from epivra.harness import BUILTINS, Harness, validate
from epivra.prompts import PROMPT_VERSION, ROLES, ROUTE_PROMPT, TOOLS
from epivra.research import ResearchLedger
from epivra.storage import Store
from epivra.writing import WritingWorkspace


class Echo:
    identity = "final-contracts-offline"
    call = None

    async def complete(self, request):
        return Reply("", (self.call,)).to_json()


class FinalPassTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "state.db"
        self.store = Store(self.path)
        c = self.store.create("s", "Explain what the supplied records establish.", {})
        self.plan = self.store.put("s", "plan", {"text": "Read records and compare their scope."}, (c.direction,))
        self.c = self.store.command("s", "approved", c.ref, "approve", {"plan": self.plan.ref})
        self.owner = self.store.work("s", self.c.ref, "lead", "Research and deliver", (self.plan.ref,))
        self.source = self.store.put("s", "source", {"text": "Of 80 shipped items, 6 were inspected. Those 6 passed inspection.", "origin": "shipping.txt"})
        self.model = Echo()
        self.h = Harness(self.store, self.model)
        self.ledger = ResearchLedger(self.store)
        self.writing = WritingWorkspace(self.store)

    async def asyncTearDown(self):
        self.store.close()
        self.temp.cleanup()

    async def call(self, name, args, work=None):
        work = work or self.owner
        self.model.call = Call(name, args)
        await self.h.step("s", work.ref)
        return self.h._steps("s", "observation", work.ref)[-1].body

    def finding(self, statement="The inspected 6 passed", **extra):
        return self.ledger.record_finding("s", self.owner.ref, self.c.epoch, statement=statement, status="source_statement", support=[self.source.ref], **extra)

    def basis(self, findings, replaces=None):
        return self.ledger.prepare_writing("s", self.owner.ref, self.c.epoch, findings=[f.ref for f in findings], coverage=[{"question": 0, "findings": [f.ref for f in findings]}], rationale="The record supports a sample-only answer.", replaces=replaces)

    async def draft(self):
        f = self.finding()
        b = self.basis([f])
        obs = await self.call("draft_report", {"text": "# Result\n\nThe 6 inspected items passed[[cite:" + self.source.ref + "]].\n\nOther items were not inspected.", "evidence": [self.source.ref]})
        self.assertIsNone(obs["failure"], obs)
        return f, b, self.store.get("s", obs["result"]["ref"])

    def updated_basis(self, finding, basis):
        f = self.finding("Six of the 80 shipped items were inspected and passed", replaces=finding.ref, reason="Retain the sample condition", conditions=["Only the 6 inspected items"], limits=["No finding on the other 74"])
        return f, self.basis([f], basis.ref)

    async def test_basis_only_update_preserves_exact_text_citations_and_author_lifecycle(self):
        f, b, report = await self.draft()
        corrected, new_basis = self.updated_basis(f, b)
        obs = await self.call("patch_draft", {"base": report.ref, "basis": new_basis.ref, "handoff": "Statement and scope fixed in canonical evidence; prose already qualified."})
        self.assertIsNone(obs["failure"], obs)
        self.assertEqual("basis_rebind", obs["result"]["mode"])
        self.assertEqual(0, obs["result"]["edit_count"])
        current = self.store.get("s", obs["result"]["ref"])
        for key in ("text", "manuscript", "evidence", "citations"):
            self.assertEqual(report.body[key], current.body[key])
        self.assertEqual(new_basis.ref, current.body["basis"])
        self.assertEqual(report.ref, current.body["previous_report"])
        self.assertEqual([corrected.ref], new_basis.body["findings"])
        self.assertEqual(b.ref, self.store.get("s", report.ref).body["basis"])
        self.assertFalse(self.h.finished("s", self.owner.ref))
        self.assertEqual([], self.store.list("s", "publication"))

    async def test_basis_only_update_requires_a_real_change(self):
        _, b, report = await self.draft()
        count = self.store.count("s", "report")
        for args in ({"base": report.ref}, {"base": report.ref, "basis": b.ref}, {"base": report.ref, "edits": []}):
            with self.subTest(args=args):
                obs = await self.call("patch_draft", args)
                self.assertIsNotNone(obs["failure"])
                self.assertEqual(count, self.store.count("s", "report"))

    async def test_no_basis_rebind_before_first_draft(self):
        b = self.basis([self.finding()])
        obs = await self.call("patch_draft", {"base": "a" * 64, "basis": b.ref})
        self.assertIsNotNone(obs["failure"])
        self.assertEqual([], self.store.list("s", "report"))

    async def test_basis_only_update_cannot_silently_change_source_set(self):
        f, b, report = await self.draft()
        _, new = self.updated_basis(f, b)
        obs = await self.call("patch_draft", {"base": report.ref, "basis": new.ref, "evidence": []})
        self.assertIsNotNone(obs["failure"])
        self.assertEqual(report.ref, self.writing.current("s").ref)

    async def test_basis_rebind_rejects_new_basis_missing_cited_source(self):
        f, b, report = await self.draft()
        other = self.store.put("s", "source", {"text": "The inventory says nothing about inspection."})
        unrelated = self.ledger.record_finding("s", self.owner.ref, self.c.epoch, statement="The inventory cannot answer inspection", status="observation", support=[other.ref])
        new = self.basis([unrelated], b.ref)
        obs = await self.call("patch_draft", {"base": report.ref, "basis": new.ref})
        self.assertIsNotNone(obs["failure"])
        self.assertEqual(report.ref, self.writing.current("s").ref)

    async def test_stale_base_and_stale_basis_rejected(self):
        f, b, report = await self.draft()
        _, new = self.updated_basis(f, b)
        ok = await self.call("patch_draft", {"base": report.ref, "basis": new.ref})
        current = ok["result"]["ref"]
        for base, basis in ((report.ref, new.ref), (current, b.ref)):
            obs = await self.call("patch_draft", {"base": base, "basis": basis})
            self.assertIsNotNone(obs["failure"])
        self.assertEqual(current, self.writing.current("s").ref)

    async def test_old_acceptance_cannot_authorize_rebound_report(self):
        f, b, report = await self.draft()
        editor = self.store.work("s", self.c.ref, "reviewer", "Edit exact report", (report.ref,), self.owner.ref)
        await self.call("read_report", {}, editor)
        review = await self.call("submit_review", {"reason": "Correctly scoped", "defects": []}, editor)
        self.assertIsNone(review["failure"])
        _, new = self.updated_basis(f, b)
        changed = await self.call("patch_draft", {"base": report.ref, "basis": new.ref})
        obs = await self.call("publish_report", {"report": changed["result"]["ref"], "review": review["result"]["ref"]})
        self.assertIsNotNone(obs["failure"])
        self.assertFalse(self.store.list("s", "publication"))

    async def test_basis_rebind_rolls_back_when_receipt_fails(self):
        f, b, report = await self.draft()
        _, new = self.updated_basis(f, b)
        original = self.store._put
        def faulty(study, kind, *args, **kwargs):
            if kind == "draft_saved":
                raise ValueError("simulated disk failure")
            return original(study, kind, *args, **kwargs)
        with patch.object(self.store, "_put", side_effect=faulty):
            obs = await self.call("patch_draft", {"base": report.ref, "basis": new.ref})
        self.assertIsNotNone(obs["failure"])
        self.assertEqual(report.ref, self.writing.current("s").ref)
        self.assertEqual(1, self.store.count("s", "report"))

    async def test_basis_rebind_replay_is_idempotent_and_rejects_changed_identity(self):
        f, b, report = await self.draft()
        _, new = self.updated_basis(f, b)
        step = self.store.put("s", "step", {"fixture": "rebind"}, (self.owner.ref,))
        args = ("s", self.owner.ref, self.c.epoch, step.ref, 0)
        first = self.writing.save(*args, base=report.ref, basis=new.ref)
        self.assertEqual(first, self.writing.save(*args, base=report.ref, basis=new.ref))
        self.assertEqual(2, self.store.count("s", "report"))
        with self.assertRaises(Conflict):
            self.writing.save(*args, base=report.ref, basis=new.ref, handoff="different request")
        self.store.close()
        self.store = Store(self.path)
        self.assertEqual(first, WritingWorkspace(self.store).save(*args, base=report.ref, basis=new.ref))

    async def test_unassigned_helper_cannot_rebind_another_authors_draft(self):
        f, b, report = await self.draft()
        _, new = self.updated_basis(f, b)
        with self.assertRaises(NotAllowed):
            self.store.work("s", self.c.ref, "writer", "Unrelated writing", (self.source.ref,), self.owner.ref)
        self.assertEqual(report.ref, self.writing.current("s").ref)

    async def test_editor_cannot_write_basis_or_draft(self):
        f, b, report = await self.draft()
        editor = self.store.work("s", self.c.ref, "reviewer", "Edit", (report.ref,), self.owner.ref)
        _, new = self.updated_basis(f, b)
        obs = await self.call("patch_draft", {"base": report.ref, "basis": new.ref}, editor)
        self.assertIsNotNone(obs["failure"])
        self.assertEqual(report.ref, self.writing.current("s").ref)

    async def test_finding_correction_receipt_shows_stale_basis(self):
        f, b, _ = await self.draft()
        obs = await self.call("record_finding", {"statement": "6 inspected items passed", "status": "source_statement", "support": [self.source.ref], "replaces": f.ref, "reason": "Keep the scope explicit", "conditions": ["inspected items"], "limits": ["other items unknown"]})
        self.assertIsNone(obs["failure"])
        self.assertEqual(f.ref, obs["result"]["replaces"])
        self.assertEqual({"ref": b.ref, "stale": True}, obs["result"]["writing_basis"])

    async def test_focused_helper_has_relevant_findings_not_global_conclusions(self):
        relevant = self.finding("RELEVANT_SAMPLE_SCOPE")
        other = self.finding("UNRELATED_GLOBAL_CONCLUSION_987")
        b = self.basis([relevant, other])
        helper = self.store.work("s", self.c.ref, "synthesizer", "Verify only the inspection scope", (relevant.ref,), self.owner.ref)
        request = self.h._request("s", helper, prepare_wire=False)
        body = json.dumps(request, ensure_ascii=False)
        self.assertIn("RELEVANT_SAMPLE_SCOPE", body)
        self.assertNotIn("UNRELATED_GLOBAL_CONCLUSION_987", body)
        self.assertNotIn(b.ref, [x["ref"] for x in request["context"]])
        self.assertEqual(2, request["navigation"]["research_findings"]["total"])
        self.assertEqual(0, request["navigation"]["research_findings"]["next_offset"])
        self.assertEqual([], request["research_findings"])
        expanded = self.h._request("s", helper, section="research_findings", limit=20)
        self.assertIn(other.ref, [row["ref"] for row in expanded["items"]])
        source = await self.call("read_source", {"ref": self.source.ref}, helper)
        self.assertEqual(self.source.body["text"], source["result"]["text"])
        self.assertEqual("Explain what the supplied records establish.", request["direction"]["request"])

    async def test_explicit_conflict_dependency_and_replacement_reach_focused_helper(self):
        f = self.finding("BEFORE_CORRECTION")
        conflict = self.ledger.record_conflict("s", self.owner.ref, self.c.epoch, question="Is scope established?", findings=[f.ref])
        new = self.finding("CORRECTED_SAMPLE_SCOPE", replaces=f.ref, reason="scope correction")
        helper = self.store.work("s", self.c.ref, "synthesizer", "Resolve the supplied conflict", (conflict.ref,), self.owner.ref)
        text = json.dumps(self.h._request("s", helper, prepare_wire=False))
        self.assertIn(new.ref, text)
        self.assertIn("CORRECTED_SAMPLE_SCOPE", text)
        self.assertIn(conflict.ref, text)

    async def test_full_editor_and_writer_keep_complete_bound_basis(self):
        f, b, report = await self.draft()
        for role, refs in (("reviewer", (report.ref,)), ("writer", (b.ref, report.ref))):
            helper = self.store.work("s", self.c.ref, role, "Complete " + role, refs, self.owner.ref)
            text = json.dumps(self.h._request("s", helper, prepare_wire=False))
            self.assertIn(f.body["statement"], text)
            self.assertIn(b.ref, text)

    async def test_route_prompt_is_distinct_and_actual_tools_match_stage(self):
        c = self.store.create("route", "Compare supported methods, without prescribing results.", {})
        owner = self.store.work("route", c.ref, "lead", "Propose a research route")
        request = self.h._request("route", owner, prepare_wire=False)
        self.assertEqual(ROUTE_PROMPT, request["system"])
        self.assertEqual("route_approval", request["phase"])
        self.assertEqual(PROMPT_VERSION, request["prompt_version"])
        for tool in ("record_finding", "read_source", "delegate_work", "request_clarification"):
            self.assertNotIn(tool, request["tools"])
        approved = self.h._request("s", self.owner, prepare_wire=False)
        self.assertEqual(ROLES["lead"], approved["system"])
        self.assertNotIn("propose_plan", approved["tools"])
        self.assertNotIn("request_clarification", approved["tools"])

    async def test_same_prompt_for_all_provider_identities(self):
        systems = []
        for provider in ("deepseek", "openai", "anthropic", "google"):
            model = type("Offline", (), {"identity": provider})()
            h = Harness(self.store, model)
            systems.append(h._request("s", self.owner, prepare_wire=False)["system"])
        self.assertEqual([ROLES["lead"]] * 4, systems)


class PromptSurfaceTests(unittest.TestCase):
    def test_single_tool_definition_no_shadowed_legacy_contracts(self):
        from epivra import prompts
        tree = ast.parse(Path(prompts.__file__).read_text(encoding="utf-8"))
        definition = next(n.value for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "TOOLS" for t in n.targets))
        keys = [ast.literal_eval(k) for k in definition.keys]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(set(BUILTINS), set(TOOLS))
        self.assertNotIn("TOOLS.update", Path(prompts.__file__).read_text(encoding="utf-8"))

    def test_binding_only_contract_is_explicit_and_empty_edits_rejected(self):
        schema = BUILTINS["patch_draft"][1]
        validate({"base": "a" * 64, "basis": "b" * 64}, schema)
        with self.assertRaises(ValueError):
            validate({"base": "a" * 64, "edits": []}, schema)
        self.assertIn("basis-only", schema["properties"]["edits"]["description"])

    def test_delegation_batching_and_review_semantics_are_not_role_workflow(self):
        self.assertIn("能自己做不等于应该独自做", ROLES["lead"])
        self.assertIn("独立上下文", ROLES["lead"])
        self.assertIn("不重复调查同一问题", ROLES["lead"])
        self.assertIn("不是每项研究的必经阶段", ROLES["lead"])
        self.assertIn("同一原因合并", TOOLS["submit_review"])
        self.assertIn("当前有效依据", ROLES["reviewer"])
        self.assertIn("小定位范围不限制本轮修改范围", TOOLS["patch_draft"])
        self.assertIn("不提出任何研究假设或预定结论", ROUTE_PROMPT)


if __name__ == "__main__":
    unittest.main()
