"""Bounded, explicit research context. No provider or execution lifecycle."""

from __future__ import annotations

import json
from collections.abc import Callable
from copy import deepcopy
from typing import Any

from .domain import Artifact, ContextCapacity, encode
from .evidence import delivered


def ordered_state(state):
    """Stable contract first, working state next, actual incoming context last."""
    fields = (
        "role", "direction_ref", "direction", "task", "shared_context", "deliverable", "work_ref",
        "phase", "prompt_version", "work_generation", "research_scope", "current_date",
        "memory", "context_window", "inbox", "input_revisions", "pinned_evidence",
        "authoring", "draft", "writing_basis", "review_progress",
    )
    keys = [k for k in fields if k in state]
    keys.extend(sorted(set(state) - set(fields) - {"context"}))
    if "context" in state:
        keys.append("context")
    return "{" + ",".join(encode(k) + ":" + encode(state[k]) for k in keys) + "}"


def project_history(payload, *, protected=(), clear=False):
    """Project only our public JSON envelopes; never inspect assistant reasoning.

    Tool IDs, message grouping and signed native blocks are unchanged. Clearing
    is a model view, not artifact deletion or a claim that a body was delivered.
    """
    result = deepcopy(payload)
    protected = set(protected)
    cleared = []

    def project(value):
        if not isinstance(value, dict):
            return value
        ref = value.get("observation_ref")
        if clear and isinstance(ref, str) and ref not in protected and "result" in value:
            cleared.append(ref)
            return {"observation_ref": ref, "body_omitted": True,
                    "instruction": "Read the original observation with read_artifact_range."}
        entries = value.get("context")
        if clear and isinstance(entries, list):
            entries = list(entries)
            for i, entry in enumerate(entries):
                if (isinstance(entry, dict) and entry.get("kind") == "observation"
                        and isinstance(entry.get("ref"), str) and entry["ref"] not in protected
                        and "body" in entry):
                    cleared.append(entry["ref"])
                    entries[i] = {"ref": entry["ref"], "kind": "observation", "body_omitted": True,
                                  "characters": len(encode(entry["body"]))}
            value = {**value, "context": entries}
        return value

    def text_value(value):
        try:
            parsed = json.loads(value)
        except (ValueError, TypeError):
            return value
        replacement = project(parsed)
        return ordered_state(replacement) if replacement != parsed else value

    def public_value(value):
        if isinstance(value, dict) and "context" in value and "observation_ref" not in value:
            # The compaction request supplies current contracts/shared state.
            # Repeated historical snapshots consume space and are not authority.
            return {key: value[key] for key in ("memory", "inbox", "context") if key in value}
        return value

    history = result.get("messages", result.get("contents", []))
    public = []
    for message in history:
        role = message.get("role")
        if role == "system":
            continue
        if role in {"assistant", "model"}:
            # Only visible prose and tool arguments; no thinking/signature fields.
            content = message.get("content")
            parts = message.get("parts", content if isinstance(content, list) else [])
            visible = []
            if isinstance(content, str) and content:
                visible.append({"text": content})
            for part in parts:
                if part.get("thought") or part.get("type") in {"thinking", "redacted_thinking"}:
                    continue
                if part.get("type") == "text" or "text" in part:
                    visible.append({"text": part["text"]})
                elif part.get("type") == "tool_use":
                    visible.append({"name": part["name"], "arguments": part["input"]})
                elif "functionCall" in part:
                    call = part["functionCall"]
                    visible.append({"name": call["name"], "arguments": call.get("args", {})})
            for call in message.get("tool_calls", []):
                visible.append({"name": call["function"]["name"], "arguments": call["function"]["arguments"]})
            if visible:
                public.append({"role": "assistant", "content": visible})
            continue
        if role not in {"user", "tool"}:
            continue
        content = message.get("content")
        values = []
        if isinstance(content, str):
            message["content"] = text_value(content)
            try:
                values.append(public_value(json.loads(message["content"])))
            except (ValueError, TypeError):
                values.append(content)
        else:
            for part in message.get("parts", content or []):
                if "functionResponse" in part:
                    response = part["functionResponse"]
                    response["response"] = project(response["response"])
                    values.append(response["response"])
                elif part.get("type") == "tool_result":
                    part["content"] = text_value(part["content"])
                    try:
                        values.append(public_value(json.loads(part["content"])))
                    except (ValueError, TypeError):
                        values.append(part["content"])
                elif "text" in part:
                    part["text"] = text_value(part["text"])
                    try:
                        values.append(public_value(json.loads(part["text"])))
                    except (ValueError, TypeError):
                        values.append(part["text"])
        if values:
            public.append({"role": role, "content": values})
    return result, public, list(dict.fromkeys(cleared))


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


