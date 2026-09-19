"""Agent capabilities, not a mandated research route. No provider calls."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from epivra.citations import manuscript, render
from epivra.citations import validate as validate_citations
from epivra.context import source_ranges
from epivra.domain import Call, ContextCapacity, Reply, encode
from epivra.harness import BUILTINS, Harness, validate
from epivra.review import edit_manuscript
from epivra.storage import Store
from epivra.workspace import Workspace


class EditTests(unittest.TestCase):
    def test_simultaneous_edits_keep_unaffected_unicode_and_markdown(self):
        text = "# 标题\r\n\r\nA😀e\u0301\n\n| x |\n|---|\n| B |"
        self.assertEqual(
            text.replace("A", "B").replace("| B |", "| C |"),
            edit_manuscript(
                text, [{"old": "A", "new": "B"}, {"old": "| B |", "new": "| C |"}]
            ),
        )

    def test_empty_missing_ambiguous_overlapping_or_noop_rejected(self):
        for text, edits in [
            ("abc", []),
            ("abc", [{"old": "", "new": "x"}]),
            ("abc", [{"old": "z", "new": "x"}]),
            ("aaaa", [{"old": "aa", "new": "x"}]),
            ("abc", [{"old": "ab", "new": "x"}, {"old": "bc", "new": "y"}]),
            ("abc", [{"old": "a", "new": "a"}]),
        ]:
            with self.subTest(text=text, edits=edits), self.assertRaises(ValueError):
                edit_manuscript(text, edits)

    def test_deletion_and_append_by_exact_anchor(self):
        self.assertEqual(
            "first\n\nlast\nnew",
            edit_manuscript(
                "first\n\nremove\n\nlast",
                [{"old": "remove\n\n", "new": ""}, {"old": "last", "new": "last\nnew"}],
            ),
        )


class Scripted:
    identity = "agent-efficiency-offline"
    call = None

    async def complete(self, request):
        return Reply("", (self.call,)).to_json()


class AgentCapabilityTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.folder.name) / "state.db")
        c = self.store.create(
            "s",
            "Answer the actual question; preserve evidence and all important conditions.",
            {},
        )
        p = self.store.put(
            "s",
            "plan",
            {"text": "Use originals, adapt the investigation as necessary."},
            (c.direction,),
        )
        self.c = self.store.command("s", "approve", c.ref, "approve", {"plan": p.ref})
        self.lead = self.store.work("s", self.c.ref, "lead", "Coordinate")
        self.source = self.store.put(
            "s",
            "source",
            {
                "text": "Campaign registrants increased 20%. Clinical effectiveness was not measured.",
                "origin": "record.txt",
                "coverage": "complete",
            },
        )
        self.investigator = self.child("investigator", [self.source.ref])
        producer = self.child(
            "investigator", [self.source.ref], "Completed preliminary finding"
        )
        self.finding = self.store.put(
            "s",
            "work_result",
            {
                "text": "20% refers to registrants, not effectiveness.",
                "producer": producer.ref,
            },
            (producer.ref, self.source.ref),
        )
        self.model = Scripted()
        self.h = Harness(self.store, self.model)

    async def asyncTearDown(self):
        self.store.close()
        self.folder.cleanup()

    def child(self, role, refs, task="Investigate or write the assigned result"):
        return self.store.work("s", self.c.ref, role, task, tuple(refs), self.lead.ref)

    async def call(self, work, tool, args):
        self.model.call = Call(tool, args)
        await self.h.step("s", work.ref)
        return self.h._steps("s", "observation", work.ref)[-1].body

    async def draft(self, text=None):
        writer = self.child("writer", [self.finding.ref])
        text = (
            text
            or "Registration increased 20%[[cite:"
            + self.source.ref
            + "]].\n\nOther text remains."
        )
        result = await self.call(
            writer, "draft_report", {"text": text, "evidence": [self.source.ref]}
        )
        self.assertIsNone(result["failure"])
        return self.store.get("s", result["result"]["ref"])

    async def test_agent_selects_search_terms_and_can_expand_original(self):
        # The decisive boundary is far beyond an ordinary first page.
        text = (
            ("background " * 4000)
            + "Key condition: indoor ONLY. Outdoor performance untested."
            + (" appendix" * 1000)
        )
        source = self.store.put(
            "s", "source", {"text": text, "origin": "manual.txt", "coverage": "partial"}
        )
        obs = await self.call(
            self.investigator,
            "search_sources",
            {"terms": ["indoor"], "refs": [source.ref]},
        )
        self.assertIsNone(obs["failure"])
        hit = obs["result"]["matches"][0]
        self.assertEqual(text[hit["offset"] : hit["end"]], hit["text"])
        self.assertIn("Outdoor performance untested", hit["text"])
        self.assertEqual("partial", hit["source_coverage"])
        self.assertIn("No hit does not establish absence", obs["result"]["limitation"])
        ranges = source_ranges(
            source, self.h._steps("s", "observation", self.investigator.ref)
        )
        self.assertEqual([[hit["offset"], hit["end"]]], ranges)
        # Authentic search snippets can be saved without retranscribing the quote.
        note = await self.call(
            self.investigator,
            "record_evidence",
            {"text": "Indoor-only condition.", "selection": hit["selection"]},
        )
        self.assertIsNone(note["failure"])
        saved = self.store.get("s", note["result"]["ref"])
        self.assertEqual(hit["text"], saved.body["quote"])
        self.assertEqual(hit["offset"], saved.body["offset"])

    async def test_search_keeps_role_study_and_selection_ownership_boundaries(self):
        for role in ("investigator", "synthesizer", "writer", "reviewer"):
            self.assertIn("search_sources", self.h._schema(role, {}))
        self.assertNotIn("search_sources", self.h._schema("lead", {}))
        denied = await self.call(
            self.lead, "search_sources", {"terms": ["registrants"]}
        )
        self.assertIsNotNone(denied["failure"])
        hit = (
            await self.call(
                self.investigator, "search_sources", {"terms": ["registrants"]}
            )
        )["result"]["matches"][0]
        other = self.child("investigator", [self.source.ref], "Independent check")
        bad = await self.call(
            other,
            "record_evidence",
            {"text": "unsupported ownership", "selection": hit["selection"]},
        )
        self.assertIsNotNone(bad["failure"])
        self.store.create("other", "unrelated", {})
        foreign = self.store.put(
            "other", "source", {"text": "registrants 99", "origin": "foreign"}
        )
        invalid = await self.call(
            other, "search_sources", {"terms": ["registrants"], "refs": [foreign.ref]}
        )
        self.assertIsNotNone(invalid["failure"])

    def test_search_limits_are_advertised_and_validated_before_execution(self):
        terms = BUILTINS["search_sources"][1]["properties"]["terms"]
        self.assertEqual(16, terms["maxItems"])
        self.assertEqual(200, terms["items"]["maxLength"])
        for value in (["word"], [str(i) for i in range(16)], ["x" * 200]):
            validate(value, terms, "arguments.terms")
        with self.assertRaisesRegex(ValueError, "arguments.terms: too many"):
            validate([str(i) for i in range(17)], terms, "arguments.terms")
        with self.assertRaisesRegex(ValueError, r"arguments.terms\[0\]: text too long"):
            validate(["x" * 201], terms, "arguments.terms")
        for value in ([], [""], ["  "]):
            with self.assertRaises(ValueError):
                validate(value, terms, "arguments.terms")

    async def test_search_literal_metacharacters_unicode_and_stable_pages(self):
        ws = Workspace(self.store)
        sources = [
            self.store.put(
                "s",
                "source",
                {
                    "text": ("中😀 noise " * 120) + term + (" suffix " * 200),
                    "origin": "source" + str(i),
                },
            )
            for i, term in enumerate(["[a.*]", "[A.*]", "e\u0301"])
        ]
        first = ws.search_sources(
            "s", ["[a.*]", "e\u0301"], [s.ref for s in sources], limit=1, capacity=5000
        )
        self.assertEqual(1, first["next_offset"])
        second = ws.search_sources(
            "s",
            ["[a.*]", "e\u0301"],
            [s.ref for s in sources],
            offset=1,
            limit=1,
            capacity=5000,
        )
        third = ws.search_sources(
            "s",
            ["[a.*]", "e\u0301"],
            [s.ref for s in sources],
            offset=2,
            limit=1,
            capacity=5000,
        )
        self.assertEqual(2, second["next_offset"])
        self.assertIsNone(third["next_offset"])
        for source, result in zip(sources, [first, second, third]):
            hit = result["matches"][0]
            self.assertEqual(source.ref, hit["ref"])
            self.assertEqual(
                source.body["text"][hit["offset"] : hit["end"]], hit["text"]
            )
            self.assertLessEqual(len(encode(result)), 5000)
        empty = ws.search_sources("s", ["does-not-exist"])
        self.assertEqual([], empty["matches"])
        self.assertIsNone(empty["next_offset"])
        with self.assertRaises(ContextCapacity):
            ws.search_sources("s", ["x"], capacity=10)
        for terms in ([], [" "], ["x" * 201], [str(i) for i in range(17)]):
            with self.assertRaises(ValueError):
                ws.search_sources("s", terms)

    async def test_edit_creates_new_exact_citable_report_without_rewriting(self):
        original = (
            "# Summary\r\n\r\nRegistration increased 20%[[cite:"
            + self.source.ref
            + "]].\n\n"
            + ("Unchanged original context.\n" * 2500)
        )
        report = await self.draft(original)
        writer = self.child(
            "writer",
            [report.ref, self.finding.ref],
            "Revise exactly the unsupported strength; preserve all relevant unaffected text",
        )
        read = await self.call(writer, "read_manuscript", {"report": report.ref})
        self.assertIn("[[cite:" + self.source.ref + "]]", read["result"]["text"])
        self.assertNotEqual(None, read["result"]["next_offset"])
        changed = await self.call(
            writer,
            "revise_report",
            {
                "report": report.ref,
                "edits": [
                    {
                        "old": "Registration increased 20%",
                        "new": "Registration increased 20%; effectiveness was not measured",
                    }
                ],
            },
        )
        self.assertIsNone(changed["failure"])
        revised = self.store.get("s", changed["result"]["ref"])
        self.assertNotEqual(revised.ref, report.ref)
        self.assertEqual(report.ref, revised.body["revises"])
        self.assertIn(report.ref, revised.parents)
        expected = original.replace(
            "Registration increased 20%",
            "Registration increased 20%; effectiveness was not measured",
        )
        self.assertEqual(
            expected, manuscript(revised.body, lambda ref: self.store.get("s", ref))
        )
        self.assertEqual(
            original, manuscript(report.body, lambda ref: self.store.get("s", ref))
        )
        validate_citations(revised.body, lambda ref: self.store.get("s", ref))
        self.assertTrue(self.h.finished("s", writer.ref))
        self.assertEqual([], self.store.list("s", "review"))
        self.assertEqual([], self.store.list("s", "publication"))

    async def test_edit_requires_assigned_current_report_and_valid_evidence(self):
        report = await self.draft()
        unassigned = self.child("writer", [self.finding.ref], "Unassigned work")
        denied = await self.call(
            unassigned,
            "revise_report",
            {
                "report": report.ref,
                "edits": [{"old": "Other text remains.", "new": "Changed."}],
            },
        )
        self.assertIsNotNone(denied["failure"])
        writer = self.child("writer", [report.ref, self.finding.ref], "Correction")
        initial = self.store.count("s", "report")
        for edits in (
            [{"old": "absent", "new": "x"}],
            [{"old": "Registration", "new": "Unsupported[[cite:" + "0" * 64 + "]]"}],
        ):
            result = await self.call(
                writer, "revise_report", {"report": report.ref, "edits": edits}
            )
            self.assertIsNotNone(result["failure"])
            self.assertEqual(initial, self.store.count("s", "report"))
        self.assertFalse(self.h.finished("s", writer.ref))

    async def test_report_receipt_failure_rolls_back_both_artifacts(self):
        writer = self.child("writer", [self.finding.ref])
        old_put = self.store._put

        def faulty(study, kind, *args, **kwargs):
            if kind == "work_result":
                raise ValueError("simulated receipt failure")
            return old_put(study, kind, *args, **kwargs)

        with patch.object(self.store, "_put", side_effect=faulty):
            result = await self.call(
                writer, "draft_report", {"text": "Valid report", "evidence": []}
            )
        self.assertIsNotNone(result["failure"])
        self.assertEqual(0, self.store.count("s", "report"))
        self.assertFalse(self.h.finished("s", writer.ref))

    async def test_citation_roundtrip_preserves_notes_code_and_manual_number_literals(
        self,
    ):
        text = (
            "Evidence[[cite:"
            + self.source.ref
            + "]].\n\n```text\n[1] [[cite:"
            + "0" * 64
            + "]]\n```"
        )
        rendered = render(text, [self.source.ref], lambda ref: self.store.get("s", ref))
        report = {**rendered, "evidence": [self.source.ref]}
        self.assertEqual(text, manuscript(report, lambda ref: self.store.get("s", ref)))
        validate_citations(report, lambda ref: self.store.get("s", ref))
        with self.assertRaises(ValueError):
            manuscript(
                {**report, "text": rendered["text"].replace("[1].", "[2].")},
                lambda ref: self.store.get("s", ref),
            )


if __name__ == "__main__":
    unittest.main()
