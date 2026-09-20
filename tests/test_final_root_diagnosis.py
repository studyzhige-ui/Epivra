"""Offline controls for the final diagnostic, not quality acceptance tests."""
import asyncio
import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from epivra.prompts import ROLES
from tools.run_final_root_diagnosis import (
    REQUEST,
    SHORT,
    admit,
    real_inputs,
    run,
    trials,
)


def fixture():
    first = {"kind": "work_result", "seq": 901, "ref": "1" * 64, "body": {
        "text": "original research", "findings": [{}, {}, {"statement": '因此长读事务只能经"checkpoint 无法完成/重置"的间接路径影响提交延迟。'}]}}
    second = {"kind": "work_result", "seq": 983, "ref": "2" * 64, "body": {"text": "second research"}}
    return [first, second, {"seq": 1055, "kind": "work", "body": {"task": "original assignment"}},
            {"seq": 3, "kind": "source", "ref": "3" * 64, "body": {"text": "complete original source"}}], {"task": "original user question"}


class FinalDiagnosisTests(unittest.TestCase):
    def test_schedule_balanced_and_output_claims_not_in_generation_inputs(self):
        selected = trials(*fixture())
        self.assertEqual(24, len(selected))
        self.assertEqual(24, len({x["id"] for x in selected}))
        for x in selected:
            if x["group"] == "short_generation":
                self.assertNotIn("claim", x["input"])
                self.assertEqual(SHORT[x["case"]]["source"], x["input"]["source"])
        real = [x for x in selected if x["group"] == "historical_input_ablation"]
        self.assertEqual([x["arm"] for x in real[:4]], list(reversed([x["arm"] for x in real[4:]])))

    def test_interventions_keep_original_material_and_do_not_mutate_production(self):
        records, case = fixture()
        before = copy.deepcopy(records)
        roles = dict(ROLES)
        arms = real_inputs(records, case)
        original = arms["original"][1]
        neutral = arms["neutral_task"][1]
        self.assertEqual(original["upstream"], neutral["upstream"])
        self.assertNotEqual(original["task"], neutral["task"])
        for _, data in arms.values():
            self.assertEqual(original["sources"], data["sources"])
            self.assertEqual(original["original_request"], data["original_request"])
        corrected = arms["corrected_upstream"][1]
        self.assertEqual(original["task"], corrected["task"])
        self.assertEqual(original["upstream"][1], corrected["upstream"][1])
        self.assertNotEqual(original["upstream"][0]["ref"], corrected["upstream"][0]["ref"])
        self.assertEqual(before, records)
        self.assertEqual(roles, ROLES)

    def test_exact_request_identity_and_no_blind_repeat(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "new"
            admit(REQUEST, "unit-test", path)
            for value in ({**REQUEST, "version": True}, {**REQUEST, "case": "benchmark10"}, None):
                with self.assertRaises(ValueError):
                    admit(value, "unit-test", path)
            with patch.dict(os.environ, {"GITHUB_RUN_ATTEMPT": "2"}), self.assertRaises(ValueError):
                admit(REQUEST, "unit-test", path)
            path.mkdir()
            with self.assertRaises(ValueError):
                admit(REQUEST, "unit-test", path)

    def test_empty_existing_secret_is_rejected_before_execution(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            (root / "evals").mkdir()
            (root / "evals/final-root-request.json").write_text(json.dumps(REQUEST))
            with patch("tools.run_final_root_diagnosis.load_archive", return_value=fixture()), patch.dict(os.environ, {"DEEPSEEK_API_KEY": ""}), self.assertRaisesRegex(ValueError, "credential"):
                asyncio.run(run(root, "offline", root / "unused.zip"))


if __name__ == "__main__":
    unittest.main()
