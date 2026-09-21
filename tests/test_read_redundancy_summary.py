"""Tests for exact-result read repetition summaries."""

from __future__ import annotations

import unittest

from tools.summarize_read_redundancy import summarize


class ReadRedundancySummaryTests(unittest.TestCase):
    def test_counts_only_successful_exact_repeats_within_same_role_tool(self):
        work = {
            "ref": "w",
            "kind": "work",
            "parents": [],
            "seq": 1,
            "body": {"role": "reviewer"},
        }
        result = {"ref": "s", "offset": 0, "end": 10, "text": "same"}
        rows = [work] + [
            {
                "kind": "observation",
                "parents": ["w"],
                "seq": seq,
                "body": {"tool": "read_source", "result": value},
            }
            for seq, value in (
                (2, result),
                (3, dict(result)),
                (4, {**result, "end": 9}),
            )
        ]
        summary = summarize(rows)
        self.assertEqual(3, summary["successful_public_reads"])
        self.assertEqual(1, summary["additional_identical_read_results"])
        self.assertEqual(1, len(summary["repeated_groups"]))
        self.assertEqual([2, 3], summary["repeated_groups"][0]["sequences"])

    def test_failures_nonreads_and_different_roles_do_not_collapse(self):
        rows = [
            {
                "ref": "a",
                "kind": "work",
                "parents": [],
                "seq": 1,
                "body": {"role": "writer"},
            },
            {
                "ref": "b",
                "kind": "work",
                "parents": [],
                "seq": 2,
                "body": {"role": "reviewer"},
            },
            {
                "kind": "observation",
                "parents": ["a"],
                "seq": 3,
                "body": {"tool": "read_source", "result": {"text": "x"}},
            },
            {
                "kind": "observation",
                "parents": ["b"],
                "seq": 4,
                "body": {"tool": "read_source", "result": {"text": "x"}},
            },
            {
                "kind": "observation",
                "parents": ["a"],
                "seq": 5,
                "body": {"tool": "calculate", "result": {"text": "x"}},
            },
            {
                "kind": "observation",
                "parents": ["a"],
                "seq": 6,
                "body": {
                    "tool": "read_source",
                    "result": {"text": "x"},
                    "failure": "failed",
                },
            },
        ]
        summary = summarize(rows)
        self.assertEqual(2, summary["successful_public_reads"])
        self.assertEqual(0, summary["additional_identical_read_results"])

    def test_empty_input_is_explicit(self):
        summary = summarize([])
        self.assertEqual(0, summary["successful_public_reads"])
        self.assertEqual(0.0, summary["exact_repeat_fraction"])
        self.assertEqual([], summary["repeated_groups"])


if __name__ == "__main__":
    unittest.main()