def fit_read_result(build: Callable[[int], dict], count: int, capacity: int, *, fits=None) -> dict:
    """Fit a lossless page to the actual serialized tool-result contract.

    The caller rebuilds offsets, cursors and excerpt metadata for each prefix.
    Nothing is sliced after persistence, and raw text is never summarized.
    If required metadata and one unit cannot fit, fail explicitly instead of
    returning an endlessly redirected observation or a non-advancing cursor.
    """
    if count < 0 or capacity < 1:
        raise ValueError("invalid read-result capacity")
    def accepts(result):
        return len(encode(result)) <= capacity and (fits is None or fits(result))

    result = build(count)
    if accepts(result):
        return result
    minimum = 1 if count else 0
    result = build(minimum)
    if not accepts(result):
        raise ContextCapacity("read metadata and one unit exceed tool-result capacity")
    low, high = minimum, count - 1
    while low < high:
        middle = (low + high + 1) // 2
        trial = build(middle)
        if accepts(trial):
            low, result = middle, trial
        else:
            high = middle - 1
    return result


def fit_provider(request: dict, prepare, *, priority_refs=()) -> dict:
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
    # Latest state can grow after a page was read. Preserve its retrieval handle
    # in the minimum window, then try the pending body before older context.
    pending = [item for item in minimal["context"] if item["ref"] in priority_refs]
    additions = [("pending", item) for item in pending if "body" in item]
    additions.extend(("context", item) for item in reversed(minimal["context"])
                     if item["ref"] not in priority_refs)
    for key, nav in minimal.get("navigation", {}).items():
        parent = minimal["review_progress"] if key.startswith("review_") else minimal
        field = key.removeprefix("review_") if key.startswith("review_") else key
        additions.extend((key, item) for item in parent[field])
        parent[field] = []
        nav["next_offset"] = nav["offset"] if nav["total"] else None
    minimal["omitted_count"] += sum("body" in item for key, item in additions
                                    if key in {"context", "pending"})
    minimal["context"] = [
        {"ref": item["ref"], "kind": item["kind"], "body_omitted": True,
         "characters": len(encode(item["body"]))} if "body" in item else item
        for item in pending
    ]
    prepare(minimal, None)  # Essential capacity failures are actionable, never hidden.

    def restore(count):
        candidate = deepcopy(minimal)
        for key, item in additions[:count]:
            if key == "pending":
                index = next(i for i, old in enumerate(candidate["context"])
                             if old["ref"] == item["ref"])
                candidate["context"][index] = item
                candidate["omitted_count"] -= 1
            elif key == "context":
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
        if delivered(result):
            for part in delivered(result):
                start, end = part["offset"], part["end"]
                if part["ref"] == source.ref and 0 <= start < end <= len(source.body["text"]):
                    if part["text"] == source.body["text"][start:end]:
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


def deduplicate_originals(request, protected=()):
    """Project repeated exact originals only when their text remains in this request."""
    result = deepcopy(request)
    entries = sorted(result["context"], key=lambda entry: entry["ref"] in protected, reverse=True)
    seen = {}
    for entry in entries:
        body = entry.get("body", {})
        for part in delivered(body.get("result", {})):
            key = (part["ref"], part["offset"], part["end"], part["text"])
            if key in seen and entry["ref"] not in protected:
                compact = {key: value for key, value in part.items() if key != "text"}
                compact["text_from"] = seen[key]
                if len(encode(compact)) < len(encode(part)):
                    part.clear()
                    part.update(compact)
                    continue
            seen[key] = entry["ref"]
    for entry in entries:
        body = entry.get("body", {})
        if entry["kind"] != "note" or entry["ref"] in protected or not isinstance(body.get("quote"), str):
            continue
        start, quote = body.get("offset"), body["quote"]
        key = (body.get("source"), start, start + len(quote), quote) if type(start) is int else None
        if key in seen and len(quote) > len(seen[key]) + 20:
            body["quote_from"] = seen[key]
            del body["quote"]
    return result


def assemble(
    base: dict[str, Any],
    candidates: list[Artifact],
    memory: Artifact | None,
    capacity: int,
    *,
    direct_refs=None,
    priority_refs=(),
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
        key=lambda a: (a.ref in priority_refs, a.ref in direct, a.kind == "clarification_answer", a.seq),
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
