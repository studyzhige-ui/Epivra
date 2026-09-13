"""Provider decoding and acquired web evidence have separate responsibilities."""

import tempfile
import unittest
from pathlib import Path

from epivra.adapters import ProviderFailure, Tavily
from epivra.domain import Call, Reply
from epivra.harness import Harness, Tool, object_schema
from epivra.storage import Store
from epivra.workspace import Workspace


class WebAcquisitionRecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_retry_snapshot_survives_crash_before_observation(self):
        class Model:
            identity = "web-acquisition-recovery"
            calls = 0

            async def complete(self, request):
                self.calls += 1
                return Reply("", (Call("fetch_web", {}),)).to_json()

        model, fetches = Model(), 0

        async def fetch(arguments):
            nonlocal fetches
            fetches += 1
            return (
                {"http_status": 429}
                if fetches == 1
                else {
                    "http_status": 200,
                    "data": {
                        "results": [
                            {
                                "url": "https://example.org/original",
                                "raw_content": "原始资料",
                            }
                        ]
                    },
                }
            )

        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "research.db"
            store = Store(path)
            try:
                c = store.create("s", "Read original", {"network": True})
                plan = store.put("s", "plan", {"text": "Read original"}, (c.direction,))
                c = store.command("s", "approve", c.ref, "approve", {"plan": plan.ref})
                work = store.work("s", c.ref, "investigator", "Read original")

                def harness():
                    workspace = Workspace(store)
                    tool = Tool(
                        "Read original",
                        object_schema({}),
                        fetch,
                        permission="network",
                        observe=lambda raw, acquisition: workspace.web_snapshot(
                            "s", Tavily.decode_extract(raw), acquisition
                        ),
                        retry_delay=lambda raw, attempt: (
                            0 if raw["http_status"] == 429 else None
                        ),
                    )
                    return Harness(store, model, {"fetch_web": tool})

                original = store.observation

                def crash(study, work, epoch, body, parents=()):
                    if body.get("tool") == "fetch_web":
                        self.assertEqual(len(store.list("s", "source")), 1)
                        raise RuntimeError("crash before web observation")
                    return original(study, work, epoch, body, parents)

                store.observation = crash
                with self.assertRaisesRegex(RuntimeError, "crash before web"):
                    await harness().step("s", work.ref)
                self.assertFalse(
                    any(
                        a.body.get("tool") == "fetch_web"
                        for a in store.list("s", "observation")
                    )
                )
                first_ref = store.list("s", "source")[0].ref
                store.close()
                store = Store(path)
                await harness().step("s", work.ref)
                self.assertEqual((model.calls, fetches), (1, 2))
                sources = store.list("s", "source")
                self.assertEqual([s.ref for s in sources], [first_ref])
                retry = store.list("s", "retry")[0]
                acquisition = sources[0].body["acquisition"]
                self.assertEqual(acquisition["operation"], retry.body["next"])
                self.assertNotEqual(acquisition["operation"], retry.body["operation"])
                self.assertEqual(acquisition["work"], work.ref)
                self.assertEqual(set(sources[0].parents), {work.ref, acquisition["step"]})
                observation = next(
                    a
                    for a in store.list("s", "observation")
                    if a.body.get("tool") == "fetch_web"
                )
                self.assertEqual(
                    observation.body["result"]["sources"][0]["ref"], first_ref
                )
            finally:
                store.close()


class WebSourceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / "research.db")
        self.control = self.store.create("s", "Research", {})
        self.work = self.store.work("s", self.control.ref, "lead", "Read")
        self.step = self.store.put("s", "step", {"request": {}}, (self.work.ref,))
        self.acquisition = {
            "work": self.work.ref,
            "step": self.step.ref,
            "operation": "retry-1",
        }
        self.raw = {
            "http_status": 200,
            "data": {
                "results": [{"url": "https://example.org/a", "raw_content": "原文"}]
            },
        }
        self.workspace = Workspace(self.store)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def admit(self, operation, raw=None, work=None):
        self.store.admit("s", work or self.work.ref, self.control.epoch, operation, {})
        if raw is not None:
            self.store.settle(operation, raw)

    def test_snapshot_replay_has_one_source_and_actual_successful_acquisition(self):
        self.admit("original", {"http_status": 429})
        self.admit("retry-1", self.raw)
        decoded = Tavily.decode_extract(self.raw)
        first = self.workspace.web_snapshot("s", decoded, self.acquisition)
        replay = self.workspace.web_snapshot("s", decoded, self.acquisition)
        self.assertEqual(first, replay)
        sources = self.store.list("s", "source")
        self.assertEqual(len(sources), 1)
        self.assertEqual(set(sources[0].parents), {self.work.ref, self.step.ref})
        self.assertEqual(sources[0].body["acquisition"], self.acquisition)
        self.assertEqual(sources[0].body["text"], "原文")
        self.assertEqual(self.store.result("s", "retry-1"), self.raw)
        self.assertNotIn("data", sources[0].body)
        self.assertEqual(self.store.list("s", "material_bytes"), [])

    def test_unknown_or_other_work_operation_cannot_supply_provenance(self):
        self.admit("retry-1")
        with self.assertRaisesRegex(ValueError, "successful"):
            self.workspace.web_snapshot(
                "s", Tavily.decode_extract(self.raw), self.acquisition
            )
        other = self.store.work("s", self.control.ref, "lead", "Other")
        self.admit("other", self.raw, other.ref)
        with self.assertRaisesRegex(ValueError, "successful"):
            self.workspace.web_snapshot(
                "s",
                Tavily.decode_extract(self.raw),
                {**self.acquisition, "operation": "other"},
            )
        self.assertEqual(self.store.list("s", "source"), [])

    def test_failed_extraction_is_actionable_and_is_not_evidence(self):
        raw = {
            "http_status": 200,
            "data": {
                "results": [{"url": "https://example.org/empty", "raw_content": " "}],
                "failed_results": [
                    {"url": "https://example.org/blocked", "error": "Access denied"}
                ],
            },
        }
        self.admit("retry-1", raw)
        result = self.workspace.web_snapshot(
            "s", Tavily.decode_extract(raw), self.acquisition
        )
        self.assertEqual(result["sources"], [])
        self.assertEqual(len(result["failures"]), 2)
        self.assertEqual(result["failures"][0]["reason"], "Access denied")
        self.assertTrue(all(f["url"] and f["action"] for f in result["failures"]))
        self.assertEqual(self.store.list("s", "source"), [])

    def test_search_stays_a_lead_and_malformed_or_http_failure_is_rejected(self):
        raw = {
            "http_status": 200,
            "data": {"results": [{"url": "https://example.org", "content": "Snippet"}]},
        }
        result = Tavily.decode_search(raw)["results"][0]
        self.assertEqual(result["content_type"], "search_snippet")
        self.assertNotIn("ref", result)
        with self.assertRaises(ProviderFailure):
            Tavily.decode_extract({"http_status": 432})
        for raw in (
            {"http_status": 200, "data": {}},
            {"http_status": 200, "data": {"results": [None]}},
        ):
            with self.assertRaises(ValueError):
                Tavily.decode_extract(raw)
