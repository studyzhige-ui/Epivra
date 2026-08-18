"""Reading public sources into exact, immutable text.

The reader is the only component allowed to fetch an arbitrary URL, and it does
so under a fixed policy: public hosts only, no credentials, redirects checked
before they are followed, and PDF parsing isolated in a killable subprocess.
Untrusted bytes never get to choose where the process connects next.
"""

from __future__ import annotations

import asyncio
import ipaddress
import multiprocessing
import socket
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from html.parser import HTMLParser
from io import BytesIO
from typing import Any
from urllib.parse import urljoin, urlsplit

import aiohttp
from pypdf import PdfReader

from ..tools import ReadResult
from ._http import SourceReadError, UnsafeUrlError


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



__all__ = [
    "PublicHttpReader",
    "PublicUrlPolicy",
    "SourceReadError",
    "UnsafeUrlError",
]
