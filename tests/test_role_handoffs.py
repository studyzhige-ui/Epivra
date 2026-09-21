from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from research_fixture import prepare_basis

from epivra.domain import Call, Reply
from epivra.harness import Harness
from epivra.storage import Store


class ScriptedModel:
    identity = "role-handoff-fixture"

    def __init__(self):
        self.call = None
        self.requests = []

    async def complete(self, request):
        self.requests.append(request)
        return Reply("", (self.call,)).to_json()


class RoleHandoffTests(unittest.IsolatedAsyncioTestCase):
    """Check delivered inputs, not whether a model reasons correctly about them."""

    async def asyncSetUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.folder.name) / "state.db")
        c = self.store.create("s", "报告登记人群的结果", {})
        plan = self.store.put(
            "s", "plan", {"text": "Use supplied evidence"}, (c.direction,)
        )
        self.control = self.store.command(
            "s", "approve", c.ref, "approve", {"plan": plan.ref}
        )
        self.lead = self.store.work("s", self.control.ref, "lead", "Coordinate")
        self.source = self.store.put(
            "s",
            "source",
            {"text": "登记17人，其中12人到会。", "origin": "registry.txt"},
        )
        self.model = ScriptedModel()
        self.harness = Harness(self.store, self.model)

    async def asyncTearDown(self):
        self.store.close()
        self.folder.cleanup()

    def child(self, role, task, refs=()):
        return self.store.work(
            "s", self.control.ref, role, task, tuple(refs), self.lead.ref
        )

    async def execute(self, work, name, args):
        if name == "draft_report":
            prepare_basis(self.store, work)
        self.model.call = Call(name, args)
        await self.harness.step("s", work.ref)
        return self.model.requests[-1]

    async def finding(self, text, task):
        producer = self.child("investigator", task)
        await self.execute(
            producer, "finish_work", {"text": text, "refs": [self.source.ref]}
        )
        return self.harness._steps("s", "work_result", producer.ref)[0]

    async def clarify(self, work, old_result):
        await self.execute(
            work,
            "request_clarification",
            {
                "text": "原成果使用到会人数，是否需要登记人数？",
                "refs": [old_result.ref],
            },
        )
        question = self.store.clarifications("s", work=work.ref, open_only=True)[0]
        updated = await self.finding("补查原成果：登记17人；到会12人。", "核对登记口径")
        await self.execute(
            self.lead,
            "answer_clarification",
            {
                "question": question.ref,
                "text": "以登记人群为准，保留到会口径区别。",
                "refs": [updated.ref],
            },
        )
        answer = self.store.list("s", "clarification_answer")[-1]
        return updated, answer

    def assert_original_bodies(self, request, *artifacts):
        context = {item["ref"]: item for item in request["context"]}
        for artifact in artifacts:
            self.assertIn(artifact.ref, context)
            self.assertEqual(artifact.body, context[artifact.ref]["body"])

    async def test_writer_supplement_and_decision_reach_reviewer_without_rewording(
        self,
    ):
        old = await self.finding("最初结果：到会12人。", "初始调查")
        writer = self.child("writer", "撰写登记人群报告", [old.ref])
        updated, answer = await self.clarify(writer, old)
        writer_request = await self.execute(
            writer,
            "draft_report",
            {"text": "登记17人，其中12人到会。", "evidence": [self.source.ref]},
        )
        self.assert_original_bodies(writer_request, old, updated, answer)
        self.assertTrue(
            {updated.ref, answer.ref} <= {i["ref"] for i in writer_request["inputs"]}
        )
        report = self.store.list("s", "report")[-1]
        self.assertTrue({old.ref, updated.ref, answer.ref} <= set(report.parents))

        reviewer = self.child("reviewer", "核查登记人群报告", [report.ref])
        request = await self.execute(
            reviewer, "read_report", {"offset": 0, "limit": 20}
        )
        self.assert_original_bodies(request, answer)
        for finding in (old, updated):
            self.assertNotIn(finding.body["text"], str(request["context"]))
        relations = {i["ref"]: i for i in request["review_progress"]["inputs"]}
        self.assertTrue({old.ref, updated.ref, answer.ref} <= relations.keys())
        self.assertEqual(updated.body["producer"], relations[updated.ref]["producer"])
        observation = self.harness._steps("s", "observation", reviewer.ref)[-1]
        result = observation.body["result"]
        self.assertEqual(report.ref, result["report"])
        self.assertEqual(report.body["text"], result["units"][0]["text"])
        self.assertTrue(
            {updated.ref, answer.ref} <= {i["ref"] for i in result["inputs"]}
        )

        await self.execute(reviewer, "read_artifact", {"ref": updated.ref})
        original = self.harness._steps("s", "observation", reviewer.ref)[-1].body[
            "result"
        ]
        self.assertEqual(updated.body, original["body"])
        producer_ref = original["body"]["producer"]
        self.assertEqual(updated.body["producer"], producer_ref)
        self.assertIn(producer_ref, {i["ref"] for i in original["parents"]})
        await self.execute(reviewer, "read_artifact", {"ref": producer_ref})
        producer = self.harness._steps("s", "observation", reviewer.ref)[-1].body[
            "result"
        ]
        self.assertEqual(self.store.get("s", producer_ref).body, producer["body"])
        self.assertEqual("核对登记口径", producer["body"]["task"])

    async def test_completed_research_preserves_clarification_dependencies(self):
        for role in ("investigator", "synthesizer"):
            with self.subTest(role=role):
                old = await self.finding("先前成果：到会12人。", f"{role}前置调查")
                work = self.child(role, f"{role}登记口径任务", [old.ref])
                updated, answer = await self.clarify(work, old)
                request = await self.execute(
                    work,
                    "finish_work",
                    {"text": "登记17人；到会12人。", "refs": [self.source.ref]},
                )
                self.assert_original_bodies(request, updated, answer)
                result = self.harness._steps("s", "work_result", work.ref)[0]
                self.assertTrue(
                    {old.ref, updated.ref, answer.ref} <= set(result.parents)
                )
                self.assertEqual(work.ref, result.body["producer"])
                self.assertEqual([self.source.ref], result.body["refs"])

    async def test_synthesis_revision_accepts_direct_prior_synthesis(self):
        investigation = await self.finding("登记17人；到会12人。", "调查")
        first = self.child("synthesizer", "形成共同答案", [investigation.ref])
        await self.execute(
            first,
            "finish_work",
            {"text": "两种口径应分开报告。", "refs": [investigation.ref]},
        )
        result = self.harness._steps("s", "work_result", first.ref)[0]
        revision = self.child("synthesizer", "解释两种口径的关系", [result.ref])
        request = await self.execute(revision, "read_artifact", {"ref": result.ref})
        self.assertEqual([result.ref], revision.body["inputs"])
        self.assert_original_bodies(request, result)
        observation = self.harness._steps("s", "observation", revision.ref)[-1]
        self.assertEqual(result.body, observation.body["result"]["body"])
        await self.execute(
            revision,
            "finish_work",
            {"text": "登记人数与到会人数回答不同问题。", "refs": [result.ref]},
        )
        revised = self.harness._steps("s", "work_result", revision.ref)[0]
        self.assertIn(result.ref, revised.parents)
        self.assertEqual(revision.ref, revised.body["producer"])

    async def test_source_read_returns_identity_with_original_text(self):
        work = self.child("investigator", "核对登记记录", [self.source.ref])
        await self.execute(
            work, "read_source", {"ref": self.source.ref, "offset": 0, "limit": 100}
        )
        result = self.harness._steps("s", "observation", work.ref)[-1].body["result"]
        self.assertEqual(self.source.body["text"], result["text"])
        self.assertEqual(self.source.body["origin"], result["origin"])
        self.assertEqual(self.source.ref, result["ref"])

    async def test_explicit_reviewer_finding_input_is_navigable_without_default_judgment_body(
        self,
    ):
        finding = await self.finding(
            "原判断：登记人群17人与到会12人应分别报告。", "核对两种口径"
        )
        writer = self.child("writer", "Write findings", [finding.ref])
        writer_request = await self.execute(
            writer,
            "draft_report",
            {"text": "登记17人，其中12人到会。", "evidence": [self.source.ref]},
        )
        self.assert_original_bodies(writer_request, finding)
        report = self.store.list("s", "report")[-1]
        reviewer = self.child("reviewer", "Review report", [report.ref, finding.ref])
        request = self.harness._request("s", reviewer)
        self.assertIn(finding.ref, {i["ref"] for i in request["inputs"]})
        self.assertNotIn(finding.body["text"], str(request["context"]))
        relation = next(
            i for i in request["review_progress"]["inputs"] if i["ref"] == finding.ref
        )
        self.assertEqual(finding.body["producer"], relation["producer"])
        await self.execute(reviewer, "read_artifact", {"ref": finding.ref})
        observed = self.harness._steps("s", "observation", reviewer.ref)[-1].body[
            "result"
        ]
        self.assertEqual(finding.body, observed["body"])
        await self.execute(reviewer, "read_artifact", {"ref": finding.body["producer"]})
        producer = self.harness._steps("s", "observation", reviewer.ref)[-1].body[
            "result"
        ]
        self.assertEqual("核对两种口径", producer["body"]["task"])

    async def test_shared_scope_and_reader_deliverable_reach_actual_child_request(self):
        await self.execute(
            self.lead,
            "delegate_work",
            {
                "role": "investigator",
                "task": "核对结果",
                "refs": [self.source.ref],
                "shared_context": "统一使用登记人群，不能混用到会人数。",
                "deliverable": "供读者判断参与情况的结果与证据。",
            },
        )
        child = self.store.list("s", "work")[-1]
        await self.execute(child, "read_source", {"ref": self.source.ref})
        request = self.model.requests[-1]
        self.assertEqual(child.body["shared_context"], request["shared_context"])
        self.assertEqual(child.body["deliverable"], request["deliverable"])

    async def test_report_measurement_matches_submitted_rendered_text(self):
        result = await self.finding("登记17人", "核对人数")
        writer = self.child("writer", "短报告", (result.ref,))
        args = {
            "text": "登记17人[[cite:" + self.source.ref + "]]。",
            "evidence": [self.source.ref],
        }
        await self.execute(writer, "measure_text", args)
        measured = self.store.list("s", "observation")[-1].body["result"]
        await self.execute(writer, "draft_report", args)
        report = self.store.list("s", "report")[-1]
        self.assertEqual(len(report.body["text"]), measured["characters"])
        self.assertEqual(
            report.body["citation_body_length"], measured["body"]["characters"]
        )
        self.assertLess(measured["body"]["characters"], measured["characters"])
