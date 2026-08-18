from __future__ import annotations

import unittest

import httpx

from deep_research_agent.providers.academic import (
    ArxivSearchProvider,
    CrossrefSearchProvider,
    PubMedSearchProvider,
)
from deep_research_agent.providers.web import DuckDuckGoSearchProvider

ARXIV_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2601.01234v2</id>
    <title>A Method
      For Something</title>
    <summary>We describe an approach and its limits.</summary>
    <published>2026-01-15T00:00:00Z</published>
    <author><name>Ada Lovelace</name></author>
    <author><name>Alan Turing</name></author>
  </entry>
</feed>
"""


def mock_client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


class ArxivTest(unittest.IsolatedAsyncioTestCase):
    async def test_atom_entries_become_leads_with_preprint_context(self) -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual("export.arxiv.org", request.url.host)
            self.assertEqual("all:rsv", request.url.params["search_query"])
            return httpx.Response(200, text=ARXIV_FEED)

        client = mock_client(handler)
        try:
            results = await ArxivSearchProvider(client=client).search(
                query="rsv", intent="primary literature", source_kind="web"
            )
        finally:
            await client.aclose()

        self.assertEqual("A Method For Something", results[0].title)
        self.assertEqual("http://arxiv.org/abs/2601.01234v2", results[0].url)
        self.assertIn("Ada Lovelace, Alan Turing", results[0].snippet)
        # The preprint boundary must be visible before a Curator relies on it.
        self.assertIn("arXiv preprint, 2026-01-15", results[0].snippet)
        self.assertEqual("", results[0].content)

    async def test_needs_no_credential(self) -> None:
        info = await ArxivSearchProvider().describe()
        self.assertIn("keyless", info.capabilities)
        self.assertIn("academic", info.capabilities)

    async def test_malformed_xml_is_a_transparent_failure(self) -> None:
        async def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text="<feed><broken>")

        client = mock_client(handler)
        try:
            with self.assertRaises(Exception) as caught:
                await ArxivSearchProvider(client=client).search(
                    query="q", intent="i", source_kind="web"
                )
            self.assertIn("arxiv", str(caught.exception))
        finally:
            await client.aclose()


class CrossrefTest(unittest.IsolatedAsyncioTestCase):
    async def test_doi_metadata_including_retraction_notices_is_surfaced(self) -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual("api.crossref.org", request.url.host)
            return httpx.Response(
                200,
                json={
                    "message": {
                        "items": [
                            {
                                "DOI": "10.1000/example",
                                "title": ["A Trial Report"],
                                "container-title": ["The Lancet"],
                                "issued": {"date-parts": [[2025, 4]]},
                                "type": "journal-article",
                                "author": [{"given": "Jo", "family": "Smith"}],
                                "update-to": [{"type": "retraction"}],
                            }
                        ]
                    }
                },
            )

        client = mock_client(handler)
        try:
            results = await CrossrefSearchProvider(client=client).search(
                query="trial", intent="version of record", source_kind="web"
            )
        finally:
            await client.aclose()

        self.assertEqual("A Trial Report", results[0].title)
        self.assertEqual("https://doi.org/10.1000/example", results[0].url)
        self.assertIn("The Lancet 2025", results[0].snippet)
        # A retraction that a web snippet would never mention.
        self.assertIn("update notice: retraction", results[0].snippet)

    async def test_the_polite_pool_is_used_when_a_contact_is_configured(self) -> None:
        seen: dict[str, str] = {}

        async def handler(request: httpx.Request) -> httpx.Response:
            seen.update(dict(request.url.params))
            return httpx.Response(200, json={"message": {"items": []}})

        client = mock_client(handler)
        try:
            await CrossrefSearchProvider(
                client=client, mailto="user@example.test"
            ).search(query="q", intent="i", source_kind="web")
        finally:
            await client.aclose()

        self.assertEqual("user@example.test", seen["mailto"])


class PubMedTest(unittest.IsolatedAsyncioTestCase):
    async def test_esearch_and_esummary_are_combined_into_citable_leads(self) -> None:
        calls: list[str] = []

        async def handler(request: httpx.Request) -> httpx.Response:
            calls.append(request.url.path)
            if request.url.path.endswith("esearch.fcgi"):
                return httpx.Response(
                    200, json={"esearchresult": {"idlist": ["40000001"]}}
                )
            return httpx.Response(
                200,
                json={
                    "result": {
                        "40000001": {
                            "title": "Maternal vaccination and infant outcomes",
                            "source": "N Engl J Med",
                            "pubdate": "2025 Mar 12",
                            "authors": [{"name": "Smith J"}],
                            "pubtype": ["Randomized Controlled Trial"],
                        }
                    }
                },
            )

        client = mock_client(handler)
        try:
            results = await PubMedSearchProvider(client=client).search(
                query="rsv maternal", intent="pivotal trials", source_kind="web"
            )
        finally:
            await client.aclose()

        self.assertEqual(2, len(calls))
        self.assertEqual(
            "https://pubmed.ncbi.nlm.nih.gov/40000001/", results[0].url
        )
        self.assertIn("N Engl J Med 2025 Mar 12", results[0].snippet)
        self.assertIn("Randomized Controlled Trial", results[0].snippet)

    async def test_no_matches_skips_the_second_call(self) -> None:
        calls: list[str] = []

        async def handler(request: httpx.Request) -> httpx.Response:
            calls.append(request.url.path)
            return httpx.Response(200, json={"esearchresult": {"idlist": []}})

        client = mock_client(handler)
        try:
            results = await PubMedSearchProvider(client=client).search(
                query="nothing", intent="i", source_kind="web"
            )
        finally:
            await client.aclose()

        self.assertEqual((), results)
        self.assertEqual(1, len(calls))

    async def test_an_api_key_is_optional_and_never_shown(self) -> None:
        provider = PubMedSearchProvider(api_key="ncbi-secret")
        self.assertNotIn("ncbi-secret", repr(provider))


class SnippetContractTest(unittest.IsolatedAsyncioTestCase):
    async def test_no_discovery_provider_claims_to_return_source_text(self) -> None:
        """Snippets are leads; only a read can produce anchorable evidence."""

        async def handler(request: httpx.Request) -> httpx.Response:
            if "arxiv" in str(request.url.host):
                return httpx.Response(200, text=ARXIV_FEED)
            if "crossref" in str(request.url.host):
                return httpx.Response(
                    200,
                    json={
                        "message": {
                            "items": [
                                {"DOI": "10.1/x", "title": ["T"], "URL": "https://d.test/x"}
                            ]
                        }
                    },
                )
            return httpx.Response(
                200,
                text='<a class="result__a" href="https://x.test/a">T</a>'
                '<a class="result__snippet">S</a>',
            )

        client = mock_client(handler)
        try:
            for provider in (
                ArxivSearchProvider(client=client),
                CrossrefSearchProvider(client=client),
                DuckDuckGoSearchProvider(client=client),
            ):
                results = await provider.search(
                    query="q", intent="i", source_kind="web"
                )
                for result in results:
                    with self.subTest(provider=provider.provider_id):
                        self.assertEqual("", result.content)
        finally:
            await client.aclose()


if __name__ == "__main__":
    unittest.main()
