"""Search and reader protocols. Each invocation sends exactly one request."""

from datetime import date, datetime, timezone
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlsplit

from .adapters import JsonAPI, ProviderFailure, Tavily, rate_limit_delay
from .domain import encode, identity

CONNECTIONS = {
    "tavily": ("https://api.tavily.com", "TAVILY_API_KEY", "Authorization", "Bearer "),
    "exa": ("https://api.exa.ai", "EXA_API_KEY", "x-api-key", ""),
    "brave": (
        "https://api.search.brave.com",
        "BRAVE_API_KEY",
        "X-Subscription-Token",
        "",
    ),
    "perplexity": (
        "https://api.perplexity.ai",
        "PERPLEXITY_API_KEY",
        "Authorization",
        "Bearer ",
    ),
    "bocha": ("https://api.bochaai.com", "BOCHA_API_KEY", "Authorization", "Bearer "),
    "duckduckgo": ("https://html.duckduckgo.com", None, "Authorization", ""),
    "jina": ("https://r.jina.ai", "JINA_API_KEY", "Authorization", "Bearer "),
}
SEARCH = ("tavily", "exa", "brave", "perplexity", "bocha", "duckduckgo")


class TavilyKeyPool(JsonAPI):
    """One request per invocation; explicit rejection retries belong to Harness."""

    def __init__(self, origin, key, client=None, **kwargs):
        super().__init__(origin, "", client, **kwargs)
        self.replace_key(key)

    def replace_key(self, key):
        keys = list(dict.fromkeys(k.strip() for k in key.split(",") if k.strip()))
        if not keys:
            raise ValueError("credential required")
        self._keys, self._disabled, self._cursor = keys, set(), 0

    @property
    def authorization_identity(self):
        return identity("authorization-pool-v1", self.origin, self.auth_header, self._keys)

    async def request(self, method, path, **kwargs):
        available = [i for i in range(len(self._keys)) if i not in self._disabled]
        if not available:
            return {"http_status": 432, "key_pool_exhausted": True}
        slot = next((i for i in available if i >= self._cursor), available[0])
        self._cursor = (slot + 1) % len(self._keys)
        # A request-local wrapper prevents concurrent calls from sharing auth state.
        api = JsonAPI(
            self.origin,
            self._keys[slot],
            self._client,
            auth_header=self.auth_header,
            auth_prefix=self.auth_prefix,
            headers=self.headers,
            deadline=self.deadline,
            max_response_bytes=self.max_response_bytes,
            max_event_bytes=self.max_event_bytes,
        )
        raw = await api.request(method, path, **kwargs)
        raw["credential_slot"] = slot + 1
        if raw.get("http_status") in {401, 432, 433}:
            self._disabled.add(slot)
            raw["credential_retry"] = len(self._disabled) < len(self._keys)
        return raw


class _DuckResults(HTMLParser):
    def __init__(self):
        super().__init__()
        self.results, self.capture = [], None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = attrs.get("class", "").split()
        if tag == "a" and "result__a" in classes:
            href = attrs.get("href", "")
            target = parse_qs(urlsplit(href).query).get("uddg", [href])[0]
            self.results.append({"url": target, "title": "", "snippet": ""})
            self.capture = (tag, "title")
        elif "result__snippet" in classes and self.results:
            self.capture = (tag, "snippet")

    def handle_data(self, text):
        if self.capture:
            self.results[-1][self.capture[1]] += text

    def handle_endtag(self, tag):
        if self.capture and self.capture[0] == tag:
            self.capture = None


