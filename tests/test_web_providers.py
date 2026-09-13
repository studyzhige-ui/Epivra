import json
import unittest

import httpx

from epivra.web_providers import CONNECTIONS, SEARCH, connect


class WebProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def test_six_search_requests_and_original_result_shapes(self):
        fixtures = {
            "tavily": {
                "results": [
                    {
                        "url": "https://example.com/p",
                        "title": "Title",
                        "content": "snippet",
                    }
                ]
            },
            "exa": {
                "results": [
                    {
                        "url": "https://example.com/p",
                        "title": "Title",
                        "highlights": ["snippet"],
                    }
                ]
            },
            "brave": {
                "web": {
                    "results": [
                        {
                            "url": "https://example.com/p",
                            "title": "Title",
                            "description": "snippet",
                        }
                    ]
                }
            },
            "perplexity": {
                "results": [
                    {
                        "url": "https://example.com/p",
                        "title": "Title",
                        "snippet": "snippet",
                    }
                ]
            },
            "bocha": {
                "code": 200,
                "data": {
                    "webPages": {
                        "value": [
                            {
                                "url": "https://example.com/p",
                                "name": "Title",
                                "snippet": "snippet",
                            }
                        ]
                    }
                },
            },
        }
        html = '<div class="result"><a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fp">Title</a><a class="result__snippet">snippet</a></div>'
        paths = {
            "tavily": "/search",
            "exa": "/search",
            "brave": "/res/v1/web/search",
            "perplexity": "/search",
            "bocha": "/v1/web-search",
            "duckduckgo": "/html/",
        }
        for name in SEARCH:
            with self.subTest(provider=name):
                requests = []

                def respond(request):
                    requests.append(request)
                    return (
                        httpx.Response(200, text=html)
                        if name == "duckduckgo"
                        else httpx.Response(200, json=fixtures[name])
                    )

                async with httpx.AsyncClient(
                    transport=httpx.MockTransport(respond)
                ) as client:
                    provider = connect(
                        name, {CONNECTIONS[name][1]: "fixture-key"}, client
                    )
                    raw = await provider.search({"query": "中文研究"})
                    result = provider.decode_search(raw)["results"][0]
                    self.assertEqual(
                        ("https://example.com/p", "snippet", "search_snippet"),
                        (result["url"], result["snippet"], result["content_type"]),
                    )
                    self.assertEqual(paths[name], requests[0].url.path)
                    if name in {"brave", "duckduckgo"}:
                        self.assertEqual("中文研究", requests[0].url.params["q"])
                    else:
                        self.assertEqual(
                            "中文研究", json.loads(requests[0].content)["query"]
                        )
                    if name != "duckduckgo":
                        self.assertEqual(
                            CONNECTIONS[name][3] + "fixture-key",
                            requests[0].headers[CONNECTIONS[name][2]],
                        )
                    self.assertEqual(1, len(requests))

    async def test_three_readers_preserve_content_url_and_acquisition_time(self):
        for name, body in {
            "tavily": {
                "results": [{"url": "https://example.com/p", "raw_content": "原件正文"}]
            },
            "exa": {"results": [{"url": "https://example.com/p", "text": "原件正文"}]},
            "jina": {
                "code": 200,
                "data": {"url": "https://example.com/p", "content": "原件正文"},
            },
        }.items():
            with self.subTest(provider=name):
                requests = []

                def respond(request):
                    requests.append(request)
                    return httpx.Response(200, json=body)

                async with httpx.AsyncClient(
                    transport=httpx.MockTransport(respond)
                ) as client:
                    provider = connect(name, {CONNECTIONS[name][1]: "fixture"}, client)
                    raw = await provider.extract({"url": "https://example.com/p"})
                    source = provider.decode_extract(raw)["sources"][0]
                    self.assertEqual("原件正文", source["text"])
                    self.assertEqual(
                        "https://example.com/p", source["segments"][0]["locator"]["url"]
                    )
                    self.assertEqual(raw["retrieved_at"], source["retrieved_at"])
                    self.assertEqual(1, len(requests))
                    self.assertEqual("POST", requests[0].method)
                    self.assertEqual(
                        {"tavily": "/extract", "exa": "/contents", "jina": "/"}[name],
                        requests[0].url.path,
                    )
                    payload = json.loads(requests[0].content)
                    if name == "exa":
                        self.assertEqual(
                            {"ids": ["https://example.com/p"], "text": True}, payload
                        )
                    elif name == "jina":
                        self.assertEqual({"url": "https://example.com/p"}, payload)
                        self.assertEqual(
                            "application/json", requests[0].headers["accept"]
                        )
                    else:
                        self.assertEqual(["https://example.com/p"], payload["urls"])

    async def test_malformed_provider_envelopes_are_protocol_errors(self):
        async with httpx.AsyncClient() as client:
            for name, body in [
                ("brave", {"web": None}),
                ("bocha", {"code": 200, "data": None}),
                ("bocha", {"data": {"webPages": None}}),
            ]:
                provider = connect(name, {CONNECTIONS[name][1]: "fixture"}, client)
                with self.subTest(provider=name), self.assertRaises(ValueError):
                    provider.decode_search({"http_status": 200, "data": body})

    async def test_anonymous_jina_no_empty_bearer_and_private_url_rejected(self):
        requests = []

        def respond(request):
            requests.append(request)
            return httpx.Response(200, json={"code": 200, "data": {"content": "text"}})

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            reader = connect("jina", {}, client)
            with self.assertRaises(ValueError):
                await reader.extract({"url": "http://127.0.0.1/private"})
            self.assertFalse(requests)
            await reader.extract({"url": "https://example.com"})
            self.assertNotIn("authorization", requests[0].headers)
            self.assertEqual("application/json", requests[0].headers["accept"])

    async def test_duck_challenge_and_reader_empty_content_are_not_evidence(self):
        async with httpx.AsyncClient() as client:
            ddg = connect("duckduckgo", {}, client)
            with self.assertRaises(ValueError):
                ddg.decode_search(
                    {"http_status": 200, "data": {"html": "Please solve CAPTCHA"}}
                )
            self.assertEqual(
                [],
                ddg.decode_search(
                    {
                        "http_status": 200,
                        "data": {"html": '<div class="no-results">No results</div>'},
                    }
                )["results"],
            )
            jina = connect("jina", {}, client)
            empty = jina.decode_extract(
                {
                    "http_status": 200,
                    "data": {"data": {"content": ""}},
                    "requested_url": "https://example.com",
                }
            )
            self.assertEqual([], empty["sources"])
            self.assertTrue(empty["failures"])
