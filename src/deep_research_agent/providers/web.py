"""General web search adapters.

Each adapter maps one vendor's protocol onto the neutral tool contract.  None of
them judges relevance, ranks by quality, or decides when searching is done --
that is the Investigator's semantic work, and moving it here is how a research
system quietly acquires a hidden completion heuristic.

Snippets are discovery leads, never evidence.  Only Tavily and Exa can return
cleaned page text directly; everything else must be read through
:class:`~deep_research_agent.providers.reader.PublicHttpReader` before a quote
can be anchored to it.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any
from urllib.parse import parse_qsl, unquote, urlsplit

import httpx

from ..tools import ProviderInfo, ProviderResult, SourceKind
from ._http import (
    ProviderUnavailableError,
    raise_provider_status,
    request_provider_json,
)


@dataclass(slots=True)
class TavilySearchProvider:
    """Tavily Search with provider-returned cleaned page content enabled."""

    api_key: str = field(repr=False)
    max_results: int = 8
    client: httpx.AsyncClient | None = field(default=None, repr=False)
    provider_id: str = "tavily"

    def __post_init__(self) -> None:
        if not self.api_key.strip():
            raise ValueError("Tavily api_key must not be empty")
        if self.max_results < 1:
            raise ValueError("max_results must be positive")

    async def describe(self) -> ProviderInfo:
        return ProviderInfo(
            self.provider_id,
            ("web", "news", "official", "full_content"),
            "healthy",
        )

    async def search(
        self, *, query: str, intent: str, source_kind: SourceKind
    ) -> Sequence[ProviderResult]:
        payload: dict[str, Any] = {
            "query": query,
            "max_results": self.max_results,
            "include_answer": False,
            "include_raw_content": "markdown",
            "auto_parameters": True,
            "topic": "news" if source_kind == "news" else "general",
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        data = await request_provider_json(
            self.provider_id,
            method="POST",
            url="https://api.tavily.com/search",
            headers=headers,
            client=self.client,
            payload=payload,
        )
        raw_results = data.get("results", ())
        if not isinstance(raw_results, list):
            raise ProviderUnavailableError("tavily response has no result list")
        results: list[ProviderResult] = []
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            url = str(item.get("url", "")).strip()
            if not url:
                continue
            results.append(
                ProviderResult(
                    title=str(item.get("title", "")).strip() or url,
                    url=url,
                    snippet=str(item.get("content", "")).strip(),
                    content=str(item.get("raw_content") or ""),
                )
            )
        return results


@dataclass(slots=True)
class ExaSearchProvider:
    """Exa semantic search with provider-returned page text."""

    api_key: str = field(repr=False)
    max_results: int = 8
    max_characters: int = 12_000
    client: httpx.AsyncClient | None = field(default=None, repr=False)
    provider_id: str = "exa"

    def __post_init__(self) -> None:
        if not self.api_key.strip():
            raise ValueError("Exa api_key must not be empty")
        if not 1 <= self.max_results <= 100 or self.max_characters < 1:
            raise ValueError("Exa result and content limits must be positive")

    async def describe(self) -> ProviderInfo:
        return ProviderInfo(
            self.provider_id,
            ("web", "news", "research", "full_content", "semantic"),
        )

    async def search(
        self, *, query: str, intent: str, source_kind: SourceKind
    ) -> Sequence[ProviderResult]:
        payload: dict[str, Any] = {
            "query": query,
            "type": "auto",
            "numResults": self.max_results,
            "contents": {"text": {"maxCharacters": self.max_characters}},
        }
        if source_kind == "news":
            payload["category"] = "news"
        data = await request_provider_json(
            self.provider_id,
            method="POST",
            url="https://api.exa.ai/search",
            headers={
                "x-api-key": self.api_key,
                "Content-Type": "application/json",
            },
            client=self.client,
            payload=payload,
        )
        raw_results = data.get("results", ())
        if not isinstance(raw_results, list):
            raise ProviderUnavailableError("exa response has no result list")
        results: list[ProviderResult] = []
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            url = str(item.get("url", "")).strip()
            if not url:
                continue
            highlights = item.get("highlights", ())
            snippet = (
                "\n".join(str(value) for value in highlights if str(value).strip())
                if isinstance(highlights, list)
                else ""
            )
            results.append(
                ProviderResult(
                    title=str(item.get("title", "")).strip() or url,
                    url=url,
                    snippet=snippet,
                    content=str(item.get("text") or ""),
                )
            )
        return results


@dataclass(slots=True)
class BraveSearchProvider:
    """Brave's independent Web/News index; results remain snippets until read."""

    api_key: str = field(repr=False)
    max_results: int = 10
    client: httpx.AsyncClient | None = field(default=None, repr=False)
    provider_id: str = "brave"

    def __post_init__(self) -> None:
        if not self.api_key.strip():
            raise ValueError("Brave api_key must not be empty")
        if not 1 <= self.max_results <= 20:
            raise ValueError("Brave max_results must be between 1 and 20")

    async def describe(self) -> ProviderInfo:
        return ProviderInfo(
            self.provider_id, ("web", "news", "independent_index")
        )

    async def search(
        self, *, query: str, intent: str, source_kind: SourceKind
    ) -> Sequence[ProviderResult]:
        news = source_kind == "news"
        url = (
            "https://api.search.brave.com/res/v1/news/search"
            if news
            else "https://api.search.brave.com/res/v1/web/search"
        )
        data = await request_provider_json(
            self.provider_id,
            method="GET",
            url=url,
            headers={
                "Accept": "application/json",
                "X-Subscription-Token": self.api_key,
            },
            client=self.client,
            params={
                "q": query,
                "count": self.max_results,
                "safesearch": "moderate",
                "extra_snippets": "true",
            },
        )
        container = data if news else data.get("web", {})
        raw_results = container.get("results", ()) if isinstance(container, dict) else ()
        if not isinstance(raw_results, list):
            raise ProviderUnavailableError("brave response has no result list")
        results: list[ProviderResult] = []
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            result_url = str(item.get("url", "")).strip()
            if not result_url:
                continue
            extras = item.get("extra_snippets", ())
            parts = [str(item.get("description", "")).strip()]
            if isinstance(extras, list):
                parts.extend(str(value).strip() for value in extras)
            results.append(
                ProviderResult(
                    title=str(item.get("title", "")).strip() or result_url,
                    url=result_url,
                    snippet="\n".join(value for value in parts if value),
                )
            )
        return results


