import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import httpx

from epivra.application import online_service
from epivra.domain import Call, Reply
from epivra.storage import Store
from epivra.web_providers import connect


class WebIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_malformed_nested_payload_reaches_alternative_observation(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder) / "state.db")
            async with httpx.AsyncClient() as client:
                store.create(
                    "s",
                    "Research",
                    {
                        "network": True,
                        "search_providers": ["brave", "bocha", "duckduckgo"],
                        "reader_providers": [],
                    },
                )
                with (
                    patch(
                        "epivra.models.create_model",
                        return_value=(SimpleNamespace(context_tokens=49024, max_tokens=1024), client),
                    ),
                    patch(
                        "epivra.web_providers.connect",
                        side_effect=lambda name, keys: connect(name, keys, client),
                    ),
                ):
                    service, _ = online_service(
                        store,
                        "s",
                        {"BRAVE_API_KEY": "fixture", "BOCHA_API_KEY": "fixture", "DEEPSEEK_API_KEY": "fixture"},
                    )
                try:
                    for name, data in [
                        ("brave", {"web": None}),
                        ("bocha", {"code": 200, "data": None}),
                    ]:
                        result = service.harness.tools["web_search"].observe(
                            {"provider": name, "http_status": 200, "data": data}, {}
                        )
                        self.assertEqual("source_provider_failed", result["error"])
                        self.assertIn("duckduckgo", result["alternatives"])
                finally:
                    await service.close()
                    store.close()

    async def test_failure_alternative_cooldown_reader_reuse_and_real_accounting(self):
        requests = []

        def respond(request):
            requests.append(request)
            if request.url.host == "api.tavily.com":
                return httpx.Response(429, headers={"Retry-After": "30"}, json={})
            if request.url.host == "html.duckduckgo.com":
                return httpx.Response(
                    200,
                    text='<a class="result__a" href="https://example.com/p">Evidence</a>',
                )
            return httpx.Response(
                200,
                json={
                    "code": 200,
                    "data": {
                        "url": "https://example.com/p",
                        "content": "Original evidence",
                    },
                },
            )

        calls = iter(
            [
                Call("web_search", {"query": "question"}),
                Call("web_search", {"query": "question", "provider": "duckduckgo"}),
                Call("fetch_web", {"url": "https://example.com/p"}),
                Call("fetch_web", {"url": "https://example.com/p"}),
                Call(
                    "fetch_web", {"url": "https://example.com/p", "force_refresh": True}
                ),
            ]
        )

        class Model:
            context_tokens = 49024
            max_tokens = 1024
            identity = "fixture"

            async def complete(self, request):
                return Reply("", (next(calls),)).to_json()

        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder) / "state.db")
            async with httpx.AsyncClient(
                transport=httpx.MockTransport(respond)
            ) as client:
                c = store.create(
                    "s",
                    "Research",
                    {
                        "network": True,
                        "search_providers": ["tavily", "duckduckgo"],
                        "reader_providers": ["jina"],
                    },
                )
                plan = store.put("s", "plan", {"text": "plan"}, (c.direction,))
                c = store.command("s", "approve", c.ref, "approve", {"plan": plan.ref})
                work = store.work("s", c.ref, "investigator", "Investigate")
                with (
                    patch(
                        "epivra.models.create_model",
                        return_value=(Model(), client),
                    ),
                    patch(
                        "epivra.web_providers.connect",
                        side_effect=lambda name, keys: connect(name, keys, client),
                    ),
                ):
                    service, _ = online_service(
                        store, "s", {"TAVILY_API_KEY": "fixture", "DEEPSEEK_API_KEY": "fixture"}
                    )
                try:
                    for _ in range(5):
                        await service.harness.step("s", work.ref)
                    observations = [
                        a.body["result"] for a in store.list("s", "observation")
                    ]
                    self.assertEqual(["duckduckgo"], observations[0]["alternatives"])
                    self.assertEqual(
                        "https://example.com/p", observations[1]["results"][0]["url"]
                    )
                    self.assertEqual(observations[2], observations[3])
                    self.assertEqual(4, len(requests))
                    self.assertEqual(2, len(store.list("s", "source")))
                    self.assertEqual(1, len(store.list("s", "cooldown")))
                    resources = [a["resource"] for a in store.admissions()]
                    self.assertEqual(1, resources.count("tavily"))
                    self.assertEqual(1, resources.count("duckduckgo"))
                    self.assertEqual(2, resources.count("jina"))
                    self.assertEqual(9, len(store.usage_records("s")))
                finally:
                    await service.close()
                    store.close()
