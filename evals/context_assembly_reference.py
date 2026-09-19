"""Frozen comparison oracle, never imported by the production runtime.

Source: src/epivra/context.py at cc0d68d89981aa0730d1bf6fbbdd9bf511ede777
Git blob: 918b2d8b6bfacb20b50193681d97e32c6b358d67.
Retain historical selection/accounting behavior for differential verification.
"""

from __future__ import annotations

from typing import Any

from epivra.domain import Artifact, ContextCapacity, encode


def assemble(
    base: dict[str, Any],
    candidates: list[Artifact],
    memory: Artifact | None,
    capacity: int,
    *,
    direct_refs=None,
) -> dict[str, Any]:
    request = {
        **base,
        "context": [],
        "omitted_count": len(candidates),
        "memory": {"ref": memory.ref, "body": memory.body}
        if isinstance(memory, Artifact)
        else memory,
    }
    if len(encode(request)) > capacity:
        raise ContextCapacity(
            "task, authority and active memory exceed context capacity"
        )
    direct = (
        set(direct_refs)
        if direct_refs is not None
        else {item["ref"] for item in base.get("inputs", [])}
    )
    ordered = sorted(
        candidates,
        key=lambda a: (a.ref in direct, a.kind == "clarification_answer", a.seq),
        reverse=True,
    )
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
        raise ContextCapacity("context metadata exceeds capacity")
    return request