@dataclass(slots=True)
class BochaSearchProvider:
    """Bocha web search; provider summaries are discovery snippets, not sources."""

    api_key: str = field(repr=False)
    max_results: int = 10
    client: httpx.AsyncClient | None = field(default=None, repr=False)
    provider_id: str = "bocha"

    def __post_init__(self) -> None:
        if not self.api_key.strip():
            raise ValueError("Bocha api_key must not be empty")
        if not 1 <= self.max_results <= 50:
            raise ValueError("Bocha max_results must be between 1 and 50")

    async def describe(self) -> ProviderInfo:
        return ProviderInfo(self.provider_id, ("web", "chinese"))

    async def search(
        self, *, query: str, intent: str, source_kind: SourceKind
    ) -> Sequence[ProviderResult]:
        data = await request_provider_json(
            self.provider_id,
            method="POST",
            url="https://api.bochaai.com/v1/web-search",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            client=self.client,
            payload={
                "query": query,
                "count": self.max_results,
                "freshness": "noLimit",
                "summary": True,
            },
        )
        nested = data.get("data", {})
        pages = nested.get("webPages", {}) if isinstance(nested, dict) else {}
        raw_results = pages.get("value", ()) if isinstance(pages, dict) else ()
        if not isinstance(raw_results, list):
            raise ProviderUnavailableError("bocha response has no result list")
        results: list[ProviderResult] = []
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            url = str(item.get("url", "")).strip()
            if not url:
                continue
            results.append(
                ProviderResult(
                    title=str(item.get("name", "")).strip() or url,
                    url=url,
                    snippet=str(item.get("summary") or item.get("snippet") or ""),
                )
            )
        return results


