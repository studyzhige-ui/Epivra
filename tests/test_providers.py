from __future__ import annotations

import json
import unittest
from unittest.mock import patch

import httpx

from deep_research_agent.providers import (
    BochaSearchProvider,
    BraveSearchProvider,
    ExaSearchProvider,
    ProviderAuthError,
    PublicHttpReader,
    PublicUrlPolicy,
    SourceReadError,
    TavilySearchProvider,
    UnsafeUrlError,
    _HttpResponse,
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


class AdditionalProviderTest(unittest.IsolatedAsyncioTestCase):
    async def test_exa_uses_fixed_origin_and_returns_extracted_text(self) -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual("https://api.exa.ai/search", str(request.url))
            self.assertEqual("exa-secret", request.headers["x-api-key"])
            payload = json.loads(request.content)
            self.assertEqual(12_000, payload["contents"]["text"]["maxCharacters"])
            self.assertEqual("news", payload["category"])
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "title": "Paper",
                            "url": "https://example.test/paper",
                            "text": "Full extracted paper text.",
                            "highlights": ["Key passage."],
                        }
                    ]
                },
            )

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            provider = ExaSearchProvider("exa-secret", client=client)
            results = await provider.search(
                query="paper", intent="research", source_kind="news"
            )
        finally:
            await client.aclose()

        self.assertEqual("Full extracted paper text.", results[0].content)
        self.assertEqual("Key passage.", results[0].snippet)
        self.assertNotIn("exa-secret", repr(provider))

    async def test_brave_news_is_discovery_only_on_fixed_origin(self) -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(
                "api.search.brave.com", request.url.host
            )
            self.assertEqual("/res/v1/news/search", request.url.path)
            self.assertEqual("brave-secret", request.headers["X-Subscription-Token"])
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "title": "News item",
                            "url": "https://news.example/item",
                            "description": "A current news description.",
                        }
                    ]
                },
            )

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            provider = BraveSearchProvider("brave-secret", client=client)
            results = await provider.search(
                query="event", intent="general discovery", source_kind="news"
            )
        finally:
            await client.aclose()

        self.assertEqual("A current news description.", results[0].snippet)
        self.assertEqual("", results[0].content)
        self.assertNotIn("brave-secret", repr(provider))

    async def test_bocha_summary_is_not_misrepresented_as_source_text(self) -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(
                "https://api.bochaai.com/v1/web-search", str(request.url)
            )
            self.assertEqual("Bearer bocha-secret", request.headers["Authorization"])
            return httpx.Response(
                200,
                json={
                    "data": {
                        "webPages": {
                            "value": [
                                {
                                    "name": "Chinese source",
                                    "url": "https://example.cn/report",
                                    "summary": "Provider-generated discovery summary.",
                                }
                            ]
                        }
                    }
                },
            )

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            provider = BochaSearchProvider("bocha-secret", client=client)
            results = await provider.search(
                query="查询", intent="中文资料", source_kind="web"
            )
        finally:
            await client.aclose()

        self.assertEqual("Provider-generated discovery summary.", results[0].snippet)
        self.assertEqual("", results[0].content)
        self.assertNotIn("bocha-secret", repr(provider))


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
