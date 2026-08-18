"""Academic search adapters: arXiv, Crossref, and PubMed.

These matter disproportionately for research quality and cost nothing: all three
are keyless public APIs, so an evidence base can reach primary literature even
when no commercial search key is configured.

They also change *what* is discoverable.  General web search surfaces coverage
of a study; these surface the study, its DOI, its version history, and its
retraction status -- which is the difference between citing a press release and
citing the trial it describes.

Adapters return discovery leads with metadata.  Whether a paper actually
supports a claim stays a Curator judgment made against the saved full text.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any
from xml.etree import ElementTree

import httpx

from ..tools import ProviderInfo, ProviderResult, SourceKind
from ._http import (
    ProviderUnavailableError,
    request_provider_json,
    request_provider_text,
)

_ATOM = {"atom": "http://www.w3.org/2005/Atom"}


def _joined_authors(names: Sequence[str], limit: int = 6) -> str:
    if not names:
        return ""
    shown = list(names[:limit])
    if len(names) > limit:
        shown.append("et al.")
    return ", ".join(shown)


def _snippet(*parts: str) -> str:
    return "\n".join(part.strip() for part in parts if part and part.strip())


@dataclass(slots=True)
class ArxivSearchProvider:
    """arXiv preprints; keyless, and the fastest route to methods sections.

    Preprints are not peer reviewed.  The adapter surfaces the version and date
    so a Curator can record that boundary rather than discovering it later.
    """

    max_results: int = 10
    client: httpx.AsyncClient | None = field(default=None, repr=False)
    provider_id: str = "arxiv"

    def __post_init__(self) -> None:
        if not 1 <= self.max_results <= 50:
            raise ValueError("arXiv max_results must be between 1 and 50")

    async def describe(self) -> ProviderInfo:
        return ProviderInfo(
            self.provider_id, ("academic", "preprint", "keyless", "full_text_pdf")
        )

    async def search(
        self, *, query: str, intent: str, source_kind: SourceKind
    ) -> Sequence[ProviderResult]:
        body = await request_provider_text(
            self.provider_id,
            method="GET",
            url="https://export.arxiv.org/api/query",
            client=self.client,
            params={
                "search_query": f"all:{query}",
                "start": 0,
                "max_results": self.max_results,
                "sortBy": "relevance",
            },
        )
        try:
            feed = ElementTree.fromstring(body)
        except ElementTree.ParseError as exc:
            raise ProviderUnavailableError("arxiv returned invalid Atom XML") from exc

        results: list[ProviderResult] = []
        for entry in feed.findall("atom:entry", _ATOM):
            url = (entry.findtext("atom:id", "", _ATOM) or "").strip()
            title = " ".join((entry.findtext("atom:title", "", _ATOM) or "").split())
            if not url or not title:
                continue
            authors = [
                " ".join((node.findtext("atom:name", "", _ATOM) or "").split())
                for node in entry.findall("atom:author", _ATOM)
            ]
            summary = " ".join(
                (entry.findtext("atom:summary", "", _ATOM) or "").split()
            )
            published = (entry.findtext("atom:published", "", _ATOM) or "")[:10]
            results.append(
                ProviderResult(
                    title=title,
                    url=url,
                    snippet=_snippet(
                        _joined_authors([a for a in authors if a]),
                        f"arXiv preprint, {published}" if published else "",
                        summary,
                    ),
                )
            )
        return results


@dataclass(slots=True)
class CrossrefSearchProvider:
    """Crossref DOI metadata; keyless, and authoritative for versions of record.

    Crossref is the registry, not the text.  Its value here is resolving what a
    citation actually refers to -- publisher, type, date, and any update notice
    such as a correction or retraction that a web snippet would not mention.
    """

    max_results: int = 10
    mailto: str = ""
    client: httpx.AsyncClient | None = field(default=None, repr=False)
    provider_id: str = "crossref"

    def __post_init__(self) -> None:
        if not 1 <= self.max_results <= 50:
            raise ValueError("Crossref max_results must be between 1 and 50")

    async def describe(self) -> ProviderInfo:
        return ProviderInfo(
            self.provider_id, ("academic", "doi", "keyless", "version_of_record")
        )

    async def search(
        self, *, query: str, intent: str, source_kind: SourceKind
    ) -> Sequence[ProviderResult]:
        params: dict[str, Any] = {"query": query, "rows": self.max_results}
        if self.mailto:
            # Crossref's polite pool: identifying the caller buys better service
            # and is the documented courtesy for automated use.
            params["mailto"] = self.mailto
        data = await request_provider_json(
            self.provider_id,
            method="GET",
            url="https://api.crossref.org/works",
            headers={"Accept": "application/json"},
            client=self.client,
            params=params,
        )
        message = data.get("message", {})
        items = message.get("items", ()) if isinstance(message, dict) else ()
        if not isinstance(items, list):
            raise ProviderUnavailableError("crossref response has no item list")

        results: list[ProviderResult] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            doi = str(item.get("DOI", "")).strip()
            url = str(item.get("URL", "")).strip() or (
                f"https://doi.org/{doi}" if doi else ""
            )
            titles = item.get("title", ())
            title = str(titles[0]).strip() if isinstance(titles, list) and titles else ""
            if not url or not title:
                continue
            authors = [
                " ".join(
                    part
                    for part in (
                        str(person.get("given", "")).strip(),
                        str(person.get("family", "")).strip(),
                    )
                    if part
                )
                for person in item.get("author", ())
                if isinstance(person, dict)
            ]
            container = item.get("container-title", ())
            venue = (
                str(container[0]).strip()
                if isinstance(container, list) and container
                else str(item.get("publisher", "")).strip()
            )
            issued = item.get("issued", {})
            parts = issued.get("date-parts", ()) if isinstance(issued, dict) else ()
            year = (
                str(parts[0][0])
                if isinstance(parts, list) and parts and parts[0]
                else ""
            )
            updates = item.get("update-to", ())
            notices = (
                ", ".join(
                    str(update.get("type", "")).strip()
                    for update in updates
                    if isinstance(update, dict) and update.get("type")
                )
                if isinstance(updates, list)
                else ""
            )
            results.append(
                ProviderResult(
                    title=title,
                    url=url,
                    snippet=_snippet(
                        _joined_authors([a for a in authors if a]),
                        " ".join(part for part in (venue, year) if part),
                        str(item.get("type", "")).replace("-", " "),
                        f"update notice: {notices}" if notices else "",
                    ),
                )
            )
        return results


@dataclass(slots=True)
class PubMedSearchProvider:
    """PubMed biomedical literature through NCBI E-utilities.

    Keyless by default; an NCBI API key only raises the rate limit.  Two calls
    are required by the API's design -- esearch returns PMIDs, esummary turns
    them into citable metadata.
    """

    max_results: int = 10
    api_key: str = field(default="", repr=False)
    client: httpx.AsyncClient | None = field(default=None, repr=False)
    provider_id: str = "pubmed"

    def __post_init__(self) -> None:
        if not 1 <= self.max_results <= 50:
            raise ValueError("PubMed max_results must be between 1 and 50")

    async def describe(self) -> ProviderInfo:
        return ProviderInfo(
            self.provider_id, ("academic", "biomedical", "keyless", "peer_reviewed")
        )

    def _credentials(self) -> dict[str, str]:
        return {"api_key": self.api_key} if self.api_key else {}

    async def search(
        self, *, query: str, intent: str, source_kind: SourceKind
    ) -> Sequence[ProviderResult]:
        found = await request_provider_json(
            self.provider_id,
            method="GET",
            url="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            headers={"Accept": "application/json"},
            client=self.client,
            params={
                "db": "pubmed",
                "term": query,
                "retmax": self.max_results,
                "retmode": "json",
                "sort": "relevance",
                **self._credentials(),
            },
        )
        result = found.get("esearchresult", {})
        identifiers = result.get("idlist", ()) if isinstance(result, dict) else ()
        if not isinstance(identifiers, list) or not identifiers:
            return ()

        summaries = await request_provider_json(
            self.provider_id,
            method="GET",
            url="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
            headers={"Accept": "application/json"},
            client=self.client,
            params={
                "db": "pubmed",
                "id": ",".join(str(value) for value in identifiers),
                "retmode": "json",
                **self._credentials(),
            },
        )
        payload = summaries.get("result", {})
        if not isinstance(payload, dict):
            raise ProviderUnavailableError("pubmed response has no result object")

        results: list[ProviderResult] = []
        for identifier in identifiers:
            item = payload.get(str(identifier))
            if not isinstance(item, dict):
                continue
            title = " ".join(str(item.get("title", "")).split())
            if not title:
                continue
            authors = [
                str(person.get("name", "")).strip()
                for person in item.get("authors", ())
                if isinstance(person, dict) and person.get("name")
            ]
            types = item.get("pubtype", ())
            kinds = (
                ", ".join(str(value) for value in types)
                if isinstance(types, list)
                else ""
            )
            results.append(
                ProviderResult(
                    title=title,
                    url=f"https://pubmed.ncbi.nlm.nih.gov/{identifier}/",
                    snippet=_snippet(
                        _joined_authors(authors),
                        " ".join(
                            part
                            for part in (
                                str(item.get("source", "")).strip(),
                                str(item.get("pubdate", "")).strip(),
                            )
                            if part
                        ),
                        kinds,
                    ),
                )
            )
        return results


__all__ = [
    "ArxivSearchProvider",
    "CrossrefSearchProvider",
    "PubMedSearchProvider",
]
