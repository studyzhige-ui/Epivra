"""Credential validation and model discovery, before a key is trusted.

Checking that a key is a non-empty string proves nothing.  A typo, a revoked key,
a key for the wrong vendor, or an account without access all look identical until
something is actually asked of the API -- and finding out during a research run
means the failure lands hours later, after the user has already approved and
started spending.

Both checks here use **listing endpoints**, which authenticate the caller and
return the model catalogue without running inference, so validation costs nothing
in tokens.  ``GET /v1/models`` serves both the OpenAI-compatible vendors and
Anthropic; only the auth header differs.

The catalogue matters as much as the check: a model list must come from the
vendor rather than being hardcoded in the interface, or the day a vendor ships a
new model the tool silently cannot use it.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

import httpx

from .llm import LlmProviderSpec

#: Long enough for a slow gateway, short enough that a wrong endpoint does not
#: leave the user watching a spinner.
VALIDATION_TIMEOUT_SECONDS = 20.0

#: Anthropic requires this header on every request, listing included.
ANTHROPIC_VERSION = "2023-06-01"


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Whether a credential works, and what it can reach.

    ``reason`` is written for a user, not a log: "the key was rejected" is
    actionable, ``HTTPStatusError(401)`` is not.
    """

    provider: str
    ok: bool
    reason: str = ""
    models: tuple[str, ...] = field(default_factory=tuple)

    @property
    def model_count(self) -> int:
        return len(self.models)


def _reason_for_status(status: int) -> str:
    if status in (401, 403):
        return "密钥被拒绝（401/403）——检查是否复制完整、是否属于这家厂商"
    if status == 404:
        return "端点不存在（404）——这个厂商的接口地址可能已变更"
    if status == 429:
        return "被限流（429）——稍后重试"
    if status >= 500:
        return f"厂商服务暂时不可用（{status}）"
    return f"请求被拒绝（HTTP {status}）"


def _extract_models(payload: object) -> tuple[str, ...]:
    """Pull model ids out of either vendor's listing shape."""

    if not isinstance(payload, dict):
        return ()
    rows = payload.get("data")
    if not isinstance(rows, list):
        return ()
    found: list[str] = []
    for row in rows:
        if isinstance(row, dict):
            identifier = row.get("id") or row.get("name")
            if isinstance(identifier, str) and identifier.strip():
                found.append(identifier.strip())
        elif isinstance(row, str) and row.strip():
            found.append(row.strip())
    return tuple(dict.fromkeys(found))


def _listing_request(spec: LlmProviderSpec, api_key: str) -> tuple[str, dict[str, str]]:
    base = spec.api_base.rstrip("/")
    if spec.protocol == "anthropic":
        return (
            f"{base}/v1/models",
            {"x-api-key": api_key, "anthropic-version": ANTHROPIC_VERSION},
        )
    # OpenAI-compatible bases already include /v1 for some vendors and not for
    # others, so the suffix is added only when it is missing.
    url = base if base.endswith("/v1") else f"{base}/v1"
    return f"{url}/models", {"Authorization": f"Bearer {api_key}"}


async def validate_llm_credentials(
    spec: LlmProviderSpec,
    api_key: str,
    *,
    client: httpx.AsyncClient | None = None,
    timeout_seconds: float = VALIDATION_TIMEOUT_SECONDS,
) -> ValidationResult:
    """Authenticate against the vendor's model listing.  Never runs inference.

    A vendor that authenticates but exposes no listing is still reported ``ok``
    with an empty catalogue: the credential is proven, and the interface can fall
    back to the registry's default model pair rather than blocking the user over
    a missing convenience.
    """

    if not api_key.strip():
        return ValidationResult(spec.name, False, "密钥为空")

    url, headers = _listing_request(spec, api_key.strip())
    owns_client = client is None
    transport = client or httpx.AsyncClient(timeout=timeout_seconds)
    try:
        try:
            response = await transport.get(url, headers=headers)
        except (httpx.TimeoutException, httpx.NetworkError) as error:
            return ValidationResult(
                spec.name, False, f"无法连接 {spec.label}（{type(error).__name__}）"
            )
    finally:
        if owns_client:
            await transport.aclose()

    if response.status_code >= 400:
        return ValidationResult(spec.name, False, _reason_for_status(response.status_code))

    try:
        payload = response.json()
    except ValueError:
        return ValidationResult(spec.name, True, "", ())
    return ValidationResult(spec.name, True, "", _extract_models(payload))


