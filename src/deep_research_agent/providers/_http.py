"""Shared HTTP plumbing and transparent failure classification for adapters.

Every adapter reports failure in the same vocabulary, because the distinction
that matters downstream is not which vendor broke but whether the caller may
retry: an Investigator must never record "provider unavailable" as "no evidence
exists".
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx


class ProviderAuthError(RuntimeError):
    """Credentials were rejected; retrying the same call cannot help."""


class ProviderRateLimitError(RuntimeError):
    """The provider throttled this call; a bounded backoff may succeed."""


class ProviderQuotaError(RuntimeError):
    """The account cannot pay for this call; no amount of retrying helps.

    Distinct from auth (the key is fine) and from throttling (waiting will not
    restore credit).  Worth its own class because an exhausted key is a resource
    fact the user has to act on, and reporting it as a generic error is how "we
    silently stopped searching" hides in a run.
    """


class ProviderUnavailableError(RuntimeError):
    """The provider could not serve the request; other providers may still."""


class UnsafeUrlError(ValueError):
    """A URL is outside the public, read-only network boundary."""


class SourceReadError(RuntimeError):
    """A public source could not be read within the deterministic boundary."""


def raise_provider_status(provider_id: str, status_code: int) -> None:
    """Map an HTTP status onto the shared, retry-relevant failure vocabulary."""

    message = f"{provider_id} request failed with HTTP {status_code}"
    if status_code in {401, 403}:
        raise ProviderAuthError(message)
    # 402 is the HTTP-standard "payment required" that DeepSeek and others use for
    # an empty balance; Tavily answers 432/433 for a plan or account usage limit.
    # Left unmapped, an out-of-credit key surfaced as a bare RuntimeError, which
    # reads like a crash instead of "top up".
    if status_code in {402, 432, 433}:
        raise ProviderQuotaError(f"{message}（额度或余额不足）")
    if status_code == 429:
        raise ProviderRateLimitError(message)
    if status_code >= 500:
        raise ProviderUnavailableError(message)
    raise RuntimeError(message)


async def request_provider_json(
    provider_id: str,
    *,
    method: str,
    url: str,
    headers: Mapping[str, str],
    client: httpx.AsyncClient | None,
    params: Mapping[str, Any] | None = None,
    payload: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    """Issue one JSON request to a fixed provider origin."""

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
        raise_provider_status(provider_id, response.status_code)
    try:
        data = response.json()
    except ValueError as exc:
        raise ProviderUnavailableError(
            f"{provider_id} returned invalid JSON"
        ) from exc
    if not isinstance(data, dict):
        raise ProviderUnavailableError(f"{provider_id} response is not an object")
    return data


async def request_provider_text(
    provider_id: str,
    *,
    method: str,
    url: str,
    client: httpx.AsyncClient | None,
    headers: Mapping[str, str] | None = None,
    params: Mapping[str, Any] | None = None,
    data: Mapping[str, str] | None = None,
) -> str:
    """Issue one request whose response body is text (XML, HTML) rather than JSON."""

    owns_client = client is None
    transport = client or httpx.AsyncClient(timeout=30.0, follow_redirects=True)
    try:
        try:
            response = await transport.request(
                method,
                url,
                headers=dict(headers or {}),
                params=dict(params or {}),
                data=dict(data) if data is not None else None,
            )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise ProviderUnavailableError(
                f"{provider_id} request unavailable"
            ) from exc
    finally:
        if owns_client:
            await transport.aclose()
    if response.status_code >= 400:
        raise_provider_status(provider_id, response.status_code)
    return response.text


__all__ = [
    "ProviderAuthError",
    "ProviderQuotaError",
    "ProviderRateLimitError",
    "ProviderUnavailableError",
    "SourceReadError",
    "UnsafeUrlError",
    "raise_provider_status",
    "request_provider_json",
    "request_provider_text",
]
