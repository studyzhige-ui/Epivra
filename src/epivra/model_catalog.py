"""Official model presets, checked 2026-09-12; no gateway or account quota data.

Presets are product choices, not claims of a provider-wide default. None means the
linked public contract did not establish a numeric limit/default: configuration
must supply it. Capacities are model limits, never account TPM/RPM allowances.
Streaming is opt-in only when usage delivery has been verified for the protocol.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelSpec:
    id: str
    context_tokens: int | None
    max_output_tokens: int | None
    output_parameter: str = "max_tokens"
    request_fields: tuple[tuple[str, object], ...] = ()
    sources: tuple[str, ...] = ()
    default_output_tokens: int | None = None
    supports_stream: bool = False
    recommended_output_tokens: int | None = None


@dataclass(frozen=True)
class ProviderSpec:
    id: str
    protocol: str
    credential_env: str
    endpoints: tuple[tuple[str, str], ...]
    default_region: str
    default_model: ModelSpec
    auth_header: str = "Authorization"
    auth_prefix: str = "Bearer "
    headers: tuple[tuple[str, str], ...] = ()
    notes: str = ""
    sources: tuple[str, ...] = ()


OFFICIAL_PROVIDERS = {
    "openai": ProviderSpec(
        "openai",
        "chat",
        "OPENAI_API_KEY",
        (("global", "https://api.openai.com/v1"),),
        "global",
        ModelSpec(
            "gpt-5.4",
            1_050_000,
            128_000,
            "max_completion_tokens",
            sources=("https://developers.openai.com/api/docs/models/gpt-5.4",),
            supports_stream=True,
        ),
        sources=("https://developers.openai.com/api/reference/resources/chat/",),
    ),
    "claude": ProviderSpec(
        "claude",
        "anthropic",
        "ANTHROPIC_API_KEY",
        (("global", "https://api.anthropic.com/v1"),),
        "global",
        ModelSpec(
            "claude-sonnet-4-6",
            1_000_000,
            128_000,
            sources=("https://platform.claude.com/docs/en/models/sonnet-4-6/overview",),
        ),
        auth_header="x-api-key",
        auth_prefix="",
        headers=(("anthropic-version", "2023-06-01"),),
        sources=("https://platform.claude.com/docs/en/api/messages",),
    ),
    "gemini": ProviderSpec(
        "gemini",
        "gemini",
        "GEMINI_API_KEY",
        (("global", "https://generativelanguage.googleapis.com/v1beta"),),
        "global",
        ModelSpec(
            "gemini-2.5-flash",
            1_048_576,
            65_536,
            "maxOutputTokens",
            sources=("https://ai.google.dev/gemini-api/docs/models/gemini-2.5-flash",),
        ),
        auth_header="x-goog-api-key",
        auth_prefix="",
        notes="Published context value is the input token limit; output has a separate limit.",
        sources=("https://ai.google.dev/api/generate-content",),
    ),
    "grok": ProviderSpec(
        "grok",
        "chat",
        "XAI_API_KEY",
        (("global", "https://api.x.ai/v1"),),
        "global",
        ModelSpec(
            "grok-4.3",
            1_000_000,
            None,
            "max_completion_tokens",
            sources=(
                "https://docs.x.ai/developers/models/grok-4.3",
                "https://docs.x.ai/developers/rest-api-reference/inference/chat-completions.md",
            ),
            default_output_tokens=128_000,
        ),
        notes="Default bounds visible output only, excluding reasoning and function calls; "
        "the official maximum is unspecified.",
        sources=("https://docs.x.ai/developers/migration/may-15-retirement",),
    ),
    "deepseek": ProviderSpec(
        "deepseek",
        "chat",
        "DEEPSEEK_API_KEY",
        (("global", "https://api.deepseek.com"),),
        "global",
        ModelSpec(
            "deepseek-flash",
            1_000_000,
            393_216,
            sources=(
                "https://api-docs.deepseek.com/quick_start/pricing/",
                "https://api-docs.deepseek.com/api/create-chat-completion/",
            ),
            default_output_tokens=65_536,
            supports_stream=True,
        ),
        notes="Default output is for default thinking/high; disabled=8192, max effort=131072.",
    ),
    "qwen": ProviderSpec(
        "qwen",
        "chat",
        "QWEN_API_KEY",
        (("beijing", "https://dashscope.aliyuncs.com/compatible-mode/v1"),),
        "beijing",
        ModelSpec(
            "qwen-plus",
            1_000_000,
            32_768,
            sources=("https://help.aliyun.com/zh/model-studio/qwen-plus",),
        ),
        notes="This preset's function calling is documented only in Beijing; other regions "
        "require a separately verified model deployment.",
        sources=(
            "https://help.aliyun.com/zh/model-studio/compatibility-of-openai-with-dashscope",
        ),
    ),
    "kimi": ProviderSpec(
        "kimi",
        "chat",
        "KIMI_API_KEY",
        (("china", "https://api.moonshot.cn/v1"),),
        "china",
        ModelSpec(
            "kimi-k3",
            1_048_576,
            1_048_576,
            "max_completion_tokens",
            sources=(
                "https://platform.kimi.com/docs/models",
                "https://platform.kimi.com/docs/api/models-overview",
                "https://platform.kimi.com/docs/guide/kimi-k3-quickstart",
            ),
            default_output_tokens=131_072,
        ),
        notes="K3 uses reasoning_effort (default max), not K2's thinking field. "
        "Preserve reasoning_content. Output maximum shares the total context window; "
        "default output reserve is 131072, not the full window.",
        sources=("https://platform.kimi.com/docs/get-api-key",),
    ),
    "glm": ProviderSpec(
        "glm",
        "chat",
        "GLM_API_KEY",
        (("china", "https://open.bigmodel.cn/api/paas/v4"),),
        "china",
        ModelSpec(
            "glm-5",
            200_000,
            131_072,
            sources=(
                "https://docs.bigmodel.cn/cn/guide/models/text/glm-5",
                "https://docs.bigmodel.cn/cn/guide/start/concept-param",
            ),
            default_output_tokens=65_536,
        ),
        notes="Context uses decimal 200K as the product effective capacity; output and "
        "default are exact integers from the official parameter table.",
    ),
    "doubao": ProviderSpec(
        "doubao",
        "chat",
        "DOUBAO_API_KEY",
        (("beijing", "https://ark.cn-beijing.volces.com/api/v3"),),
        "beijing",
        ModelSpec(
            "doubao-seed-2-0-pro-260215",
            256_000,
            None,
            recommended_output_tokens=32_000,
            sources=(
                "https://www.volcengine.com/docs/82379/1925114",
                "https://developer.volcengine.com/articles/7616633140483719219",
            ),
        ),
        notes="Standard Ark API, not Coding Plan. Enable model access in the account; "
        "256000/32000 are effective context/output settings in the official "
        "integration example, not a claim of maximum output capacity.",
        sources=("https://www.volcengine.com/docs/82379/1330310",),
    ),
    "minimax": ProviderSpec(
        "minimax",
        "chat",
        "MINIMAX_API_KEY",
        (("china", "https://api.minimax.cn/v1"),),
        "china",
        ModelSpec(
            "MiniMax-M3",
            1_000_000,
            524_288,
            "max_completion_tokens",
            request_fields=(("reasoning_split", True),),
            sources=(
                "https://platform.minimax.cn/docs/api-reference/text-openai-api",
                "https://platform.minimaxi.com/docs/api-reference/text-chat-openai.md",
            ),
            recommended_output_tokens=131_072,
        ),
        notes="Preserve reasoning_details and reasoning_content; non-streaming until "
        "stream accumulation semantics are verified. Official recommended output is "
        "131072; recommendation is not a documented API default.",
    ),
    "hunyuan": ProviderSpec(
        "hunyuan",
        "chat",
        "HUNYUAN_API_KEY",
        (
            ("guangzhou", "https://tokenhub.tencentmaas.com/v1"),
            ("singapore", "https://tokenhub-intl.tencentmaas.com/v1"),
        ),
        "guangzhou",
        ModelSpec(
            "hy3",
            256_000,
            128_000,
            sources=("https://cloud.tencent.com/document/product/1823/130051",),
        ),
        notes="Official Tencent TokenHub replaces retired Hunyuan platform. Credentials "
        "and availability are region-specific. Published 256k/128k are normalized "
        "as decimal product effective capacities, not asserted exact server limits.",
        sources=(
            "https://cloud.tencent.com/document/product/1823/130078",
            "https://cloud.tencent.com/document/product/1823/130079",
        ),
    ),
    "ernie": ProviderSpec(
        "ernie",
        "chat",
        "ERNIE_API_KEY",
        (("china", "https://qianfan.baidubce.com/v2"),),
        "china",
        ModelSpec(
            "ernie-5.0",
            128_000,
            65_536,
            sources=("https://cloud.baidu.com/doc/qianfan/s/rmh4stp0j",),
        ),
        notes="API Key Bearer authentication, not legacy AK/SK OAuth. Public context "
        "label 128k is normalized as decimal effective capacity. Output includes reasoning.",
        sources=(
            "https://cloud.baidu.com/doc/qianfan-api/s/ym9chdsy5",
            "https://cloud.baidu.com/doc/qianfan-docs/s/xm95lyys5",
        ),
    ),
}


def get_provider(provider_id: str) -> ProviderSpec:
    """Resolve an explicit official identity; never infer from a model or URL."""
    try:
        return OFFICIAL_PROVIDERS[provider_id]
    except KeyError as exc:
        raise ValueError(f"unknown official model provider: {provider_id}") from exc


def resolve_endpoint(provider_id: str, region: str | None = None) -> str:
    provider = get_provider(provider_id)
    selected = provider.default_region if region is None else region
    try:
        return dict(provider.endpoints)[selected]
    except KeyError as exc:
        raise ValueError(f"unsupported region for {provider_id}: {selected}") from exc
