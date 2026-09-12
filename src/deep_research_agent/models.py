"""Compose official model connections; credentials never enter a frozen request."""

from .adapters import ChatCompletions, DeepSeek, JsonAPI
from .model_catalog import get_provider, resolve_endpoint
from .native_models import Anthropic, Gemini


def model_settings(policy):
    provider = get_provider(policy.get("provider", "deepseek"))
    preset = provider.default_model
    model = policy.get("model") or preset.id
    if not isinstance(model, str) or not model.strip():
        raise ValueError("model ID required")
    known = model == preset.id
    context = policy.get("context_tokens", preset.context_tokens if known else None)
    output = policy.get(
        "max_tokens",
        (
            preset.default_output_tokens
            or preset.recommended_output_tokens
            or preset.max_output_tokens
        )
        if known
        else None,
    )
    if (
        provider.id == "deepseek"
        and "provider" not in policy
        and "context_tokens" not in policy
    ):
        context = 1000000
    if type(output) is not int or output < 1:
        raise ValueError("model output allowance required")
    if type(context) is not int or context <= output:
        raise ValueError("model context capacity must exceed output allowance")
    if known and preset.max_output_tokens and output > preset.max_output_tokens:
        raise ValueError("output allowance exceeds documented model limit")
    if known and preset.context_tokens and context > preset.context_tokens:
        raise ValueError("context capacity exceeds documented model limit")
    # Resolve only catalogued official endpoints. No user URL or credential here.
    origin = resolve_endpoint(provider.id, policy.get("region"))
    if policy.get("stream_model") and not (known and preset.supports_stream):
        raise ValueError("streaming is not verified for this model; use non-streaming")
    return provider, model, context, output, origin


def create_model(policy, keys, *, client=None):
    provider, model, context, output, origin = model_settings(policy)
    key = keys.get(provider.credential_env, "")
    if not key.strip():
        raise ValueError(f"{provider.credential_env} required")
    # Validate everything before allocating an owned network client.
    frozen = policy.get("model_profile", {})
    fields = frozen.get(
        "request_fields",
        dict(provider.default_model.request_fields)
        if model == provider.default_model.id
        else {},
    )
    output_parameter = frozen.get(
        "output_parameter", provider.default_model.output_parameter
    )
    api = JsonAPI(
        origin,
        key,
        client,
        auth_header=provider.auth_header,
        auth_prefix=provider.auth_prefix,
        headers=dict(provider.headers),
        credential_env=provider.credential_env,
    )
    if provider.id == "deepseek":
        adapter = DeepSeek(
            api,
            model=model,
            context_tokens=context,
            # Preserve the existing documented DeepSeek defaults and binding.
            max_tokens=output,
            stream=policy.get("stream_model", False),
            reasoning_effort=policy.get("reasoning_effort", "high"),
        )
    elif provider.protocol == "chat":
        adapter = ChatCompletions(
            api,
            model,
            provider=provider.id,
            context_tokens=context,
            max_tokens=output,
            output_parameter=output_parameter,
            request_fields=fields,
            stream=policy.get("stream_model", False),
        )
    elif provider.protocol == "anthropic":
        adapter = Anthropic(
            api,
            model,
            max_tokens=output,
            context_tokens=context,
            thinking=fields.get("thinking"),
            effort=fields.get("output_config", {}).get("effort"),
            stream=policy.get("stream_model", False),
        )
    else:
        thinking = fields.get("thinkingConfig", {})
        adapter = Gemini(
            api,
            model,
            max_tokens=output,
            context_tokens=context,
            thinking_level=thinking.get("thinkingLevel"),
            thinking_budget=thinking.get("thinkingBudget"),
            stream=policy.get("stream_model", False),
        )
    return adapter, api


def freeze_model_settings(policy):
    provider, model, context, output, _ = model_settings(policy)
    preset = provider.default_model
    return {
        **policy,
        "provider": provider.id,
        "model": model,
        "context_tokens": context,
        "max_tokens": output,
        "region": policy.get("region") or provider.default_region,
        "stream_model": policy.get(
            "stream_model", model == preset.id and preset.supports_stream
        ),
        "model_profile": {
            "output_parameter": preset.output_parameter,
            "request_fields": dict(preset.request_fields) if model == preset.id else {},
        },
    }
