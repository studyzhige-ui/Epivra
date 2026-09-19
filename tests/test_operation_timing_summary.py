"""Tests for interval-aware timing summaries."""

from __future__ import annotations

import unittest

from tools.summarize_operation_timing import intervals_union_seconds, summarize


class TimingSummaryTests(unittest.TestCase):
    def test_union_does_not_double_count_parallel_external_calls(self):
        calls = [
            {
                "resource": "model",
                "status": "succeeded",
                "queued_at": 0.0,
                "admitted_at": 1.0,
                "invoked_at": 1.1,
                "settled_at": 5.0,
                "admission_to_invoke_seconds": 0.1,
            },
            {
                "resource": "model",
                "status": "succeeded",
                "queued_at": 0.5,
                "admitted_at": 1.5,
                "invoked_at": 2.0,
                "settled_at": 6.0,
                "admission_to_invoke_seconds": 0.5,
            },
        ]
        result = summarize(calls, {"started_at": 0.0, "finished_at": 10.0})
        self.assertAlmostEqual(7.9, result["external_sum_seconds"])
        self.assertAlmostEqual(4.9, result["external_union_seconds"])
        self.assertLess(
            result["external_union_seconds"], result["external_sum_seconds"]
        )
        self.assertAlmostEqual(6.0, result["tracked_wait_union_seconds"])
        self.assertAlmostEqual(4.0, result["untracked_or_local_wall_seconds"])

    def test_missing_and_unknown_spans_are_explicit(self):
        calls = [
            {"resource": "model", "status": "unknown", "invoked_at": 3.0},
            {"resource": "legacy", "status": "succeeded"},
        ]
        result = summarize(calls)
        self.assertEqual(2, result["operations"])
        self.assertEqual(0, result["timed_external_operations"])
        self.assertEqual(2, result["operations_without_complete_external_span"])
        self.assertEqual(1, result["unknown_operations"])

    def test_union_handles_nested_touching_and_invalid_intervals(self):
        self.assertEqual(
            7.0,
            intervals_union_seconds(
                [(0, 2), (1, 4), (4, 5), (10, 12), (9, 8)]
            ),
        )


if __name__ == "__main__":
    unittest.main()
