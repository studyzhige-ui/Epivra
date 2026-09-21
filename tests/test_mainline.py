from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from epivra.application import ResearchService
from epivra.domain import Call, Conflict, NotAllowed, Reply
from epivra.harness import BUILTINS, Harness, Tool, object_schema, validate
from epivra.review import text_metrics
from epivra.storage import Store


class MainlineTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.folder.name) / "research.db")
        c = self.store.create("s", "Question", {})
        self.brief = {
            "subject": "User evidence",
            "given_context": ["Case materials supplied by user"],
            "questions": ["Does the evidence support the premise?"],
            "material_scope": {"mode": "case_materials", "basis": "User task"},
        }
        p = self.store.put(
            "s", "plan", {"text": "Plan", "brief": self.brief}, (c.direction,)
        )
        self.c = self.store.command("s", "approve", c.ref, "approve", {"plan": p.ref})
        self.lead = self.store.work("s", self.c.ref, "lead", "Lead", (p.ref,))

    async def asyncTearDown(self):
        self.store.close()
        self.folder.cleanup()

    def child(self, role, task, refs=()):
        return self.store.work("s", self.c.ref, role, task, refs, self.lead.ref)

    async def execute(self, work, call):
        class Model:
            identity = "boundary"

            async def complete(self, request):
                return Reply("", (call,)).to_json()

        h = Harness(self.store, Model())
        await h.step("s", work.ref)
        return h

    async def test_dependency_reference_cannot_impersonate_producer(self):
        a, b = self.child("investigator", "A"), self.child("investigator", "B")
        h = await self.execute(
            a, Call("save_memory", {"text": "A progress only", "refs": [b.ref]})
        )
        self.assertEqual(
            "A progress only", h._request("s", a)["memory"]["body"]["text"]
        )
        self.assertIsNone(h._request("s", b)["memory"])
        h = await self.execute(
            a, Call("finish_work", {"text": "A only", "refs": [b.ref]})
        )
        self.assertTrue(h.finished("s", a.ref))
        self.assertFalse(h.finished("s", b.ref))
        result = h._steps("s", "work_result", a.ref)[0]
        syn = self.child("synthesizer", "Combine", (result.ref,))
        other = self.child("investigator", "C")
        await self.execute(other, Call("finish_work", {"text": "C", "refs": [syn.ref]}))
        forged = h._steps("s", "work_result", other.ref)[0]
        self.assertEqual(other.ref, forged.body["producer"])
        self.assertEqual([], h._steps("s", "work_result", syn.ref))
        writer = self.child(
            "writer", "Use complementary answers", (result.ref, forged.ref)
        )
        self.assertEqual([result.ref, forged.ref], writer.body["inputs"])
        self.assertFalse(h.finished("s", syn.ref))

    async def test_brief_is_shared_but_superseded_on_steer(self):
        inv = self.child("investigator", "Subquestion")
        h = await self.execute(
            inv, Call("save_memory", {"text": "Progress", "refs": []})
        )
        for work in (inv, self.lead):
            self.assertEqual(
                self.brief, h._request("s", work)["research_scope"]["brief"]
            )
        c = self.store.command(
            "s", "new-question", self.c.ref, "steer", {"request": "Changed subject"}
        )
        new = self.store.work("s", c.ref, "lead", "New question")
        scope = h._request("s", new)["research_scope"]
        self.assertIsNone(scope["brief"])
        self.assertFalse(scope["approved_plan"]["current_direction"])

    def test_plan_requires_subject_questions_and_material_scope(self):
        schema = BUILTINS["propose_plan"][1]
        validate({"text": "Method", "brief": self.brief}, schema)
        for brief in (
            {**self.brief, "questions": []},
            {**self.brief, "material_scope": {"mode": "all-related", "basis": "guess"}},
        ):
            with self.assertRaises(ValueError):
                validate({"text": "Method", "brief": brief}, schema)
        with self.assertRaises(ValueError):
            validate({"text": "Method"}, schema)

    async def test_report_handoff_is_not_manuscript(self):
        inv = self.child("investigator", "Investigate")
        h = await self.execute(
            inv, Call("finish_work", {"text": "Finding", "refs": []})
        )
        result = h._steps("s", "work_result", inv.ref)[0]
        syn = self.child("synthesizer", "Combine", (result.ref,))
        self.assertTrue(
            any(
                x.get("body", {}).get("text") == "Finding"
                for x in h._request("s", syn)["context"]
            )
        )
        h = await self.execute(
            syn, Call("finish_work", {"text": "Answer", "refs": [result.ref]})
        )
        writer = self.child(
            "writer", "Write", (h._steps("s", "work_result", syn.ref)[0].ref,)
        )
        text = "\n\n".join(["结果：90人次。", *[f"第{i}节" for i in range(12)]])
        args = {
            "text": text,
            "evidence": [],
            "handoff": "Changed wording; internal only",
        }
        h = await self.execute(writer, Call("draft_report", args))
        report = self.store.list("s", "report")[0]
        self.assertEqual(text, report.body["text"])
        self.assertNotIn("handoff", report.body)
        result = h._steps("s", "draft_saved", writer.ref)[0]
        self.assertEqual(args["handoff"], result.body["handoff"])
        reviewer = self.child("reviewer", "Check", (report.ref,))
        await self.execute(reviewer, Call("read_report", {"offset": 0, "limit": 20}))
        observation = self.store.list("s", "observation")[-1].body["result"]
        self.assertEqual(text_metrics(text), observation["text_metrics"])
        self.assertEqual(text_metrics(text), observation["displayed_units_metrics"])
        self.assertNotIn("measure_text", h._request("s", reviewer)["tools"])
        self.assertEqual(13, len(observation["unit_metrics"]))
        self.assertEqual(text_metrics("第11节"), observation["unit_metrics"]["12"])
        self.assertNotIn("internal only", str(observation))

    def test_measurement_and_optional_fields(self):
        self.assertEqual(
            {"characters": 6, "non_whitespace_characters": 3},
            text_metrics("中 a\n😀\t"),
        )
        schema = BUILTINS["draft_report"][1]
        validate({"text": "Report", "evidence": []}, schema)
        with self.assertRaises(ValueError):
            validate({"evidence": []}, schema)
        with self.assertRaises(ValueError):
            validate({"text": "Report", "evidence": [], "handoff": 5}, schema)
        with self.assertRaises(ValueError):
            validate({"text": "Report", "evidence": [], "unexpected": "x"}, schema)

    async def test_citation_rendering_is_reviewed_and_published_unchanged(self):
        source = self.store.put(
            "s", "source", {"text": "Original", "origin": "source.txt"}
        )
        investigator = self.child("investigator", "Read source", (source.ref,))
        harness = await self.execute(
            investigator,
            Call("finish_work", {"text": "Finding from source", "refs": [source.ref]}),
        )
        finding = harness._steps("s", "work_result", investigator.ref)[0]
        writer = self.child("writer", "Write", (finding.ref, source.ref))
        await self.execute(
            writer,
            Call(
                "draft_report",
                {"text": "Unknown [[cite:" + "f" * 64 + "]]", "evidence": [source.ref]},
            ),
        )
        self.assertEqual([], self.store.list("s", "report"))
        self.assertIn("error", self.store.list("s", "observation")[-1].body["result"])
        await self.execute(
            writer,
            Call(
                "draft_report",
                {"text": f"Finding [[cite:{source.ref}]].", "evidence": [source.ref]},
            ),
        )
        report = self.store.list("s", "report")[0]
        self.assertEqual("Finding [1].\n\n---\n\n1. source.txt", report.body["text"])
        reviewer = self.child("reviewer", "Review", (report.ref,))
        await self.execute(reviewer, Call("read_report", {"offset": 0, "limit": 20}))
        self.assertIn("Finding [1]", str(self.store.list("s", "observation")[-1].body))
        await self.execute(
            reviewer,
            Call(
                "submit_review", {"reason": "Reviewed exact manuscript", "defects": []}
            ),
        )
        review = self.store.list("s", "review")[0]
        publication = self.store.publish(
            "s", self.lead.ref, self.c.epoch, report.ref, review.ref
        )
        self.assertEqual(
            report.body["text"],
            self.store.get("s", publication.body["report"]).body["text"],
        )
        forged = self.store.put(
            "s",
            "report",
            {**report.body, "text": report.body["text"].replace("[1]", "[8]")},
            report.parents,
        )
        checker = self.child("reviewer", "Review altered report", (forged.ref,))
        accepted = self.store.put(
            "s",
            "review",
            {"accepted": True, "work": checker.ref},
            (forged.ref, checker.ref),
        )
        with self.assertRaises(ValueError):
            self.store.publish(
                "s", self.lead.ref, self.c.epoch, forged.ref, accepted.ref
            )

    async def test_archived_runtime_cannot_restart_paid_work(self):
        # Construct a legacy snapshot without mutating any real database.
        old = self.store._put("old", "direction", {"request": "Old", "policy": {}})
        self.store._control("old", 0, old.ref, True, False, False, ())
        old_work = self.store._put(
            "old",
            "work",
            {
                "role": "researcher",
                "direction": old.ref,
                "task": "Unfinished",
                "inputs": [],
                "owner": None,
            },
            (old.ref,),
        )
        self.store.db.execute(
            "INSERT INTO operations(id,study,work,direction,epoch,request,status) VALUES(?,?,?,?,?,?,?)",
            ("old-paid", "old", old_work.ref, old.ref, 0, "{}", "unknown"),
        )

        class Model:
            identity = "never-call"

            async def complete(self, request):
                raise AssertionError("must not restart legacy research")

        service = ResearchService(self.store, Harness(self.store, Model()))
        await service.run("old")
        self.assertEqual("RuntimeMismatch", service.errors["old"])
        self.assertEqual(1, len(self.store.unsettled("old")))
        self.assertEqual([], self.store.list("old", "step"))

    async def test_evidence_location_checked_and_limits_retained(self):
        inv = self.child("investigator", "Read")
        source = self.store.put("s", "source", {"text": "Value 17; sample only"})
        args = {
            "text": "Measured 17",
            "source": source.ref,
            "offset": 1,
            "quote": "Value 17",
            "limits": "sample only",
        }
        await self.execute(inv, Call("record_evidence", args))
        self.assertEqual([], self.store.list("s", "note"))
        args["offset"] = 0
        await self.execute(inv, Call("record_evidence", args))
        note = self.store.list("s", "note")[0]
        self.assertEqual("sample only", note.body["limits"])
        self.assertIn(source.ref, note.parents)

    async def test_owner_can_draft_but_unapproved_external_tool_is_unavailable(self):
        await self.execute(
            self.lead, Call("draft_report", {"text": "Bypass", "evidence": []})
        )
        self.assertEqual(1, len(self.store.list("s", "report")))
        self.assertEqual("writer", self.child("writer", "No mandatory synthesis").body["role"])
        c = self.store.create("p", "Plan", {"network": True})
        lead = self.store.work("p", c.ref, "lead", "Plan")

        class Model:
            identity = "plan"

        async def paid(args):
            raise AssertionError("must not be called")

        h = Harness(
            self.store, Model(), {"paid": Tool("Paid", object_schema({}), paid)}
        )
        self.assertNotIn("paid", h._request("p", lead)["tools"])
        self.assertIn("read_source", h._request("s", self.lead)["tools"])
        self.assertIn("snapshot_local", h._request("s", self.lead)["tools"])

    async def test_report_dependency_cannot_impersonate_author(self):
        inv = self.child("investigator", "Find")
        h = await self.execute(inv, Call("finish_work", {"text": "Facts", "refs": []}))
        syn = self.child(
            "synthesizer", "Combine", (h._steps("s", "work_result", inv.ref)[0].ref,)
        )
        await self.execute(syn, Call("finish_work", {"text": "Answer", "refs": []}))
        synthesis = h._steps("s", "work_result", syn.ref)[0]
        other_lead = self.store.work("s", self.c.ref, "lead", "Other lead")
        other_writer = self.store.work(
            "s", self.c.ref, "writer", "Other writer", (synthesis.ref,), other_lead.ref
        )
        writer = self.child("writer", "Write", (synthesis.ref, other_writer.ref))
        await self.execute(
            writer, Call("draft_report", {"text": "Answer", "evidence": []})
        )
        report = self.store.list("s", "report")[0]
        reviewer = self.child("reviewer", "Review", (report.ref,))
        await self.execute(
            reviewer, Call("submit_review", {"reason": "Checked", "defects": []})
        )
        review = self.store.list("s", "review")[0]
        with self.assertRaises(Conflict):
            self.store.publish(
                "s", other_lead.ref, self.c.epoch, report.ref, review.ref
            )
        self.assertEqual(
            self.lead.ref, self.store.get("s", report.body["producer"]).body["owner"]
        )

    async def test_old_direction_result_cannot_start_new_writer(self):
        inv = self.child("investigator", "Find")
        h = await self.execute(inv, Call("finish_work", {"text": "Found", "refs": []}))
        syn = self.child(
            "synthesizer", "Combine", (h._steps("s", "work_result", inv.ref)[0].ref,)
        )
        await self.execute(syn, Call("finish_work", {"text": "Combined", "refs": []}))
        old = h._steps("s", "work_result", syn.ref)[0]
        self.c = self.store.command(
            "s", "steer", self.c.ref, "steer", {"request": "Changed"}
        )
        self.lead = self.store.work("s", self.c.ref, "lead", "New lead")
        with self.assertRaises(NotAllowed):
            self.child("writer", "Old result", (old.ref,))
