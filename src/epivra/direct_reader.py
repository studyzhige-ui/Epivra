"""Public HTTP acquisition without browser state or provider credentials."""

import asyncio
import ipaddress
import socket
from datetime import datetime, timezone
from urllib.parse import urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup
from markdownify import MarkdownConverter

from .adapters import JsonAPI, Tavily, decoded_response
from .recovery import retry_delay


def extract_html(content, url, encoding=None):
    soup = BeautifulSoup(content, "html.parser", from_encoding=encoding)
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    if title.casefold().strip() in {"just a moment...", "access denied", "verify you are human", "checking your browser"}:
        raise ValueError("challenge_page")
    if soup.select_one('#challenge-form, .g-recaptcha, .h-captcha, input[type="password"]'):
        raise ValueError("authentication_or_challenge")
    for element in soup.select('head, script, style, template, noscript, nav, footer, form, iframe, svg, [hidden], [aria-hidden="true"]'):
        element.decompose()
    root = soup.find("main") or soup.find("article") or soup.body or soup
    if root.get_text(" ", strip=True).casefold() in {
            "", "loading...", "loading…", "please enable javascript", "enable javascript to continue", "加载中..."}:
        raise ValueError("empty_page")
    for link in root.find_all("a", href=True):
        target = urljoin(url, link["href"])
        if urlsplit(target).scheme in {"http", "https"}:
            link["href"] = target
        else:
            del link["href"]
    text = MarkdownConverter(heading_style="ATX", strip=["img"]).convert_soup(root).strip()
    if not text:
        raise ValueError("empty_page")
    return text, title


async def public_address(url):
    Tavily.validate_extract({"url": url})
    try:
        parsed = httpx.URL(url)
    except httpx.InvalidURL as exc:
        raise ValueError("invalid_url") from exc
    addresses = await asyncio.get_running_loop().getaddrinfo(
        parsed.host, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(row[4][0]).is_global for row in addresses):
        raise ValueError("non_public_address")
    return parsed.copy_with(host=addresses[0][4][0]), parsed


class DirectReader:
    resource = "http"
    identity = "direct-http-markdown-v1"
    authorization_identity = "public-http-no-credentials-v1"
    credential_env = None
    validate_extract = staticmethod(Tavily.validate_extract)
    retry_delay = staticmethod(retry_delay)

    def __init__(self):
        self.api = self

    async def close(self):
        pass

    async def extract(self, args):
        original = args["url"]
        raw = {"provider": self.resource, "requested_url": original,
               "retrieved_at": datetime.now(timezone.utc).isoformat()}
        try:
            async with asyncio.timeout(30), httpx.AsyncClient(
                    trust_env=False, follow_redirects=False, timeout=20) as client:
                url = original
                for hop in range(6):
                    try:
                        address, target = await public_address(url)
                    except ValueError:
                        return {**raw, "error": "non_public_url", "fallback_allowed": False}
                    request = httpx.Request("GET", address, headers={
                        "Host": target.netloc.decode(), "User-Agent": "Epivra/0.3 public-reader",
                        "Accept": "text/html, text/plain, text/markdown"},
                        extensions={"sni_hostname": target.host})
                    response = await client.send(request, stream=True)
                    try:
                        raw.update(http_status=response.status_code, final_url=url)
                        if response.is_redirect:
                            if hop == 5 or not response.headers.get("location"):
                                return {**raw, "error": "redirect_limit_or_missing_location"}
                            url = urljoin(url, response.headers["location"])
                            continue
                        if response.status_code != 200:
                            return {**raw, **JsonAPI._rejection(httpx.Response(
                                response.status_code, headers=response.headers)), "error": "http_error"}
                        mime = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                        if mime not in {"text/html", "application/xhtml+xml", "text/plain", "text/markdown"}:
                            return {**raw, "error": "unsupported_content_type"}
                        body = bytearray()
                        async for chunk in response.aiter_bytes():
                            body.extend(chunk)
                            if len(body) > 8 * 1024 * 1024:
                                return {**raw, "error": "response_too_large"}
                        if mime in {"text/html", "application/xhtml+xml"}:
                            encoding = response.charset_encoding
                            try:
                                text, title = await asyncio.to_thread(extract_html, bytes(body), url, encoding)
                            except ValueError as exc:
                                return {**raw, "error": str(exc)}
                        else:
                            text = decoded_response(response, bytes(body)).text.strip()
                            title = ""
                        if not text:
                            return {**raw, "error": "empty_page"}
                        return {**raw, "text": text, "title": title}
                    finally:
                        await response.aclose()
        except (httpx.HTTPError, OSError, TimeoutError):
            return {**raw, "error": "transport_failure"}

    def decode_extract(self, raw):
        if not raw.get("text"):
            return {"sources": [], "failures": [{"url": raw["requested_url"],
                    "reason": raw.get("error", "no_readable_content"), "http_status": raw.get("http_status")} ]}
        return {"sources": [{"origin": raw["final_url"], "requested_url": raw["requested_url"],
                "text": raw["text"], "title": raw["title"], "parser": self.identity,
                "coverage": "extracted_not_reviewed", "retrieved_at": raw["retrieved_at"]}], "failures": []}
