from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from deep_research_agent.context import assemble
from deep_research_agent.domain import Artifact, NotAllowed, encode
from deep_research_agent.storage import Store
from deep_research_agent.workspace import Workspace


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.corpus = self.root / "corpus"
        self.corpus.mkdir()
        self.store = Store(self.root / "research.db")
        self.store.create("s", "Study documents", {"local_roots": [str(self.corpus)]})
        self.workspace = Workspace(self.store)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_hundred_sources_are_pageable_and_unsupported_files_visible(self):
        for i in range(99):
            (self.corpus / f"{i:04}.txt").write_text(f"文献 {i}", encoding="utf-8")
        (self.corpus / "unknown.bin").write_bytes(b"binary")
        catalog = self.workspace.discover("s", str(self.corpus))
        collected, offset = [], 0
        while offset is not None:
            page = self.workspace.catalog_page("s", catalog.ref, offset, 100)
            collected.extend(page["entries"])
            offset = page["next_offset"]
        self.assertEqual(100, len(collected))
        self.assertEqual(99, sum(e["status"] == "available" for e in collected))
        self.assertEqual([], self.store.list("s", "source"))

    def test_snapshot_is_reused_after_original_changes(self):
        path = self.corpus / "source.txt"
        path.write_text("Original 原始证据", encoding="utf-8")
        catalog = self.workspace.discover("s", str(self.corpus))
        first = self.workspace.snapshot("s", catalog.ref, "source.txt")
        self.assertEqual(
            first.ref,
            self.workspace.catalog_page("s", catalog.ref, 0, 10)["entries"][0][
                "source_ref"
            ],
        )
        path.write_text("Changed evidence and a different length", encoding="utf-8")
        replay = self.workspace.snapshot("s", catalog.ref, "source.txt")
        self.assertEqual(first.ref, replay.ref)
        fresh_catalog = self.workspace.discover("s", str(self.corpus))
        second = self.workspace.snapshot("s", fresh_catalog.ref, "source.txt")
        self.assertNotEqual(first.ref, second.ref)
        self.assertEqual(
            "Original 原始证据", self.store.get("s", first.ref).body["text"]
        )

    def test_catalog_does_not_silently_substitute_changed_content(self):
        path = self.corpus / "source.txt"
        path.write_text("first", encoding="utf-8")
        catalog = self.workspace.discover("s", str(self.corpus))
        path.write_text("longer revised content", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "changed since discovery"):
            self.workspace.snapshot("s", catalog.ref, "source.txt")

    def test_ungranted_root_and_uncatalogued_path_are_rejected(self):
        with self.assertRaises(NotAllowed):
            self.workspace.discover("s", str(self.root))
        catalog = self.workspace.discover("s", str(self.corpus))
        with self.assertRaises(ValueError):
            self.workspace.snapshot("s", catalog.ref, "../secret.txt")

    def test_link_escape_is_not_read(self):
        outside = self.root / "outside.txt"
        outside.write_text("private", encoding="utf-8")
        link = self.corpus / "link.txt"
        try:
            link.symlink_to(outside)
        except OSError:
            self.skipTest("OS does not permit creating symlinks")
        catalog = self.workspace.discover("s", str(self.corpus))
        self.assertEqual("unavailable", catalog.body["entries"][0]["status"])
        with self.assertRaises(ValueError):
            self.workspace.snapshot("s", catalog.ref, "link.txt")

    def test_invalid_utf8_is_not_silently_replaced(self):
        (self.corpus / "bad.txt").write_bytes(b"\xff\xfe\xff")
        catalog = self.workspace.discover("s", str(self.corpus))
        with self.assertRaises(UnicodeError):
            self.workspace.snapshot("s", catalog.ref, "bad.txt")
        self.assertEqual([], self.store.list("s", "source"))

    def test_upload_is_scoped_and_preserves_content(self):
        source = self.workspace.upload("s", "中文.txt", "内容".encode())
        self.assertEqual("内容", source.body["text"])
        self.store.create("other", "another", {})
        with self.assertRaises(ValueError):
            self.store.get("other", source.ref)


class ContextTests(unittest.TestCase):
    def artifact(self, i, text):
        return Artifact(f"ref-{i}", "s", "observation", {"text": text}, (), i)

    def test_large_tool_result_keeps_a_retrievable_handle(self):
        result = assemble({"task": "x"}, [self.artifact(1, "x" * 10000)], None, 800)
        self.assertEqual("ref-1", result["context"][0]["ref"])
        self.assertTrue(result["context"][0]["body_omitted"])
        self.assertEqual(1, result["omitted_count"])
        self.assertLessEqual(len(encode(result)), 800)

    def test_memory_is_never_silently_omitted(self):
        memory = Artifact(
            "memory", "s", "memory", {"text": "critical contradiction"}, (), 1
        )
        result = assemble(
            {"task": "x"},
            [self.artifact(i, "x" * 100) for i in range(1000)],
            memory,
            900,
        )
        self.assertEqual(memory.body, result["memory"]["body"])
        self.assertLessEqual(len(encode(result)), 900)
        with self.assertRaises(ValueError):
            assemble({"task": "x" * 900}, [], memory, 900)

    def test_serialized_budget_accounts_for_escapes_and_metadata(self):
        candidates = [self.artifact(i, '\\"\n' * 20) for i in range(1000)]
        for capacity in [300, 400, 500, 1000]:
            with self.subTest(capacity=capacity):
                result = assemble({"task": "问题"}, candidates, None, capacity)
                self.assertLessEqual(len(encode(result)), capacity)