@dataclass(slots=True)
class DuckDuckGoSearchProvider:
    """Keyless fallback so a missing or throttled Tavily key never blinds research.

    DuckDuckGo's HTML endpoint returns discovery snippets only, never page text,
    so every result here must be read through :class:`PublicHttpReader` before it
    can become evidence.  That is the same rule Tavily results follow; the
    difference is only that Tavily can hand back cleaned content directly.
    """

    max_results: int = 10
    client: httpx.AsyncClient | None = field(default=None, repr=False)
    provider_id: str = "duckduckgo"

    def __post_init__(self) -> None:
        if not 1 <= self.max_results <= 30:
            raise ValueError("DuckDuckGo max_results must be between 1 and 30")

    async def describe(self) -> ProviderInfo:
        return ProviderInfo(self.provider_id, ("web", "keyless", "fallback"))

    async def search(
        self, *, query: str, intent: str, source_kind: SourceKind
    ) -> Sequence[ProviderResult]:
        owns_client = self.client is None
        transport = self.client or httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        try:
            try:
                response = await transport.request(
                    "POST",
                    "https://html.duckduckgo.com/html/",
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    data={"q": query},
                )
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                raise ProviderUnavailableError(
                    "duckduckgo request unavailable"
                ) from exc
        finally:
            if owns_client:
                await transport.aclose()
        if response.status_code >= 400:
            raise_provider_status(self.provider_id, response.status_code)
        return _parse_duckduckgo_html(response.text, self.max_results)


class _DuckDuckGoParser(HTMLParser):
    """Collect result links and snippets from DuckDuckGo's HTML endpoint."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.results: list[tuple[str, str, str]] = []
        self._pending_url = ""
        self._collecting: str = ""
        self._buffer: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attributes = {key: value or "" for key, value in attrs}
        classes = attributes.get("class", "").split()
        if tag == "a" and "result__a" in classes:
            self._pending_url = _duckduckgo_target(attributes.get("href", ""))
            self._collecting = "title"
            self._buffer = []
        elif tag == "a" and "result__snippet" in classes:
            self._collecting = "snippet"
            self._buffer = []

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or not self._collecting:
            return
        text = " ".join("".join(self._buffer).split())
        if self._collecting == "title" and self._pending_url:
            self.results.append((text or self._pending_url, self._pending_url, ""))
        elif self._collecting == "snippet" and self.results:
            title, url, _ = self.results[-1]
            self.results[-1] = (title, url, text)
        self._collecting = ""
        self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._collecting:
            self._buffer.append(data)


def _duckduckgo_target(href: str) -> str:
    """Unwrap DuckDuckGo's ``/l/?uddg=`` redirect into the real target URL."""

    if not href:
        return ""
    parts = urlsplit(href)
    if parts.path.startswith("/l/"):
        targets = dict(parse_qsl(parts.query)).get("uddg", "")
        return unquote(targets)
    if parts.scheme in ("http", "https"):
        return href
    return ""


def _parse_duckduckgo_html(html: str, max_results: int) -> Sequence[ProviderResult]:
    parser = _DuckDuckGoParser()
    parser.feed(html)
    results: list[ProviderResult] = []
    for title, url, snippet in parser.results:
        if not url:
            continue
        results.append(ProviderResult(title=title or url, url=url, snippet=snippet))
        if len(results) >= max_results:
            break
    return results


__all__ = [
    "BochaSearchProvider",
    "BraveSearchProvider",
    "DuckDuckGoSearchProvider",
    "ExaSearchProvider",
    "TavilySearchProvider",
]
