"""The paired paid experiment must be explicit, isolated and correctly seeded."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from epivra.harness import Harness
from epivra.storage import Store
from evals.read_contract_cases import CASE_IDS, selection
from tools.run_read_contract_eval import assess, run, seed


class ContractEvalTests(unittest.IsolatedAsyncioTestCase):
    def request(self, cases):
        return {"version": 1, "request_id": "probe-1", "cases": cases}

    def test_only_fixed_small_case_ids_are_admitted(self):
        self.assertEqual(list(CASE_IDS), selection(self.request(list(CASE_IDS))))
        for cases in ([], ["benchmark10"], ["lead-registry"] * 2, [1], "lead-registry"):
            with self.subTest(cases=cases), self.assertRaises(ValueError):
                selection(self.request(cases))
        for value in (True, "1", None):
            with self.subTest(version=value), self.assertRaises(ValueError):
                selection({**self.request(["lead-registry"]), "version": value})

    async def test_rejects_large_or_repeated_attempt_before_credentials(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("tools.run_read_contract_eval.credentials", side_effect=AssertionError("credential access")):
                with self.assertRaises(ValueError):
                    await run(Path(folder), self.request(["benchmark10"]), "run", "candidate")
                with patch.dict("os.environ", {"GITHUB_RUN_ATTEMPT": "2"}):
                    with self.assertRaises(ValueError):
                        await run(Path(folder), self.request(["lead-registry"]), "run", "candidate")

    def test_expected_labels_are_not_in_agent_inputs(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder) / "state.db")
            try:
                for case in CASE_IDS:
                    work, source, expected = seed(store, case)
                    model = type("Offline", (), {"identity": "no-network"})()
                    request = Harness(store, model)._request(case, work)
                    self.assertNotIn('"expected"', json.dumps(request))
                    self.assertNotIn('"contract_match"', json.dumps(request))
                    row = assess(store, case, work, source, expected)
                    self.assertFalse(row["contract_match"])
                    if "accept" in expected:
                        report = store.list(case, "report")[-1]
                        end = report.body["citation_body_length"]
                        self.assertEqual(expected["author_non_whitespace_characters"], sum(not ch.isspace() for ch in report.body["text"][:end]))
                        self.assertEqual(expected["accept"], expected["author_non_whitespace_characters"] <= expected["maximum"])
            finally:
                store.close()
