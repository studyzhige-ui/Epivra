from __future__ import annotations

import json
import unittest
from unittest.mock import patch

import httpx

from deep_research_agent.providers import (
    DuckDuckGoSearchProvider,
    ProviderAuthError,
    ProviderUnavailableError,
    PublicHttpReader,
    PublicUrlPolicy,
    SourceReadError,
    TavilySearchProvider,
    UnsafeUrlError,
    _HttpResponse,
    configured_search_providers,
)


async def public_resolver(_hostname: str) -> tuple[str, ...]:
    return ("93.184.216.34",)


class StubReader(PublicHttpReader):
    def __init__(self, responses: list[_HttpResponse], **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.responses = responses
        self.fetch_calls = 0

    async def _fetch(self, _session: object, _url: str) -> _HttpResponse:
        self.fetch_calls += 1
        return self.responses.pop(0)


class TavilyProviderTest(unittest.IsolatedAsyncioTestCase):
    async def test_returns_provider_full_content_without_an_extra_read(self) -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual("Bearer secret", request.headers["Authorization"])
            payload = json.loads(request.content)
            self.assertEqual("markdown", payload["include_raw_content"])
            self.assertFalse(payload["include_answer"])
            self.assertEqual("general", payload["topic"])
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "title": "Official source",
                            "url": "https://example.test/report",
                            "content": "search summary",
                            "raw_content": "complete cleaned body",
                        }
                    ]
                },
            )

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            provider = TavilySearchProvider("secret", client=client)
            results = await provider.search(
                query="query", intent="news 新闻 official", source_kind="web"
            )
        finally:
            await client.aclose()

        self.assertEqual("complete cleaned body", results[0].content)
        self.assertEqual("search summary", results[0].snippet)

    async def test_auth_failure_does_not_include_response_body(self) -> None:
        async def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, text="secret upstream diagnostic")

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            provider = TavilySearchProvider("secret", client=client)
            with self.assertRaises(ProviderAuthError) as raised:
                await provider.search(
                    query="query", intent="general", source_kind="web"
                )
        finally:
            await client.aclose()

        self.assertNotIn("upstream diagnostic", str(raised.exception))
        self.assertNotIn("secret", repr(provider))


class DuckDuckGoProviderTest(unittest.IsolatedAsyncioTestCase):
    RESULT_HTML = """
    <div class="result results_links">
      <a class="result__a" href="/l/?uddg=https%3A%2F%2Fexample.test%2Freport">
        Official <b>report</b>
      </a>
      <a class="result__snippet">A discovery snippet, not source text.</a>
    </div>
    <div class="result results_links">
      <a class="result__a" href="https://direct.test/page">Direct link</a>
      <a class="result__snippet">Second snippet.</a>
    </div>
    """

    async def search(self, html: str, **kwargs: object) -> tuple[object, ...]:
        async def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual("https://html.duckduckgo.com/html/", str(request.url))
            self.assertNotIn("authorization", {k.lower() for k in request.headers})
            return httpx.Response(200, text=html)

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            provider = DuckDuckGoSearchProvider(client=client, **kwargs)  # type: ignore[arg-type]
            return tuple(
                await provider.search(
                    query="rsv prevention", intent="discovery", source_kind="web"
                )
            )
        finally:
            await client.aclose()

    async def test_redirect_wrapped_urls_are_unwrapped_to_their_target(self) -> None:
        results = await self.search(self.RESULT_HTML)

        self.assertEqual("https://example.test/report", results[0].url)
        self.assertEqual("Official report", results[0].title)
        self.assertEqual("https://direct.test/page", results[1].url)

    async def test_results_stay_discovery_snippets_and_never_claim_content(
        self,
    ) -> None:
        results = await self.search(self.RESULT_HTML)

        self.assertEqual("A discovery snippet, not source text.", results[0].snippet)
        for result in results:
            self.assertEqual("", result.content)

    async def test_result_count_is_bounded(self) -> None:
        results = await self.search(self.RESULT_HTML, max_results=1)
        self.assertEqual(1, len(results))

    async def test_needs_no_credential_and_reports_itself_as_fallback(self) -> None:
        info = await DuckDuckGoSearchProvider().describe()

        self.assertEqual("duckduckgo", info.provider_id)
        self.assertIn("keyless", info.capabilities)

    async def test_upstream_failure_is_a_transparent_provider_error(self) -> None:
        async def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(503)

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            provider = DuckDuckGoSearchProvider(client=client)
            with self.assertRaises(ProviderUnavailableError):
                await provider.search(
                    query="q", intent="discovery", source_kind="web"
                )
        finally:
            await client.aclose()


