import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import httpx

from epivra.application import online_service
from epivra.domain import Call, Reply
from epivra.public_sources import TOOLS, PublicSource, request
from epivra.scheduling import Scheduler
from epivra.storage import Store
from epivra.web_providers import connect


class PublicTests(unittest.IsolatedAsyncioTestCase):
    async def test_pubmed_mixed_records_preserve_success_and_contact(self):
        xml = "<PubmedArticleSet><ERROR>Missing record</ERROR><PubmedArticle><MedlineCitation><PMID>123</PMID><Article><ArticleTitle>Valid</ArticleTitle><Abstract><AbstractText>Evidence</AbstractText></Abstract></Article></MedlineCitation></PubmedArticle></PubmedArticleSet>"
        requests = []
        def handle(request):
            requests.append(request)
            return httpx.Response(200, text=xml)
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            provider = PublicSource("pubmed", client)
            with patch.dict("os.environ", {"EPIVRA_CONTACT_EMAIL": "research@example.org"}):
                raw = await provider.invoke("read_pubmed", {"ids": ["123", "456"]})
            result = provider.decode(raw)
        self.assertEqual("research@example.org", requests[0].url.params["email"])
        self.assertEqual("123", result["records"][0]["pmid"])
        self.assertEqual(1, len(result["failures"]))
        self.assertIn("Missing record", result["sources"][0]["text"])

    async def test_http_contracts_and_record_identity(self):
        fixtures = {
            "search_crossref": (
                {
                    "query": "optical",
                    "start_date": "2024-01-01",
                    "end_date": "2025-12-31",
                },
                {
                    "status": "ok",
                    "message": {
                        "total-results": 1,
                        "items": [{"DOI": "10.1/x", "title": ["A"]}],
                    },
                },
                "/works",
                "query.bibliographic",
            ),
            "search_pubmed": (
                {"query": "diabetes[MeSH Terms]"},
                {"esearchresult": {"count": "1", "idlist": ["123"]}},
                "/entrez/eutils/esearch.fcgi",
                "term",
            ),
            "read_pubmed": (
                {"ids": ["123"]},
                "<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>123</PMID><Article><Abstract><AbstractText>Original abstract</AbstractText></Abstract></Article></MedlineCitation></PubmedArticle></PubmedArticleSet>",
                "/entrez/eutils/efetch.fcgi",
                "id",
            ),
            "search_europe_pmc": (
                {"query": "diabetes", "cursor": "cursor+="},
                {
                    "hitCount": 1,
                    "nextCursorMark": "next",
                    "resultList": {
                        "result": [
                            {
                                "id": "123",
                                "source": "MED",
                                "abstractText": "Original abstract",
                            }
                        ]
                    },
                },
                "/europepmc/webservices/rest/search",
                "query",
            ),
            "world_bank_indicators": (
                {"indicator": "SP.POP.TOTL"},
                [
                    {"page": 1, "pages": 1},
                    [
                        {
                            "id": "SP.POP.TOTL",
                            "unit": "people",
                            "sourceNote": "Definition",
                        }
                    ],
                ],
                "/v2/indicator/SP.POP.TOTL",
                "page",
            ),
            "query_world_bank": (
                {
                    "indicator": "SP.POP.TOTL",
                    "country": "CHN",
                    "start_year": 2023,
                    "end_year": 2024,
                },
                [
                    {"page": 1, "pages": 1, "lastupdated": "2025-01-01"},
                    [{"date": "2023", "value": None, "unit": ""}],
                ],
                "/v2/country/CHN/indicator/SP.POP.TOTL",
                "date",
            ),
        }
        for tool, (args, body, path, parameter) in fixtures.items():
            with self.subTest(tool=tool):
                calls = []

                def respond(req):
                    calls.append(req)
                    self.assertNotIn("authorization", req.headers)
                    return (
                        httpx.Response(200, text=body)
                        if isinstance(body, str)
                        else httpx.Response(
                            200,
                            json=body,
                            headers={
                                "x-rate-limit-limit": "1",
                                "x-rate-limit-interval": "1s",
                            },
                        )
                    )

                async with httpx.AsyncClient(
                    transport=httpx.MockTransport(respond)
                ) as client:
                    p = PublicSource(TOOLS[tool][0], client)
                    raw = await p.invoke(tool, args)
                    decoded = p.decode(raw)
                self.assertEqual(len(calls), 1)
                self.assertEqual(calls[0].url.path, path)
                self.assertIn(parameter, calls[0].url.params)
                source = decoded["sources"][0]
                self.assertEqual(source["origin"], raw["origin"])
                if isinstance(body, str):
                    self.assertEqual(source["text"], body)
                else:
                    self.assertEqual(json.loads(source["text"]), body)
                if tool == "search_crossref":
                    self.assertEqual(
                        calls[0].url.params["filter"],
                        "from-pub-date:2024-01-01,until-pub-date:2025-12-31",
                    )
                if tool == "query_world_bank":
                    self.assertIsNone(decoded["records"][0]["value"])
                    self.assertEqual(decoded["content_type"], "structured_data")

    async def test_invalid_args_make_no_request_and_filters_are_not_ignored(self):
        for tool, args in [
            (
                "search_crossref",
                {"query": "a", "start_date": "2025-03-01", "end_date": "2024-01-01"},
            ),
            ("search_pubmed", {"query": "a", "start_date": "2025-01-01"}),
            ("search_pubmed", {"query": "a", "offset": 10000}),
            ("read_pubmed", {"ids": ["../bad"]}),
            (
                "query_world_bank",
                {
                    "indicator": "a/b",
                    "country": "all",
                    "start_year": 2023,
                    "end_year": 2024,
                },
            ),
            ("world_bank_indicators", {"query": "population"}),
        ]:
            with self.subTest(tool=tool), self.assertRaises(ValueError):
                request(tool, args)
        sent = []
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda r: sent.append(r) or httpx.Response(200, json={"results": []})
            )
        ) as client:
            p = connect("tavily", {"TAVILY_API_KEY": "test"}, client)
            await p.search(
                {
                    "query": "a",
                    "include_domains": ["example.org"],
                    "start_date": "2025-01-01",
                }
            )
            self.assertEqual(
                json.loads(sent[0].content)["include_domains"], ["example.org"]
            )
            with self.assertRaises(ValueError):
                await connect("exa", {"EXA_API_KEY": "test"}, client).search(
                    {"query": "a", "start_date": "2025-01-01"}
                )
            self.assertEqual(len(sent), 1)

    async def test_live_assembly_saves_sources_and_keeps_plan_without_manual_input(
        self,
    ):
        class Model:
            identity = "fixture"

            async def complete(self, req):
                return Reply(
                    "",
                    (
                        Call(
                            "query_world_bank",
                            {
                                "indicator": "SP.POP.TOTL",
                                "country": "CHN",
                                "start_year": 2023,
                                "end_year": 2023,
                            },
                        ),
                    ),
                ).to_json()

        class API:
            async def close(self):
                pass

        with tempfile.TemporaryDirectory() as folder:
            s = Store(Path(folder) / "test.db")
            c = s.create(
                "s",
                "Compare population",
                {
                    "network": True,
                    "public_sources": True,
                    "search_providers": [],
                    "reader_providers": [],
                },
            )
            plan = s.put(
                "s",
                "plan",
                {"text": "Original approved purpose and format", "brief": {}},
                (c.direction,),
            )
            c = s.command("s", "approve", c.ref, "approve", {"plan": plan.ref})
            owner = s.work("s", c.ref, "lead", "Own research", (plan.ref,))
            work = s.work("s", c.ref, "investigator", "Find evidence", (), owner.ref)
            with patch("epivra.models.create_model", return_value=(Model(), API())):
                service, clients = online_service(s, "s", {})
            try:
                req = service.harness._request("s", work)
                self.assertTrue(set(TOOLS) <= req["tools"].keys())
                self.assertEqual(
                    date.fromisoformat(req["current_date"]).year, date.today().year
                )
                self.assertTrue(any(x.get("body") == plan.body for x in req["context"]))
                body = [{"page": 1, "pages": 1}, [{"value": None, "date": "2023"}]]

                async def invoke(self, tool, args):
                    return {
                        "http_status": 200,
                        "data": body,
                        "provider": "world_bank",
                        "tool": tool,
                        "origin": "https://api.worldbank.org/v2/test",
                        "retrieved_at": "2026-01-01",
                    }

                with patch.object(PublicSource, "invoke", invoke):
                    await service.harness.step("s", work.ref)
                sources = s.list("s", "source")
                self.assertEqual(len(sources), 1)
                self.assertEqual(json.loads(sources[0].body["text"]), body)
                self.assertEqual(sources[0].body["content_type"], "structured_data")
                result = s.put(
                    "s",
                    "work_result",
                    {
                        "text": "Original findings",
                        "refs": [sources[0].ref],
                        "producer": work.ref,
                    },
                    (work.ref, sources[0].ref),
                )
                writer = s.work("s", c.ref, "writer", "Write", (result.ref,), owner.ref)
                self.assertIn(
                    "read_writing_guide", service.harness._request("s", writer)["tools"]
                )
                self.assertIn("read_writing_guide", req["tools"])
            finally:
                await service.close()
                for client in clients:
                    await client.close()
                s.close()

    def test_spacing_is_shared_and_tightens(self):
        clock = [10.0]
        scheduler = Scheduler(clock=lambda: clock[0])
        scheduler.constrain("public:crossref", 1)
        scheduler.history["public:crossref"] = [(10, 0)]
        self.assertEqual(scheduler.rate_delay("public:crossref", 0), 1)
        scheduler.constrain("public:crossref", 2)
        scheduler.constrain("public:crossref", 0.5)
        self.assertEqual(scheduler.rate_delay("public:crossref", 0), 2)

    async def test_http_200_error_payload_is_not_evidence(self):
        for name, tool, data in [
            (
                "world_bank",
                "query_world_bank",
                [{"message": [{"id": "120", "value": "bad indicator"}]}],
            ),
            (
                "pubmed",
                "search_pubmed",
                {"esearchresult": {"errorlist": {"phrasesnotfound": ["bad"]}}},
            ),
            ("pubmed", "search_pubmed", {"esearchresult": []}),
        ]:
            async with httpx.AsyncClient() as client:
                with self.assertRaises((ValueError, KeyError)):
                    PublicSource(name, client).decode(
                        {"http_status": 200, "tool": tool, "data": data}
                    )
