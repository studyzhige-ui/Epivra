"""External bytes, immutable receipts, and public observations share one contract."""
import base64
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from epivra.adapters import DeepSeek, IncompleteStream, JsonAPI
from epivra.harness import Harness
from epivra.storage import Store
from epivra.web_providers import connect


class ProviderContractTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "state.db"
        self.store = Store(self.path)
        control = self.store.create("s", "test", {})
        plan = self.store.put("s", "plan", {"text": "test"}, (control.direction,))
        control = self.store.command("s", "approve", control.ref, "approve", {"plan": plan.ref})
        self.work = self.store.work("s", control.ref, "lead", "test")
        self.epoch = control.epoch

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    async def test_nonfinite_response_settles_and_replays_after_process_restart(self):
        requests = []
        def respond(request):
            requests.append(request)
            return httpx.Response(200, content=b'{"value":1e999}')
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            model = DeepSeek(JsonAPI("https://fixture.test", "fixture", client), stream=False)
            harness = Harness(self.store, model)
            with patch.object(harness, "_done", side_effect=RuntimeError("crash after receipt")):
                with self.assertRaisesRegex(RuntimeError, "crash after receipt"):
                    await harness.step("s", self.work.ref)
            self.store.close()
            self.store = Store(self.path)
            harness = Harness(self.store, model)
            self.assertEqual("continue", await harness.step("s", self.work.ref))
            self.assertEqual(1, len(requests))
            receipt = self.store.db.execute("SELECT status,result FROM operations").fetchone()
            self.assertEqual("succeeded", receipt["status"])
            saved = json.loads(receipt["result"])
            self.assertTrue(saved["malformed_json"])
            self.assertEqual(b'{"value":1e999}', base64.b64decode(saved["raw_response"]["data"]))
            observation = self.store.list("s", "observation")[-1].body
            self.assertIn("error", observation)
            self.assertNotIn("1e999", json.dumps(observation))
            self.assertNotIn("raw_response", json.dumps(observation))

    async def test_bad_stream_numbers_require_completion_before_settlement(self):
        for value in ("NaN", "Infinity", "-Infinity", "1e999"):
            for completed in (False, True):
                with self.subTest(value=value, completed=completed):
                    body = 'data: {"usage":{"total_tokens":' + value + '}}\n\n'
                    if completed:
                        body += "data: [DONE]\n\n"
                    async with httpx.AsyncClient(transport=httpx.MockTransport(
                        lambda request: httpx.Response(200, content=body.encode())
                    )) as client:
                        api = JsonAPI("https://fixture.test", "fixture", client)
                        if completed:
                            result = await api.chat_stream("/", {})
                            self.assertEqual({"http_status": 200, "malformed_json": True,
                                              "invalid_events": ['{"usage":{"total_tokens":' + value + '}}']}, result)
                            json.dumps(result, allow_nan=False)
                        else:
                            with self.assertRaises(IncompleteStream):
                                await api.chat_stream("/", {})

    async def test_completed_bad_stream_preserves_private_event_on_restart(self):
        event = '{"private_fixture":"receipt-only", "value":NaN}'
        requests = []

        def respond(request):
            requests.append(request)
            return httpx.Response(200, content=("data: " + event + "\n\ndata: [DONE]\n\n").encode())

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            model = DeepSeek(JsonAPI("https://fixture.test", "fixture", client), stream=True)
            harness = Harness(self.store, model)
            with patch.object(harness, "_done", side_effect=RuntimeError("crash after receipt")):
                with self.assertRaisesRegex(RuntimeError, "crash after receipt"):
                    await harness.step("s", self.work.ref)
            self.store.close()
            self.store = Store(self.path)
            self.assertEqual("continue", await Harness(self.store, model).step("s", self.work.ref))
            self.assertEqual(1, len(requests))
            receipt = self.store.db.execute("SELECT status,result FROM operations").fetchone()
            self.assertEqual("succeeded", receipt["status"])
            self.assertEqual([event], json.loads(receipt["result"])["invalid_events"])
            for observation in self.store.list("s", "observation"):
                self.assertNotIn("receipt-only", json.dumps(observation.body))
                self.assertNotIn("invalid_events", json.dumps(observation.body))

    async def test_mixed_search_receipt_preserves_successful_observation(self):
        for name in ("exa", "tavily"):
            with self.subTest(provider=name):
                items = [
                    {"url": "https://example.com/a", "title": "bad\ud800"},
                    {"url": "https://example.com/a", "title": "Valid", "content": "Evidence"},
                    {"url": "https://example.com/b", "title": "bad\udfff"},
                ]
                raw = {"http_status": 200, "data": {"results": items}}
                self.store.admit("s", self.work.ref, self.epoch, name, {"query": "test"})
                self.store.mark_invoked(name, 1)
                self.store.settle(name, raw)
                self.store.close()
                self.store = Store(self.path)
                replay = self.store.admit("s", self.work.ref, self.epoch, name, {"query": "test"})
                self.assertEqual(raw, replay)
                async with httpx.AsyncClient() as client:
                    provider = connect(name, {name.upper() + "_API_KEY": "fixture"}, client)
                    decoded = provider.decode_search(replay)
                observation = self.store.observation("s", self.work.ref, self.epoch, {"result": decoded})
                saved = self.store.get("s", observation.ref).body["result"]
                self.assertEqual(["Valid"], [r["title"] for r in saved["results"]])
                self.assertEqual([0, 2], [r["index"] for r in saved["failures"]])
