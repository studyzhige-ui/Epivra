"""Navigation bytecode-independent boundaries; not report-length restrictions."""

import copy
import unittest

from epivra.context import page
from epivra.domain import ContextCapacity, encode


class ContextPageTests(unittest.TestCase):
    def test_terminal_null_must_fit_the_actual_envelope(self):
        items = [{"ref": "r", "value": ""}]
        # Historical code checked a numeric next_offset=1, then returned null,
        # producing a 74-character result inside a 71-character allowance.
        result = page(items, 0, 1, 71)
        self.assertEqual([], result["items"])
        self.assertEqual(0, result["next_offset"])
        self.assertLessEqual(len(encode(result)), 71)
        exact = page(items, 0, 1, 74)
        self.assertEqual(items, exact["items"])
        self.assertIsNone(exact["next_offset"])
        self.assertEqual(74, len(encode(exact)))

    def test_empty_metadata_cannot_claim_to_fit_impossible_capacity(self):
        minimum = len(encode(page([], 0, 1, 256)))
        with self.assertRaisesRegex(ContextCapacity, "page metadata"):
            page([], 0, 1, minimum - 1)
        self.assertEqual(minimum, len(encode(page([], 0, 1, minimum))))

    def test_every_returned_page_is_bounded_across_cursor_digit_changes(self):
        items = [{"ref": str(i), "value": "汉\\\"\n" * (i % 5)} for i in range(110)]
        for offset in (0, 8, 9, 10, 98, 99, 100, 109, 110, 1000):
            for capacity in range(30, 250):
                try:
                    result = page(items, offset, 12, capacity)
                except ContextCapacity:
                    continue
                self.assertLessEqual(len(encode(result)), capacity)
                end = min(offset, len(items)) + len(result["items"])
                self.assertEqual(end if end < len(items) else None, result["next_offset"])

    def test_large_details_become_handles_without_mutating_originals(self):
        items = [{"ref": "a", "kind": "note", "text": "long" * 1000}, {"ref": "b", "kind": "note"}]
        before = copy.deepcopy(items)
        result = page(items, 0, 2, 256)
        self.assertEqual(before, items)
        self.assertEqual({"ref": "a", "kind": "note", "details_omitted": True}, result["items"][0])
        self.assertEqual(items[1], result["items"][1])
        self.assertIsNone(result["next_offset"])

    def test_multi_page_order_and_complete_coverage(self):
        items = [{"ref": str(i), "text": "small"} for i in range(31)]
        seen, offset = [], 0
        while offset is not None:
            result = page(items, offset, 9, 180)
            self.assertTrue(result["items"])
            seen.extend(result["items"])
            offset = result["next_offset"]
        self.assertEqual(items, seen)


if __name__ == "__main__":
    unittest.main()
