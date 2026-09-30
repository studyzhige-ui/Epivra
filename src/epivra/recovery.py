"""Safe failure facts and recovery conditions. No requests or mutable state."""

import math
import re

from .domain import identity

PARAMETERS = frozenset({"model", "max_tokens", "max_completion_tokens", "messages", "tools",
                       "thinking", "reasoning_effort", "output_config", "stream", "query", "url"})


def conditions(request):
    """Record comparison facts, without duplicating prompts or acquired text."""
    return {key: identity(request[key]) for key in PARAMETERS if key in request}

_ACTIONS = {
    "authentication": ("authorization", "repair_account", "Provide a valid credential before retrying; a new query cannot repair authentication."),
    "quota": ("authorization", "repair_account", "Restore account quota or balance, or use an authorized alternative channel."),
    "permission": ("request", "repair_access", "Obtain the required access or use an authorized alternative; do not weaken permissions."),
    "rate_limit": ("provider", "wait", "Wait for the recorded provider deadline before retrying."),
    "overloaded": ("provider", "wait", "The provider explicitly reports temporary overload; follow its retry contract."),
    "not_sent": ("request", "retry", "No request was sent: reconnect after backoff before retrying the operation."),
    "invalid_request": ("request", "correct_input", "Correct the reported input or capacity condition before resending."),
    "not_found": ("request", "revise_method", "Verify the URL or requested resource, or use an authorized alternative."),
    "protocol": ("request", "revise_method", "The saved response is unusable under this contract; do not purchase the same response again."),
    "unavailable": ("request", "revise_method", "The service failed; retry safety is not established. Use another authorized path or repair the service."),
    "read_failure": ("request", "revise_method", "No usable original was obtained; preserve acquired material and revise the reading path."),
    "unknown": ("request", "reconcile", "The request may have executed. Recover its original receipt; do not resend it under another step, work or credential."),
}


def diagnose(raw, *, provider="", protocol=False):
    """Classify established transport/provider facts, never infer a hidden cause."""
    if not isinstance(raw, dict):
        raw = {}
    status = raw.get("http_status")
    if type(status) is not int:
        status = None
    kind = raw.get("error_kind")
    if raw.get("completion") == "unknown":
        cause = "unknown"
    elif raw.get("completion") == "not_sent":
        cause = "not_sent"
    elif isinstance(kind, str) and kind in {"authentication", "quota"}:
        cause = kind
    elif status == 401 and provider != "http":
        cause = "authentication"
    elif status == 402 and provider != "http" or provider == "tavily" and status in {432, 433}:
        cause = "quota"
    elif status in {401, 403}:
        cause = "permission"
    elif status == 429:
        cause = "rate_limit"
    elif provider == "typesafe" and status == 529:
        cause = "overloaded"
    elif status in {400, 413, 422}:
        cause = "invalid_request"
    elif status in {404, 410}:
        cause = "not_found"
    elif type(status) is int and status >= 500:
        cause = "unavailable"
    elif protocol or raw.get("malformed_json"):
        cause = "protocol"
    elif raw.get("error"):
        cause = "read_failure"
    else:
        return None
    scope, action, instruction = _ACTIONS[cause]
    if cause == "permission" and provider != "http":
        scope = "access"
    completion = raw.get("completion")
    result = {"cause": cause, "scope": scope, "action": action,
              "completion": completion if isinstance(completion, str) and completion in {"received", "not_sent", "unknown"} else "received", "instruction": instruction}
    if type(status) is int:
        result["http_status"] = status
    for field in ("provider_code", "provider_type", "parameter"):
        value = raw.get(field)
        if isinstance(value, str) and re.fullmatch(r"[a-z_]{1,64}", value):
            result[field] = value
    delay = raw.get("retry_after")
    if type(delay) in {int, float} and math.isfinite(delay) and delay >= 0:
        result["retry_after"] = delay
    return result


def protocol_failure(raw, *, provider=""):
    diagnosis = diagnose(raw, provider=provider, protocol=True)
    return {"error": "invalid_external_result", "diagnosis": diagnosis,
            "instruction": diagnosis["instruction"]}


def repair_on_resume(raw, *, provider=""):
    diagnosis = diagnose(raw, provider=provider)
    return bool(diagnosis and diagnosis["scope"] in {"authorization", "access"})


def retry_delay(raw, attempt, *, provider=""):
    diagnosis = diagnose(raw, provider=provider)
    if diagnosis and diagnosis["cause"] in {"rate_limit", "overloaded", "not_sent"}:
        return max(float(2 ** min(attempt + 1, 6)), diagnosis.get("retry_after", 0))
    return None
