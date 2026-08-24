"""LLM vendor registry: which vendors exist, and which protocol each speaks.

Most vendors expose an OpenAI-compatible Chat Completions endpoint, so most of
them share one transport.  **Anthropic does not** -- its Messages API is a
different wire format, and pointing an OpenAI client at it produces 404s and
400s rather than a useful error.  The registry therefore records a ``protocol``
per vendor and the runtime picks the matching transport; a vendor is data, but
its protocol is not something to guess.

The registry deliberately records no pricing.  Prices change faster than a
repository does, and a stale number embedded in code is worse than none; the
tier names say which model is meant to be expensive and which is meant to be
cheap, and the operator decides what fills them.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

#: Which end of a vendor's line-up a role should draw from.  Two tiers is the
#: distinction that actually maps onto research work: open-ended judgment and
#: long-form synthesis on one side, bounded well-specified work on the other.
ModelTier = Literal["reasoning", "fast"]

MODEL_TIERS: tuple[ModelTier, ...] = ("reasoning", "fast")

#: The wire format a vendor speaks.  Adding a protocol means adding a transport,
#: not just a registry row -- which is exactly why it is recorded explicitly.
LlmProtocol = Literal["openai_compatible", "anthropic"]

#: How much thinking a role is asked to spend.  Named after the API parameter it
#: becomes, and deliberately a closed set: an unbounded knob invites tuning it per
#: task, which is how a cost setting turns into a research decision.
ModelEffort = Literal["low", "medium", "high", "xhigh", "max"]

MODEL_EFFORTS: tuple[ModelEffort, ...] = ("low", "medium", "high", "xhigh", "max")


@dataclass(frozen=True, slots=True)
class ModelLimits:
    """Conservative floors for one tier's input and output ceilings.

    **These are floors, not the vendor's real numbers.**  Context windows change
    faster than this repository does -- the same reason the registry records no
    prices (§9.1) -- and a stale optimistic window is worse than none: it would
    let the capacity red line wave through a request that cannot fit.  A floor
    that is too low only fails earlier, with a readable message.

    The truth is asked of the vendor: ``providers.validation`` reads the real
    input ceiling from the model catalogue where the vendor publishes it, and
    ``doctor --live`` reports where floor and reality disagree.  An operator who
    needs the real number today sets it per role in the environment.
    """

    context: int
    output: int

    def __post_init__(self) -> None:
        if self.context < 1 or self.output < 1:
            raise ValueError("model limits must be positive")


@dataclass(frozen=True, slots=True)
class LlmProviderSpec:
    """One vendor, its endpoint, its protocol, and its default tier pair."""

    name: str
    label: str
    api_base: str
    key_env_var: str
    reasoning_model: str
    fast_model: str
    protocol: LlmProtocol = "openai_compatible"
    #: Conservative floors per tier; see :class:`ModelLimits` for why they are
    #: floors.  The defaults suit a mainstream 2026 long-context model and are
    #: overridden per vendor below where a vendor is known to differ.
    reasoning_limits: ModelLimits = ModelLimits(context=128_000, output=32_000)
    fast_limits: ModelLimits = ModelLimits(context=128_000, output=16_000)

    def default_model(self, tier: ModelTier) -> str:
        return self.reasoning_model if tier == "reasoning" else self.fast_model

    def default_limits(self, tier: ModelTier) -> ModelLimits:
        return self.reasoning_limits if tier == "reasoning" else self.fast_limits

    def api_key(self, environ: Mapping[str, str] | None = None) -> str:
        source = os.environ if environ is None else environ
        return source.get(self.key_env_var, "").strip()


#: Vendors this runtime can talk to.  Defaults name each vendor's current
#: strong/cheap pair; an operator overrides them per role through configuration
#: without touching this table.
LLM_PROVIDERS: tuple[LlmProviderSpec, ...] = (
    LlmProviderSpec(
        name="deepseek",
        label="DeepSeek",
        api_base="https://api.deepseek.com",
        key_env_var="DEEPSEEK_API_KEY",
        reasoning_model="deepseek-v4-pro",
        fast_model="deepseek-v4-flash",
    ),
    LlmProviderSpec(
        name="anthropic",
        label="Anthropic Claude",
        # Native Messages API -- not OpenAI-compatible.  Model IDs carry no date
        # suffix; appending one 404s.
        api_base="https://api.anthropic.com",
        key_env_var="ANTHROPIC_API_KEY",
        reasoning_model="claude-opus-5",
        fast_model="claude-haiku-4-5",
        protocol="anthropic",
        # The reasoning tier is long-context, which is what keeps the Reviewer --
        # the largest role, because it reads the whole evidence set including what
        # the report did not cite -- inside one request at the scale this system
        # actually runs at.  The fast tier is a smaller window, and the
        # Investigator sits there precisely because its work is per-assignment.
        reasoning_limits=ModelLimits(context=1_000_000, output=64_000),
        fast_limits=ModelLimits(context=200_000, output=16_000),
    ),
    LlmProviderSpec(
        name="openai",
        label="OpenAI",
        api_base="https://api.openai.com/v1",
        key_env_var="OPENAI_API_KEY",
        reasoning_model="gpt-5.2",
        fast_model="gpt-5.2-mini",
    ),
    LlmProviderSpec(
        name="qwen",
        label="阿里云百炼 / Qwen",
        api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
        key_env_var="DASHSCOPE_API_KEY",
        reasoning_model="qwen3-max",
        fast_model="qwen3-turbo",
    ),
    LlmProviderSpec(
        name="zhipu",
        label="智谱 GLM",
        api_base="https://open.bigmodel.cn/api/paas/v4",
        key_env_var="ZHIPU_API_KEY",
        reasoning_model="glm-5",
        fast_model="glm-5-air",
    ),
    LlmProviderSpec(
        name="moonshot",
        label="月之暗面 Kimi",
        api_base="https://api.moonshot.cn/v1",
        key_env_var="MOONSHOT_API_KEY",
        reasoning_model="kimi-k2.5",
        fast_model="kimi-k2.5-turbo",
    ),
    LlmProviderSpec(
        name="openrouter",
        label="OpenRouter",
        # A gateway: it re-exposes Claude and others behind the OpenAI protocol,
        # which is the supported way to reach Claude without a native adapter.
        api_base="https://openrouter.ai/api/v1",
        key_env_var="OPENROUTER_API_KEY",
        reasoning_model="anthropic/claude-opus-5",
        fast_model="anthropic/claude-haiku-4.5",
        # A gateway's ceilings follow whichever model is routed to, so the floor
        # is kept deliberately low: too low costs a readable early pause, too high
        # costs a request the upstream silently truncates.
        reasoning_limits=ModelLimits(context=200_000, output=32_000),
        fast_limits=ModelLimits(context=200_000, output=16_000),
    ),
)

LLM_PROVIDER_BY_NAME: Mapping[str, LlmProviderSpec] = {
    spec.name: spec for spec in LLM_PROVIDERS
}


def resolve_llm_provider(name: str) -> LlmProviderSpec:
    """Look up a vendor, listing the supported set when the name is unknown."""

    spec = LLM_PROVIDER_BY_NAME.get(name.strip().casefold())
    if spec is None:
        supported = ", ".join(sorted(LLM_PROVIDER_BY_NAME))
        raise ValueError(f"unknown LLM provider {name!r}; supported: {supported}")
    return spec


def configured_llm_providers(
    environ: Mapping[str, str] | None = None,
) -> tuple[LlmProviderSpec, ...]:
    """Vendors whose credential is present, in registry order."""

    return tuple(spec for spec in LLM_PROVIDERS if spec.api_key(environ))


__all__ = [
    "LLM_PROVIDERS",
    "LLM_PROVIDER_BY_NAME",
    "MODEL_EFFORTS",
    "MODEL_TIERS",
    "LlmProviderSpec",
    "ModelEffort",
    "ModelLimits",
    "ModelTier",
    "configured_llm_providers",
    "resolve_llm_provider",
]
