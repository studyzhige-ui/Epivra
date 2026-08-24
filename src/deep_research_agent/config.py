"""Deployment wiring: which models each role uses, and which providers exist.

This module answers "how is *this* installation configured", and nothing else.
It holds no research semantics: it cannot decide when research is finished, how
many sources suffice, or which evidence matters.

The one policy it does own is **cost**.  Roles differ enormously in how much
reasoning they need and how often they run, so binding every role to one
expensive model wastes most of the spend on work that does not benefit:

============  ======  ================================================
role          tier    why
============  ======  ================================================
architect     strong  shapes the whole task; a bad Contract wastes all
                      downstream spend
lead          strong  the hardest open-ended judgment in the system
analyst       strong  cross-source synthesis, conflicts, uncertainty
author        strong  long-form structure and tone over the full report
reviewer      strong  must catch what a strong Author got wrong
curator       strong  the source-faithfulness boundary; a cheap mistake
                      here corrupts every downstream product
investigator  fast    highest call volume by far, and its work is
                      bounded and well specified per assignment
============  ======  ================================================

Investigator is the cost driver -- many parallel assignments times many tool
calls each -- so it is the tier that matters. Curator stays strong on purpose:
it is the only role that decides whether a paraphrase still means what the
source said, and that is not a place to save money.

Every assignment is overridable per role, because these are defaults from
reasoning about the work, not measurements. Phase 2's evaluation harness is what
should eventually settle them.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal

from .providers.llm import (
    MODEL_EFFORTS,
    LlmProviderSpec,
    ModelEffort,
    ModelLimits,
    ModelTier,
    resolve_llm_provider,
)

Role = Literal[
    "architect",
    "lead",
    "investigator",
    "curator",
    "analyst",
    "author",
    "reviewer",
]

ROLES: tuple[Role, ...] = (
    "architect",
    "lead",
    "investigator",
    "curator",
    "analyst",
    "author",
    "reviewer",
)

#: Default tier per role.  See the module docstring for the reasoning.
DEFAULT_ROLE_TIERS: Mapping[Role, ModelTier] = {
    "architect": "reasoning",
    "lead": "reasoning",
    "investigator": "fast",
    "curator": "reasoning",
    "analyst": "reasoning",
    "author": "reasoning",
    "reviewer": "reasoning",
}

#: Default reasoning effort per role.  The split follows the tier split for the
#: same reason: the Investigator makes the most calls on the most bounded work, so
#: it is where lowering effort saves the most and costs the least.  Author and
#: Reviewer sit one step above the rest because long-form structure and catching
#: what a strong Author got wrong are the two hardest judgments in the system.
DEFAULT_ROLE_EFFORT: Mapping[Role, ModelEffort] = {
    "architect": "high",
    "lead": "high",
    "investigator": "low",
    "curator": "high",
    "analyst": "high",
    "author": "xhigh",
    "reviewer": "xhigh",
}

#: Web search adapters an operator may enable, by provider id.
WEB_SEARCH_PROVIDERS: frozenset[str] = frozenset(
    {"tavily", "exa", "brave", "bocha", "duckduckgo"}
)
#: Academic adapters.  All three are keyless, so they are enabled by default.
ACADEMIC_SEARCH_PROVIDERS: frozenset[str] = frozenset(
    {"arxiv", "crossref", "pubmed"}
)

_ENV_PREFIX = "DEEP_RESEARCH"


class ConfigError(ValueError):
    """The runtime is configured in a way that cannot be honoured."""


def _env(environ: Mapping[str, str], name: str, default: str = "") -> str:
    return environ.get(f"{_ENV_PREFIX}_{name}", default).strip()


def _env_flag(environ: Mapping[str, str], name: str, default: bool) -> bool:
    raw = _env(environ, name).casefold()
    if not raw:
        return default
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    raise ConfigError(f"{_ENV_PREFIX}_{name} must be a boolean, got {raw!r}")


def _env_list(environ: Mapping[str, str], name: str) -> tuple[str, ...]:
    raw = _env(environ, name)
    if not raw:
        return ()
    return tuple(
        item.strip().casefold() for item in raw.split(",") if item.strip()
    )


@dataclass(frozen=True, slots=True)
class RoleModel:
    """The exact model one role will call, and how to reach it."""

    role: Role
    provider: LlmProviderSpec
    model_id: str
    tier: ModelTier
    #: Input and output ceilings this role runs under.  Carried per role rather
    #: than looked up per call, because an operator may raise one role's output
    #: ceiling (an Author writing a deep report) without touching the others.
    limits: ModelLimits = ModelLimits(context=128_000, output=32_000)
    effort: ModelEffort = "high"

    @property
    def api_base(self) -> str:
        return self.provider.api_base

    def api_key(self, environ: Mapping[str, str] | None = None) -> str:
        """Read the credential at call time; it never enters durable state."""

        key = self.provider.api_key(environ)
        if not key:
            raise ConfigError(
                f"role {self.role!r} needs {self.provider.key_env_var}, which is "
                "not configured"
            )
        return key


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    """Everything this installation needs to make external calls."""

    role_models: Mapping[Role, RoleModel]
    search_providers: tuple[str, ...]
    academic_providers: tuple[str, ...]
    contact_email: str = ""
    ncbi_api_key: str = field(default="", repr=False)

    def model_for(self, role: Role) -> RoleModel:
        if role not in self.role_models:
            raise ConfigError(f"no model configured for role {role!r}")
        return self.role_models[role]


def _env_positive_int(environ: Mapping[str, str], name: str) -> int | None:
    """Read a positive integer override, or None when unset."""

    raw = _env(environ, name)
    if not raw:
        return None
    try:
        value = int(raw)
    except ValueError as error:
        raise ConfigError(
            f"{_ENV_PREFIX}_{name} must be a positive integer, got {raw!r}"
        ) from error
    if value < 1:
        raise ConfigError(f"{_ENV_PREFIX}_{name} must be positive, got {value}")
    return value


def _resolve_limits(
    environ: Mapping[str, str], role: Role, spec: LlmProviderSpec, tier: ModelTier
) -> ModelLimits:
    """The ceilings this role runs under: registry floor, then any override.

    Both are overridable per role because they answer different questions an
    operator legitimately has: "how much can this vendor actually take" (the
    registry only knows a floor) and "how long a report is this role allowed to
    emit" (a delivery decision).
    """

    floor = spec.default_limits(tier)
    return ModelLimits(
        context=_env_positive_int(environ, f"{role.upper()}_CONTEXT_LIMIT")
        or floor.context,
        output=_env_positive_int(environ, f"{role.upper()}_OUTPUT_CEILING")
        or floor.output,
    )


def _resolve_effort(environ: Mapping[str, str], role: Role) -> ModelEffort:
    declared = _env(environ, f"{role.upper()}_EFFORT").casefold()
    if not declared:
        return DEFAULT_ROLE_EFFORT[role]
    if declared not in MODEL_EFFORTS:
        raise ConfigError(
            f"{_ENV_PREFIX}_{role.upper()}_EFFORT must be one of "
            f"{list(MODEL_EFFORTS)}, got {declared!r}"
        )
    return declared  # type: ignore[return-value]


def load_config(environ: Mapping[str, str] | None = None) -> RuntimeConfig:
    """Build the runtime configuration from the environment.

    Resolution order for a role's model, most specific first:

    1. ``DEEP_RESEARCH_<ROLE>_MODEL`` -- an exact model for one role
    2. ``DEEP_RESEARCH_<TIER>_MODEL`` -- an exact model for one tier
    3. the provider registry's default for that tier

    The provider is ``DEEP_RESEARCH_LLM_PROVIDER`` (default ``deepseek``), with
    ``DEEP_RESEARCH_<ROLE>_PROVIDER`` allowing a role to use a different vendor
    entirely -- so a deployment can run cheap local investigation against one
    vendor and expensive synthesis against another.

    Execution limits resolve the same way: ``DEEP_RESEARCH_<ROLE>_CONTEXT_LIMIT``,
    ``DEEP_RESEARCH_<ROLE>_OUTPUT_CEILING`` and ``DEEP_RESEARCH_<ROLE>_EFFORT``
    override the registry's conservative floors and the per-role effort defaults.
    """

    source = os.environ if environ is None else environ
    default_provider = resolve_llm_provider(_env(source, "LLM_PROVIDER", "deepseek"))

    tier_overrides = {
        tier: _env(source, f"{tier.upper()}_MODEL") for tier in ("reasoning", "fast")
    }

    role_models: dict[Role, RoleModel] = {}
    for role in ROLES:
        tier: ModelTier = DEFAULT_ROLE_TIERS[role]
        declared_tier = _env(source, f"{role.upper()}_TIER").casefold()
        if declared_tier:
            if declared_tier not in ("reasoning", "fast"):
                raise ConfigError(
                    f"{_ENV_PREFIX}_{role.upper()}_TIER must be 'reasoning' or "
                    f"'fast', got {declared_tier!r}"
                )
            tier = declared_tier  # type: ignore[assignment]

        provider = default_provider
        declared_provider = _env(source, f"{role.upper()}_PROVIDER")
        if declared_provider:
            provider = resolve_llm_provider(declared_provider)

        model_id = (
            _env(source, f"{role.upper()}_MODEL")
            or (tier_overrides[tier] if provider is default_provider else "")
            or provider.default_model(tier)
        )
        role_models[role] = RoleModel(
            role=role,
            provider=provider,
            model_id=model_id,
            tier=tier,
            limits=_resolve_limits(source, role, provider, tier),
            effort=_resolve_effort(source, role),
        )

    declared_search = _env_list(source, "SEARCH_PROVIDERS")
    unknown = sorted(set(declared_search) - WEB_SEARCH_PROVIDERS)
    if unknown:
        supported = ", ".join(sorted(WEB_SEARCH_PROVIDERS))
        raise ConfigError(
            f"unknown search providers {unknown}; supported: {supported}"
        )
    search = declared_search or ("tavily",)
    # DuckDuckGo needs no credential, so it is the default safety net: a missing
    # or throttled key degrades discovery quality rather than stopping research.
    if _env_flag(source, "DUCKDUCKGO_FALLBACK", True) and "duckduckgo" not in search:
        search = (*search, "duckduckgo")

    academic: list[str] = []
    for name, flag in (
        ("arxiv", "ARXIV_SEARCH"),
        ("crossref", "CROSSREF_SEARCH"),
        ("pubmed", "PUBMED_SEARCH"),
    ):
        if _env_flag(source, flag, True):
            academic.append(name)

    return RuntimeConfig(
        role_models=role_models,
        search_providers=search,
        academic_providers=tuple(academic),
        contact_email=_env(source, "CONTACT_EMAIL"),
        ncbi_api_key=source.get("NCBI_API_KEY", "").strip(),
    )


__all__ = [
    "ACADEMIC_SEARCH_PROVIDERS",
    "DEFAULT_ROLE_EFFORT",
    "DEFAULT_ROLE_TIERS",
    "ROLES",
    "WEB_SEARCH_PROVIDERS",
    "ConfigError",
    "Role",
    "RoleModel",
    "RuntimeConfig",
    "load_config",
]
