"""First-party search and public-source adapters.

Adapters translate provider protocols into the neutral tool contracts.  They do
not choose research questions, judge evidence quality, or decide when to stop.
Credentials are process configuration and never enter graph state.
"""

from __future__ import annotations

import asyncio
import ipaddress
import multiprocessing
import os
import socket
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from html.parser import HTMLParser
from io import BytesIO
from typing import Any
from urllib.parse import parse_qsl, unquote, urljoin, urlsplit

import aiohttp
import httpx
from pypdf import PdfReader

from .tools import ProviderInfo, ProviderResult, ReadResult, SourceKind


class ProviderAuthError(RuntimeError):
    pass


class ProviderRateLimitError(RuntimeError):
    pass


class ProviderUnavailableError(RuntimeError):
    pass


class UnsafeUrlError(ValueError):
    """A URL is outside the public, read-only network boundary."""


class SourceReadError(RuntimeError):
    """A public source could not be read within the deterministic boundary."""


def _pdf_worker(
    body: bytes,
    max_pages: int,
    max_text_chars: int,
    sender: Any,
) -> None:
    """Extract untrusted PDF text in a process that can be terminated."""

    try:
        reader = PdfReader(BytesIO(body))
        if len(reader.pages) > max_pages:
            sender.send(("error", "PDF exceeds the configured page limit"))
            return
        parts: list[str] = []
        size = 0
        for page in reader.pages:
            value = (page.extract_text() or "").strip()
            size += len(value)
            if size > max_text_chars:
                sender.send(("error", "PDF text exceeds the configured size"))
                return
            parts.append(value)
        sender.send(("ok", "\n\n".join(parts).strip()))
    except Exception:
        sender.send(("error", "PDF could not be parsed"))
    finally:
        sender.close()


def _extract_pdf_in_subprocess(
    body: bytes,
    *,
    max_pages: int,
    max_text_chars: int,
    timeout_seconds: float,
) -> str:
    context = multiprocessing.get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(
        target=_pdf_worker,
        args=(body, max_pages, max_text_chars, sender),
        daemon=True,
    )
    process.start()
    sender.close()
    try:
        if not receiver.poll(timeout_seconds):
            process.terminate()
            process.join(timeout=1.0)
            raise SourceReadError("PDF extraction exceeded the time limit")
        status, payload = receiver.recv()
    finally:
        receiver.close()
        if process.is_alive():
            process.terminate()
        process.join(timeout=1.0)
    if status != "ok":
        raise SourceReadError(str(payload))
    return str(payload)


def _raise_provider_status(provider_id: str, status_code: int) -> None:
    message = f"{provider_id} request failed with HTTP {status_code}"
    if status_code in {401, 403}:
        raise ProviderAuthError(message)
    if status_code == 429:
        raise ProviderRateLimitError(message)
    if status_code >= 500:
        raise ProviderUnavailableError(message)
    raise RuntimeError(message)


