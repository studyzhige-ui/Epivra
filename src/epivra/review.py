"""Deterministic manuscript navigation and text metrics."""

from __future__ import annotations

import json
import re


def text_metrics(text: str) -> dict[str, int]:
    """Unicode code points, not words or a model's linguistic interpretation."""
    return {
        "characters": len(text),
        "non_whitespace_characters": sum(not c.isspace() for c in text),
    }


def units(text: str) -> list[dict]:
    """Stable bounded navigation units, including very long paragraphs/tables."""
    result: list[dict] = []
    for part in re.split(r"\n\s*\n", text.strip()):
        part = part.strip()
        for offset in range(0, len(part), 1024):
            result.append({"unit": len(result), "text": part[offset : offset + 1024]})
    return result


def public_inputs(request):
    """Actual public wire blocks; never assistant output, arguments or reasoning."""
    if "wire" not in request:
        yield request  # Provider-neutral offline models receive this exact object.
        return
    payload = request["wire"]["payload"]
    for message in payload.get("messages", payload.get("contents", [])):
        if message.get("role") not in {"user", "tool"}:
            continue
        content = message.get("content", message.get("parts", []))
        blocks = [content] if isinstance(content, str) else content
        for block in blocks:
            if isinstance(block, str):
                value = block
            elif "functionResponse" in block:
                value = block["functionResponse"].get("response", {})
            elif block.get("type") == "tool_result":
                value = block.get("content")
            else:
                value = block.get("text")
            if isinstance(value, str):
                try:
                    value = json.loads(value)
                except ValueError:
                    continue
            if isinstance(value, dict):
                yield value
