"""Bounded, explicit research context. No provider or execution lifecycle."""

from __future__ import annotations

from typing import Any

from .domain import Artifact, encode


def source_ranges(source: Artifact, observations: list[Artifact]) -> list[list[int]]:
    """Returned text coverage, not proof of comprehension or evidence quality."""
    ranges = []
    for observation in observations:
        body = observation.body
        result = body.get("result", {})
        if not isinstance(result, dict):
            continue
        if body.get("tool") == "read_source" and result.get("ref") == source.ref:
            start, end = result["offset"], result["end"]
            if 0 <= start < end <= len(source.body["text"]):
                ranges.append([start, end])
        elif body.get("tool") == "read_artifact" and result.get("body") == source.body:
            ranges.append([0, len(source.body["text"])])
    merged = []
    for start, end in sorted(ranges):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged


def assemble(
    base: dict[str, Any],
    candidates: list[Artifact],
    memory: Artifact | None,
    capacity: int,
) -> dict[str, Any]:
    request = {
        **base,
        "context": [],
        "omitted_count": len(candidates),
        "memory": None if memory is None else {"ref": memory.ref, "body": memory.body},
    }
    if len(encode(request)) > capacity:
        raise ValueError("task, authority and active memory exceed context capacity")
    ordered = sorted(candidates, key=lambda a: a.seq, reverse=True)
    selected = []
    for item in ordered:
        entry = {"ref": item.ref, "kind": item.kind, "body": item.body}
        trial = {
            **request,
            "context": [*selected, entry],
            "omitted_count": len(candidates) - len(selected) - 1,
        }
        if len(encode(trial)) <= capacity:
            selected.append(entry)
        else:
            # Preserve retrieval handles instead of losing oversized results.
            handle = {
                "ref": item.ref,
                "kind": item.kind,
                "body_omitted": True,
                "characters": len(encode(item.body)),
            }
            trial["context"] = [*selected, handle]
            if len(encode(trial)) <= capacity:
                selected.append(handle)
    request["context"] = list(reversed(selected))
    request["omitted_count"] = len(candidates) - sum("body" in x for x in selected)
    # omitted_count can gain digits relative to a full-body trial.
    while len(encode(request)) > capacity and request["context"]:
        request["context"].pop(0)
        request["omitted_count"] = len(candidates) - sum(
            "body" in x for x in request["context"]
        )
    if len(encode(request)) > capacity:
        raise ValueError("context metadata exceeds capacity")
    return request