async def _request_provider_json(
    provider_id: str,
    *,
    method: str,
    url: str,
    headers: Mapping[str, str],
    client: httpx.AsyncClient | None,
    params: Mapping[str, Any] | None = None,
    payload: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    owns_client = client is None
    transport = client or httpx.AsyncClient(timeout=30.0)
    try:
        try:
            response = await transport.request(
                method,
                url,
                headers=dict(headers),
                params=dict(params or {}),
                json=dict(payload) if payload is not None else None,
            )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise ProviderUnavailableError(
                f"{provider_id} request unavailable"
            ) from exc
    finally:
        if owns_client:
            await transport.aclose()
    if response.status_code >= 400:
        _raise_provider_status(provider_id, response.status_code)
    try:
        data = response.json()
    except ValueError as exc:
        raise ProviderUnavailableError(
            f"{provider_id} returned invalid JSON"
        ) from exc
    if not isinstance(data, dict):
        raise ProviderUnavailableError(f"{provider_id} response is not an object")
    return data


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
        data = await _request_provider_json(
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
            _raise_provider_status(self.provider_id, response.status_code)
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


Resolver = Callable[[str], Awaitable[Sequence[str]]]


async def _resolve_public_addresses(hostname: str) -> Sequence[str]:
    loop = asyncio.get_running_loop()
    records = await loop.run_in_executor(
        None,
        lambda: socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM),
    )
    return tuple(dict.fromkeys(record[4][0] for record in records))


def _is_public_address(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    return address.is_global


@dataclass(frozen=True, slots=True)
class PublicUrlPolicy:
    resolver: Resolver = field(default=_resolve_public_addresses, repr=False)

    async def validate(self, url: str) -> None:
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"}:
            raise UnsafeUrlError("source URL must use HTTP or HTTPS")
        if not parsed.hostname or parsed.username or parsed.password:
            raise UnsafeUrlError("source URL must have a public host and no credentials")
        try:
            port = parsed.port
        except ValueError as exc:
            raise UnsafeUrlError("source URL has an invalid port") from exc
        allowed_port = 80 if parsed.scheme == "http" else 443
        if port not in {None, allowed_port}:
            raise UnsafeUrlError("source URL must use the standard Web port")
        hostname = parsed.hostname.casefold().rstrip(".")
        if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith(
            ".localhost"
        ):
            raise UnsafeUrlError("local source URLs are not allowed")
        addresses = await self.resolver(hostname)
        if not addresses or any(not _is_public_address(item) for item in addresses):
            raise UnsafeUrlError("source host does not resolve exclusively to public IPs")


class _PublicResolver(aiohttp.abc.AbstractResolver):
    """Resolve and validate the exact addresses used by the HTTP connector."""

    def __init__(self, resolver: Resolver) -> None:
        self._resolver = resolver

    async def resolve(
        self, host: str, port: int = 0, family: int = socket.AF_UNSPEC
    ) -> list[dict[str, Any]]:
        addresses = await self._resolver(host)
        if not addresses or any(not _is_public_address(item) for item in addresses):
            raise UnsafeUrlError(
                "source host does not resolve exclusively to public IPs"
            )
        values: list[dict[str, Any]] = []
        for address in addresses:
            address_family = socket.AF_INET6 if ":" in address else socket.AF_INET
            if family not in {socket.AF_UNSPEC, address_family}:
                continue
            values.append(
                {
                    "hostname": host,
                    "host": address,
                    "port": port,
                    "family": address_family,
                    "proto": 0,
                    "flags": socket.AI_NUMERICHOST,
                }
            )
        return values

    async def close(self) -> None:
        return None


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self._in_title = False
        self._ignored_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, _attrs: list[tuple[str, str | None]]) -> None:
        name = tag.casefold()
        if name == "title":
            self._in_title = True
        if name in {"script", "style", "noscript", "svg"}:
            self._ignored_depth += 1
        elif name in {"p", "div", "section", "article", "li", "br", "tr", "h1", "h2", "h3"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        name = tag.casefold()
        if name == "title":
            self._in_title = False
        if name in {"script", "style", "noscript", "svg"} and self._ignored_depth:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        value = " ".join(data.split())
        if not value:
            return
        if self._in_title:
            self.title = (self.title + " " + value).strip()
        else:
            self.parts.append(value)

    def text(self) -> str:
        lines = [" ".join(line.split()) for line in " ".join(self.parts).splitlines()]
        return "\n".join(line for line in lines if line)


@dataclass(slots=True)
class PublicHttpReader:
    """Read public HTML, text, or PDF without bypassing access controls."""

    policy: PublicUrlPolicy = field(default_factory=PublicUrlPolicy)
    max_bytes: int = 12 * 1024 * 1024
    max_redirects: int = 5
    max_text_chars: int = 5_000_000
    max_pdf_pages: int = 300
    pdf_timeout_seconds: float = 20.0

    def __post_init__(self) -> None:
        if self.max_bytes < 1:
            raise ValueError("max_bytes must be positive")
        if self.max_redirects < 0:
            raise ValueError("max_redirects must be non-negative")
        if self.max_text_chars < 1 or self.max_pdf_pages < 1:
            raise ValueError("text and PDF limits must be positive")
        if self.pdf_timeout_seconds <= 0:
            raise ValueError("pdf_timeout_seconds must be positive")

    async def read(self, url: str) -> ReadResult:
        current = url.strip()
        connector = aiohttp.TCPConnector(
            resolver=_PublicResolver(self.policy.resolver),
            use_dns_cache=False,
        )
        timeout = aiohttp.ClientTimeout(total=30.0)
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            auto_decompress=True,
            headers={"User-Agent": "DeepResearchAgent/0.1 (+public-read-only)"},
            trust_env=False,
        ) as session:
            for _ in range(self.max_redirects + 1):
                await self.policy.validate(current)
                try:
                    response = await self._fetch(session, current)
                except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                    raise SourceReadError("public source request failed") from exc
                if response.status in {301, 302, 303, 307, 308}:
                    location = response.headers.get("location", "").strip()
                    if not location:
                        raise SourceReadError("source redirect omitted its destination")
                    destination = urljoin(current, location)
                    if (
                        urlsplit(current).scheme == "https"
                        and urlsplit(destination).scheme != "https"
                    ):
                        raise UnsafeUrlError("HTTPS sources cannot redirect to HTTP")
                    current = destination
                    continue
                if response.status in {401, 402, 403}:
                    raise SourceReadError(
                        "source requires authorization, payment, or access permission"
                    )
                if response.status >= 400:
                    raise SourceReadError(
                        f"source request failed with HTTP {response.status}"
                    )
                body = response.body
                content_type = response.headers.get("content-type", "").casefold()
                if (
                    "application/pdf" in content_type
                    or urlsplit(current).path.casefold().endswith(".pdf")
                    or body.lstrip().startswith(b"%PDF-")
                ):
                    content = await asyncio.to_thread(
                        _extract_pdf_in_subprocess,
                        body,
                        max_pages=self.max_pdf_pages,
                        max_text_chars=self.max_text_chars,
                        timeout_seconds=self.pdf_timeout_seconds,
                    )
                    title = PathName.from_url(current)
                elif "html" in content_type or body.lstrip().startswith(b"<"):
                    extractor = _TextExtractor()
                    extractor.feed(self._decode(body, response.charset))
                    content = extractor.text()
                    title = extractor.title or PathName.from_url(current)
                else:
                    content = self._decode(body, response.charset).strip()
                    title = PathName.from_url(current)
                if not content:
                    raise SourceReadError("source returned no readable text")
                if len(content) > self.max_text_chars:
                    raise SourceReadError("source text exceeds the configured size")
                return ReadResult(title=title, url=current, content=content)
            raise SourceReadError("source exceeded the redirect limit")

    async def _fetch(
        self, session: aiohttp.ClientSession, url: str
    ) -> "_HttpResponse":
        async with session.get(url, allow_redirects=False) as response:
            body = bytearray()
            async for chunk in response.content.iter_chunked(64 * 1024):
                body.extend(chunk)
                if len(body) > self.max_bytes:
                    raise SourceReadError("source exceeds the configured read size")
            return _HttpResponse(
                status=response.status,
                headers={key.casefold(): value for key, value in response.headers.items()},
                body=bytes(body),
                charset=response.charset,
            )

    @staticmethod
    def _decode(body: bytes, charset: str | None) -> str:
        try:
            return body.decode(charset or "utf-8", errors="replace")
        except LookupError:
            return body.decode("utf-8", errors="replace")

class PathName:
    @staticmethod
    def from_url(url: str) -> str:
        path = urlsplit(url).path.rstrip("/")
        return path.rsplit("/", 1)[-1] or urlsplit(url).hostname or "Untitled source"


@dataclass(frozen=True, slots=True)
class _HttpResponse:
    status: int
    headers: dict[str, str]
    body: bytes
    charset: str | None = None


def tavily_from_environment(
    *, env_var: str = "TAVILY_API_KEY", client: httpx.AsyncClient | None = None
) -> TavilySearchProvider | None:
    """Build Tavily only when the caller's environment explicitly configures it."""

    key = os.environ.get(env_var, "").strip()
    return TavilySearchProvider(key, client=client) if key else None


def configured_search_providers(
    *, client: httpx.AsyncClient | None = None
) -> tuple[TavilySearchProvider | DuckDuckGoSearchProvider, ...]:
    """Build the available providers, keyed provider first, without any calls.

    DuckDuckGo needs no credential, so it is always present as a fallback: a
    missing or throttled Tavily key degrades result quality but never leaves an
    Investigator unable to search at all.  Ordering is the broker's routing
    preference, not a quality ranking the model must obey.
    """

    tavily = tavily_from_environment(client=client)
    fallback = DuckDuckGoSearchProvider(client=client)
    return (tavily, fallback) if tavily is not None else (fallback,)


__all__ = [
    "DuckDuckGoSearchProvider",
    "ProviderAuthError",
    "ProviderRateLimitError",
    "ProviderUnavailableError",
    "PublicHttpReader",
    "PublicUrlPolicy",
    "SourceReadError",
    "TavilySearchProvider",
    "UnsafeUrlError",
    "configured_search_providers",
    "tavily_from_environment",
]
