"""Version-bound manuscript coverage, separate from semantic judgment."""

from __future__ import annotations

import re

from .domain import Artifact


def text_metrics(text: str) -> dict[str, int]:
    """Unicode code points, not words or a model's linguistic interpretation."""
    return {
        "characters": len(text),
        "non_whitespace_characters": sum(not c.isspace() for c in text),
    }


def units(text: str) -> list[dict]:
    return [
        {"unit": index, "text": part.strip()}
        for index, part in enumerate(re.split(r"\n\s*\n", text.strip()))
        if part.strip()
    ]


def checked(records: list[Artifact]) -> dict[int, dict]:
    result = {}
    for record in sorted(records, key=lambda a: a.seq):
        for check in record.body["checks"]:
            result[check["unit"]] = check
    return result
