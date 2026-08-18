"""Adapters between external services and the runtime's neutral tool contracts.

Adapters translate protocols.  They never choose research questions, rank
sources by quality, or decide when searching is finished -- those are semantic
judgments that belong to the Investigator and Curator, and moving any of them
down here is how a research system acquires a hidden completion heuristic.

Layout:

``_http``     shared request plumbing and the retry-relevant failure vocabulary
``web``       general web search (Tavily, Exa, Brave, Bocha, DuckDuckGo)
``academic``  keyless scholarly search (arXiv, Crossref, PubMed)
``reader``    the sole component permitted to fetch an arbitrary public URL
``llm``       model vendor registry and tier definitions
"""

import os
from collections.abc import Mapping, Sequence

import httpx

from ._http import (
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderUnavailableError,
    SourceReadError,
    UnsafeUrlError,
)
from .academic import (
    ArxivSearchProvider,
    CrossrefSearchProvider,
    PubMedSearchProvider,
)
from .llm import (
    LLM_PROVIDERS,
    LlmProviderSpec,
    ModelTier,
    configured_llm_providers,
    resolve_llm_provider,
)
from .reader import PublicHttpReader, PublicUrlPolicy
from .web import (
    BochaSearchProvider,
    BraveSearchProvider,
    DuckDuckGoSearchProvider,
    ExaSearchProvider,
    TavilySearchProvider,
)

#: Adapters that need a credential, and which environment variable supplies it.
#: A selected provider with no credential is skipped rather than failing the
#: run: losing one index degrades discovery, while stopping research does not.
_KEYED_WEB_PROVIDERS = {
    "tavily": ("TAVILY_API_KEY", TavilySearchProvider),
    "exa": ("EXA_API_KEY", ExaSearchProvider),
    "brave": ("BRAVE_SEARCH_API_KEY", BraveSearchProvider),
    "bocha": ("BOCHA_API_KEY", BochaSearchProvider),
}


def build_search_providers(
    names: Sequence[str],
    academic_names: Sequence[str] = (),
    *,
    environ: Mapping[str, str] | None = None,
    client: httpx.AsyncClient | None = None,
    ncbi_api_key: str = "",
    contact_email: str = "",
) -> tuple[object, ...]:
    """Instantiate the selected adapters, in the order the operator listed them.

    Order is the broker's routing preference, not a quality ranking: which
    source is authoritative for a given claim is a Curator judgment, and no part
    of this function is allowed to anticipate it.
    """

    source = os.environ if environ is None else environ
    built: list[object] = []
    for name in names:
        if name == "duckduckgo":
            built.append(DuckDuckGoSearchProvider(client=client))
            continue
        entry = _KEYED_WEB_PROVIDERS.get(name)
        if entry is None:
            raise ValueError(f"unknown search provider {name!r}")
        env_var, factory = entry
        key = source.get(env_var, "").strip()
        if key:
            built.append(factory(key, client=client))

    for name in academic_names:
        if name == "arxiv":
            built.append(ArxivSearchProvider(client=client))
        elif name == "crossref":
            built.append(CrossrefSearchProvider(client=client, mailto=contact_email))
        elif name == "pubmed":
            built.append(PubMedSearchProvider(client=client, api_key=ncbi_api_key))
        else:
            raise ValueError(f"unknown academic provider {name!r}")
    return tuple(built)


__all__ = [
    "LLM_PROVIDERS",
    "ArxivSearchProvider",
    "BochaSearchProvider",
    "BraveSearchProvider",
    "CrossrefSearchProvider",
    "DuckDuckGoSearchProvider",
    "ExaSearchProvider",
    "LlmProviderSpec",
    "ModelTier",
    "ProviderAuthError",
    "ProviderRateLimitError",
    "ProviderUnavailableError",
    "PubMedSearchProvider",
    "PublicHttpReader",
    "PublicUrlPolicy",
    "SourceReadError",
    "TavilySearchProvider",
    "UnsafeUrlError",
    "build_search_providers",
    "configured_llm_providers",
    "resolve_llm_provider",
]
