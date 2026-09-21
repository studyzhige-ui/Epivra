"""A continuous authoring workspace with immutable, evidence-bound revisions.

Behavior references: Codex apply_patch and the provided Claude Code edit tools.
Exact edits are simultaneous against an explicit base. No fuzzy replacement,
source truncation, implicit acceptance, or re-generation of unchanged text.
"""

from __future__ import annotations

from .citations import render, validate
from .context import fit_read_result
from .domain import INLINE_TOOL_RESULT_CHARS, Conflict, NotAllowed, identity
from .research import ResearchLedger
from .review import report_metrics


def apply_edits(text: str, edits: list[dict[str, str]]) -> str:
    if not edits:
        raise ValueError("provide at least one exact edit")
    spans: list[tuple[int, int, str]] = []
    for index, edit in enumerate(edits):
        old, new = edit["old"], edit["new"]
        if not old or old == new:
            raise ValueError(
                f"edit {index}: old must be nonempty and change the manuscript"
            )
        start = text.find(old)
        if start < 0:
            raise ValueError(
                f"edit {index}: original text not found; read the exact current draft"
            )
        if text.find(old, start + 1) >= 0:
            raise ValueError(
                f"edit {index}: ambiguous match; include surrounding unchanged text"
            )
        spans.append((start, start + len(old), new))
    spans.sort()
    if any(a[1] > b[0] for a, b in zip(spans, spans[1:])):
        raise ValueError("edits overlap; all edits must target the same original base")
    parts: list[str] = []
    cursor = 0
    for start, end, replacement in spans:
        parts.extend((text[cursor:start], replacement))
        cursor = end
    parts.append(text[cursor:])
    return "".join(parts)


