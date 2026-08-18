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
    "ProviderRateLimitError",
    "ProviderUnavailableError",
    "SourceReadError",
    "UnsafeUrlError",
    "raise_provider_status",
    "request_provider_json",
    "request_provider_text",
]
