from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from epivra.domain import encode
from epivra.storage import Store
from evals.research_case import QUESTION, assess, corpus


class ResearchEvalTests(unittest.TestCase):
    def test_large_file_evaluation_is_deferred(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with self.assertRaises(ValueError):
                corpus(root, 1000)
            self.assertEqual([], list(root.iterdir()))

    def test_fixture_is_reproducible_and_gold_is_not_in_question(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            gold = corpus(root, 30)
            first = {p.name: p.read_bytes() for p in root.iterdir()}
            self.assertEqual(gold, corpus(root, 30))
            self.assertEqual(first, {p.name: p.read_bytes() for p in root.iterdir()})
            self.assertNotIn("RCT-03", QUESTION)
            self.assertNotIn("record-0029", QUESTION)
            self.assertEqual(30, len(first))

    def test_reading_a_prefix_does_not_count_as_full_critical_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder) / "state.db")
            try:
                c = store.create("s", "fixture", {})
                source = store.put(
                    "s", "source", {"origin": "critical.md", "text": "abcdef"}
                )
                report = store.put(
                    "s", "report", {"text": "fixture", "evidence": [source.ref]}
                )
                store._put("s", "publication", {"report": report.ref}, (c.direction,))

                def read(start, end):
                    store.put(
                        "s",
                        "observation",
                        {
                            "tool": "read_source",
                            "result": {
                                "ref": source.ref,
                                "offset": start,
                                "end": end,
                                "text": "abcdef"[start:end],
                            },
                        },
                    )

                read(0, 2)
                read(4, 6)
                gold = {"critical_origins": ["critical.md"]}
                self.assertTrue(assess(store, "s", gold)["critical_sources_cited"])
                self.assertFalse(assess(store, "s", gold)["critical_sources_read"])
                read(2, 4)
                result = assess(store, "s", gold)
                self.assertTrue(result["critical_sources_read"])
                self.assertEqual("manual_required", result["semantic_review"])
                other = store.put(
                    "s", "source", {"origin": "second.md", "text": "abcdef"}
                )
                store.put(
                    "s",
                    "observation",
                    {
                        "tool": "read_artifact_range",
                        "result": {
                            "ref": other.ref,
                            "offset": 0,
                            "end": len(encode(other.body)),
                            "text": encode(other.body),
                        },
                    },
                )
                self.assertTrue(
                    assess(store, "s", {"critical_origins": ["second.md"]})[
                        "critical_sources_read"
                    ]
                )
            finally:
                store.close()