class WritingWorkspace:
    def __init__(self, store):
        self.store = store
        self.research = ResearchLedger(store)

    def current(self, study, direction=None):
        direction = direction or self.store.control(study).direction
        # One manuscript per research direction; helpers share, rather than fork,
        # its head. The Store process lock serializes transactions across processes.
        rows = self.store.matching(study, "report", {"document": direction})
        return rows[-1] if rows else None

    def _allowed(self, study, work, epoch, base=None):
        actor = self.store.require_work(study, work, epoch)
        if not self.store.control(study).approved or actor.body["role"] == "reviewer":
            raise NotAllowed("an approved research author is required")
        if any(
            actor.body["direction"] in p.parents
            for p in self.store.list(study, "publication")
        ):
            raise NotAllowed(
                "published research is immutable; only a new user direction can reopen it"
            )
        if base and actor.body["role"] != "lead":
            report = self.store.get(study, base)
            if report.body.get("producer") != work and base not in actor.body["inputs"]:
                raise NotAllowed(
                    "a helper edits only its own draft or an explicitly assigned base"
                )
        return actor

    def save(
        self,
        study,
        work,
        epoch,
        step,
        index,
        *,
        text=None,
        edits=None,
        base=None,
        basis=None,
        evidence=None,
        handoff="",
        research_refs=(),
    ):
        key = identity(step, index, "draft_save")
        with self.store.transaction():
            actor = self._allowed(study, work, epoch, base)
            direction = actor.body["direction"]
            old_receipts = self.store.matching(
                study, "draft_saved", {"request_id": key}
            )
            request_digest = identity(text, edits, base, basis, evidence, handoff)
            if old_receipts:
                previous = old_receipts[-1]
                if previous.body["request_digest"] != request_digest:
                    raise Conflict(
                        "draft operation identity reused with different content"
                    )
                return self._result(previous)
            current = self.current(study, direction)
            if (current.ref if current else None) != base:
                raise Conflict(
                    "draft changed; read the shared current version and apply the edit to that base"
                )
            if edits is not None:
                if current is None:
                    raise ValueError("save the first manuscript before patching")
                if text is not None:
                    raise ValueError("provide either full text or edits, not both")
                if not edits:
                    if not basis or basis == current.body["basis"]:
                        raise ValueError(
                            "empty edits require an explicit different writing basis"
                        )
                    text = current.body["manuscript"]
                else:
                    text = apply_edits(current.body["manuscript"], edits)
                evidence = current.body["evidence"] if evidence is None else evidence
                basis = basis or current.body["basis"]
            if not isinstance(text, str) or not text.strip():
                raise ValueError("a nonempty manuscript is required")
            active_basis = self.research.current_basis(study, direction)
            basis = basis or (active_basis.ref if active_basis else None)
            if not basis:
                raise NotAllowed(
                    "prepare_writing must establish a source-grounded writing basis before the first full draft"
                )
            knowledge = self.research.require_basis(study, basis, direction)
            evidence = (
                knowledge.body["sources"]
                if evidence is None
                else list(dict.fromkeys(evidence))
            )
            if not set(evidence).issubset(knowledge.body["sources"]):
                raise ValueError(
                    "draft uses evidence outside its assessed writing basis; investigate and update the basis first"
                )
            rendered = render(text, evidence, lambda ref: self.store.get(study, ref))
            metrics = report_metrics(rendered)
            item = self.store._put(
                study,
                "report",
                {
                    **rendered,
                    "evidence": evidence,
                    "producer": work,
                    "manuscript": text,
                    "document": direction,
                    "basis": basis,
                    **({"previous_report": base} if base else {}),
                },
                (
                    work,
                    direction,
                    step,
                    basis,
                    *evidence,
                    *rendered["citations"],
                    *actor.body["inputs"],
                    *research_refs,
                    *((base,) if base else ()),
                ),
            )
            receipt = self.store._put(
                study,
                "draft_saved",
                {
                    "ref": item.ref,
                    "producer": work,
                    "document": direction,
                    "basis": basis,
                    "handoff": handoff,
                    "report_metrics": metrics,
                    "request_id": key,
                    "request_digest": request_digest,
                    "edit_count": len(edits) if edits is not None else None,
                    "mode": (
                        "basis_rebind"
                        if edits == []
                        else "patch"
                        if edits is not None
                        else "full_save"
                    ),
                },
                (work, direction, step, item.ref, basis),
            )
            return self._result(receipt)

    @staticmethod
    def _result(receipt):
        return {
            "ref": receipt.body["ref"],
            "receipt": receipt.ref,
            "basis": receipt.body["basis"],
            "state": "saved_not_finished",
            "report_metrics": receipt.body["report_metrics"],
            "mode": receipt.body["mode"],
            "edit_count": receipt.body["edit_count"],
        }

    def read(
        self, study, work, epoch, *, ref=None, offset=0, limit=None, capacity=12000
    ):
        actor = self.store.require_work(study, work, epoch)
        current = self.current(study, actor.body["direction"])
        if ref is None:
            if current is None:
                raise ValueError("no saved draft")
            report = current
        else:
            report = self.store.get(study, ref)
        if (
            report.kind != "report"
            or report.body.get("document") != actor.body["direction"]
        ):
            raise NotAllowed("draft must belong to this research direction")
        validate(report.body, lambda source: self.store.get(study, source))
        text = report.body["manuscript"]
        if (
            type(offset) is not int
            or offset < 0
            or (limit is not None and (type(limit) is not int or limit < 1))
        ):
            raise ValueError("invalid draft page")
        offset = min(offset, len(text))
        size = min(len(text) - offset, limit or capacity)

        def page(count):
            end = offset + count
            return {
                "ref": report.ref,
                "current": report.ref == (current.ref if current else None),
                "basis": report.body["basis"],
                "format": "author Markdown with original [[cite:ref]] markers",
                "text": text[offset:end],
                "offset": offset,
                "end": end,
                "total": len(text),
                "next_offset": end if end < len(text) else None,
            }

        return fit_read_result(page, size, min(capacity, INLINE_TOOL_RESULT_CHARS))

    def require_publishable(self, study, report):
        if "document" not in report.body:
            raise NotAllowed(
                "legacy draft has no current evidence-bound workspace; start a new study"
            )
        current = self.current(study)
        if current is None or current.ref != report.ref:
            raise Conflict("publication requires the current shared draft")
        self.research.require_basis(study, report.body["basis"])
        text = report.body.get("manuscript")
        if not isinstance(text, str):
            raise ValueError("saved draft is missing its author text")
        rendered = render(
            text, report.body["evidence"], lambda ref: self.store.get(study, ref)
        )
        if any(report.body.get(key) != value for key, value in rendered.items()):
            raise ValueError("saved manuscript and citation rendering do not match")
