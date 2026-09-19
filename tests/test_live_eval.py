"""No API calls: admission, truthful CI results and public artifact boundaries."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from epivra.storage import Store
from tools.run_live_eval import collect, review_checks, run, save, scrub, validate_request


def request(**changes):
    return {
        "version": 1, "request_id": "unit-test", "mode": "review",
        "cases": ["M03-positive", "M03-negative"], "probe_providers": False,
        **changes,
    }


class LiveEvalTests(unittest.IsolatedAsyncioTestCase):
    def test_small_selection_only(self):
        self.assertEqual(request(), validate_request(request()))
        for value in [
            request(mode="benchmark10"), request(mode="research-quality"),
            request(cases=[]), request(cases=["M03-positive"] * 2),
            request(cases=["M99-positive"]), request(cases=["M01-positive", "M02-positive",
                      "M03-positive", "M04-positive", "M05-positive"]),
            request(mode="closed", cases=["training", "archive"]),
            request(mode="closed", cases=["../../data"]), request(version=True),
            request(request_id="../../invalid"), request(probe_providers="false"),
            request(approval=True), request(cases=[{}]),
        ]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_request(value)
        validate_request(request(mode="closed", cases=["training"]))
        validate_request(request(mode="providers", cases=[], probe_providers=True))

    async def test_rejected_batch_never_loads_credentials(self):
        with tempfile.TemporaryDirectory() as name, patch(
            "tools.run_live_eval.credentials", side_effect=AssertionError("no secrets")
        ):
            with self.assertRaises(ValueError):
                await run(Path(name), request(mode="benchmark10"), "test")
            self.assertEqual([], list(Path(name).iterdir()))

    async def test_rerun_is_not_silent_paid_replay(self):
        with tempfile.TemporaryDirectory() as name, patch.dict(
            "os.environ", {"GITHUB_RUN_ATTEMPT": "2"}
        ), patch("tools.run_live_eval.credentials", side_effect=AssertionError("no secrets")):
            with self.assertRaisesRegex(ValueError, "prior run"):
                await run(Path(name), request(), "test")

    async def test_stale_legacy_directory_rejected_before_provider(self):
        with tempfile.TemporaryDirectory() as name, patch.dict(
            "os.environ", {"GITHUB_RUN_ATTEMPT": "1"}
        ), patch("tools.run_live_eval.credentials", side_effect=AssertionError("no secrets")):
            root = Path(name)
            (root / ".epivra/review-test").mkdir(parents=True)
            with self.assertRaisesRegex(ValueError, "existing diagnostic"):
                await run(root, request(), "test")

    def test_incomplete_or_wrong_review_is_not_ci_success(self):
        selected = ["M03-positive"]
        row = {"case": selected[0], "accepted": True, "expected_accept": True,
               "review": {"reason": "Source supports the claim"}, "error": None}
        result = review_checks([row], selected)
        self.assertTrue(result["decision_gate"])
        self.assertEqual("pending_independent_reason_review", result["semantic_acceptance"])
        for changed in [{"accepted": None}, {"accepted": False}, {"error": "TimeoutError"},
                        {"review": None}]:
            self.assertFalse(review_checks([{**row, **changed}], selected)["decision_gate"])
        for rows in [[], [{**row, "case": "different"}]]:
            with self.assertRaises(ValueError):
                review_checks(rows, selected)

    def test_redaction_handles_individual_pool_keys_and_private_blocks(self):
        secrets = ("sample-secret-one", "sample-secret-two")
        value = {"Authorization": "Bearer sample-secret-one", "reasoning_content": "PRIVATE",
                 "nested": [{"type": "thinking", "text": "PRIVATE"},
                            {"type": ["string", "null"], "text": "sample-secret-two"}],
                 "sample-secret-one": "public statement"}
        text = json.dumps(scrub(value, secrets))
        for forbidden in (*secrets, "PRIVATE", "Bearer"):
            self.assertNotIn(forbidden, text)
        self.assertIn("public statement", text)
        self.assertIn("null", text)

    def test_export_does_not_copy_native_protocol_or_headers(self):
        with tempfile.TemporaryDirectory() as name:
            db = Path(name) / "research.db"
            store = Store(db)
            try:
                c = store.create("s", "test", {})
                work = store.work("s", c.ref, "lead", "test")
                store.put("s", "source", {"origin": "fixture.txt", "text": "public evidence"})
                store.put("s", "step", {
                    "request": {"wire": {"payload": {"messages": [
                        {"role": "assistant", "reasoning_content": "PRIVATE"}
                    ]}}}, "response": {"authorization": "SECRET"}
                }, (work.ref,))
            finally:
                store.close()
            projection = collect(db)
            text = json.dumps(projection)
            self.assertNotIn("PRIVATE", text)
            self.assertNotIn("SECRET", text)
            self.assertIn("public evidence", text)
            self.assertEqual(0, projection["unknown_operations"])
            self.assertNotIn("step", {a["kind"] for a in projection["artifacts"]})

    def test_saved_public_json_is_redacted(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "summary.json"
            save(path, {"x": "escaped-\"secret\""}, ('escaped-"secret"',))
            self.assertEqual({"x": "[REDACTED]"}, json.loads(path.read_text()))
            self.assertFalse(path.with_suffix(".json.tmp").exists())


if __name__ == "__main__":
    unittest.main()