class WebProvider:
    retry_delay = staticmethod(rate_limit_delay)
    retry_on_resume = staticmethod(Tavily.retry_on_resume)
    validate_extract = staticmethod(Tavily.validate_extract)

    def __init__(self, name, api):
        self.resource, self.api = name, api
        self.identity = identity("web-protocol-v2-search-content", name, api.account)

    def validate_search(self, args):
        filters = {"include_domains", "exclude_domains", "start_date", "end_date"}
        if filters & args.keys() and self.resource != "tavily":
            raise ValueError(
                "structured domain/date filters are supported by tavily only"
            )
        for key in ("start_date", "end_date"):
            if key in args:
                value = date.fromisoformat(args[key])
                if value.isoformat() != args[key]:
                    raise ValueError("expected YYYY-MM-DD")
        if args.get("start_date", "") > args.get("end_date", "9999-12-31"):
            raise ValueError("reversed date range")
        for key, maximum in (("include_domains", 300), ("exclude_domains", 150)):
            if key in args:
                values = args[key]
                if (
                    not isinstance(values, list)
                    or len(values) > maximum
                    or any(
                        not isinstance(v, str)
                        or not v.strip()
                        or "://" in v
                        or any(c.isspace() for c in v)
                        for v in values
                    )
                ):
                    raise ValueError("expected domain list within provider limit")

    async def search(self, args):
        self.validate_search(args)
        query, name = args["query"], self.resource
        if name == "tavily":
            raw = await Tavily(self.api).search(args)
        elif name == "exa":
            raw = await self.api.post(
                "/search", {"query": query, "type": "auto", "numResults": 10,
                            "contents": {"text": True, "highlights": True}}
            )
        elif name == "brave":
            raw = await self.api.request(
                "GET", "/res/v1/llm/context", params={"q": query, "count": 10}
            )
        elif name == "perplexity":
            raw = await self.api.post("/search", {"query": query, "max_results": 10, "search_context_size": "high"})
        elif name == "bocha":
            raw = await self.api.post(
                "/v1/web-search", {"query": query, "count": 10, "summary": True}
            )
        elif name == "duckduckgo":
            raw = await self.api.request(
                "GET", "/html/", params={"q": query}, text=True
            )
        else:
            raise ValueError("provider does not support search")
        return {
            **raw,
            "provider": name,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
        }

    async def extract(self, args):
        self.validate_extract(args)
        if self.resource == "tavily":
            raw = await Tavily(self.api).extract(args)
        elif self.resource == "exa":
            raw = await self.api.post("/contents", {"ids": [args["url"]], "text": True})
        elif self.resource == "jina":
            raw = await self.api.post("/", {"url": args["url"]})
        else:
            raise ValueError("provider does not support extraction")
        return {
            **raw,
            "provider": self.resource,
            "requested_url": args["url"],
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
        }

    def _data(self, raw):
        if raw.get("http_status") != 200:
            raise ProviderFailure(self.resource, raw.get("http_status", 0))
        data = raw.get("data")
        if not isinstance(data, dict):
            raise ValueError("invalid provider JSON")
        if self.resource in {"bocha", "jina"} and data.get("code", 200) != 200:
            raise ValueError("provider rejected request")
        return data

    def decode_search(self, raw):
        data = self._data(raw)
        if self.resource == "tavily":
            return self._search_sources(Tavily.decode_search(raw), raw)
        if self.resource == "duckduckgo":
            html = data.get("html", "")
            parser = _DuckResults()
            parser.feed(html)
            items = parser.results
            if not items and "no-results" not in html:
                raise ValueError("DuckDuckGo unavailable or page format changed")
        elif self.resource == "brave":
            web = data.get("grounding")
            if not isinstance(web, dict):
                raise ValueError("invalid Brave grounding results")
            items = web.get("generic", [])
        elif self.resource == "bocha":
            payload = data.get("data")
            if not isinstance(payload, dict):
                raise ValueError("invalid Bocha payload")
            web = payload.get("webPages", {})
            if not isinstance(web, dict):
                raise ValueError("invalid Bocha web results")
            items = web.get("value", [])
        else:
            items = data.get("results")
        if not isinstance(items, list):
            raise ValueError("expected search results array")
        results, failures = [], []
        seen = set()
        for index, item in enumerate(items):
            try:
                if not isinstance(item, dict) or not isinstance(item.get("url"), str):
                    raise ValueError("invalid search result")
                url = item["url"]
                self.validate_extract({"url": url})
                if url in seen:
                    continue
                excerpt = ""
                if self.resource in {"exa", "brave"}:
                    field = "highlights" if self.resource == "exa" else "snippets"
                    parts = item.get(field)
                    if parts is not None:
                        if isinstance(parts, list) and all(isinstance(p, str) for p in parts):
                            excerpt = "\n".join(parts)
                        else:
                            failures.append({"index": index, "error": "invalid_search_excerpt"})
                snippet = item.get("snippet") or item.get("description") or excerpt
                title = item.get("title") or item.get("name") or ""
                if not isinstance(title, str) or not isinstance(snippet, str):
                    raise ValueError("invalid search text")
                result = {
                        "url": url,
                        "title": title,
                        "snippet": snippet,
                        "content_type": "search_snippet",
                        "published_at": item.get("publishedDate")
                        or item.get("datePublished")
                        or item.get("date"),
                    }
                text, kind = None, None
                if self.resource == "exa":
                    text = item.get("text")
                    kind = "extracted_page"
                    if not text:
                        text, kind = excerpt, "selected_excerpt"
                elif self.resource == "brave":
                    text, kind = excerpt, "selected_excerpt"
                elif self.resource == "perplexity":
                    text, kind = item.get("snippet"), "selected_excerpt"
                if text is not None and not isinstance(text, str):
                    failures.append({"index": index, "error": "invalid_search_content"})
                elif text and text.strip():
                    result.update(text=text, content_type=kind)
                    if kind == "selected_excerpt" and self.resource in {"exa", "brave"}:
                        offset, segments = 0, []
                        for part in parts:
                            end = offset + len(part)
                            segments.append({"start": offset, "end": end,
                                             "locator": {"url": url, "label": "excerpt", "discontinuous": True},
                                             "status": "selected_excerpt_not_reviewed"})
                            offset = end + 1
                        result["segments"] = segments
                if self.resource == "bocha" and item.get("summary"):
                    if isinstance(item["summary"], str):
                        result.update(summary=item["summary"], summary_type="provider_summary")
                    else:
                        failures.append({"index": index, "error": "invalid_search_summary"})
                encode(result)
                seen.add(url)
                results.append(result)
            except (ValueError, TypeError, KeyError):
                failures.append({"index": index, "error": "invalid_search_result"})
        return self._search_sources({"results": results, "failures": failures}, raw)

    def _search_sources(self, decoded, raw):
        """Normalize supplied original content; storage belongs to Workspace."""
        sources = []
        for result in decoded["results"]:
            text = result.pop("text", None)
            if text:
                coverage = result["content_type"] + "_not_reviewed"
                sources.append({
                    "origin": result["url"], "title": result["title"],
                    "text": text, "parser": self.resource + "-search-v2",
                    "coverage": coverage, "content_type": result["content_type"],
                    "retrieved_at": raw.get("retrieved_at"),
                    "published_at": result.get("published_at"),
                    "segments": result.pop("segments", None) or [{"start": 0, "end": len(text),
                                  "locator": {"url": result["url"]},
                                  "status": coverage}],
                })
                if not result["snippet"]:
                    result["snippet"] = text
            if len(result["snippet"]) > 1000:
                result["snippet"] = result["snippet"][:1000]
                result["preview_truncated"] = True
        return {**decoded, "sources": sources, "provider": self.resource}

    def decode_extract(self, raw):
        data = self._data(raw)
        if self.resource == "tavily":
            decoded = Tavily.decode_extract(raw)
        else:
            items = (
                [data.get("data")] if self.resource == "jina" else data.get("results")
            )
            if not isinstance(items, list):
                raise ValueError("expected extracted contents")
            decoded = {"sources": [], "failures": []}
            for item in items:
                if not isinstance(item, dict):
                    raise ValueError("invalid extracted document")
                url = item.get("url") or raw.get("requested_url")
                text = item.get("content" if self.resource == "jina" else "text")
                if not isinstance(text, str) or not text.strip():
                    decoded["failures"].append(
                        {
                            "url": url,
                            "reason": "No readable content; try another reader",
                        }
                    )
                    continue
                self.validate_extract({"url": url})
                decoded["sources"].append(
                    {
                        "origin": url,
                        "text": text,
                        "title": item.get("title", ""),
                        "parser": self.resource + "-reader-v1",
                        "coverage": "extracted_not_reviewed",
                    }
                )
            if not items:
                decoded["failures"].append(
                    {"url": raw.get("requested_url"), "reason": "No contents returned"}
                )
        for source in decoded["sources"]:
            source.update(
                retrieved_at=raw.get("retrieved_at"),
                requested_url=raw.get("requested_url"),
            )
            source["segments"] = [
                {
                    "start": 0,
                    "end": len(source["text"]),
                    "locator": {"url": source["origin"]},
                    "status": "extracted_not_reviewed",
                }
            ]
        return decoded


def connect(name, keys, client=None):
    if name == "http":
        from .direct_reader import DirectReader

        return DirectReader()
    origin, key_name, header, prefix = CONNECTIONS[name]
    key = keys.get(key_name, "")
    if name not in {"jina", "duckduckgo"} and not key:
        raise ValueError(f"{key_name} required")
    api = (TavilyKeyPool if name == "tavily" else JsonAPI)(
        origin,
        key,
        client,
        auth_header=header,
        auth_prefix=prefix,
        credential_env=key_name,
        headers={"Accept": "application/json"} if name == "jina" else {},
    )
    return WebProvider(name, api)
