"""Continuous ownership, not a prescribed research route. All models are offline."""

from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from research_fixture import prepare_basis

from epivra.application import ResearchService
from epivra.domain import Call, Conflict, NotAllowed, Reply, RuntimeMismatch
from epivra.harness import Harness, Tool, object_schema
from epivra.presentation import progress, work_detail
from epivra.prompts import ROLES
from epivra.storage import Store

BRIEF = {
    "subject": "Supplied registration record",
    "given_context": ["One original record was supplied"],
    "questions": ["What does the record establish?"],
    "material_scope": {"mode": "case_materials", "basis": "Original user question"},
}


class Scripted:
    identity = "continuous-owner-offline"
    call = None

    async def complete(self, request):
        return Reply("", (self.call,)).to_json()


class OwnerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.db = Path(self.folder.name) / "research.db"
        self.store = Store(self.db)
        c = self.store.create("s", "Explain the record, retaining its limitations.", {})
        self.plan = self.store.put(
            "s",
            "plan",
            {"text": "Read the record and establish its scope.", "brief": BRIEF},
            (c.direction,),
        )
        self.initial = c
        self.control = self.store.command(
            "s", "approve", c.ref, "approve", {"plan": self.plan.ref}
        )
        self.owner = self.store.work(
            "s", self.control.ref, "lead", "Own the research", (self.plan.ref,)
        )
        self.source = self.store.put(
            "s",
            "source",
            {
                "origin": "record.txt",
                "text": "17 registered; 12 attended. This is not a population estimate.",
            },
        )
        self.model = Scripted()
        self.harness = Harness(self.store, self.model)

    async def asyncTearDown(self):
        self.store.close()
        self.folder.cleanup()

    async def call(self, name, args, work=None):
        work = work or self.owner
        if name == "draft_report":
            prepare_basis(self.store, work)
        self.model.call = Call(name, args)
        await self.harness.step("s", work.ref)
        return self.harness._steps("s", "observation", work.ref)[-1].body

    async def save(self, text="17 registered", base=None, work=None):
        args = {
            "text": text + "[[cite:" + self.source.ref + "]]",
            "evidence": [self.source.ref],
        }
        if base:
            args["base"] = base
        result = await self.call("draft_report", args, work)
        self.assertIsNone(result.get("failure"), result)
        return self.store.get("s", result["result"]["ref"])

    async def accept(self, report):
        reviewer = self.store.work(
            "s",
            self.control.ref,
            "reviewer",
            "Edit exact version " + report.ref,
            (report.ref,),
            self.owner.ref,
        )
        await self.call("read_report", {}, reviewer)
        result = await self.call(
            "submit_review",
            {"reason": "Matches the supplied record", "defects": []},
            reviewer,
        )
        self.assertIsNone(result.get("failure"), result)
        return self.store.get("s", result["result"]["ref"])

    async def test_owner_can_read_record_and_draft_without_helper_identity(self):
        read = await self.call("read_source", {"ref": self.source.ref})
        selection = read["result"]["selections"][0]["selection"]
        note = await self.call(
            "record_evidence",
            {
                "selection": selection,
                "text": "Registration and attendance are different counts.",
            },
        )
        self.assertIsNone(note.get("failure"))
        report = await self.save()
        self.assertEqual(self.owner.ref, report.body["producer"])
        self.assertEqual(1, self.store.count("s", "work"))
        self.assertFalse(self.harness.finished("s", self.owner.ref))
        self.assertEqual(
            report.ref, self.harness._request("s", self.owner)["draft"]["ref"]
        )

    async def test_direct_author_has_to_use_separate_exact_version_editor(self):
        report = await self.save()
        denied = await self.call(
            "submit_review", {"reason": "Self approval", "defects": []}
        )
        self.assertIsNotNone(denied.get("failure"))
        self.assertEqual([], self.store.list("s", "publication"))
        review = await self.accept(report)
        published = await self.call(
            "publish_report", {"report": report.ref, "review": review.ref}
        )
        self.assertIsNone(published.get("failure"), published)
        self.assertTrue(self.harness.finished("s", self.owner.ref))
        self.assertEqual(2, self.store.count("s", "work"))

    async def test_saving_twice_preserves_work_and_fences_stale_report(self):
        first = await self.save()
        old_review = await self.accept(first)
        second = await self.save("17 registered; 12 attended", first.ref)
        self.assertEqual(first.ref, second.body["previous_report"])
        self.assertIn(first.ref, second.parents)
        self.assertNotEqual(first.ref, second.ref)
        self.assertFalse(self.harness.finished("s", self.owner.ref))
        before = self.store.count("s", "report")
        wrong = await self.call(
            "draft_report", {"text": "Stale", "base": first.ref, "evidence": []}
        )
        self.assertIsNotNone(wrong.get("failure"))
        self.assertEqual(before, self.store.count("s", "report"))
        with self.assertRaises(Conflict):
            self.store.publish(
                "s", self.owner.ref, self.control.epoch, first.ref, old_review.ref
            )
        with self.assertRaises(Conflict):
            self.store.publish(
                "s", self.owner.ref, self.control.epoch, second.ref, old_review.ref
            )
        new_review = await self.accept(second)
        self.store.publish(
            "s", self.owner.ref, self.control.epoch, second.ref, new_review.ref
        )

    async def test_helper_can_start_from_sources_and_saving_is_not_completion(self):
        for role in ("investigator", "synthesizer", "writer"):
            previous = self.harness._draft_head("s", self.owner)
            refs = (self.source.ref,) + ((previous["ref"],) if previous else ())
            helper = self.store.work(
                "s", self.control.ref, role, "Use original record", refs, self.owner.ref
            )
            report = await self.save(
                work=helper, base=previous["ref"] if previous else None
            )
            self.assertFalse(self.harness.finished("s", helper.ref))
            bad = await self.call("finish_work", {"text": "Done", "refs": []}, helper)
            self.assertIsNotNone(bad.get("failure"))
            done = await self.call(
                "finish_work",
                {"text": "Delivered supported record", "refs": [report.ref]},
                helper,
            )
            self.assertIsNone(done.get("failure"))
            self.assertTrue(self.harness.finished("s", helper.ref))
            receipt = self.harness._steps("s", "work_result", helper.ref)[-1]
            self.assertEqual(report.ref, receipt.body["ref"])

    async def test_save_receipt_and_active_draft_survive_reopen(self):
        report = await self.save()
        self.store.close()
        self.store = Store(self.db)
        self.harness = Harness(self.store, self.model)
        self.assertEqual(
            report.ref, self.harness._request("s", self.owner)["draft"]["ref"]
        )
        self.assertFalse(self.harness.finished("s", self.owner.ref))
        second = await self.save(
            "17 registrations, not an effectiveness estimate", report.ref
        )
        self.assertIn(report.ref, second.parents)
        public = progress(self.store, "s")["work"][0]
        self.assertNotEqual("delivered", public["state"])
        self.assertIn("draft_saved", public["revision"])
        self.assertTrue(
            any(
                x["kind"] == "report"
                for x in work_detail(self.store, "s", self.owner.ref)["entries"]
            )
        )

    async def test_failed_receipt_rolls_back_draft_for_owner_and_helper(self):
        actual = self.store._put

        def fail(study, kind, *args, **kwargs):
            if kind == "draft_saved":
                raise ValueError("injected storage failure")
            return actual(study, kind, *args, **kwargs)

        for work in (
            self.owner,
            self.store.work(
                "s", self.control.ref, "writer", "Direct write", (), self.owner.ref
            ),
        ):
            with patch.object(self.store, "_put", side_effect=fail):
                failed = await self.call(
                    "draft_report", {"text": "Report", "evidence": []}, work
                )
            self.assertIsNotNone(failed.get("failure"))
            self.assertEqual([], self.store.list("s", "report"))
            self.assertEqual([], self.harness._steps("s", "draft_saved", work.ref))
            self.assertFalse(self.harness.finished("s", work.ref))

    async def test_initial_approval_idempotent_but_no_second_approval(self):
        replay = self.store.command(
            "s", "approve", self.initial.ref, "approve", {"plan": self.plan.ref}
        )
        self.assertEqual(self.control, replay)
        with self.assertRaises(NotAllowed):
            self.store.command(
                "s", "again", self.control.ref, "approve", {"plan": self.plan.ref}
            )
        for tool in ("propose_plan", "request_clarification"):
            self.assertNotIn(tool, self.harness._request("s", self.owner)["tools"])
        declined = await self.call(
            "request_clarification", {"text": "Ask the user", "refs": []}
        )
        self.assertIsNotNone(declined.get("failure"))
        self.assertEqual([], self.store.clarifications("s"))
        with self.assertRaises(NotAllowed):
            self.harness._builtin(
                "s",
                self.owner,
                self.control.epoch,
                self.owner.ref,
                0,
                Call("propose_plan", {"text": "new", "brief": BRIEF}),
            )

    async def test_source_approval_boundary_is_separate_from_role_permissions(self):
        c = self.store.create("pending", "Plan only", {"network": True})
        owner = self.store.work("pending", c.ref, "lead", "Plan")
        src = self.store.put("pending", "source", {"text": "Provided original"})
        for tool in ("read_source", "read_artifact", "read_artifact_range"):
            with self.assertRaises(NotAllowed):
                self.harness._builtin(
                    "pending",
                    owner,
                    c.epoch,
                    owner.ref,
                    0,
                    Call(tool, {"ref": src.ref}),
                )
        for kind in ("step", "material_bytes"):
            hidden = self.store.put("s", kind, {"text": "private wire"})
            result = await self.call("read_artifact", {"ref": hidden.ref})
            self.assertIsNotNone(result.get("failure"))

    def test_extra_tools_keep_explicit_permission_and_role_grants(self):
        async def never(args):
            raise AssertionError("offline test")

        tools = {
            "owner_web": Tool(
                "Read", object_schema({}), never, roles=("lead",), permission="network"
            ),
            "restricted": Tool(
                "Restricted",
                object_schema({}),
                never,
                roles=("investigator",),
                permission="network",
            ),
        }
        h = Harness(self.store, self.model, tools)
        self.assertNotIn(
            "owner_web", h._schema("lead", {"_approved": True, "network": False})
        )
        enabled = h._schema("lead", {"_approved": True, "network": True})
        self.assertIn("owner_web", enabled)
        self.assertNotIn("restricted", enabled)
        self.assertNotIn("owner_web", h._schema("lead", {"network": True}))
        self.assertIn(
            "run_analysis", h._schema("lead", {"_approved": True, "analysis": True})
        )
        self.assertNotIn(
            "run_analysis", h._schema("lead", {"_approved": True, "analysis": False})
        )

    async def test_pause_and_user_steer_preserve_authority_without_reapproval(self):
        report = await self.save()
        paused = self.store.command("s", "pause", self.control.ref, "pause")
        with self.assertRaises(NotAllowed):
            self.store.require_work("s", self.owner.ref, paused.epoch)
        resumed = self.store.command("s", "resume", paused.ref, "resume")
        self.assertEqual(
            report.ref, self.harness._request("s", self.owner)["draft"]["ref"]
        )
        changed = self.store.command(
            "s", "steer", resumed.ref, "steer", {"request": "User initiates a revision"}
        )
        self.assertTrue(changed.approved)
        with self.assertRaises(Conflict):
            self.store.require_work("s", self.owner.ref, changed.epoch)
        fresh = self.store.work(
            "s", changed.ref, "lead", "Follow the revised user question"
        )
        self.assertIsNone(self.harness._request("s", fresh)["draft"])
        self.assertNotIn("propose_plan", self.harness._request("s", fresh)["tools"])

    async def test_old_runtime_readable_but_not_silently_resumed(self):
        with self.store.transaction():
            old = self.store._put(
                "old",
                "direction",
                {"request": "History", "runtime": "research-mainline-v2", "policy": {}},
            )
            c = self.store._control("old", 0, old.ref, False, False, False, ())
        self.assertEqual("History", self.store.get("old", old.ref).body["request"])
        with self.assertRaises(RuntimeMismatch):
            self.store.work("old", c.ref, "lead", "Resume")
        self.assertEqual([], self.store.list("old", "work"))

    def test_route_and_owner_prompt_do_not_prescribe_hypotheses_or_fixed_roles(self):
        instructions = ROLES["lead"]
        self.assertIn("不提出任何研究假设或预定结论", instructions)
        self.assertIn("批准后不再请示用户", instructions)
        self.assertIn("不是每项研究的必经阶段", instructions)
        self.assertNotIn("默认假设在方案中说明", instructions)
        self.assertNotIn("不承担资料逐篇调查或代写成果", instructions)
        # This checks the prompt contract, not model compliance or research quality.


class ContinuousServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_full_owner_edit_cycle_without_investigator_synthesizer_or_writer(
        self,
    ):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder) / "state.db")
            try:
                store.create("s", "Explain the supplied record", {})
                source = store.put(
                    "s",
                    "source",
                    {"text": "17 registered; 12 attended.", "origin": "record.txt"},
                )
                seen_owner = set()

                class Model:
                    identity = "owner-service-fixture"

                    async def complete(self, request):
                        work = store.get("s", request["work_ref"])
                        observations = [
                            x.body for x in store.related("s", "observation", work.ref)
                        ]
                        if "propose_plan" in request["tools"]:
                            call = Call(
                                "propose_plan",
                                {
                                    "text": "Read the supplied record, determine what it establishes, and organize the answer.",
                                    "brief": BRIEF,
                                },
                            )
                        elif request["role"] == "reviewer":
                            report = store.get(
                                "s", request["review_progress"]["report"]
                            )
                            if not any(
                                x.get("tool") == "read_report" for x in observations
                            ):
                                call = Call("read_report", {})
                            else:
                                defects = (
                                    []
                                    if "12 attended" in report.body["text"]
                                    else [
                                        "The answer omits attendance from the supplied record."
                                    ]
                                )
                                call = Call(
                                    "submit_review",
                                    {
                                        "reason": "Checked the exact record and answer",
                                        "defects": defects,
                                    },
                                )
                        else:
                            seen_owner.add(work.ref)
                            draft = request["draft"]
                            if not any(
                                x.get("tool") == "read_source" for x in observations
                            ):
                                call = Call("read_source", {"ref": source.ref})
                            elif not store.list("s", "finding"):
                                call = Call(
                                    "record_finding",
                                    {
                                        "statement": "17 registered; 12 attended.",
                                        "status": "source_statement",
                                        "support": [source.ref],
                                    },
                                )
                            elif not request.get("writing_basis"):
                                finding = store.list("s", "finding")[0]
                                call = Call(
                                    "prepare_writing",
                                    {
                                        "findings": [finding.ref],
                                        "coverage": [
                                            {"question": 0, "findings": [finding.ref]}
                                        ],
                                        "rationale": "The original record covers the requested counts.",
                                    },
                                )
                            elif not draft:
                                call = Call(
                                    "draft_report",
                                    {
                                        "text": "17 registered[[cite:"
                                        + source.ref
                                        + "]]",
                                        "evidence": [source.ref],
                                    },
                                )
                            else:
                                refs = [
                                    x
                                    for x in store.list("s", "review")
                                    if x.body["report"] == draft["ref"]
                                ]
                                children = [
                                    x
                                    for x in store.list("s", "work")
                                    if x.body["owner"] == work.ref
                                    and draft["ref"] in x.body["inputs"]
                                ]
                                if refs and refs[-1].body["accepted"]:
                                    call = Call(
                                        "publish_report",
                                        {
                                            "report": draft["ref"],
                                            "review": refs[-1].ref,
                                        },
                                    )
                                elif refs:
                                    call = Call(
                                        "draft_report",
                                        {
                                            "text": "17 registered; 12 attended[[cite:"
                                            + source.ref
                                            + "]]",
                                            "evidence": [source.ref],
                                            "base": draft["ref"],
                                        },
                                    )
                                elif children:
                                    call = Call(
                                        "wait_for_work", {"refs": [children[-1].ref]}
                                    )
                                else:
                                    call = Call(
                                        "delegate_work",
                                        {
                                            "role": "reviewer",
                                            "task": "Check faithfulness of this exact report "
                                            + draft["ref"],
                                            "refs": [draft["ref"], source.ref],
                                        },
                                    )
                        return Reply("", (call,)).to_json()

                service = ResearchService(store, Harness(store, Model()))
                await asyncio.wait_for(service.run("s"), 5)
                self.assertEqual(1, store.count("s", "plan"))
                self.assertEqual(0, store.count("s", "report"))
                c = store.control("s")
                store.command(
                    "s",
                    "approve",
                    c.ref,
                    "approve",
                    {"plan": store.list("s", "plan")[0].ref},
                )
                await asyncio.wait_for(service.run("s"), 10)
                self.assertEqual({}, service.errors)
                self.assertEqual({}, service.work_errors)
                self.assertEqual(1, len(seen_owner))
                self.assertEqual(
                    {"lead", "reviewer"},
                    {w.body["role"] for w in store.list("s", "work")},
                )
                self.assertEqual(2, store.count("s", "draft_saved"))
                self.assertEqual(1, store.count("s", "publication"))
                self.assertEqual(0, store.count("s", "clarification"))
                self.assertEqual(
                    1,
                    store.db.execute(
                        "SELECT COUNT(*) FROM commands WHERE request LIKE '%approve%'"
                    ).fetchone()[0],
                )
                before = store.count("s", "step")
                await service.run("s")
                self.assertEqual(before, store.count("s", "step"))
            finally:
                store.close()
