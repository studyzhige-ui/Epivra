import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from epivra.application import ResearchService, online_service
from epivra.domain import Call, Reply, UnknownOutcome
from epivra.harness import Harness
from epivra.storage import Store
from epivra.web_providers import connect
from tools.run_benchmark10 import run, run_status, snapshot


class BatchTests(unittest.IsolatedAsyncioTestCase):
    async def test_round_robin_concurrent_and_exhaustion(self):
        seen = []

        async def handler(request):
            seen.append(request.headers["Authorization"])
            await asyncio.sleep(0)
            return httpx.Response(432)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = connect(
                "tavily", {"TAVILY_API_KEY": "one,two,one,three"}, client
            )
            raw = await asyncio.gather(
                *(provider.search({"query": "test"}) for _ in range(3))
            )
            self.assertEqual(seen, ["Bearer one", "Bearer two", "Bearer three"])
            self.assertFalse(raw[-1]["credential_retry"])
            await provider.search({"query": "test"})
            self.assertEqual(len(seen), 3)
            provider.api.replace_key("replacement")
            await provider.search({"query": "test"})
            self.assertEqual(seen[-1], "Bearer replacement")

    async def test_production_tool_ledger_retries_quota_but_never_unknown(self):
        for unknown in (False, True):
            seen = []

            def handler(request):
                seen.append(request.headers["Authorization"])
                if unknown:
                    raise httpx.ReadTimeout("unknown")
                return httpx.Response(
                    432 if len(seen) == 1 else 200, json={"results": []}
                )

            class Model:
                identity = "fixture"

                async def complete(self, request):
                    return Reply("", (Call("web_search", {"query": "test"}),)).to_json()

            with tempfile.TemporaryDirectory() as temp:
                store = Store(Path(temp) / "research.db")
                c = store.create("s", "Question", {"network": True})
                plan = store.put("s", "plan", {"text": "Plan"}, (c.direction,))
                c = store.command("s", "approve", c.ref, "approve", {"plan": plan.ref})
                work = store.work("s", c.ref, "investigator", "Investigate")
                async with httpx.AsyncClient(
                    transport=httpx.MockTransport(handler)
                ) as client:
                    with patch(
                        "epivra.web_providers.connect",
                        side_effect=lambda n, k: connect(n, k, client),
                    ):
                        service, clients = online_service(
                            store,
                            "s",
                            {
                                "TAVILY_API_KEY": "one,two",
                                "DEEPSEEK_API_KEY": "fixture",
                            },
                        )
                    service.harness.model = Model()
                    if unknown:
                        with self.assertRaises(httpx.ReadTimeout):
                            await service.harness.step("s", work.ref)
                        with self.assertRaises(UnknownOutcome):
                            await service.harness.step("s", work.ref)
                        self.assertEqual(len(seen), 1)
                    else:
                        await service.harness.step("s", work.ref)
                        await service.harness.step("s", work.ref)
                        self.assertEqual(len(store.list("s", "retry")), 1)
                        self.assertNotIn("Bearer", json.dumps(store.usage_records("s")))
                    await service.close()
                    for api in clients:
                        await api.close()
                store.close()

    async def test_metrics_keep_unknown_separate_and_export_original_results(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            store = Store(folder / "research.db")
            c = store.create("s", "Original question", {})
            work = store.work("s", c.ref, "lead", "Plan")
            store.admit("s", work.ref, c.epoch, "unknown-call", {"test": True})
            result = snapshot(
                store, "s", folder, {"started_at": 1, "status": "blocked"}
            )
            self.assertEqual(result["unknown_operations"], 1)
            self.assertFalse(result["published"])
            self.assertFalse((folder / "report.md").exists())
            self.assertIn(
                "Original question",
                (folder / "artifacts.json").read_text(encoding="utf-8"),
            )
            store.close()

    @unittest.skipUnless(os.name == "nt", "batch runner uses Windows process locks")
    async def test_cancel_inflight_request_keeps_unknown_and_does_not_start_next_case(
        self,
    ):
        entered = asyncio.Event()
        calls = []

        async def handler(request):
            calls.append(request.url.path)
            entered.set()
            await asyncio.Event().wait()
            return httpx.Response(200, json={})

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            queries = root / "cases.jsonl"
            queries.write_text(
                "\n".join(json.dumps({"id": i, "prompt": "Question"}) for i in (2, 7)),
                encoding="utf8",
            )
            async with httpx.AsyncClient(
                transport=httpx.MockTransport(handler)
            ) as client:

                class Model:
                    identity = "cancel-fixture"

                    async def complete(self, request):
                        return (await client.post("https://example.test/model")).json()

                def service(store, study, keys, scheduler):
                    return ResearchService(store, Harness(store, Model())), []

                with (
                    patch("tools.run_benchmark10.online_service", side_effect=service),
                    patch(
                        "tools.run_benchmark10.credentials",
                        return_value={"TAVILY_API_KEY": "fixture"},
                    ),
                ):
                    task = asyncio.create_task(
                        run(root, "cancel-fixture", queries=queries)
                    )
                    await asyncio.wait_for(entered.wait(), 5)
                    task.cancel()
                    with self.assertRaises(asyncio.CancelledError):
                        await task
            folder = root / ".epivra/cancel-fixture"
            state = run_status(folder)
            self.assertFalse(state["alive"])
            self.assertFalse(state["complete"])
            self.assertEqual("interrupted", state["cases"][0]["status"])
            self.assertEqual([7], state["queued_case_ids"])
            store = Store(folder / "research.db")
            try:
                self.assertEqual(1, len(store.unsettled("cancel-fixture-case-02")))
                self.assertEqual([], store.list("cancel-fixture-case-07", "direction"))
            finally:
                store.close()
            self.assertEqual(["/model"], calls)
