"""Transparent research tools and deterministic execution boundaries.

The broker exposes provider choice and failures to the Researcher.  It does
not rank evidence quality, decide whether research is complete, or impose a
task budget.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, replace
from typing import Literal, Protocol, Sequence
from urllib.parse import urlsplit, urlunsplit

ProviderHealth = Literal["healthy", "degraded", "unavailable"]
RoutingMode = Literal["auto", "prefer", "only", "exclude"]
SourceKind = Literal["web", "news"]


@dataclass(frozen=True)
class ProviderInfo:
    provider_id: str
    capabilities: tuple[str, ...]
    health: ProviderHealth = "healthy"

    def __post_init__(self) -> None:
        if not self.provider_id.strip():
            raise ValueError("provider_id must not be empty")


@dataclass(frozen=True)
class SearchRouting:
    """Which providers a search may reach, and how strictly.

    ``providers`` names vendors directly and is a *deployment* concern -- which
    vendor is cheapest or best-covered is not a research judgment.  A role
    instead states the ``capabilities`` its question needs (``academic`` for
    peer-reviewed literature and preprints, ``web`` for official sites and
    documentation) and the broker resolves that against what each provider
    declares about itself.  That keeps the model naming a research need rather
    than a runtime identity, and keeps the tool stable across deployments whose
    provider sets differ.

    It is also the main cost lever.  Under ``auto`` every eligible provider is
    queried, while capability routing avoids metered calls for questions that an
    academic index can answer directly.
    """

    mode: RoutingMode = "auto"
    providers: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.mode in {"prefer", "only"} and not self.providers:
            raise ValueError(f"{self.mode} routing requires at least one provider")
        if any(not provider.strip() for provider in self.providers):
            raise ValueError("provider IDs must not be empty")
        if any(not capability.strip() for capability in self.capabilities):
            raise ValueError("capabilities must not be empty")


@dataclass(frozen=True)
class SearchRequest:
    query: str
    intent: str
    source_kind: SourceKind = "web"
    routing: SearchRouting = SearchRouting()

    def __post_init__(self) -> None:
        if not self.query.strip():
            raise ValueError("query must not be empty")
        if not self.intent.strip():
            raise ValueError("intent must not be empty")
        if not isinstance(self.source_kind, str) or self.source_kind not in {
            "web",
            "news",
        }:
            raise ValueError("source_kind must be web or news")


@dataclass(frozen=True)
class ProviderResult:
    title: str
    url: str
    snippet: str = ""
    content: str = ""


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str = ""
    content: str = ""
    provider_ids: tuple[str, ...] = ()
    content_provider_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class SearchAttempt:
    provider_id: str
    status: Literal["success", "failed", "skipped"]
    result_count: int = 0
    error_type: str = ""


@dataclass(frozen=True)
class SearchResponse:
    results: tuple[SearchResult, ...]
    attempts: tuple[SearchAttempt, ...]


@dataclass(frozen=True)
class ReadResult:
    title: str
    url: str
    content: str


class SearchProvider(Protocol):
    async def describe(self) -> ProviderInfo: ...

    async def search(
        self, *, query: str, intent: str, source_kind: SourceKind
    ) -> Sequence[ProviderResult]: ...


def _normalized_url(url: str) -> str:
    parsed = urlsplit(url.strip())
    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        raise ValueError("search result URL must be HTTP(S) without credentials")
    host = parsed.hostname.lower() if parsed.hostname else ""
    port = parsed.port
    if port and not (
        parsed.scheme.lower() == "http" and port == 80
        or parsed.scheme.lower() == "https" and port == 443
    ):
        host = f"{host}:{port}"
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/")
    return urlunsplit((parsed.scheme.lower(), host, path, parsed.query, ""))


def _error_type(error: BaseException) -> str:
    name = type(error).__name__.lower()
    message = str(error).lower()
    if isinstance(error, TimeoutError) or "timeout" in name or "timed out" in message:
        return "timeout"
    # Before the rate-limit check: an exhausted quota is not throttling, and
    # retrying it spends nothing but wall-clock.
    if "quota" in name:
        return "quota_exhausted"
    if "rate" in name or "rate limit" in message or "429" in message:
        return "rate_limited"
    if "auth" in name or "unauthorized" in message or "401" in message:
        return "auth_failed"
    if "unavailable" in name or "connection" in name:
        return "provider_down"
    return "provider_error"


class TransparentSearchBroker:
    """Route searches while preserving provider provenance and failures."""

    def __init__(
        self,
        providers: Sequence[SearchProvider],
        *,
        rate_limit_retries: int = 1,
        provider_timeout_seconds: float = 45.0,
    ) -> None:
        if rate_limit_retries < 0:
            raise ValueError("rate_limit_retries must be non-negative")
        if provider_timeout_seconds <= 0:
            raise ValueError("provider_timeout_seconds must be positive")
        self._providers = tuple(providers)
        self._rate_limit_retries = rate_limit_retries
        self._provider_timeout_seconds = provider_timeout_seconds

    async def list_providers(self) -> tuple[ProviderInfo, ...]:
        described = await asyncio.gather(
            *(
                asyncio.wait_for(
                    provider.describe(), timeout=self._provider_timeout_seconds
                )
                for provider in self._providers
            ),
            return_exceptions=True,
        )
        infos: list[ProviderInfo] = []
        for index, (provider, value) in enumerate(
            zip(self._providers, described, strict=True), start=1
        ):
            if isinstance(value, BaseException):
                provider_id = str(
                    getattr(provider, "provider_id", "")
                    or getattr(getattr(provider, "info", None), "provider_id", "")
                    or f"provider-{index}"
                )
                infos.append(ProviderInfo(provider_id, (), "unavailable"))
            else:
                infos.append(value)
        seen: set[str] = set()
        for info in infos:
            if info.provider_id in seen:
                raise ValueError(f"duplicate provider_id {info.provider_id!r}")
            seen.add(info.provider_id)
        return tuple(infos)

    async def search(self, request: SearchRequest) -> SearchResponse:
        infos = await self.list_providers()
        providers_by_id = {
            info.provider_id: (provider, info)
            for provider, info in zip(self._providers, infos, strict=True)
        }
        selected, skipped = self._select(
            request.routing, providers_by_id, request.source_kind
        )
        if request.routing.mode == "prefer":
            preferred_ids = set(request.routing.providers)
            preferred = [item for item in selected if item[1].provider_id in preferred_ids]
            fallback = [item for item in selected if item[1].provider_id not in preferred_ids]
            completed = list(
                await asyncio.gather(
                    *(
                        self._call_provider(provider, info, request)
                        for provider, info in preferred
                    )
                )
            )
            preferred_succeeded = any(
                any(attempt.status == "success" for attempt in attempts)
                for _results, attempts in completed
            )
            if not preferred_succeeded and fallback:
                completed.extend(
                    await asyncio.gather(
                        *(
                            self._call_provider(provider, info, request)
                            for provider, info in fallback
                        )
                    )
                )
        else:
            completed = list(
                await asyncio.gather(
                    *(
                        self._call_provider(provider, info, request)
                        for provider, info in selected
                    )
                )
            )

        attempts = list(skipped)
        grouped: dict[str, list[SearchResult]] = {}
        order: list[str] = []
        for provider_results, provider_attempts in completed:
            attempts.extend(provider_attempts)
            for result in provider_results:
                key = _normalized_url(result.url)
                if key not in grouped:
                    grouped[key] = [result]
                    order.append(key)
                    continue
                variants = grouped[key]
                matching_index = next(
                    (
                        index
                        for index, existing in enumerate(variants)
                        if existing.content == result.content
                    ),
                    None,
                )
                if matching_index is None and result.content:
                    matching_index = next(
                        (
                            index
                            for index, existing in enumerate(variants)
                            if not existing.content
                        ),
                        None,
                    )
                if matching_index is None and not result.content:
                    matching_index = 0
                if matching_index is None:
                    variants.append(result)
                    continue
                existing = variants[matching_index]
                variants[matching_index] = replace(
                    existing,
                    content=existing.content or result.content,
                    snippet=existing.snippet or result.snippet,
                    provider_ids=tuple(
                        dict.fromkeys(existing.provider_ids + result.provider_ids)
                    ),
                    content_provider_ids=tuple(
                        dict.fromkeys(
                            existing.content_provider_ids
                            + result.content_provider_ids
                        )
                    ),
                )

        merged: list[SearchResult] = []
        for key in order:
            variants = grouped[key]
            discovered_by = tuple(
                dict.fromkeys(
                    provider_id
                    for result in variants
                    for provider_id in result.provider_ids
                )
            )
            merged.extend(
                replace(result, provider_ids=discovered_by) for result in variants
            )
        return SearchResponse(
            results=tuple(merged), attempts=tuple(attempts)
        )

    @staticmethod
    def _select(
        routing: SearchRouting,
        providers_by_id: dict[str, tuple[SearchProvider, ProviderInfo]],
        source_kind: SourceKind,
    ) -> tuple[
        list[tuple[SearchProvider, ProviderInfo]], list[SearchAttempt]
    ]:
        requested = tuple(dict.fromkeys(routing.providers))
        unknown = [item for item in requested if item not in providers_by_id]
        if unknown:
            raise ValueError(f"unknown search providers: {', '.join(unknown)}")

        ordered_ids = list(providers_by_id)
        if routing.mode == "only":
            ordered_ids = list(requested)
        elif routing.mode == "prefer":
            ordered_ids = list(requested) + [
                item for item in ordered_ids if item not in requested
            ]
        elif routing.mode == "exclude":
            ordered_ids = [item for item in ordered_ids if item not in requested]

        selected: list[tuple[SearchProvider, ProviderInfo]] = []
        skipped: list[SearchAttempt] = []
        for provider_id in ordered_ids:
            provider, info = providers_by_id[provider_id]
            if info.health == "unavailable":
                skipped.append(
                    SearchAttempt(
                        provider_id=provider_id,
                        status="skipped",
                        error_type="provider_unavailable",
                    )
                )
                continue
            declared_source_kinds = {"web", "news"}.intersection(info.capabilities)
            if declared_source_kinds and source_kind not in declared_source_kinds:
                skipped.append(
                    SearchAttempt(
                        provider_id=provider_id,
                        status="skipped",
                        error_type="unsupported_source_kind",
                    )
                )
                continue
            if routing.capabilities and not set(routing.capabilities).intersection(
                info.capabilities
            ):
                # Recorded rather than silently dropped: a role that asked for
                # academic sources and got nothing must be able to tell "no such
                # literature" from "no academic provider is configured here".
                skipped.append(
                    SearchAttempt(
                        provider_id=provider_id,
                        status="skipped",
                        error_type="capability_not_declared",
                    )
                )
                continue
            selected.append((provider, info))
        return selected, skipped

    async def _call_provider(
        self,
        provider: SearchProvider,
        info: ProviderInfo,
        request: SearchRequest,
    ) -> tuple[list[SearchResult], list[SearchAttempt]]:
        attempts: list[SearchAttempt] = []
        for attempt_index in range(self._rate_limit_retries + 1):
            try:
                raw = await asyncio.wait_for(
                    provider.search(
                        query=request.query.strip(),
                        intent=request.intent.strip(),
                        source_kind=request.source_kind,
                    ),
                    timeout=self._provider_timeout_seconds,
                )
                results: list[SearchResult] = []
                for item in raw:
                    if not isinstance(item.url, str):
                        continue
                    try:
                        _normalized_url(item.url)
                    except (TypeError, ValueError):
                        continue
                    results.append(
                        SearchResult(
                            title=item.title.strip(),
                            url=item.url.strip(),
                            snippet=item.snippet.strip(),
                            content=item.content,
                            provider_ids=(info.provider_id,),
                            content_provider_ids=(info.provider_id,)
                            if item.content
                            else (),
                        )
                    )
                attempts.append(
                    SearchAttempt(
                        provider_id=info.provider_id,
                        status="success",
                        result_count=len(results),
                    )
                )
                return results, attempts
            except Exception as error:  # provider failures are research observations
                kind = _error_type(error)
                if kind in {"timeout", "provider_down"}:
                    # A request may have run even though its response never became
                    # usable.  Let the enclosing operation ledger freeze it rather
                    # than hiding a retry or reporting "no results" to the Agent.
                    raise
                attempts.append(
                    SearchAttempt(
                        provider_id=info.provider_id,
                        status="failed",
                        error_type=kind,
                    )
                )
                if (
                    kind != "rate_limited"
                    or attempt_index >= self._rate_limit_retries
                ):
                    break
        return [], attempts


__all__ = [
    "ProviderHealth",
    "ProviderInfo",
    "ProviderResult",
    "ReadResult",
    "RoutingMode",
    "SearchAttempt",
    "SearchProvider",
    "SearchRequest",
    "SearchResponse",
    "SearchResult",
    "SearchRouting",
    "SourceKind",
    "TransparentSearchBroker",
]