class ProviderConfigurationTest(unittest.TestCase):
    def test_the_keyless_fallback_is_always_available(self) -> None:
        with patch.dict("os.environ", {"TAVILY_API_KEY": ""}, clear=False):
            providers = configured_search_providers()

        self.assertEqual(1, len(providers))
        self.assertIsInstance(providers[0], DuckDuckGoSearchProvider)

    def test_a_configured_key_is_preferred_over_the_fallback(self) -> None:
        with patch.dict("os.environ", {"TAVILY_API_KEY": "tavily-secret"}, clear=False):
            providers = configured_search_providers()

        self.assertIsInstance(providers[0], TavilySearchProvider)
        self.assertIsInstance(providers[1], DuckDuckGoSearchProvider)
        self.assertNotIn("tavily-secret", repr(providers))


class PublicHttpReaderTest(unittest.IsolatedAsyncioTestCase):
    async def test_rejects_private_and_credentialed_urls(self) -> None:
        async def private_resolver(_hostname: str) -> tuple[str, ...]:
            return ("127.0.0.1",)

        private = PublicUrlPolicy(resolver=private_resolver)
        with self.assertRaises(UnsafeUrlError):
            await private.validate("http://internal.test/data")

        public = PublicUrlPolicy(resolver=public_resolver)
        with self.assertRaises(UnsafeUrlError):
            await public.validate("https://user:password@example.test/data")
        with self.assertRaises(UnsafeUrlError):
            await public.validate("https://example.test:8443/data")

    async def test_parses_public_html_and_drops_script_content(self) -> None:
        reader = StubReader(
            [
                _HttpResponse(
                    200,
                    {"content-type": "text/html; charset=utf-8"},
                    (
                        "<html><head><title>Report</title><script>bad()</script></head>"
                        "<body><h1>Finding</h1><p>Useful evidence.</p></body></html>"
                    ).encode(),
                    "utf-8",
                )
            ],
            policy=PublicUrlPolicy(resolver=public_resolver),
        )
        result = await reader.read("https://example.test/report")

        self.assertEqual("Report", result.title)
        self.assertIn("Useful evidence.", result.content)
        self.assertNotIn("bad()", result.content)

    async def test_redirect_destination_is_checked_before_following(self) -> None:
        async def split_resolver(hostname: str) -> tuple[str, ...]:
            return ("127.0.0.1",) if hostname == "private.test" else ("93.184.216.34",)

        reader = StubReader(
            [_HttpResponse(302, {"location": "http://private.test/secret"}, b"")],
            policy=PublicUrlPolicy(resolver=split_resolver),
        )
        with self.assertRaises(UnsafeUrlError):
            await reader.read("https://public.test/start")

        self.assertEqual(1, reader.fetch_calls)

    async def test_https_redirect_cannot_downgrade_to_http(self) -> None:
        reader = StubReader(
            [_HttpResponse(302, {"location": "http://public.test/plain"}, b"")],
            policy=PublicUrlPolicy(resolver=public_resolver),
        )

        with self.assertRaisesRegex(UnsafeUrlError, "cannot redirect"):
            await reader.read("https://public.test/start")

    async def test_extracted_text_has_a_separate_size_limit(self) -> None:
        reader = StubReader(
            [_HttpResponse(200, {"content-type": "text/plain"}, b"too long")],
            policy=PublicUrlPolicy(resolver=public_resolver),
            max_text_chars=3,
        )

        with self.assertRaisesRegex(SourceReadError, "text exceeds"):
            await reader.read("https://example.test/text")

    async def test_pdf_detection_uses_url_path_and_file_signature(self) -> None:
        cases = (
            ("https://example.test/report.pdf?download=1", b"not a real pdf"),
            ("https://example.test/download", b"  %PDF-1.7 fake"),
        )
        for url, body in cases:
            with self.subTest(url=url):
                reader = StubReader(
                    [
                        _HttpResponse(
                            200,
                            {"content-type": "application/octet-stream"},
                            body,
                        )
                    ],
                    policy=PublicUrlPolicy(resolver=public_resolver),
                )
                with patch(
                    "deep_research_agent.providers._extract_pdf_in_subprocess",
                    return_value="Extracted PDF evidence.",
                ) as extract:
                    result = await reader.read(url)

                self.assertEqual("Extracted PDF evidence.", result.content)
                extract.assert_called_once()

    async def test_access_control_failure_is_transparent(self) -> None:
        reader = StubReader(
            [_HttpResponse(403, {}, b"")],
            policy=PublicUrlPolicy(resolver=public_resolver),
        )
        with self.assertRaisesRegex(SourceReadError, "authorization"):
            await reader.read("https://example.test/protected")


if __name__ == "__main__":
    unittest.main()
