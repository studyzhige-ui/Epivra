"""Read provider-reported usage; absent counters stay unknown, never estimated."""

FIELDS = (
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "cache_read_tokens",
    "cache_write_tokens",
    "reasoning_tokens",
    "search_credits",
    "reader_tokens",
    "cost_usd",
)


def counters(raw, resource=None):
    data = raw.get("data", {}) if isinstance(raw, dict) else {}
    if not isinstance(data, dict):
        data = {}
    usage = data.get("usage") or {}
    if not isinstance(usage, dict):
        usage = {}
    result = {}
    if isinstance(data.get("usageMetadata"), dict):
        usage = data["usageMetadata"]
        for target, source in (
            ("input_tokens", "promptTokenCount"),
            ("output_tokens", "candidatesTokenCount"),
            ("total_tokens", "totalTokenCount"),
            ("cache_read_tokens", "cachedContentTokenCount"),
            ("reasoning_tokens", "thoughtsTokenCount"),
        ):
            result[target] = usage.get(source)
        if all(
            type(usage.get(k)) is int and usage[k] >= 0
            for k in ("candidatesTokenCount", "thoughtsTokenCount")
        ):
            result["output_tokens"] = (
                usage["candidatesTokenCount"] + usage["thoughtsTokenCount"]
            )
    elif "input_tokens" in usage:
        # Anthropic input_tokens excludes both cache categories.
        result.update(
            input_tokens=usage.get("input_tokens"),
            output_tokens=usage.get("output_tokens"),
            cache_read_tokens=usage.get("cache_read_input_tokens"),
            cache_write_tokens=usage.get("cache_creation_input_tokens"),
        )
        parts = [
            usage.get(k, 0)
            for k in (
                "input_tokens",
                "cache_read_input_tokens",
                "cache_creation_input_tokens",
            )
        ]
        if all(type(v) is int and v >= 0 for v in parts):
            result["input_tokens"] = sum(parts)
        if (
            type(result.get("input_tokens")) is int
            and type(result.get("output_tokens")) is int
        ):
            result["total_tokens"] = result["input_tokens"] + result["output_tokens"]
    else:
        result.update(
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            total_tokens=usage.get("total_tokens"),
        )
        for key, target in (
            ("prompt_tokens_details", "cache_read_tokens"),
            ("completion_tokens_details", "reasoning_tokens"),
        ):
            detail = usage.get(key) or {}
            if isinstance(detail, dict):
                result[target] = detail.get(
                    "cached_tokens"
                    if target == "cache_read_tokens"
                    else "reasoning_tokens"
                )
        if "prompt_cache_hit_tokens" in usage:
            result["cache_read_tokens"] = usage["prompt_cache_hit_tokens"]
        if result.get("total_tokens") is None and all(
            type(result.get(k)) is int for k in ("input_tokens", "output_tokens")
        ):
            result["total_tokens"] = result["input_tokens"] + result["output_tokens"]
    result["search_credits"] = usage.get("credits")
    if resource == "jina":
        document = data.get("data")
        reader_usage = document.get("usage") if isinstance(document, dict) else None
        if isinstance(reader_usage, dict):
            result["reader_tokens"] = reader_usage.get("tokens")
    if resource == "exa" and isinstance(data.get("costDollars"), dict):
        result["cost_usd"] = data["costDollars"].get("total")
    return {
        key: value
        if type(value) in (int, float)
        and value >= 0
        and value < float("inf")
        and (key in {"search_credits", "cost_usd"} or type(value) is int)
        else None
        for key in FIELDS
        for value in [result.get(key)]
    }


def summarize(records):
    groups = {}
    for row in records:
        key = (row["resource"], row["model"], row.get("tool"))
        group = groups.setdefault(
            key,
            {
                "resource": key[0],
                "model": key[1],
                "tool": key[2],
                "calls": 0,
                "unresolved_calls": 0,
                "http_error_calls": 0,
                "totals": {k: None for k in FIELDS},
                "reported_calls": {k: 0 for k in FIELDS},
            },
        )
        group["calls"] += 1
        group["unresolved_calls"] += row["status"] == "unknown"
        group["http_error_calls"] += (
            isinstance(row.get("http_status"), int) and row["http_status"] >= 400
        )
        for field, value in row["usage"].items():
            if value is not None:
                group["totals"][field] = (group["totals"][field] or 0) + value
                group["reported_calls"][field] += 1
    return list(groups.values())
