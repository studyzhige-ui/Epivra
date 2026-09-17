"""Keyless discovery and data protocols. One HTTP request per tool invocation."""

import json
import re
from datetime import date, datetime, timezone
from urllib.parse import urlencode

from .adapters import JsonAPI, ProviderFailure


def spacing(raw):
    """Product baseline with stricter advertised spacing when present."""
    import math

    limits = raw.get("rate_limits", {})
    try:
        interval = limits["x-rate-limit-interval"]
        value = float(interval.removesuffix("s")) / float(limits["x-rate-limit-limit"])
        if interval.endswith("s") and math.isfinite(value) and value > 0:
            return max(1.0, value)
    except (KeyError, ValueError, ZeroDivisionError, TypeError, AttributeError):
        pass
    return 1.0


ORIGINS = {
    "crossref": "https://api.crossref.org",
    "pubmed": "https://eutils.ncbi.nlm.nih.gov",
    "europe_pmc": "https://www.ebi.ac.uk",
    "world_bank": "https://api.worldbank.org",
}


def schema(required, **optional):
    return {
        "type": "object",
        "properties": {**required, **optional},
        "required": list(required),
        "additionalProperties": False,
    }


TEXT = {"type": "string", "minLength": 1}
PAGE = {"type": "integer"}
TOOLS = {
    "search_crossref": (
        "crossref",
        "Search cross-disciplinary publication metadata and DOI links. Not full text. query is bibliographic text; optional start_date/end_date are publication dates YYYY-MM-DD; offset paginates 10 records.",
        schema({"query": TEXT}, start_date=TEXT, end_date=TEXT, offset=PAGE),
    ),
    "search_pubmed": (
        "pubmed",
        "Search biomedical literature with PubMed query syntax (MeSH/field tags allowed). Returns PMIDs, not abstracts. Use read_pubmed with selected IDs. Optional publication dates YYYY-MM-DD must be supplied together; offset paginates 10 records (first 10,000 only).",
        schema({"query": TEXT}, start_date=TEXT, end_date=TEXT, offset=PAGE),
    ),
    "read_pubmed": (
        "pubmed",
        "Read up to 10 selected PMIDs as original PubMed XML records including available abstracts, dates and publication types. Not article full text. Returns a saved source; use read_source to read it.",
        schema({"ids": {"type": "array", "items": TEXT}}),
    ),
    "search_europe_pmc": (
        "europe_pmc",
        "Search life-science papers/preprints and available abstracts. Supports Europe PMC syntax, e.g. FIRST_PDATE:[2024-01-01 TO 2025-12-31]. cursor defaults to *; use returned nextCursorMark for the next 10 records. Metadata/abstracts are not full text.",
        schema({"query": TEXT}, cursor=TEXT),
    ),
    "world_bank_indicators": (
        "world_bank",
        "Discover World Bank indicator IDs, definitions and source notes. Supply an exact indicator ID when known, otherwise page through the indicator catalogue (50/page). No keyword search is implied. Use query_world_bank for observations.",
        schema({}, indicator=TEXT, page=PAGE),
    ),
    "query_world_bank": (
        "world_bank",
        "Read World Bank observations. indicator must be an identified indicator code; country is ISO code, aggregate code or all; start_year/end_year bound the period. Page through 100 rows. Preserve nulls, units, indicator definition, source and lastupdated; a null is not zero. Read indicator metadata if its meaning is uncertain.",
        schema(
            {"indicator": TEXT, "country": TEXT, "start_year": PAGE, "end_year": PAGE},
            page=PAGE,
        ),
    ),
}


def request(tool, args):
    """Validate semantic bounds before any network request; no model-built URLs."""
    if tool not in TOOLS:
        raise ValueError("unknown public source tool")
    spec = TOOLS[tool][2]
    if set(args) - spec["properties"].keys() or set(spec["required"]) - args.keys():
        raise ValueError("unsupported or missing public source parameter")
    for key, value in args.items():
        kind = spec["properties"][key]["type"]
        if kind == "string" and (not isinstance(value, str) or not value.strip()):
            raise ValueError("expected nonempty " + key)
        if kind == "integer" and type(value) is not int:
            raise ValueError("expected integer " + key)
    offset, page = args.get("offset", 0), args.get("page", 1)
    if offset < 0 or page < 1:
        raise ValueError("offset >= 0 and page >= 1 required")
    for key in ("start_date", "end_date"):
        if key in args:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args[key]):
                raise ValueError("expected YYYY-MM-DD")
            date.fromisoformat(args[key])
    if args.get("start_date", "") > args.get("end_date", "9999-12-31"):
        raise ValueError("reversed date range")
    if tool == "search_crossref":
        if offset > 10000:
            raise ValueError("Crossref offset limit reached; narrow query")
        params = {"query.bibliographic": args["query"], "rows": 10, "offset": offset}
        filters = [
            f"{prefix}-pub-date:{args[key]}"
            for key, prefix in (("start_date", "from"), ("end_date", "until"))
            if key in args
        ]
        if filters:
            params["filter"] = ",".join(filters)
        return "/works", params, False
    if tool == "search_pubmed":
        if offset >= 10000:
            raise ValueError("PubMed first 10,000 results only; narrow query")
        params = {
            "db": "pubmed",
            "term": args["query"],
            "retmode": "json",
            "retmax": 10,
            "retstart": offset,
            "tool": "Epivra",
        }
        if ("start_date" in args) != ("end_date" in args):
            raise ValueError("PubMed requires both publication date bounds")
        if "start_date" in args:
            params.update(
                datetype="pdat", mindate=args["start_date"], maxdate=args["end_date"]
            )
        return "/entrez/eutils/esearch.fcgi", params, False
    if tool == "read_pubmed":
        ids = args["ids"]
        if (
            not isinstance(ids, list)
            or not 1 <= len(ids) <= 10
            or any(
                not isinstance(i, str) or not re.fullmatch(r"[1-9][0-9]*", i)
                for i in ids
            )
        ):
            raise ValueError("supply 1–10 numeric PMIDs")
        return (
            "/entrez/eutils/efetch.fcgi",
            {"db": "pubmed", "id": ",".join(ids), "retmode": "xml", "tool": "Epivra"},
            True,
        )
    if tool == "search_europe_pmc":
        return (
            "/europepmc/webservices/rest/search",
            {
                "query": args["query"],
                "format": "json",
                "resultType": "core",
                "pageSize": 10,
                "cursorMark": args.get("cursor", "*"),
            },
            False,
        )
    indicator = args.get("indicator")
    if indicator and not re.fullmatch(r"[A-Za-z0-9_.-]+", indicator):
        raise ValueError("expected a single indicator code")
    if tool == "world_bank_indicators":
        return (
            "/v2/indicator" + ("/" + indicator if indicator else ""),
            {"format": "json", "page": page, "per_page": 50},
            False,
        )
    if not re.fullmatch(r"[A-Za-z0-9]+", args["country"]):
        raise ValueError("expected a single country/aggregate code or all")
    if not 1 <= args["start_year"] <= args["end_year"] <= 9999:
        raise ValueError("invalid year range")
    return (
        f"/v2/country/{args['country']}/indicator/{indicator}",
        {
            "format": "json",
            "date": f"{args['start_year']}:{args['end_year']}",
            "page": page,
            "per_page": 100,
        },
        False,
    )


