"""Shared evidence judgments, conflict investigations and versioned writing bases.

The host checks identity, lineage and completeness of the declared coverage. It
never decides whether a semantic claim is true or whether research is saturated.
All records are immutable; replacing a judgment is an explicit compare-and-swap.
"""

from __future__ import annotations

from .domain import Conflict, NotAllowed, identity

RESEARCH_KINDS = frozenset({"finding", "research_conflict", "writing_basis"})
STATUSES = ("source_statement", "observation", "inference", "prediction")
DISPOSITIONS = (
    "open",
    "different_scope",
    "different_version",
    "transcription_error",
    "no_conflict",
    "genuine_disagreement",
    "insufficient_material",
)


class ResearchLedger:
    def __init__(self, store):
        self.store = store

    def _scope(self, study, work, epoch):
        actor = self.store.require_work(study, work, epoch)
        if any(
            actor.body["direction"] in p.parents
            for p in self.store.list(study, "publication")
        ):
            raise NotAllowed(
                "published research evidence is immutable; only a new user direction can reopen it"
            )
        if not self.store.control(study).approved:
            raise NotAllowed("initial route approval required")
        if actor.body["role"] == "reviewer":
            raise NotAllowed(
                "the independent editor returns issues; it does not rewrite research evidence"
            )
        return actor, actor.body["direction"]

    def _receipt(self, study, kind, operation, request):
        if operation is None:
            return None
        rows = self.store.matching(study, kind, {"operation": operation})
        if rows:
            if rows[-1].body.get("request_hash") != request:
                raise Conflict(
                    "research operation identity reused with different input"
                )
            return rows[-1]
        return None

    def _records(self, study, kind, direction):
        return [
            a
            for a in self.store.list(study, kind)
            if a.body.get("direction") == direction
        ]

    def current(self, study, kind, direction=None):
        direction = direction or self.store.control(study).direction
        records = self._records(study, kind, direction)
        replaced = {a.body["replaces"] for a in records if a.body.get("replaces")}
        return [a for a in records if a.ref not in replaced]

    def _current(self, study, ref, kind, direction):
        item = self.store.get(study, ref)
        if item.kind != kind or item.body.get("direction") != direction:
            raise NotAllowed("record must belong to this research direction")
        if any(
            a.body.get("replaces") == ref for a in self._records(study, kind, direction)
        ):
            raise Conflict(
                "record changed; read the current research workspace before updating"
            )
        return item

    def sources(self, study, refs):
        """Only actual original snapshots/exact excerpts, never consensus votes."""
        sources = []
        for ref in dict.fromkeys(refs):
            item = self.store.get(study, ref)
            if item.kind == "note":
                source = self.store.get(study, item.body.get("source", ""))
                quote, offset = item.body.get("quote"), item.body.get("offset")
                if (
                    not isinstance(quote, str)
                    or not quote.strip()
                    or type(offset) is not int
                    or offset < 0
                    or source.ref not in item.parents
                    or source.body.get("text", "")[offset : offset + len(quote)]
                    != quote
                ):
                    raise ValueError(
                        "support note must preserve its exact original excerpt"
                    )
                item = source
            if item.kind != "source" or not isinstance(item.body.get("text"), str):
                raise ValueError(
                    "support must be a source snapshot or exact evidence note, not a plan, review or summary"
                )
            if item.ref not in sources:
                sources.append(item.ref)
        return sources

    def record_finding(
        self,
        study,
        work,
        epoch,
        *,
        statement,
        status,
        support,
        conditions=(),
        limits=(),
        replaces=None,
        reason="",
        _operation=None,
    ):
        if not statement.strip() or status not in STATUSES or not support:
            raise ValueError(
                "finding requires a statement, declared evidence status and direct support"
            )
        with self.store.transaction():
            actor, direction = self._scope(study, work, epoch)
            request_hash = identity(
                statement, status, support, conditions, limits, replaces, reason
            )
            replay = self._receipt(study, "finding", _operation, request_hash)
            if replay:
                return replay
            sources = self.sources(study, support)
            prior = (
                self._current(study, replaces, "finding", direction)
                if replaces
                else None
            )
            if prior and not reason.strip():
                raise ValueError(
                    "explain which premise changed when replacing a finding"
                )
            if (
                prior
                and status == "source_statement"
                and prior.body["status"] != status
            ):
                if set(support).issubset(prior.body["support"]):
                    raise ValueError(
                        "a restatement cannot upgrade an inference to source fact; supply new direct support or retain its status"
                    )
            body = {
                "statement": statement,
                "status": status,
                "support": list(dict.fromkeys(support)),
                "sources": sources,
                "conditions": list(conditions),
                "limits": list(limits),
                "producer": actor.ref,
                "direction": direction,
                "operation": _operation,
                "request_hash": request_hash,
            }
            if prior:
                body.update(replaces=prior.ref, reason=reason)
            return self.store._put(
                study,
                "finding",
                body,
                (work, direction, *support, *((replaces,) if replaces else ())),
            )

    def record_conflict(
        self,
        study,
        work,
        epoch,
        *,
        question,
        findings,
        disposition="open",
        explanation="",
        evidence=(),
        replaces=None,
        _operation=None,
    ):
        if not question.strip() or not findings or disposition not in DISPOSITIONS:
            raise ValueError(
                "a conflict investigation requires a concrete question and affected findings"
            )
        if disposition != "open" and (not explanation.strip() or not evidence):
            raise ValueError(
                "investigated conflicts require a source-grounded explanation"
            )
        with self.store.transaction():
            _, direction = self._scope(study, work, epoch)
            request_hash = identity(
                question, findings, disposition, explanation, evidence, replaces
            )
            replay = self._receipt(study, "research_conflict", _operation, request_hash)
            if replay:
                return replay
            for ref in findings:
                self._current(study, ref, "finding", direction)
            self.sources(study, evidence)
            if replaces:
                self._current(study, replaces, "research_conflict", direction)
            body = {
                "question": question,
                "findings": list(dict.fromkeys(findings)),
                "disposition": disposition,
                "explanation": explanation,
                "evidence": list(dict.fromkeys(evidence)),
                "producer": work,
                "direction": direction,
                "operation": _operation,
                "request_hash": request_hash,
            }
            if replaces:
                body["replaces"] = replaces
            return self.store._put(
                study,
                "research_conflict",
                body,
                (
                    work,
                    direction,
                    *findings,
                    *evidence,
                    *((replaces,) if replaces else ()),
                ),
            )

    def questions(self, study):
        control = self.store.control(study)
        if control.plan:
            plan = self.store.get(study, control.plan)
            questions = plan.body.get("brief", {}).get("questions")
            if control.direction in plan.parents and questions:
                return questions
        return [self.store.get(study, control.direction).body["request"]]

    def conflict_stale(self, study, item, direction):
        try:
            for ref in item.body["findings"]:
                self._current(study, ref, "finding", direction)
        except (ValueError, Conflict, NotAllowed):
            return True
        return False

    def prepare_writing(
        self,
        study,
        work,
        epoch,
        *,
        findings,
        coverage,
        rationale,
        limitations=(),
        replaces=None,
        _operation=None,
    ):
        """Version the Agent's readiness judgment; don't manufacture truth scores."""
        if not rationale.strip():
            raise ValueError(
                "explain coverage, source support and why further feasible investigation is not needed now"
            )
        with self.store.transaction():
            _, direction = self._scope(study, work, epoch)
            request_hash = identity(
                findings, coverage, rationale, limitations, replaces
            )
            replay = self._receipt(study, "writing_basis", _operation, request_hash)
            if replay:
                return replay
            chosen = {
                ref: self._current(study, ref, "finding", direction) for ref in findings
            }
            expected = list(range(len(self.questions(study))))
            if (
                any(type(c["question"]) is not int for c in coverage)
                or sorted(c["question"] for c in coverage) != expected
            ):
                raise ValueError(
                    "coverage must address each approved research question exactly once, using its zero-based index"
                )
            used = set()
            for row in coverage:
                refs = set(row.get("findings", ()))
                if not refs.issubset(chosen):
                    raise ValueError(
                        "coverage can only cite findings in this writing basis"
                    )
                if not refs and not row.get("limitation", "").strip():
                    raise ValueError(
                        "an unanswered question requires its actual limitation, not an invented answer"
                    )
                used.update(refs)
            if used != set(chosen):
                raise ValueError(
                    "every selected finding must serve at least one approved question"
                )
            conflicts = self.current(study, "research_conflict", direction)
            if any(
                c.body["disposition"] == "open"
                or self.conflict_stale(study, c, direction)
                for c in conflicts
            ):
                raise Conflict(
                    "an open or stale conflict still needs investigation; update it from original evidence"
                )
            current = self.current_basis(study, direction)
            if (current.ref if current else None) != replaces:
                raise Conflict(
                    "writing basis changed; replace the current basis explicitly"
                )
            sources = list(
                dict.fromkeys(ref for a in chosen.values() for ref in a.body["sources"])
            )
            body = {
                "direction": direction,
                "producer": work,
                "findings": list(chosen),
                "coverage": coverage,
                "rationale": rationale,
                "limitations": list(limitations),
                "conflicts": [c.ref for c in conflicts],
                "sources": sources,
                "status": "agent_assessed_not_host_certified",
                "considered_findings": [
                    f.ref for f in self.current(study, "finding", direction)
                ],
                "operation": _operation,
                "request_hash": request_hash,
            }
            if replaces:
                body["replaces"] = replaces
            return self.store._put(
                study,
                "writing_basis",
                body,
                (
                    work,
                    direction,
                    *chosen,
                    *sources,
                    *(c.ref for c in conflicts),
                    *((replaces,) if replaces else ()),
                ),
            )

    def current_basis(self, study, direction=None):
        entries = self.current(study, "writing_basis", direction)
        return entries[-1] if entries else None

    def require_basis(self, study, ref, direction=None):
        direction = direction or self.store.control(study).direction
        basis = self._current(study, ref, "writing_basis", direction)
        if set(basis.body["considered_findings"]) != {
            f.ref for f in self.current(study, "finding", direction)
        }:
            raise Conflict(
                "research knowledge changed; assess the updated findings before writing or publishing"
            )
        for finding in basis.body["findings"]:
            self._current(study, finding, "finding", direction)
        conflicts = self.current(study, "research_conflict", direction)
        if set(basis.body["conflicts"]) != {c.ref for c in conflicts}:
            raise Conflict("conflict knowledge changed; reassess the writing basis")
        if any(
            c.body["disposition"] == "open" or self.conflict_stale(study, c, direction)
            for c in conflicts
        ):
            raise Conflict("writing basis has an uninvestigated or stale conflict")
        return basis

    def snapshot(self, study):
        direction = self.store.control(study).direction
        basis = self.current_basis(study, direction)
        stale = False
        if basis:
            try:
                self.require_basis(study, basis.ref, direction)
            except (Conflict, NotAllowed):
                stale = True
        return {
            "questions": [
                {"index": i, "question": q} for i, q in enumerate(self.questions(study))
            ],
            "findings": [
                {
                    "ref": a.ref,
                    "statement": a.body["statement"],
                    "status": a.body["status"],
                }
                for a in self.current(study, "finding", direction)
            ],
            "conflicts": [
                {
                    "ref": a.ref,
                    "question": a.body["question"],
                    "disposition": a.body["disposition"],
                    "stale": self.conflict_stale(study, a, direction),
                }
                for a in self.current(study, "research_conflict", direction)
            ],
            "basis": None if not basis else {"ref": basis.ref, "stale": stale},
        }
