"""Read-only public work/report views. Never inspect model steps or responses."""

from .citations import occurrences
from .domain import Conflict


def source_info(source):
    return {
        "ref": source.ref,
        **{key: source.body.get(key) for key in ("origin", "name", "title", "coverage")},
    }


def published_report(store, study, expected=None):
    direction = store.control(study).direction
    publications = [
        p for p in store.list(study, "publication") if direction in p.parents
    ]
    if not publications:
        if expected:
            raise Conflict("report is no longer current")
        return {"report": None}
    report = store.get(study, publications[-1].body["report"])
    if expected and report.ref != expected:
        raise Conflict("report has changed")
    sources = {ref: store.get(study, ref) for ref in report.body["evidence"]}
    citations = {}
    numbers = []
    for ref in report.body.get("citations", []):
        item = store.get(study, ref)
        source = item.body["source"] if item.kind == "note" else item.ref
        if source not in sources:
            raise ValueError("citation outside report evidence")
        entry = citations.setdefault(
            source,
            {
                "number": len(citations) + 1,
                "source": source,
                "quotes": [],
            },
        )
        numbers.append(entry["number"])
        if item.kind == "note":
            quote = {"text": item.body["quote"], "offset": item.body["offset"]}
            if quote not in entry["quotes"]:
                entry["quotes"].append(quote)
    length = report.body.get("citation_body_length", len(report.body["text"]))
    marks = (
        list(occurrences(report.body["text"][:length], numbered=True))
        if numbers
        else []
    )
    if len(marks) != len(numbers) or any(
        int(mark[1]) != n for mark, n in zip(marks, numbers)
    ):
        raise ValueError("citation occurrence binding changed")
    return {
        "ref": report.ref,
        "direction": direction,
        "text": report.body["text"],
        "citation_body_length": report.body.get("citation_body_length"),
        "citations": list(citations.values()),
        "citation_marks": [
            {"start": mark.start(), "end": mark.end(), "number": n}
            for mark, n in zip(marks, numbers)
        ],
        "sources": [source_info(s) for s in sources.values()],
    }


def source_page(store, study, ref, offset=0, length=12000):
    if (
        type(offset) is not int
        or offset < 0
        or type(length) is not int
        or not 1 <= length <= 24000
    ):
        raise ValueError("invalid source page")
    source = store.get(study, ref)
    if source.kind != "source":
        raise ValueError("expected source")
    text = source.body.get("text", "")
    return {
        **source_info(source),
        "text": text[offset : offset + length],
        "offset": offset,
        "total": len(text),
        "next_offset": min(offset + length, len(text)),
    }


def progress(store, study, errors=None):
    direction = store.control(study).direction
    works = [w for w in store.list(study, "work") if w.body["direction"] == direction]
    results = {r.body.get("producer"): r for r in store.list(study, "work_result")}
    questions = {q.body["work"]: q for q in store.clarifications(study, open_only=True)}
    waits = {}
    for wait in store.list(study, "work_wait"):
        waits[wait.body.get("producer")] = wait
    revisions = {}
    for kind in ("note", "clarification_answer", "draft_saved"):
        for item in store.list(study, kind):
            revisions.setdefault(item.body.get("producer"), {})[kind] = item.ref
    items = []
    for work in works:
        result = results.get(work.ref)
        question = questions.get(work.ref)
        error = (errors or {}).get(work.ref)
        wait = waits.get(work.ref)
        waiting = wait and any(ref not in results for ref in wait.body.get("refs", []))
        state = (
            "delivered"
            if result
            else "blocked"
            if error
            else "clarification"
            if question
            else "waiting"
            if waiting
            else "pending"
        )
        items.append(
            {
                "ref": work.ref,
                "role": work.body["role"],
                "task": work.body["task"],
                "state": state,
                "result": result.ref if result else None,
                "revision": revisions.get(work.ref),
                "question": question.body["text"] if question else None,
                "error": error,
            }
        )
    return {"direction": direction, "work": items}


def work_detail(store, study, ref):
    work = store.get(study, ref)
    if work.kind != "work" or work.body["direction"] != store.control(study).direction:
        raise Conflict("work is no longer current")
    entries = []
    for kind in ("note", "clarification_answer", "draft_saved", "work_result"):
        for item in store.list(study, kind):
            if item.body.get("producer") != work.ref:
                continue
            body = item.body
            if kind in {"work_result", "draft_saved"} and body.get("ref"):
                target = store.get(study, body["ref"])
                body = target.body
                kind_label = target.kind
            else:
                kind_label = kind
            # Public tool artifacts only; never fallback to dumping unknown bodies.
            text = body.get("text") or body.get("claim") or body.get("summary") or ""
            if kind_label == "review":
                text = (
                    body.get("reason", "")
                    or body.get("rationale", "")
                    or body.get("text", "")
                )
            entries.append(
                {
                    "ref": item.ref,
                    "kind": kind_label,
                    "text": text,
                    "quote": body.get("quote"),
                    "source": body.get("source"),
                    "accepted": body.get("accepted"),
                    "report": body.get("report"),
                    "defects": body.get("defects", []),
                    "comments": body.get("comments", []),
                }
            )
    return {"work": ref, "entries": entries}