def suggest_models(
    spec: LlmProviderSpec, catalogue: Sequence[str], *, fast: bool
) -> tuple[str, ...]:
    """Order a catalogue so the likely-right model is first, without filtering.

    The registry's own default for the tier is surfaced first when the vendor
    still lists it.  Everything else stays selectable -- the tier split is a
    recommendation about cost and speed, not a restriction, and a user who wants
    a strong model doing investigation is allowed to have one.
    """

    preferred = spec.fast_model if fast else spec.reasoning_model
    ordered = [name for name in catalogue if name == preferred]
    ordered += [name for name in catalogue if name != preferred]
    if not ordered:
        # No catalogue: offer the registry pair so setup can still complete.
        ordered = [preferred]
    return tuple(ordered)


async def validate_search_credentials(
    provider_id: str,
    api_key: str,
    *,
    client: httpx.AsyncClient | None = None,
) -> ValidationResult:
    """Prove a search credential with the smallest real query the vendor allows.

    Unlike the model vendors these expose no free listing endpoint, so the check
    is one search for one result -- the minimum-cost request to use when no
    metadata endpoint exists.  A single credit spent at setup is worth far more
    than discovering a dead key an hour into a study.

    The vendor's own adapter performs the call, so validation exercises exactly
    the code path research will use rather than a parallel implementation that
    could pass while the real one fails.
    """

    from . import build_search_providers
    from ._http import (
        ProviderAuthError,
        ProviderRateLimitError,
        ProviderUnavailableError,
    )

    if not api_key.strip():
        return ValidationResult(provider_id, False, "密钥为空")

    credentials = search_credential_variables()
    env_var = credentials.get(provider_id)
    if env_var is None:
        return ValidationResult(provider_id, False, f"未知的搜索厂商 {provider_id!r}")

    built = build_search_providers(
        (provider_id,), (), environ={env_var: api_key.strip()}, client=client
    )
    if not built:
        return ValidationResult(provider_id, False, "适配器未能创建（密钥被忽略）")

    provider = built[0]
    try:
        results = await provider.search(
            query="deep research validation probe", intent="validate", source_kind="web"
        )
    except ProviderAuthError:
        return ValidationResult(provider_id, False, "密钥被拒绝——检查是否复制完整")
    except ProviderRateLimitError:
        return ValidationResult(provider_id, False, "被限流，稍后重试")
    except ProviderUnavailableError as error:
        return ValidationResult(
            provider_id, False, f"无法连接（{type(error).__name__}）"
        )
    except Exception as error:  # noqa: BLE001 - reported to the user verbatim
        return ValidationResult(
            provider_id, False, f"{type(error).__name__}: {str(error)[:120]}"
        )

    # Zero results is not a credential failure: the probe query is deliberately
    # meaningless, and some indexes legitimately return nothing for it.
    return ValidationResult(provider_id, True, "", (f"{len(results)} results",))


def search_credential_variables() -> dict[str, str]:
    """Which environment variable supplies each keyed search provider."""

    from . import search_credentials

    return dict(search_credentials())


__all__ = [
    "ANTHROPIC_VERSION",
    "VALIDATION_TIMEOUT_SECONDS",
    "ValidationResult",
    "search_credential_variables",
    "suggest_models",
    "validate_llm_credentials",
    "validate_search_credentials",
]
