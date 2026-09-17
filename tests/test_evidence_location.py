from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from epivra.domain import Call, Reply
from epivra.harness import BUILTINS, Harness, validate
from epivra.storage import Store


class EvidenceLocationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.folder.name) / "state.db")
        c = self.store.create("s", "Investigate supplied material", {})
        plan = self.store.put("s", "plan", {"text": "Investigate"}, (c.direction,))
        self.c = self.store.command(
            "s", "approve", c.ref, "approve", {"plan": plan.ref}
        )
        self.lead = self.store.work("s", self.c.ref, "lead", "Coordinate")
        self.work = self.store.work(
            "s",
            self.c.ref,
            "investigator",
            "Find supporting evidence",
            owner=self.lead.ref,
        )

    async def asyncTearDown(self):
        self.store.close()
        self.folder.cleanup()

    async def execute(self, call, work=None):
        class Model:
            identity = "evidence-location-fixture"

            async def complete(self, request):
                return Reply("", (call,)).to_json()

        await Harness(self.store, Model()).step("s", (work or self.work).ref)
        return self.store.list("s", "observation")[-1].body["result"]

    def arguments(self, source, quote, **extra):
        return {
            "source": source.ref,
            "quote": quote,
            "text": "The source supports this finding",
            "limits": "Only the stated scope",
            **extra,
        }

    async def test_paging_and_selection_preserve_exact_original_without_copying(self):
        raw = "标题😀\n\n包含“原文引号”与\n换行。\n\n" + "其他资料。" * 5000
        source = self.store.put("s", "source", {"text": raw})
        page = await self.execute(
            Call("read_source", {"ref": source.ref, "limit": 28000})
        )
        self.assertEqual(raw[: page["end"]], page["text"])
        self.assertIsNotNone(page["next_offset"])
        choice = page["selections"][1]["selection"]
        result = await self.execute(
            Call("record_evidence", {"selection": choice, "text": "Finding"})
        )
        note = self.store.get("s", result["ref"])
        self.assertEqual("包含“原文引号”与\n换行。", note.body["quote"])
        self.assertEqual(source.ref, note.body["source"])
        other = self.store.work(
            "s", self.c.ref, "investigator", "Other work", owner=self.lead.ref
        )
        denied = await self.execute(
            Call("record_evidence", {"selection": choice, "text": "Finding"}), other
        )
        self.assertIn("error", denied)
        unread = await self.execute(
            Call(
                "record_evidence", {"selection": f"{source.ref}:0:2", "text": "Finding"}
            )
        )
        self.assertIn("error", unread)

    async def test_large_artifact_first_read_is_a_page_not_an_error(self):
        item = self.store.put("s", "note", {"text": "Data " * 9000})
        page = await self.execute(Call("read_artifact", {"ref": item.ref}))
        self.assertNotIn("error", page)
        self.assertEqual("canonical-json", page["encoding"])
        tail = await self.execute(
            Call(
                "read_artifact_range",
                {"ref": item.ref, "offset": page["next_offset"], "limit": 30000},
            )
        )
        self.assertEqual(page["end"], tail["offset"])

    def test_quote_contract_requires_content_and_makes_offset_optional(self):
        schema = BUILTINS["record_evidence"][1]
        args = {
            "source": "source-ref",
            "quote": "Original evidence",
            "text": "Finding",
            "limits": "",
        }
        validate(args, schema)
        validate({**args, "offset": 0}, schema)
        for key in ("source", "quote", "text"):
            with self.subTest(missing=key), self.assertRaises(ValueError):
                validate({k: v for k, v in args.items() if k != key}, schema)

    async def test_unique_chinese_quote_is_located_without_model_offset_and_directly_readable(
        self,
    ):
        raw = "标题😀\r\n背景：按登记口径。\r\n结果：17人完成。\r\n限制：仅本期。"
        source = self.store.put("s", "source", {"text": raw})
        quote = "结果：17人完成。\r\n限制：仅本期。"
        args = self.arguments(source, quote)
        result = await self.execute(Call("record_evidence", args))
        self.assertNotIn("error", result)
        note = self.store.get("s", result["ref"])
        self.assertEqual(raw.index(quote), note.body["offset"])
        self.assertEqual(quote, note.body["quote"])
        self.assertEqual(args["limits"], note.body["limits"])
        self.assertEqual(
            quote, raw[note.body["offset"] : note.body["offset"] + len(quote)]
        )
        self.assertIn(source.ref, note.parents)
        finished = await self.execute(
            Call("finish_work", {"text": "Scoped finding", "refs": [note.ref]})
        )
        downstream = self.store.work(
            "s",
            self.c.ref,
            "synthesizer",
            "Use direct evidence",
            (finished["ref"], note.ref),
            self.lead.ref,
        )
        read = await self.execute(Call("read_artifact", {"ref": note.ref}), downstream)
        self.assertEqual(note.body, read["body"])

    async def test_ambiguous_quote_returns_positions_and_explicit_choice_succeeds(self):
        source = self.store.put("s", "source", {"text": "甲：共同结果；乙：共同结果。"})
        quote = "共同结果"
        args = self.arguments(source, quote)
        result = await self.execute(Call("record_evidence", args))
        self.assertIn("error", result)
        offsets = [source.body["text"].index(quote), source.body["text"].rindex(quote)]
        self.assertEqual(offsets, result["candidate_offsets"])
        self.assertEqual([], self.store.list("s", "note"))
        result = await self.execute(
            Call("record_evidence", {**args, "offset": offsets[1]})
        )
        self.assertNotIn("error", result)
        self.assertEqual(offsets[1], self.store.get("s", result["ref"]).body["offset"])

    async def test_explicit_wrong_offset_is_not_silently_corrected(self):
        source = self.store.put("s", "source", {"text": "前言\r\n证据：原始结果。"})
        quote = "证据：原始结果。"
        result = await self.execute(
            Call("record_evidence", self.arguments(source, quote, offset=1))
        )
        self.assertIn("error", result)
        self.assertEqual(
            [source.body["text"].index(quote)], result["candidate_offsets"]
        )
        self.assertEqual([], self.store.list("s", "note"))

    async def test_empty_or_absent_quote_never_creates_evidence(self):
        source = self.store.put("s", "source", {"text": "Original evidence"})
        for quote in ("", "Not in this source"):
            with self.subTest(quote=quote):
                result = await self.execute(
                    Call("record_evidence", self.arguments(source, quote))
                )
                self.assertIn("error", result)
        self.assertEqual([], self.store.list("s", "note"))

    async def test_overlapping_matches_are_not_misclassified_as_unique(self):
        source = self.store.put("s", "source", {"text": "aaaa"})
        result = await self.execute(
            Call("record_evidence", self.arguments(source, "aaa"))
        )
        self.assertIn("error", result)
        self.assertEqual([0, 1], result["candidate_offsets"])
        self.assertEqual([], self.store.list("s", "note"))

    async def test_note_reads_bound_original_without_turning_other_records_into_sources(
        self,
    ):
        source = self.store.put("s", "source", {"text": "前言。证据原文。"})
        result = await self.execute(
            Call("record_evidence", self.arguments(source, "证据原文。"))
        )
        page = await self.execute(Call("read_source", {"ref": result["ref"]}))
        self.assertEqual(source.ref, page["ref"])
        self.assertEqual("证据原文。", page["text"])
        wrong = self.store.put(
            "s",
            "note",
            {"source": source.ref, "quote": "不存在", "offset": 0},
            (source.ref,),
        )
        rejected = await self.execute(Call("read_source", {"ref": wrong.ref}))
        self.assertIn("error", rejected)
