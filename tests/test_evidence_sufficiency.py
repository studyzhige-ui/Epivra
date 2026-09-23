"""Readiness contracts across acquisition, ownership, recovery and publication gates."""

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from epivra.domain import Call, Conflict, NotAllowed, Reply
from epivra.harness import Harness, Tool, object_schema
from epivra.research import ResearchLedger
from epivra.storage import Store
from epivra.workspace import Workspace


class Model:
    context_tokens = 49024
    max_tokens = 1024
    identity = "offline-sufficiency-v1"
    call = None

    async def complete(self, request):
        return Reply("", (self.call,)).to_json()


class SufficiencyTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / "study.db")
        c = self.store.create(
            "s", "Compare the supplied count and its limitations", {"network": True}
        )
        plan = self.store.put("s", "plan", {"text": "Inspect evidence"}, (c.direction,))
        self.c = self.store.command(
            "s", "approve", c.ref, "approve", {"plan": plan.ref}
        )
        self.owner = self.store.work("s", self.c.ref, "lead", "Research", (plan.ref,))
        self.workspace = Workspace(self.store)
        self.source = self.workspace.upload(
            "s", "record.txt", b"12 attended; population effect unknown."
        )
        self.ledger = ResearchLedger(self.store)
        self.finding = self.ledger.record_finding(
            "s",
            self.owner.ref,
            self.c.epoch,
            statement="12 attended, without population inference",
            status="source_statement",
            support=[self.source.ref],
        )
        self.model = Model()
        self.calls = 0
        self.result = {
            "results": [{"url": "https://example.test/record", "snippet": "Candidate"}]
        }

        async def search(args):
            self.calls += 1
            return self.result

        tool = Tool(
            "Search",
            {
                **object_schema(
                    {"query": {"type": "string"}, "force_refresh": {"type": "boolean"}}
                ),
                "required": ["query"],
            },
            search,
            roles=("lead",),
            permission="network",
            observe=lambda raw, acq: raw,
            research_fields=("query", "force_refresh"),
            cache_research=True,
        )
        self.h = Harness(self.store, self.model, {"web_search": tool})

    async def asyncTearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def update(self, **extra):
        return {
            "question": 0,
            "answer_target": "Report the count and limits; no population claim",
            "findings": [self.finding.ref],
            "checks": [],
            "remaining": [],
            "decision": "ready",
            "reason": "Original record supports the requested scoped answer",
            **extra,
        }

    def prepare(self, **extra):
        return self.ledger.prepare_writing(
            "s",
            self.owner.ref,
            self.c.epoch,
            updates=[self.update()],
            rationale="Scoped original answers the question",
            **extra,
        )

    async def call(self, name, args):
        self.model.call = Call(name, args)
        await self.h.step("s", self.owner.ref)
        return self.h._steps("s", "observation", self.owner.ref)[-1]

    def check(self, ref, effect="changed"):
        return {
            "angle": "Test a relevant gap",
            "refs": [ref],
            "effect": effect,
            "reason": "Classify the actual result and retain its limitations",
        }

    async def test_atomic_finalization_and_replay_do_not_reauthorize_stale_basis(self):
        basis = self.prepare(_operation="finish")
        self.assertEqual(1, self.store.count("s", "question_assessment"))
        self.workspace.upload("s", "late.txt", b"A relevant new limitation")
        self.assertEqual(basis.ref, self.prepare(_operation="finish").ref)
        self.assertEqual(1, self.store.count("s", "question_assessment"))
        with self.assertRaises(Conflict):
            self.ledger.require_basis("s", basis.ref)

    async def test_failed_finalization_rolls_back_all_assessments(self):
        await self.call("web_search", {"query": "counterexample"})
        with self.assertRaises(Conflict):
            self.prepare()
        self.assertEqual([], self.store.list("s", "question_assessment"))
        self.assertEqual([], self.store.list("s", "writing_basis"))

    async def test_search_batch_without_source_reopens_readiness(self):
        basis = self.prepare()
        obs = await self.call("web_search", {"query": "counterexample"})
        with self.assertRaises(Conflict):
            self.ledger.require_basis("s", basis.ref)
        prior = basis.body["assessments"][0]
        updated = self.ledger.prepare_writing(
            "s",
            self.owner.ref,
            self.c.epoch,
            updates=[
                self.update(
                    replaces=prior, checks=[self.check(obs.ref, "no_material_change")]
                )
            ],
            rationale="Candidate adds no material beyond the scoped original",
            replaces=basis.ref,
        )
        self.ledger.require_basis("s", updated.ref)

    async def test_identical_query_reuses_original_receipt_and_refresh_reopens(self):
        first = await self.call("web_search", {"query": "same"})
        args = self.update(checks=[self.check(first.ref)])
        basis = self.ledger.prepare_writing(
            "s",
            self.owner.ref,
            self.c.epoch,
            updates=[args],
            rationale="Considered batch",
        )
        second = await self.call("web_search", {"query": "same"})
        self.assertEqual(1, self.calls)
        self.assertEqual(first.ref, second.body["research_receipt"]["reused_from"])
        self.ledger.require_basis("s", basis.ref)
        await self.call("web_search", {"query": "same", "force_refresh": True})
        self.assertEqual(2, self.calls)
        with self.assertRaises(Conflict):
            self.ledger.require_basis("s", basis.ref)

    async def test_query_and_binding_changes_do_not_hit_cache(self):
        await self.call("web_search", {"query": "a"})
        await self.call("web_search", {"query": "b"})
        self.h.tools["web_search"] = replace(self.h.tools["web_search"], identity="v2")
        await self.call("web_search", {"query": "a"})
        self.assertEqual(3, self.calls)

    async def test_authorization_change_invalidates_research_reuse(self):
        authorization = ["account-a"]
        self.h.tools["web_search"] = replace(
            self.h.tools["web_search"],
            research_authorization=lambda request: authorization[0],
        )
        first = await self.call("web_search", {"query": "same"})
        second = await self.call("web_search", {"query": "same"})
        self.assertEqual(first.ref, second.body["research_receipt"]["reused_from"])
        authorization[0] = "account-b"
        third = await self.call("web_search", {"query": "same"})
        self.assertNotIn("reused_from", third.body["research_receipt"])
        self.assertEqual(2, self.calls)
        self.assertNotIn("account-b", third.body["research_receipt"]["request_key"])

    async def test_settled_call_replayed_after_key_change_keeps_original_reuse_key(self):
        authorization = ["account-a"]
        self.h.tools["web_search"] = replace(
            self.h.tools["web_search"],
            research_authorization=lambda request: authorization[0],
        )
        self.model.call = Call("web_search", {"query": "same"})
        with patch.object(self.store, "observation", side_effect=RuntimeError("crash")):
            with self.assertRaisesRegex(RuntimeError, "crash"):
                await self.h.step("s", self.owner.ref)
        self.assertEqual(1, self.calls)
        path = self.store.path
        tool = self.h.tools["web_search"]
        self.store.close()
        self.store = Store(path)
        self.h = Harness(self.store, self.model, {"web_search": tool})
        authorization[0] = "account-b"
        await self.h.step("s", self.owner.ref)
        replayed = self.h._steps("s", "observation", self.owner.ref)[-1]
        self.assertNotEqual(
            self.h.tools["web_search"].research_key({"query": "same"}),
            replayed.body["research_receipt"]["request_key"],
        )
        await self.call("web_search", {"query": "same"})
        self.assertEqual(2, self.calls)

    async def test_failed_search_cannot_prove_low_gain_or_be_cached(self):
        self.result = {"error": "provider_failed"}
        obs = await self.call("web_search", {"query": "same"})
        await self.call("web_search", {"query": "same"})
        self.assertEqual(2, self.calls)
        with self.assertRaises(ValueError):
            self.ledger.assess_questions(
                "s",
                self.owner.ref,
                self.c.epoch,
                updates=[
                    self.update(checks=[self.check(obs.ref, "no_material_change")])
                ],
            )

    async def test_empty_success_is_reusable_but_not_a_sufficiency_certificate(self):
        self.result = {"results": []}
        obs = await self.call("web_search", {"query": "empty"})
        await self.call("web_search", {"query": "empty"})
        self.assertEqual(1, self.calls)
        self.assertEqual("empty", obs.body["research_receipt"]["outcome"])
        with self.assertRaises(Conflict):
            self.prepare()

    async def test_owner_only_updates_and_writer_schema_has_no_updates(self):
        writer = self.store.work(
            "s", self.c.ref, "writer", "Write", (self.source.ref,), self.owner.ref
        )
        schema = self.h._request("s", writer)["tools"]
        self.assertNotIn("assess_questions", schema)
        self.assertNotIn(
            "updates", schema["prepare_writing"]["parameters"]["properties"]
        )
        with self.assertRaises(NotAllowed):
            self.ledger.prepare_writing(
                "s",
                writer.ref,
                self.c.epoch,
                updates=[self.update()],
                rationale="Forged update",
            )
        basis = self.prepare()
        rebuilt = self.ledger.prepare_writing(
            "s",
            writer.ref,
            self.c.epoch,
            assessments=basis.body["assessments"],
            rationale="Use owner assessment",
            replaces=basis.ref,
        )
        self.assertEqual(basis.body["assessments"], rebuilt.body["assessments"])

    async def test_assessment_batch_replay_and_stale_cas(self):
        args = {
            "updates": [self.update(decision="continue")],
            "_operation": "assessment",
        }
        original = self.ledger.assess_questions(
            "s", self.owner.ref, self.c.epoch, **args
        )
        revised = self.update(replaces=original[0].ref)
        self.ledger.assess_questions(
            "s", self.owner.ref, self.c.epoch, updates=[revised]
        )
        self.assertEqual(
            original,
            self.ledger.assess_questions("s", self.owner.ref, self.c.epoch, **args),
        )
        with self.assertRaises(Conflict):
            self.ledger.assess_questions(
                "s", self.owner.ref, self.c.epoch, updates=[revised]
            )

    async def test_ready_and_limited_cannot_hide_declared_next(self):
        for decision in ("ready", "limited"):
            with self.assertRaises(ValueError):
                self.ledger.assess_questions(
                    "s",
                    self.owner.ref,
                    self.c.epoch,
                    updates=[
                        self.update(
                            decision=decision,
                            remaining=[
                                {
                                    "question": "Missing counterexample",
                                    "disposition": "next",
                                    "reason": "Available original can change the answer",
                                }
                            ],
                        )
                    ],
                )

    async def test_unfinished_helper_blocks_and_delivery_requires_adoption(self):
        helper = self.store.work(
            "s",
            self.c.ref,
            "investigator",
            "Check scope",
            (self.source.ref,),
            self.owner.ref,
        )
        with self.assertRaises(Conflict):
            self.prepare()
        done = self.store.cancel_work(
            "s", self.owner.ref, helper.ref, self.c.epoch, "No longer required"
        )
        with self.assertRaises(Conflict):
            self.prepare()
        basis = self.ledger.prepare_writing(
            "s",
            self.owner.ref,
            self.c.epoch,
            updates=[self.update(checks=[self.check(done.ref, "blocked")])],
            rationale="Original suffices; cancelled redundant work is disclosed",
        )
        self.ledger.require_basis("s", basis.ref)

    async def test_failed_analysis_and_unclassified_mcp_are_not_success(self):
        failed = self.h._research_receipt(
            "s",
            self.owner,
            Call("run_analysis", {}),
            {"status": "failed", "log": self.source.ref, "files": []},
        )
        self.assertEqual("blocked", failed["outcome"])
        self.h.tools["custom"] = replace(
            self.h.tools["web_search"], research_fields=(), cache_research=False
        )
        unknown = self.h._research_receipt(
            "s",
            self.owner,
            Call("custom", {"secret": "do not publish"}),
            {"links": ["candidate"]},
        )
        self.assertEqual("unclassified", unknown["outcome"])
        self.assertEqual({}, unknown["request"])
        self.assertTrue(unknown["input"])

    async def test_source_reuse_does_not_duplicate_input_but_new_direction_adopts_it(
        self,
    ):
        basis = self.prepare()
        self.assertEqual(
            self.source.ref,
            self.workspace.upload(
                "s", "record.txt", b"12 attended; population effect unknown."
            ).ref,
        )
        self.ledger.require_basis("s", basis.ref)
        c = self.store.command(
            "s", "new", self.c.ref, "steer", {"request": "Another question"}
        )
        reused = self.workspace.upload(
            "s", "record.txt", b"12 attended; population effect unknown."
        )
        self.assertEqual(self.source.ref, reused.ref)
        self.assertIn(reused.ref, self.ledger.inputs("s", c.direction))

    async def test_late_analysis_output_stays_in_producing_direction(self):
        job = self.store.put(
            "s",
            "analysis_job",
            {"inputs": {}, "purpose": "Check data"},
            (self.owner.ref,),
        )
        self.store.command(
            "s", "new", self.c.ref, "steer", {"request": "Another question"}
        )
        result = self.workspace.save_analysis(
            "s",
            job,
            {"status": "cancelled", "log": "Old work recovered", "files": []},
            1024,
        )
        log = self.store.get("s", result.body["log"])
        self.assertEqual(self.c.direction, log.body["direction"])
        self.assertNotIn(log.ref, self.ledger.inputs("s"))

    async def test_helper_cannot_launder_failed_receipt_into_low_gain(self):
        self.result = {"error": "provider_failed"}
        failed = await self.call("web_search", {"query": "failed attempt"})
        helper = self.store.work(
            "s", self.c.ref, "investigator", "Check scope", (), self.owner.ref
        )
        self.model.call = Call(
            "finish_work", {"text": "Search unavailable", "refs": [failed.ref]}
        )
        await self.h.step("s", helper.ref)
        delivered = self.store.matching("s", "work_result", {"producer": helper.ref})[
            -1
        ]
        with self.assertRaises(ValueError):
            self.ledger.prepare_writing(
                "s",
                self.owner.ref,
                self.c.epoch,
                updates=[
                    self.update(
                        checks=[self.check(delivered.ref, "no_material_change")]
                    )
                ],
                rationale="Unsupported low gain",
            )
        self.assertEqual([], self.store.list("s", "writing_basis"))
        accepted = self.ledger.prepare_writing(
            "s",
            self.owner.ref,
            self.c.epoch,
            updates=[
                self.update(
                    decision="limited",
                    checks=[self.check(delivered.ref, "blocked")],
                    remaining=[
                        {
                            "question": "External check unavailable",
                            "disposition": "blocked",
                            "reason": "Provider failed; answer limited to supplied original",
                        }
                    ],
                )
            ],
            rationale="Disclose unavailable external check",
        )
        self.ledger.require_basis("s", accepted.ref)

    async def test_effort_counts_cache_and_atomic_finalization_without_new_paid_calls(self):
        from epivra.usage import research_effort
        first = await self.call("web_search", {"query": "same"})
        await self.call("web_search", {"query": "same"})
        await self.call("prepare_writing", {"updates": [self.update(checks=[self.check(first.ref)])], "rationale": "Assess and bind once"})
        counts = research_effort(a for kind in ("observation", "question_assessment", "writing_basis", "report", "review") for a in self.store.list("s", kind))
        self.assertEqual(1, counts["research_cache_hits"])
        self.assertEqual(1, counts["acquisition_batches"])
        self.assertEqual(1, counts["atomic_finalizations"])
        self.assertEqual(0, counts["assessment_calls"])
        self.assertEqual(1, self.calls)
