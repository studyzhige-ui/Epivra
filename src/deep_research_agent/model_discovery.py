"""Read-only official account model discovery; never inference or guessed limits."""

import json
import time

import httpx

from .model_catalog import get_provider, resolve_endpoint

# No inferred /models endpoint for providers whose current connection is unverified.
DISCOVERY = {
    "openai",
    "claude",
    "gemini",
    "grok",
    "deepseek",
    "kimi",
    "hunyuan",
    "ernie",
    "minimax",
}


class DiscoveryError(ValueError):
    pass


def discover(provider_id, region, key, *, transport=None):
    provider = get_provider(provider_id)
    base = resolve_endpoint(provider_id, region)
    if not isinstance(key, str) or not key.strip():
        raise DiscoveryError("请先填写 API Key。")
    if provider_id not in DISCOVERY:
        return {
            "models": [{"id": provider.default_model.id}],
            "source": "preset",
            "message": "此连接尚无已核实的账户列表接口，显示本地预设；可手动输入型号。",
        }
    headers = {
        **dict(provider.headers),
        provider.auth_header: provider.auth_prefix + key.strip(),
    }
    path = "/language-models" if provider_id == "grok" else "/models"
    params, seen, models = {}, set(), {}
    deadline = time.monotonic() + 30
    try:
        with httpx.Client(
            transport=transport, follow_redirects=False, trust_env=False
        ) as client:
            for _ in range(100):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise DiscoveryError("获取模型列表超时，请重试。")
                with client.stream(
                    "GET",
                    base + path,
                    headers=headers,
                    params=params,
                    timeout=min(10, remaining),
                ) as response:
                    if response.status_code != 200:
                        message = {
                            401: "密钥无效或已过期。",
                            403: "账户没有模型列表访问权限。",
                            429: "模型列表请求受到限流，请稍后重试。",
                        }.get(response.status_code, "模型列表接口暂不可用。")
                        raise DiscoveryError(message)
                    body = bytearray()
                    for chunk in response.iter_bytes():
                        if time.monotonic() > deadline:
                            raise DiscoveryError("获取模型列表超时，请重试。")
                        body.extend(chunk)
                        if len(body) > 4 * 1024 * 1024:
                            raise DiscoveryError("模型列表响应超过读取范围。")
                    data = json.loads(body)
                if not isinstance(data, dict):
                    raise DiscoveryError("模型列表响应格式无效。")
                rows = data.get(
                    "models" if provider_id in {"gemini", "grok"} else "data"
                )
                if not isinstance(rows, list):
                    raise DiscoveryError("模型列表响应格式无效。")
                for row in rows:
                    if not isinstance(row, dict):
                        raise DiscoveryError("模型列表条目格式无效。")
                    model_id = row.get("name" if provider_id == "gemini" else "id")
                    if (
                        not isinstance(model_id, str)
                        or not model_id
                        or len(model_id) > 256
                    ):
                        raise DiscoveryError("模型列表条目缺少有效名称。")
                    if provider_id == "gemini":
                        if "generateContent" not in row.get(
                            "supportedGenerationMethods", []
                        ):
                            continue
                        model_id = model_id.removeprefix("models/")
                    entry = {"id": model_id}
                    if provider_id in {"gemini", "claude"}:
                        context = row.get(
                            "inputTokenLimit"
                            if provider_id == "gemini"
                            else "max_input_tokens"
                        )
                        output = row.get(
                            "outputTokenLimit"
                            if provider_id == "gemini"
                            else "max_tokens"
                        )
                        if (
                            type(context) is int
                            and type(output) is int
                            and 0 < output < context
                        ):
                            entry.update(context_tokens=context, max_tokens=output)
                    models[model_id] = entry
                cursor = (
                    data.get("nextPageToken")
                    if provider_id == "gemini"
                    else (data.get("last_id") if data.get("has_more") else None)
                )
                if data.get("has_more") and not cursor:
                    raise DiscoveryError("模型列表分页缺少游标。")
                if not cursor:
                    return {
                        "models": sorted(models.values(), key=lambda m: m["id"]),
                        "source": "account",
                        "message": "已获取接口模型列表；列出不代表已验证工具能力。",
                    }
                if not isinstance(cursor, str) or cursor in seen:
                    raise DiscoveryError("模型列表分页重复或无效。")
                seen.add(cursor)
                params = {
                    "pageToken" if provider_id == "gemini" else "after_id": cursor
                }
            raise DiscoveryError("模型列表分页超过读取范围。")
    except (httpx.HTTPError, UnicodeError):
        raise DiscoveryError("无法连接模型列表接口，请检查网络后重试。") from None
    except (TypeError, KeyError, json.JSONDecodeError):
        raise DiscoveryError("模型列表响应格式无效。") from None
