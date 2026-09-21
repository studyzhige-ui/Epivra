"""End-to-end research contracts, not an assertion that a model is truthful."""

from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from epivra.application import ResearchService
from epivra.domain import Call, Conflict, NotAllowed, Reply
from epivra.harness import BUILTINS, Harness, validate
from epivra.research import ResearchLedger
from epivra.storage import Store
from epivra.writing import WritingWorkspace, apply_edits


class Echo:
    identity = "workspace-contract-fixture"
    call = None

    async def complete(self, request):
        return Reply("", (self.call,)).to_json()


class WorkspaceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "research.db"
        self.store = Store(self.path)
        c = self.store.create(
            "s", "Explain attendance, not population effectiveness", {}
        )
        self.plan = self.store.put(
            "s",
            "plan",
            {"text": "Read the registry and check the scope."},
            (c.direction,),
        )
        self.c = self.store.command(
            "s", "approve", c.ref, "approve", {"plan": self.plan.ref}
        )
        self.owner = self.store.work(
            "s", self.c.ref, "lead", "Own the entire research", (self.plan.ref,)
        )
        self.source = self.store.put(
            "s",
            "source",
            {
                "text": "17 registered; 12 attended. No population effectiveness was measured.",
                "origin": "registry.txt",
            },
        )
        self.ledger = ResearchLedger(self.store)
        self.writing = WritingWorkspace(self.store)
        self.model = Echo()
        self.h = Harness(self.store, self.model)

    async def asyncTearDown(self):
        self.store.close()
        self.tmp.cleanup()

    async def call(self, name, args, work=None):
        work = work or self.owner
        self.model.call = Call(name, args)
        await self.h.step("s", work.ref)
        result = self.h._steps("s", "observation", work.ref)[-1].body
        return result

    async def finding(self, **changes):
        args = {
            "statement": "17 registered and 12 attended",
            "status": "source_statement",
            "support": [self.source.ref],
            "conditions": ["registry scope"],
            "limits": ["No population inference"],
        }
        args.update(changes)
        obs = await self.call("record_finding", args)
        self.assertIsNone(obs.get("failure"), obs)
        return self.store.get("s", obs["result"]["ref"])

    async def basis(self, findings, **changes):
        args = {
            "findings": [f.ref for f in findings],
            "coverage": [{"question": 0, "findings": [f.ref for f in findings]}],
            "rationale": "The supplied original answers the only question; its limitation is explicit.",
        }
        args.update(changes)
        obs = await self.call("prepare_writing", args)
        self.assertIsNone(obs.get("failure"), obs)
        return self.store.get("s", obs["result"]["ref"])

    async def draft(self, **changes):
        args = {
            "text": "# Attendance\n\n17 registered; 12 attended[[cite:"
            + self.source.ref
            + "]].\n\nNot a population estimate.",
            "evidence": [self.source.ref],
        }
        args.update(changes)
        obs = await self.call("draft_report", args)
        self.assertIsNone(obs.get("failure"), obs)
        return self.store.get("s", obs["result"]["ref"])

    async def accept(self, report):
        editor = self.store.work(
            "s",
            self.c.ref,
            "reviewer",
            "Check the exact document " + report.ref,
            (report.ref,),
            self.owner.ref,
        )
        await self.call("read_report", {}, editor)
        obs = await self.call(
            "submit_review",
            {"reason": "Matches the original and basis", "defects": []},
            editor,
        )
        self.assertIsNone(obs.get("failure"), obs)
        return self.store.get("s", obs["result"]["ref"])

    async def test_no_draft_before_readiness_and_no_false_host_certification(self):
        obs = await self.call("draft_report", {"text": "Premature", "evidence": []})
        self.assertIsNotNone(obs.get("failure"))
        self.assertFalse(self.store.list("s", "report"))
        finding = await self.finding()
        basis = await self.basis([finding])
        self.assertEqual("agent_assessed_not_host_certified", basis.body["status"])
        report = await self.draft()
        self.assertEqual(basis.ref, report.body["basis"])
        self.assertFalse(self.h.finished("s", self.owner.ref))

    async def test_plan_or_review_cannot_be_source_support(self):
        for ref in (self.plan.ref, self.owner.ref):
            obs = await self.call(
                "record_finding",
                {
                    "statement": "Consensus",
                    "status": "source_statement",
                    "support": [ref],
                },
            )
            self.assertIsNotNone(obs.get("failure"))
        self.assertEqual([], self.store.list("s", "finding"))

    async def test_original_excerpt_support_and_cross_study_guard(self):
        read = await self.call("read_source", {"ref": self.source.ref})
        note = await self.call(
            "record_evidence",
            {
                "text": "Registered and attended differ",
                "selection": read["result"]["selections"][0]["selection"],
            },
        )
        finding = await self.finding(support=[note["result"]["ref"]])
        self.assertEqual([self.source.ref], finding.body["sources"])
        c = self.store.create("other", "Unrelated", {})
        foreign = self.store.put("other", "source", {"text": "foreign"}, (c.direction,))
        obs = await self.call(
            "record_finding",
            {"statement": "bad", "status": "observation", "support": [foreign.ref]},
        )
        self.assertIsNotNone(obs.get("failure"))

    async def test_inference_cannot_become_source_statement_by_restatement(self):
        f = await self.finding(status="inference")
        obs = await self.call(
            "record_finding",
            {
                "statement": "Same consensus",
                "status": "source_statement",
                "support": [self.source.ref],
                "replaces": f.ref,
                "reason": "Another role agrees",
            },
        )
        self.assertIsNotNone(obs.get("failure"))
        self.assertEqual([f.ref], [a.ref for a in self.ledger.current("s", "finding")])

    async def test_support_novelty_uses_original_ranges_not_note_identity(self):
        def note(start, end, label):
            return self.store.put(
                "s", "note",
                {"source": self.source.ref, "offset": start,
                 "quote": self.source.body["text"][start:end], "text": label},
                (self.source.ref,),
            ).ref

        original = note(0, 20, "first")
        duplicate = note(0, 20, "another producer annotation")
        subset = note(2, 10, "subset")
        overlap = note(10, 25, "new tail")
        left, right = note(0, 10, "left"), note(10, 20, "right")
        for prior, proposed, allowed in (
            ([original], [duplicate], False),
            ([original], [subset], False),
            ([left, right], [duplicate], False),
            ([self.source.ref], [duplicate], False),
            ([original], [overlap], True),
            ([original], [self.source.ref], True),
        ):
            with self.subTest(prior=prior, proposed=proposed):
                finding = await self.finding(status="inference", support=prior)
                result = await self.call("record_finding", {
                    "statement": "Reassessed claim", "status": "source_statement",
                    "support": proposed, "replaces": finding.ref,
                    "reason": "Reassess original evidence",
                })
                self.assertEqual(allowed, result.get("failure") is None, result)

    async def test_finding_replacement_is_cas_and_invalidates_written_basis(self):
        first = await self.finding()
        basis = await self.basis([first])
        report = await self.draft()
        second = await self.finding(
            replaces=first.ref,
            reason="Preserve exact meaning",
            statement="Attendance was 12, not the 17 registrations",
        )
        with self.assertRaises(Conflict):
            self.ledger.require_basis("s", basis.ref)
        self.assertTrue(self.ledger.snapshot("s")["basis"]["stale"])
        obs = await self.call(
            "record_finding",
            {
                "statement": "stale",
                "status": "observation",
                "support": [self.source.ref],
                "replaces": first.ref,
                "reason": "stale edit",
            },
        )
        self.assertIsNotNone(obs.get("failure"))
        new = await self.basis([second], replaces=basis.ref)
        obs = await self.call(
            "patch_draft",
            {
                "base": report.ref,
                "basis": new.ref,
                "edits": [
                    {
                        "old": "17 registered; 12 attended",
                        "new": "Of 17 registrations, 12 attended",
                    }
                ],
            },
        )
        self.assertIsNone(obs.get("failure"), obs)

    async def test_new_knowledge_is_not_silently_ignored_by_old_basis(self):
        f = await self.finding()
        old = await self.basis([f])
        await self.finding(statement="Effectiveness was not measured")
        with self.assertRaises(Conflict):
            self.ledger.require_basis("s", old.ref)

    async def test_open_conflict_blocks_writing_then_real_unresolved_result_is_permitted(
        self,
    ):
        f = await self.finding()
        obs = await self.call(
            "record_conflict",
            {"question": "Can these counts imply effectiveness?", "findings": [f.ref]},
        )
        conflict = self.store.get("s", obs["result"]["ref"])
        obs = await self.call(
            "prepare_writing",
            {
                "findings": [f.ref],
                "coverage": [{"question": 0, "findings": [f.ref]}],
                "rationale": "premature",
            },
        )
        self.assertIsNotNone(obs.get("failure"))
        obs = await self.call(
            "record_conflict",
            {
                "question": conflict.body["question"],
                "findings": [f.ref],
                "replaces": conflict.ref,
                "disposition": "insufficient_material",
                "explanation": "The registry explicitly says effectiveness was not measured.",
                "evidence": [self.source.ref],
            },
        )
        self.assertIsNone(obs.get("failure"), obs)
        await self.basis(
            [f], limitations=["No inference about population effectiveness"]
        )
        await self.draft()

    async def test_closed_conflict_becomes_stale_when_its_finding_changes(self):
        f = await self.finding()
        self.ledger.record_conflict(
            "s",
            self.owner.ref,
            self.c.epoch,
            question="Count interpretation",
            findings=[f.ref],
            disposition="no_conflict",
            explanation="Different events",
            evidence=[self.source.ref],
        )
        await self.finding(
            replaces=f.ref,
            reason="Corrected count interpretation",
            statement="Only attendance counted",
        )
        self.assertTrue(self.ledger.snapshot("s")["conflicts"][0]["stale"])

    async def test_every_approved_question_needs_coverage_or_explicit_limitation(self):
        for coverage in (
            [],
            [{"question": 1, "findings": []}],
            [{"question": 0, "findings": []}],
        ):
            obs = await self.call(
                "prepare_writing",
                {
                    "findings": [],
                    "coverage": coverage,
                    "rationale": "Not an assertion of completeness",
                },
            )
            self.assertIsNotNone(obs.get("failure"))
        obs = await self.call(
            "prepare_writing",
            {
                "findings": [],
                "coverage": [
                    {
                        "question": 0,
                        "findings": [],
                        "limitation": "No accessible original for this claim",
                    }
                ],
                "rationale": "Only a bounded inability statement is supported.",
            },
        )
        self.assertIsNone(obs.get("failure"), obs)

    async def test_patch_preserves_every_unaffected_character_and_citation(self):
        await self.basis([await self.finding()])
        report = await self.draft(
            text="# 计数\r\n\n17 registered[[cite:"
            + self.source.ref
            + "]].\n\n"
            + "e\u0301😀 untouched\n" * 1000
        )
        obs = await self.call(
            "patch_draft",
            {
                "base": report.ref,
                "edits": [
                    {"old": "17 registered", "new": "17 registered; 12 attended"}
                ],
            },
        )
        self.assertIsNone(obs.get("failure"), obs)
        revised = self.store.get("s", obs["result"]["ref"])
        self.assertEqual(
            report.body["manuscript"].replace(
                "17 registered", "17 registered; 12 attended"
            ),
            revised.body["manuscript"],
        )
        self.assertEqual(report.body["citations"], revised.body["citations"])
        self.assertEqual(report.ref, revised.body["previous_report"])
        self.assertFalse(self.h.finished("s", self.owner.ref))
        self.assertEqual("patch", obs["result"]["mode"])

    async def test_shared_draft_rejects_stale_helper_write_and_old_review(self):
        await self.basis([await self.finding()])
        report = await self.draft()
        review = await self.accept(report)
        helper = self.store.work(
            "s",
            self.c.ref,
            "writer",
            "Edit the supplied draft",
            (report.ref,),
            self.owner.ref,
        )
        obs = await self.call(
            "patch_draft",
            {
                "base": report.ref,
                "edits": [{"old": "Attendance", "new": "Registry counts"}],
            },
            helper,
        )
        self.assertIsNone(obs.get("failure"), obs)
        stale = await self.call(
            "patch_draft",
            {"base": report.ref, "edits": [{"old": "Attendance", "new": "Old edit"}]},
        )
        self.assertIsNotNone(stale.get("failure"))
        with self.assertRaises(Conflict):
            self.store.publish(
                "s", self.owner.ref, self.c.epoch, report.ref, review.ref
            )
        current = self.writing.current("s")
        self.assertEqual(helper.ref, current.body["producer"])

    async def test_unknown_or_invalid_edit_does_not_leave_partial_document(self):
        await self.basis([await self.finding()])
        report = await self.draft()
        for edit in (
            {"old": "not present", "new": "x"},
            {"old": "Attendance", "new": "Unsupported[[cite:" + "0" * 64 + "]]"},
        ):
            obs = await self.call("patch_draft", {"base": report.ref, "edits": [edit]})
            self.assertIsNotNone(obs.get("failure"))
            self.assertEqual(report.ref, self.writing.current("s").ref)
        self.assertEqual(1, self.store.count("s", "draft_saved"))

    async def test_patch_and_save_receipt_are_atomic(self):
        await self.basis([await self.finding()])
        report = await self.draft()
        original = self.store._put

        def fail(study, kind, *args, **kwargs):
            if kind == "draft_saved":
                raise OSError("simulated receipt failure")
            return original(study, kind, *args, **kwargs)

        with patch.object(self.store, "_put", side_effect=fail):
            with self.assertRaises(OSError):
                await self.call(
                    "patch_draft",
                    {
                        "base": report.ref,
                        "edits": [{"old": "Attendance", "new": "Registry"}],
                    },
                )
        self.assertEqual(report.ref, self.writing.current("s").ref)
        self.assertEqual(1, self.store.count("s", "report"))

    async def test_exact_research_action_replay_survives_replacement_commit(self):
        f = await self.finding()
        args = dict(
            statement="New actual interpretation",
            status="inference",
            support=[self.source.ref],
            replaces=f.ref,
            reason="Bound the interpretation",
            _operation="saved-step-action",
        )
        revised = self.ledger.record_finding("s", self.owner.ref, self.c.epoch, **args)
        again = self.ledger.record_finding("s", self.owner.ref, self.c.epoch, **args)
        self.assertEqual(revised.ref, again.ref)
        with self.assertRaises(Conflict):
            self.ledger.record_finding(
                "s", self.owner.ref, self.c.epoch, **{**args, "statement": "Different"}
            )

    async def test_workspace_survives_reopen_and_is_exposed_to_editor(self):
        basis = await self.basis([await self.finding()])
        report = await self.draft()
        self.store.close()
        self.store = Store(self.path)
        self.h = Harness(self.store, self.model)
        self.writing = WritingWorkspace(self.store)
        self.assertEqual(report.ref, self.writing.current("s").ref)
        request = self.h._request("s", self.owner)
        self.assertEqual(basis.ref, request["writing_basis"]["ref"])
        editor = self.store.work(
            "s",
            self.c.ref,
            "reviewer",
            "Read exact saved basis",
            (report.ref,),
            self.owner.ref,
        )
        request = self.h._request("s", editor)
        self.assertTrue(any(x.get("ref") == basis.ref for x in request["context"]))
        self.assertNotIn("patch_draft", request["tools"])

    async def test_no_second_approval_or_owner_question_and_old_direction_is_fenced(
        self,
    ):
        with self.assertRaises(NotAllowed):
            self.store.command(
                "s", "approve-again", self.c.ref, "approve", {"plan": self.plan.ref}
            )
        self.assertNotIn(
            "request_clarification", self.h._request("s", self.owner)["tools"]
        )
        f = await self.finding()
        basis = await self.basis([f])
        c = self.store.command(
            "s", "user-steer", self.c.ref, "steer", {"request": "New user direction"}
        )
        self.assertTrue(c.approved)
        with self.assertRaises(NotAllowed):
            ResearchLedger(self.store).require_basis("s", basis.ref)
        self.assertEqual([], ResearchLedger(self.store).current("s", "finding"))

    def test_exact_edit_conflicts_and_simultaneous_application(self):
        self.assertEqual(
            "B C",
            apply_edits("A B", [{"old": "A", "new": "B"}, {"old": "B", "new": "C"}]),
        )
        for text, edits in (
            ("abc", []),
            ("aaa", [{"old": "a", "new": "x"}]),
            ("abc", [{"old": "ab", "new": "x"}, {"old": "bc", "new": "y"}]),
        ):
            with self.assertRaises(ValueError):
                apply_edits(text, edits)

    def test_new_tool_arguments_reject_model_authority_or_extra_fields(self):
        with self.assertRaises(ValueError):
            validate(
                {"base": "x", "edits": [], "accepted": True}, BUILTINS["patch_draft"][1]
            )


class WholeServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_approve_research_basis_edit_same_owner_publish(self):
        with tempfile.TemporaryDirectory() as name:
            store = Store(Path(name) / "study.db")
            try:
                c = store.create("s", "Explain observed counts", {})
                source = store.put(
                    "s",
                    "source",
                    {"text": "17 registered; 12 attended.", "origin": "record.txt"},
                )

                class Model:
                    identity = "whole-workspace-fixture"

                    async def complete(self, request):
                        if "propose_plan" in request["tools"]:
                            call = Call(
                                "propose_plan",
                                {
                                    "text": "Read the registry and establish which events were counted.",
                                    "brief": {
                                        "subject": "Observed counts",
                                        "given_context": [],
                                        "questions": [
                                            "What does the registry establish?"
                                        ],
                                        "material_scope": {
                                            "mode": "case_materials",
                                            "basis": "User supplied a registry",
                                        },
                                    },
                                },
                            )
                        elif request["role"] == "reviewer":
                            report = store.get(
                                "s", request["review_progress"]["report"]
                            )
                            obs = store.related("s", "observation", request["work_ref"])
                            if not any(
                                x.body.get("tool") == "read_report" for x in obs
                            ):
                                call = Call("read_report", {})
                            else:
                                call = Call(
                                    "submit_review",
                                    {
                                        "reason": "Check registry and coverage",
                                        "defects": []
                                        if "12 attended" in report.body["text"]
                                        else ["Attendance is omitted"],
                                    },
                                )
                        else:
                            findings = ResearchLedger(store).current("s", "finding")
                            obs = store.related("s", "observation", request["work_ref"])
                            draft = request.get("draft")
                            if not any(
                                x.body.get("tool") == "read_source" for x in obs
                            ):
                                call = Call("read_source", {"ref": source.ref})
                            elif not findings:
                                call = Call(
                                    "record_finding",
                                    {
                                        "statement": source.body["text"],
                                        "status": "source_statement",
                                        "support": [source.ref],
                                    },
                                )
                            elif not request["writing_basis"]:
                                call = Call(
                                    "prepare_writing",
                                    {
                                        "findings": [findings[0].ref],
                                        "coverage": [
                                            {
                                                "question": 0,
                                                "findings": [findings[0].ref],
                                            }
                                        ],
                                        "rationale": "Registry covers both events; no extrapolation.",
                                    },
                                )
                            elif not draft:
                                call = Call(
                                    "draft_report",
                                    {
                                        "text": "17 registered[[cite:"
                                        + source.ref
                                        + "]].",
                                        "evidence": [source.ref],
                                    },
                                )
                            else:
                                reviews = [
                                    x
                                    for x in store.list("s", "review")
                                    if x.body["report"] == draft["ref"]
                                ]
                                editors = [
                                    x
                                    for x in store.list("s", "work")
                                    if x.body["role"] == "reviewer"
                                    and draft["ref"] in x.body["inputs"]
                                ]
                                if reviews and reviews[-1].body["accepted"]:
                                    call = Call(
                                        "publish_report",
                                        {
                                            "report": draft["ref"],
                                            "review": reviews[-1].ref,
                                        },
                                    )
                                elif reviews:
                                    call = Call(
                                        "patch_draft",
                                        {
                                            "base": draft["ref"],
                                            "edits": [
                                                {
                                                    "old": "17 registered",
                                                    "new": "17 registered; 12 attended",
                                                }
                                            ],
                                        },
                                    )
                                elif editors:
                                    call = Call(
                                        "wait_for_work", {"refs": [editors[-1].ref]}
                                    )
                                else:
                                    call = Call(
                                        "delegate_work",
                                        {
                                            "role": "reviewer",
                                            "task": "Edit this exact report "
                                            + draft["ref"],
                                            "refs": [draft["ref"]],
                                        },
                                    )
                        return Reply("", (call,)).to_json()

                service = ResearchService(store, Harness(store, Model()))
                await asyncio.wait_for(service.run("s"), 5)
                c = store.control("s")
                store.command(
                    "s",
                    "once",
                    c.ref,
                    "approve",
                    {"plan": store.list("s", "plan")[0].ref},
                )
                await asyncio.wait_for(service.run("s"), 12)
                self.assertEqual({}, service.errors)
                self.assertEqual(1, store.count("s", "publication"))
                self.assertEqual(2, store.count("s", "report"))
                self.assertEqual(
                    1,
                    len(
                        [
                            r
                            for r in store.list("s", "draft_saved")
                            if r.body["mode"] == "patch"
                        ]
                    ),
                )
                authors = {r.body["producer"] for r in store.list("s", "report")}
                self.assertEqual(1, len(authors))
                self.assertEqual(
                    {"lead", "reviewer"},
                    {w.body["role"] for w in store.list("s", "work")},
                )
                self.assertEqual(0, store.count("s", "clarification"))
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
