"""Exact-output and complexity regressions for local context assembly.

The frozen oracle is an evaluation fixture, not an alternate product runtime.
"""

from __future__ import annotations

import copy
import random
import unittest
from unittest.mock import patch

from epivra import context
from epivra.domain import Artifact, ContextCapacity, encode, identity
from evals import context_assembly_reference as reference


def artifact(seq, body, kind="note"):
    return Artifact(identity(seq, body, kind), "fixture", kind, body, (), seq)


def outcome(function, *args, **kwargs):
    try:
        return ("result", encode(function(*args, **kwargs)))
    except ContextCapacity as exc:
        return ("capacity", str(exc))


class ContextAccountingTests(unittest.TestCase):
    def assert_same(self, base, candidates, memory, capacity, **kwargs):
        self.assertEqual(
            outcome(reference.assemble, base, candidates, memory, capacity, **kwargs),
            outcome(context.assemble, base, candidates, memory, capacity, **kwargs),
        )

    def test_empty_and_exact_essential_boundaries(self):
        for memory in (None, {"text": "legacy"}, artifact(1, {"text": "active"}, "memory")):
            base = {"direction": {"request": "完整用户原始需求"}, "authority": {"read": True}}
            request = reference.assemble(base, [], memory, 10000)
            size = len(encode(request))
            for capacity in (-1, 0, size - 1, size, size + 1, 10000):
                with self.subTest(memory=memory, capacity=capacity):
                    self.assert_same(base, [], memory, capacity)

    def test_unicode_escaping_and_nested_values_at_every_capacity(self):
        bodies = [
            {"quote": '中😀e\u0301\\\"\n\t\x00', "nested": [None, True, 3.5, {"a": "x"}]},
            ["quoted", {"unicode-key-汉": "β"}],
            "原始引文" * 70,
            {"counterevidence": "Still required", "conditions": ["A", "B"]},
        ]
        candidates = [artifact(i, b) for i, b in enumerate(bodies)]
        base = {"task": "保留条件\n不增设字数限制", "inputs": [{"ref": candidates[0].ref}]}
        size = len(encode(reference.assemble(base, candidates, None, 10000)))
        for capacity in range(size + 2):
            self.assert_same(base, candidates, None, capacity)

    def test_direct_reference_and_clarification_priority_unchanged(self):
        candidates = [
            artifact(0, {"text": "old direct source"}, "source"),
            artifact(1, {"text": "clarified condition"}, "clarification_answer"),
            artifact(2, {"text": "new indirect note"}),
        ]
        base = {"inputs": [{"ref": candidates[0].ref}], "task": "Answer the original question"}
        for direct in (None, set(), {candidates[2].ref}):
            for capacity in range(100, 1400, 7):
                self.assert_same(base, candidates, None, capacity, direct_refs=direct)

    def test_omitted_count_decimal_transitions_and_handles(self):
        for count in (9, 10, 11, 99, 100, 101):
            candidates = [artifact(i, {"text": "x" * (300 if i % 3 else 6000)}) for i in range(count)]
            for capacity in (60, 255, 256, 257, 512, 999, 1000, 2048, 4096, 48000):
                self.assert_same({"task": "unchanged"}, candidates, None, capacity)

    def test_seeded_differential_cases(self):
        rng = random.Random(69401)
        alphabet = 'abc汉字😀e\u0301\\\"\n\r\t'
        for index in range(160):
            candidates = [artifact(
                rng.randrange(300),
                {"text": "".join(rng.choices(alphabet, k=rng.randrange(0, 320))),
                 "values": [None, False, rng.randrange(100)]},
                rng.choice(["note", "source", "clarification_answer", "work_result"]),
            ) for _ in range(rng.randrange(0, 28))]
            refs = [a.ref for a in candidates[::3]]
            base = {"task": "original task" * rng.randrange(1, 20), "inputs": [{"ref": r} for r in refs]}
            memory = artifact(500, {"text": "retain scope"}, "memory") if index % 2 else None
            for capacity in (rng.randrange(1, 16000), 48000):
                with self.subTest(index=index, capacity=capacity):
                    self.assert_same(base, candidates, memory, capacity)

    def test_mixed_handles_final_count_and_no_input_mutation(self):
        base = {"direction": {"request": "Write in the user's chosen format"}, "inputs": []}
        candidates = [artifact(i, {"text": "long " * 1000 if i % 2 else "short"}) for i in range(12)]
        memory = artifact(99, {"text": "qualify the recommendation", "refs": []}, "memory")
        before = copy.deepcopy((base, candidates, memory))
        result = context.assemble(base, candidates, memory, 2000)
        self.assertEqual(before, (base, candidates, memory))
        self.assertTrue(any("body_omitted" in item for item in result["context"]))
        self.assertTrue(any("body" in item for item in result["context"]))
        self.assertEqual(12 - sum("body" in x for x in result["context"]), result["omitted_count"])
        self.assertLessEqual(len(encode(result)), 2000)
        self.assert_same(base, candidates, memory, 2000)

    def test_serialization_work_does_not_reencode_accumulated_context(self):
        candidates = [artifact(i, {"text": "evidence " * 100}) for i in range(200)]
        base = {"task": "essential instructions " * 400}
        essential = len(encode({**base, "context": [], "memory": None, "omitted_count": 200}))
        entry_total = sum(len(encode({"ref": a.ref, "kind": a.kind, "body": a.body})) for a in candidates)
        encoded_sizes = []

        def measured_encode(value):
            result = encode(value)
            encoded_sizes.append(len(result))
            return result

        with patch.object(context, "encode", side_effect=measured_encode):
            result = context.assemble(base, candidates, None, 300000)
        self.assertEqual(200, len(result["context"]))
        # One essential request, one encoding per entry, one final request.
        self.assertEqual(202, len(encoded_sizes))
        self.assertEqual(essential + entry_total + len(encode(result)), sum(encoded_sizes))
        self.assert_same(base, candidates, None, 300000)

    def test_original_writing_requirement_is_not_rewritten_or_truncated(self):
        original = "用户未设默认字数上限。\n" + '保留完整细节、来源与反例。\\"😀' * 5000
        base = {"direction": {"request": original}, "task": "Write the research findings"}
        result = context.assemble(base, [artifact(1, {"text": "a supported finding"})], None, 200000)
        self.assertEqual(original, result["direction"]["request"])
        self.assertNotIn("max_words", result)
        self.assertNotIn("report_limit", result)
        self.assert_same(base, [artifact(1, {"text": "a supported finding"})], None, 200000)


if __name__ == "__main__":
    unittest.main()
