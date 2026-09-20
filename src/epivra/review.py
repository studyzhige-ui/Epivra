"""Deterministic manuscript navigation and text metrics."""

from __future__ import annotations

import json
import re
from typing import Any


def text_metrics(text: str) -> dict[str, int]:
    """Unicode code points, not words or a model's linguistic interpretation."""
    return {
        "characters": len(text),
        "non_whitespace_characters": sum(not c.isspace() for c in text),
    }


def report_metrics(report: dict[str, Any]) -> dict[str, Any]:
    """Count exact rendered text, using only a stored boundary.

    The host knows where its bibliography starts; it cannot infer which author
    headings, notes or paragraphs the user considers the substantive body.
    Legacy reports without this boundary retain full counts, never a guessed body.
    """
    text = report["text"]
    end = report.get("citation_body_length")
    if end is not None and (type(end) is not int or not 0 <= end <= len(text)):
        raise ValueError("invalid citation body boundary")
    return {
        **text_metrics(text),
        "scope": "rendered report including generated references",
        "body": text_metrics(text[:end]) if end is not None else None,
        "citation_body_length": end,
        "body_scope": (
            "author text before generated references; includes any author title, "
            "headings, tables, notes and inline citation markers"
            if end is not None else "unavailable: report has no stored body boundary"
        ),
        "counting_method": (
            "Unicode code points, not words, tokens or graphemes; Markdown and "
            "citation notation are counted literally; non_whitespace_characters "
            "excludes only characters for which str.isspace() is true. "
            "Counts do not decide which scope the user requested or compliance."
        ),
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
