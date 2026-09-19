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
            if end is not None
            else "unavailable: report has no stored body boundary"
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


def edit_manuscript(text: str, edits: list[dict[str, str]]) -> str:
    """Apply exact, non-overlapping replacements against one immutable base.

    The agent decides every replacement and affected conclusion. Ambiguous or
    missing anchors fail before persistence; unchanged text is copied verbatim.
    """
    if not edits:
        raise ValueError(
            "provide at least one exact edit; unchanged reports need no revision"
        )
    spans = []
    for index, edit in enumerate(edits):
        old, new = edit["old"], edit["new"]
        if not old or old == new:
            raise ValueError(
                f"edits[{index}]: old must be nonempty and differ from new"
            )
        start = text.find(old)
        if start < 0:
            raise ValueError(
                f"edits[{index}]: old text not found; read_manuscript for this base version"
            )
        if text.find(old, start + 1) >= 0:
            raise ValueError(
                f"edits[{index}]: ambiguous anchor; include more surrounding original text"
            )
        spans.append((start, start + len(old), new))
    spans.sort()
    if any(a[1] > b[0] for a, b in zip(spans, spans[1:])):
        raise ValueError(
            "edits overlap; provide non-overlapping edits against the original base"
        )
    parts, end = [], 0
    for start, stop, replacement in spans:
        parts.extend((text[end:start], replacement))
        end = stop
    parts.append(text[end:])
    return "".join(parts)
