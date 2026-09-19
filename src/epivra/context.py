"""Bounded, explicit research context. No provider or execution lifecycle."""

from __future__ import annotations

from typing import Any

from .domain import Artifact, ContextCapacity, encode


def page(items: list, offset: int, limit: int, capacity: int) -> dict:
    """Bound a live, append-ordered navigation page without copying its originals."""
    if offset < 0 or limit < 1:
        raise ValueError("invalid context page")
    offset = min(offset, len(items))
    result = {
        "items": [],
        "offset": offset,
        "total": len(items),
        "next_offset": offset if offset < len(items) else None,
    }
    initial_size = len(encode(result))
    if initial_size > capacity:
        raise ContextCapacity("context page metadata exceeds capacity")
    fixed_size = initial_size - len(encode(result["next_offset"]))
    payload_size = 0
    for item in items[offset : offset + limit]:
        entry = item
        entry_size = len(encode(entry))
        if entry_size > capacity // 2 and isinstance(item, dict):
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
            entry_size = len(encode(entry))
        end = offset + len(result["items"]) + 1
        next_offset = end if end < len(items) else None
        # The terminal cursor is JSON null (four characters), not its numeric
        # predecessor. Size the actual envelope before accepting the last item.
        addition = entry_size + bool(result["items"])
        if fixed_size + payload_size + addition + len(encode(next_offset)) > capacity:
            break
        result["items"].append(entry)
        result["next_offset"] = next_offset
        payload_size += addition
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
    # Preserve actual research inputs before optional navigation directories.
    additions = [("context", item) for item in reversed(minimal["context"])]
    for key, nav in minimal.get("navigation", {}).items():
        parent = minimal["review_progress"] if key.startswith("review_") else minimal
        field = key.removeprefix("review_") if key.startswith("review_") else key
        additions.extend((key, item) for item in parent[field])
        parent[field] = []
        nav["next_offset"] = nav["offset"] if nav["total"] else None
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
    initial_size = len(encode(request))
    if initial_size > capacity:
        raise ContextCapacity(
            "task, authority and active memory exceed context capacity"
        )
    # encode() uses compact JSON: only the context-array payload and the decimal
    # omitted_count change. Account in Unicode code points exactly as before,
    # without serializing the task, authority, memory and accepted bodies again
    # for every candidate. No new model-input or report-length policy is added.
    fixed_size = initial_size - len(str(len(candidates)))
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
    selected: list[dict[str, Any]] = []
    sizes: list[int] = []
    payload_size = 0
    for item in ordered:
        entry = {"ref": item.ref, "kind": item.kind, "body": item.body}
        entry_size = len(encode(entry))
        # Preserve the previous trial's selected-entry count (handles included).
        trial_base = (
            fixed_size
            + len(str(len(candidates) - len(selected) - 1))
            + payload_size
            + bool(selected)  # The separator before this array element.
        )
        if trial_base + entry_size > capacity:
            # Preserve retrieval handles instead of losing oversized results.
            entry = {
                "ref": item.ref,
                "kind": item.kind,
                "body_omitted": True,
                "characters": len(encode(item.body)),
            }
            entry_size = len(encode(entry))
        if trial_base + entry_size <= capacity:
            payload_size += entry_size + bool(selected)
            selected.append(entry)
            sizes.append(entry_size)
    omitted = len(candidates) - sum("body" in entry for entry in selected)
    # The final count excludes handles from full-body delivery, just as before;
    # crossing a decimal boundary can require dropping low-priority entries.
    while fixed_size + len(str(omitted)) + payload_size > capacity and selected:
        removed = selected.pop()
        payload_size -= sizes.pop() + bool(selected)
        omitted += "body" in removed
    request["context"] = list(reversed(selected))
    request["omitted_count"] = omitted
    # One final exact check protects the boundary if encode's contract changes.
    if len(encode(request)) > capacity:
        raise ContextCapacity("context metadata exceeds capacity")
    return request
