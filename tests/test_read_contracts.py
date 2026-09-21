"""Read permissions and exact report metrics are contracts, not semantic graders."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from epivra.adapters import DeepSeek, JsonAPI
from epivra.domain import Call, Reply
from epivra.harness import BUILTINS, REFERENCES, Harness, validate
from epivra.review import report_metrics, text_metrics
from epivra.storage import Store


class MetricsTests(unittest.TestCase):
    def test_exact_boundary_never_strips_author_content(self):
        bodies = [
            "# 标题\r\n\r\n正文[1]。\t😀e\u0301\u3000",
            "| column |\n|---|\n| [1] |\n\nInternal note kept here.",
            "# References\n\nAn author-written section is still author text.",
            "",  # Empty author text is a known zero-length boundary.
        ]
        for body in bodies:
            with self.subTest(body=body):
                suffix = "\n\n---\n\n1. long source title [label](https://example.org)"
                value = report_metrics({"text": body + suffix, "citation_body_length": len(body)})
                self.assertEqual(text_metrics(body), value["body"])
                self.assertEqual(len(body + suffix), value["characters"])
                self.assertEqual(len(body), value["citation_body_length"])
                self.assertIn("inline citation markers", value["body_scope"])
                self.assertIn("not words", value["counting_method"])

    def test_legacy_boundary_is_unknown_not_parsed_from_headings(self):
        text = "# Body\n\nText.\n\n---\n\n1. This might be author text."
        value = report_metrics({"text": text})
        self.assertEqual(len(text), value["characters"])
        self.assertIsNone(value["body"])
        self.assertIsNone(value["citation_body_length"])

    def test_invalid_stored_boundaries_are_not_silently_clipped(self):
        for end in (-1, 4, True, 1.2, "2"):
            with self.subTest(end=end), self.assertRaises(ValueError):
                report_metrics({"text": "abc", "citation_body_length": end})


class Scripted:
    identity = "read-contract-test"
    call = None

    async def complete(self, request):
        return Reply("", (self.call,)).to_json()


class ReferenceSchemaTests(unittest.TestCase):
    def test_delegation_refs_use_existing_exact_reference_contract(self):
        schema = BUILTINS["delegate_work"][1]["properties"]["refs"]
        self.assertEqual(REFERENCES, schema)
        for valid in ([], ["a" * 64], ["0" * 64, "f" * 64]):
            validate(valid, schema, "arguments.refs")
        for ref in ("source:" + "a" * 64, "plan:" + "b" * 64, "https://example.org", "a" * 63, "A" * 64):
            with self.subTest(ref=ref), self.assertRaisesRegex(ValueError, r"arguments.refs\[0\]"):
                validate([ref], schema, "arguments.refs")


class ReadContractTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.folder.name) / "state.db")
        c = self.store.create("s", "Answer using the given material.", {})
        p = self.store.put("s", "plan", {"text": "Use supplied material."}, (c.direction,))
        self.control = self.store.command("s", "approve", c.ref, "approve", {"plan": p.ref})
        self.lead = self.store.work("s", self.control.ref, "lead", "Coordinate")
        self.source = self.store.put("s", "source", {"text": "17 arrivals.", "origin": "registry.txt"})
        self.model = Scripted()
        self.harness = Harness(self.store, self.model)

    async def asyncTearDown(self):
        self.store.close()
        self.folder.cleanup()

    def work(self, role, refs=()):
        if role == "lead":
            return self.lead
        if role in {"writer", "synthesizer"}:
            investigator = self.work("investigator")
            result = self.store.put("s", "work_result", {"text": "17 arrivals.", "producer": investigator.ref}, (investigator.ref, self.source.ref))
            refs = (result.ref, *refs)
        return self.store.work("s", self.control.ref, role, "Read the assigned record.", refs, self.lead.ref)

    async def execute(self, work, name, args):
        self.model.call = Call(name, args)
        await self.harness.step("s", work.ref)
        return self.store.list("s", "observation")[-1].body

    async def test_descriptions_match_existing_restrictions_in_all_modes(self):
        private = {"step", "step_done", "control", "material_bytes"}
        for role in ("lead", "investigator", "synthesizer", "writer", "reviewer"):
            for approved in (False, True):
                for mode in ("check", "final"):
                    schema = self.harness._schema(role, {"_approved": approved, "_review_mode": mode})
                    for name in ("read_artifact", "read_artifact_range"):
                        desc = schema[name]["description"]
                        denied = desc.split("Not readable with this tool: ")[1].split(".")[0]
                        self.assertEqual(private | ({"source"} if not approved else set()), set(denied.split(", ")))
                        self.assertNotIn("Delegate source examination", desc)
        # Per-role assembly must not mutate the base description used by later roles.
        desc = self.harness._schema("investigator", {})["read_artifact"]["description"]
        self.assertNotIn("This lead", desc)
        self.assertNotIn("Delegate source examination", desc)

    async def test_owner_sources_and_helper_findings_are_directly_readable(self):
        for name in ("read_artifact", "read_artifact_range"):
            obs = await self.execute(self.lead, name, {"ref": self.source.ref})
            self.assertIsNone(obs["failure"])
            self.assertNotIn("error", obs["result"])
        result = self.store.put("s", "note", {"text": "17 arrivals, not registrations."})
        obs = await self.execute(self.lead, "read_artifact", {"ref": result.ref})
        self.assertIsNone(obs["failure"])
        self.assertEqual(result.body, obs["result"]["body"])
        for role in ("investigator", "synthesizer", "writer"):
            obs = await self.execute(self.work(role), "read_artifact", {"ref": self.source.ref})
            self.assertIsNone(obs["failure"])
            self.assertEqual(self.source.body, obs["result"]["body"])

    async def test_private_reads_remain_blocked_via_both_handlers(self):
        records = [self.store.put("s", kind, {"private": True}) for kind in ("step", "step_done", "material_bytes")]
        # Use an unrelated producer for fake step records: the harness must never
        # mistake them for this work's real protocol steps.
        worker = self.work("investigator")
        for record in records:
            for name in ("read_artifact", "read_artifact_range"):
                obs = await self.execute(worker, name, {"ref": record.ref})
                self.assertIsNotNone(obs["failure"])
                self.assertIn("provider-private", obs["result"]["error"])

    async def test_measurement_and_bound_review_share_exact_rendered_scope(self):
        writer = self.work("writer")
        args = {"text": "# 标题\n\n登记17人[[cite:" + self.source.ref + "]]。\n\n| 数量 |\n|---|\n|17|", "evidence": [self.source.ref]}
        measured = (await self.execute(writer, "measure_text", args))["result"]
        await self.execute(writer, "draft_report", {**args, "handoff": "private count note"})
        report = self.store.list("s", "report")[-1]
        reviewer = self.work("reviewer", (report.ref,))
        first = (await self.execute(reviewer, "read_report", {"offset": 0, "limit": 1}))["result"]
        later = (await self.execute(reviewer, "read_report", {"offset": 1, "limit": 1}))["result"]
        self.assertEqual(measured, first["report_metrics"])
        self.assertEqual(measured, later["report_metrics"])
        self.assertEqual(text_metrics(report.body["text"]), first["text_metrics"])
        self.assertNotIn("private count note", report.body["text"])
        self.assertNotEqual(first["displayed_units_metrics"], first["text_metrics"])
        self.store.close()
        self.store = Store(Path(self.folder.name) / "state.db")
        self.harness = Harness(self.store, self.model)
        after = (await self.execute(reviewer, "read_report", {}))["result"]
        self.assertEqual(measured, after["report_metrics"])

    async def test_delegation_rejects_display_labels_without_repair_or_side_effects(self):
        task = {"role": "investigator", "task": "Examine the record.", "refs": ["source:" + self.source.ref]}
        before = self.store.count("s", "work")
        bad = await self.execute(self.lead, "delegate_work", task)
        self.assertIsNotNone(bad["failure"])
        self.assertIn("arguments.refs[0]", bad["result"]["error"])
        self.assertEqual(before, self.store.count("s", "work"))
        good = await self.execute(self.lead, "delegate_work", {**task, "refs": [self.source.ref]})
        self.assertIsNone(good["failure"])
        child = self.store.get("s", good["result"]["work"])
        self.assertEqual([self.source.ref], child.body["inputs"])
        self.assertEqual(self.lead.ref, child.body["owner"])
        # Syntax-valid unknown refs are still rejected by the original store check.
        missing = await self.execute(self.lead, "delegate_work", {**task, "refs": ["0" * 64]})
        self.assertIn("artifact not found", missing["result"]["error"])
        self.assertEqual(before + 1, self.store.count("s", "work"))

    async def test_restrictions_reach_native_model_wire_without_network(self):
        api = JsonAPI("https://api.deepseek.com", "test-placeholder-no-network")
        try:
            native = Harness(self.store, DeepSeek(api))
            request = native._request("s", self.lead)
            tools = request["wire"]["payload"]["tools"]
            descriptions = {t["function"]["name"]: t["function"]["description"] for t in tools}
            for name in ("read_artifact", "read_artifact_range"):
                self.assertNotIn("Delegate source examination", descriptions[name])
                self.assertIn("step_done", descriptions[name])
        finally:
            await api.close()
