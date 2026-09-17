"""Bounded, explicit research context. No provider or execution lifecycle."""

from __future__ import annotations

from typing import Any

from .domain import Artifact, ContextCapacity, encode


def page(items: list, offset: int, limit: int, capacity: int) -> dict:
    """Bound a live, append-ordered navigation page without copying its originals."""
    if offset < 0 or limit < 1:
        raise ValueError("invalid context page")
    offset = min(offset, len(items))
    result = {"items": [], "offset": offset, "total": len(items), "next_offset": None}
    for item in items[offset : offset + limit]:
        entry = item
        if len(encode(entry)) > capacity // 2 and isinstance(item, dict):
            entry = {
                k: item[k]
                for k in (
                    "ref",
                    "kind",
                    "role",
                    "finished",
                    "question",
                    "work",
                    "answer",
                )
                if k in item
            }
            entry["details_omitted"] = True
        trial = {
            **result,
            "items": [*result["items"], entry],
            "next_offset": offset + len(result["items"]) + 1,
        }
        if len(encode(trial)) > capacity:
            break
        result["items"].append(entry)
    end = offset + len(result["items"])
    result["next_offset"] = end if end < len(items) else None
    return result


def fit_provider(request: dict, prepare) -> dict:
    """Drop optional projections, never task contracts, before a fresh window.

    Preparation is local and does not send a request. Test the smallest request
    first, then retain the largest fitting prefix of optional additions.
    """
    from copy import deepcopy

    from .domain import ContextCapacity

    try:
        prepare(request, None)
        return request
    except ContextCapacity:
        pass
    minimal = deepcopy(request)
    additions = []
    for key, nav in minimal.get("navigation", {}).items():
        parent = minimal["review_progress"] if key.startswith("review_") else minimal
        field = key.removeprefix("review_") if key.startswith("review_") else key
        additions.extend((key, item) for item in parent[field])
        parent[field] = []
        nav["next_offset"] = nav["offset"] if nav["total"] else None
    additions.extend(("context", item) for item in reversed(minimal["context"]))
    minimal["omitted_count"] += sum("body" in x for x in minimal["context"])
    minimal["context"] = []
    prepare(minimal, None)  # Essential capacity failures are actionable, never hidden.

    def restore(count):
        candidate = deepcopy(minimal)
        for key, item in additions[:count]:
            if key == "context":
                candidate[key].insert(0, item)
                candidate["omitted_count"] -= "body" in item
            else:
                parent = (
                    candidate["review_progress"]
                    if key.startswith("review_")
                    else candidate
                )
                field = (
                    key.removeprefix("review_") if key.startswith("review_") else key
                )
                parent[field].append(item)
                nav = candidate["navigation"][key]
                end = nav["offset"] + len(parent[field])
                nav["next_offset"] = end if end < nav["total"] else None
        return candidate

    low, high = 0, len(additions)
    while low < high:
        middle = (low + high + 1) // 2
        try:
            prepare(restore(middle), None)
        except ContextCapacity:
            high = middle - 1
        else:
            low = middle
    return restore(low)


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