class PublicSource:
    def __init__(self, name, client=None):
        self.name = name
        self.api = JsonAPI(
            ORIGINS[name],
            "",
            client,
            headers={
                "User-Agent": "Epivra/1.0 (https://github.com/studyzhige-ui/Epivra)"
            },
        )

    async def invoke(self, tool, args):
        path, params, xml = request(tool, args)
        raw = await self.api.request("GET", path, params=params, text=xml)
        return {
            **raw,
            "provider": self.name,
            "tool": tool,
            "origin": ORIGINS[self.name] + path + "?" + urlencode(params),
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
        }

    def decode(self, raw):
        if raw.get("http_status") != 200:
            raise ProviderFailure(self.name, raw.get("http_status", 0))
        data, tool = raw.get("data"), raw["tool"]
        if tool == "read_pubmed":
            from xml.etree import ElementTree

            text = data["html"]
            root = ElementTree.fromstring(text)
            if root.tag != "PubmedArticleSet" or root.find(".//ERROR") is not None:
                raise ValueError("invalid PubMed records")
            if not list(root):
                return {"records": [], "sources": [], "failures": []}
            summary = {"record_type": "bibliographic_records_with_available_abstracts"}
        else:
            if self.name == "crossref":
                if not isinstance(data, dict) or data.get("status") != "ok":
                    raise ValueError("invalid Crossref response")
                message = data["message"]
                if not isinstance(message["items"], list) or any(
                    not isinstance(item, dict) for item in message["items"]
                ):
                    raise ValueError("invalid Crossref items")
                summary = {
                    "total": message["total-results"],
                    "records": [
                        {
                            k: item[k]
                            for k in (
                                "DOI",
                                "title",
                                "URL",
                                "type",
                                "published",
                                "container-title",
                                "abstract",
                            )
                            if k in item
                        }
                        for item in message["items"]
                    ],
                }
            elif self.name == "pubmed":
                result = data["esearchresult"]
                if not isinstance(result, dict):
                    raise ValueError("invalid PubMed search result")
                if result.get("errorlist") or "ERROR" in data:
                    raise ValueError("PubMed rejected query")
                ids = result["idlist"]
                if not isinstance(ids, list) or any(
                    not isinstance(i, str) or not i.isdecimal() for i in ids
                ):
                    raise ValueError("invalid PubMed IDs")
                summary = {
                    "total": result["count"],
                    "ids": ids,
                    "query_translation": result.get("querytranslation"),
                    "warnings": result.get("warninglist"),
                }
            elif self.name == "europe_pmc":
                results = data["resultList"]["result"]
                if not isinstance(results, list) or any(
                    not isinstance(item, dict) for item in results
                ):
                    raise ValueError("invalid Europe PMC results")
                summary = {
                    "total": data["hitCount"],
                    "next_cursor": data.get("nextCursorMark"),
                    "records": results,
                }
            else:
                if (
                    not isinstance(data, list)
                    or len(data) != 2
                    or not isinstance(data[0], dict)
                    or "page" not in data[0]
                    or (data[1] is not None and not isinstance(data[1], list))
                ):
                    raise ValueError("invalid World Bank response")
                summary = {"pagination": data[0], "records": data[1] or []}
            text = json.dumps(data, ensure_ascii=False, indent=2)
        kind = (
            "structured_data" if tool == "query_world_bank" else "metadata_or_abstracts"
        )
        return {
            **summary,
            "content_type": kind,
            "sources": [
                {
                    "origin": raw["origin"],
                    "title": tool,
                    "text": text,
                    "retrieved_at": raw["retrieved_at"],
                    "content_type": kind,
                    "coverage": kind,
                    "parser": "public-api-v1",
                }
            ],
            "failures": [],
        }
