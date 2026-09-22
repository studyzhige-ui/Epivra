"""Shared evidence judgments, conflict investigations and versioned writing bases.

The host checks identity, lineage and completeness of the declared coverage. It
never decides whether a semantic claim is true or whether research is saturated.
All records are immutable; replacing a judgment is an explicit compare-and-swap.
"""

from __future__ import annotations

from .domain import Conflict, NotAllowed, identity

RESEARCH_KINDS = frozenset(
    {"finding", "research_conflict", "writing_basis", "question_assessment"}
)
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
        return self.store.matching(study, kind, {"direction": direction})

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

    def _support_ranges(self, study, refs):
        ranges: dict[str, list[tuple[int, int]]] = {}
        for ref in refs:
            item = self.store.get(study, ref)
            if item.kind == "note":
                source = item.body["source"]
                start = item.body["offset"]
                end = start + len(item.body["quote"])
            else:
                source, start, end = item.ref, 0, len(item.body["text"])
            ranges.setdefault(source, []).append((start, end))
        return ranges

    def _adds_support(self, study, support, previous):
        prior = self._support_ranges(study, previous)
        for source, ranges in self._support_ranges(study, support).items():
            if source not in prior:
                return True
            for start, end in ranges:
                covered = start
                for left, right in sorted(prior[source]):
                    if left > covered:
                        break
                    covered = max(covered, right)
                if covered < end:
                    return True
        return False

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
                if not self._adds_support(study, support, prior.body["support"]):
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
        except ValueError:
            return True
        return False

    def inputs(self, study, direction=None):
        """Public arrivals only; identities deduplicate within this direction."""
        direction = direction or self.store.control(study).direction
        return self.store.research_input_index(study, direction)

    def _handled(self, study, assessments):
        visited, corrected = set(), set()
        history = []
        pending = list(assessments)
        while pending:
            item = pending.pop()
            if item.ref in visited:
                continue
            visited.add(item.ref)
            history.append(item)
            for check in item.body["checks"]:
                if check.get("corrects"):
                    target = check["corrects"]
                    corrected.add((target["assessment"], target["index"]))
            if item.body.get("replaces"):
                pending.append(self.store.get(study, item.body["replaces"]))
        refs = [ref for item in assessments for ref in item.body["findings"]]
        refs.extend(
            ref
            for item in history
            for i, check in enumerate(item.body["checks"])
            if (item.ref, i) not in corrected
            for ref in check["refs"]
        )
        return {item.ref for item in self._public_dependencies(study, refs)}

    def _public_dependencies(self, study, refs):
        pending, visited = list(refs), set()
        while pending:
            ref = pending.pop()
            if ref in visited:
                continue
            visited.add(ref)
            item = self.store.get(study, ref)
            yield item
            if item.kind == "finding":
                pending.extend(item.body["sources"])
            elif item.kind == "observation":
                receipt = item.body.get("research_receipt", {})
                pending.extend(receipt.get("sources", []))
                if receipt.get("reused_from"):
                    pending.append(receipt["reused_from"])
            elif item.kind == "work_result":
                pending.extend(item.body.get("refs", []))

    def pending(self, study, assessments=None):
        assessments = (
            self.current(study, "question_assessment")
            if assessments is None
            else assessments
        )
        handled = self._handled(study, assessments)
        return [
            self.store.get(study, ref)
            for ref in self.inputs(study)
            if ref not in handled
        ]

    def _assess(self, study, work, direction, updates, operation):
        questions = self.questions(study)
        current = {
            a.body["question"]: a
            for a in self.current(study, "question_assessment", direction)
        }
        seen, saved = set(), []
        available = self.inputs(study, direction)
        for row in updates:
            question = row["question"]
            if (
                type(question) is not int
                or not 0 <= question < len(questions)
                or question in seen
            ):
                raise ValueError(
                    "each update must name a distinct original question index"
                )
            seen.add(question)
            prior = current.get(question)
            if row.get("replaces") != (prior.ref if prior else None):
                raise Conflict(f"question {question} assessment changed; replaces must be {prior.ref if prior else None}")
            if not row["answer_target"].strip() or not row["reason"].strip():
                raise ValueError(
                    "answer_target and reason must preserve the user's original requirements"
                )
            if row["decision"] not in {"continue", "ready", "limited"}:
                raise ValueError("invalid assessment decision")
            for ref in row["findings"]:
                self._current(study, ref, "finding", direction)
            for gap in row["remaining"]:
                if (
                    gap["disposition"] not in {"next", "blocked", "bounded"}
                    or not gap["question"].strip()
                    or not gap["reason"].strip()
                ):
                    raise ValueError(
                        "remaining paths require a consequential question and disposition reason"
                    )
            if row["decision"] == "ready" and (
                not row["findings"]
                or any(g["disposition"] != "bounded" for g in row["remaining"])
            ):
                raise ValueError(
                    "ready requires supported findings and no outstanding next/blocked path"
                )
            if row["decision"] == "limited" and (
                not row["remaining"]
                or any(g["disposition"] == "next" for g in row["remaining"])
            ):
                raise ValueError(
                    "limited requires explicit limitations, not feasible next steps"
                )
            for check in row["checks"]:
                if (
                    check["effect"] not in {"changed", "no_material_change", "blocked"}
                    or not check["angle"].strip()
                    or not check["reason"].strip()
                    or not check["refs"]
                ):
                    raise ValueError(
                        "checks require an actual result, angle, effect and explanation"
                    )
                for ref in check["refs"]:
                    item = self.store.get(study, ref)
                    if item.kind in {"finding", "research_conflict"}:
                        if item.body.get("direction") != direction:
                            raise NotAllowed("check belongs to another direction")
                    elif (
                        item.kind == "observation"
                        and item.body.get("direction") == direction
                        and item.body.get("research_receipt")
                    ):
                        pass
                    elif ref not in available:
                        raise ValueError(
                            "check must cite a research input or finding/conflict in this direction"
                        )
                if check["effect"] == "no_material_change":
                    for item in self._public_dependencies(study, check["refs"]):
                        outcome = (
                            item.body.get("research_receipt", {}).get("outcome")
                            if item.kind == "observation"
                            else None
                        )
                        failed_analysis = item.kind == "source" and item.body.get(
                            "execution_status"
                        ) not in {None, "succeeded"}
                        cancelled = (
                            item.kind == "work_result"
                            and item.body.get("status") == "cancelled"
                        )
                        if (
                            outcome in {"blocked", "partial", "unclassified"}
                            or failed_analysis
                            or cancelled
                        ):
                            raise ValueError(
                                "failed/partial/unclassified acquisition cannot establish no material change, including through helper handoffs"
                            )
                correction = check.get("corrects")
                if correction:
                    target = self.store.get(study, correction["assessment"])
                    lineage, previous = set(), prior
                    while previous:
                        lineage.add(previous.ref)
                        previous = (
                            self.store.get(study, previous.body["replaces"])
                            if previous.body.get("replaces")
                            else None
                        )
                    if (
                        target.ref not in lineage
                        or type(correction["index"]) is not int
                        or not 0 <= correction["index"] < len(target.body["checks"])
                    ):
                        raise ValueError(
                            "correction must identify a check in this question's prior lineage"
                        )
            body = {
                **row,
                "direction": direction,
                "producer": work,
                "operation": operation,
            }
            saved.append(
                self.store._put(
                    study,
                    "question_assessment",
                    body,
                    (
                        work,
                        direction,
                        *row["findings"],
                        *((prior.ref,) if prior else ()),
                    ),
                )
            )
        return saved

    def assess_questions(self, study, work, epoch, *, updates, _operation=None):
        if not updates:
            raise ValueError("assessment update batch must not be empty")
        with self.store.transaction():
            actor, direction = self._scope(study, work, epoch)
            if actor.body["role"] != "lead":
                raise NotAllowed("only the research owner updates question assessments")
            request = identity(updates)
            receipts = (
                self.store.matching(
                    study, "question_assessment", {"batch_operation": _operation}
                )
                if _operation
                else []
            )
            if receipts:
                if any(a.body.get("request_hash") != request for a in receipts):
                    raise Conflict("assessment operation reused with different input")
                return receipts
            enriched = [
                {**row, "batch_operation": _operation, "request_hash": request}
                for row in updates
            ]
            return self._assess(study, work, direction, enriched, _operation)

    def _ready(self, study, assessments, direction):
        if sorted(a.body["question"] for a in assessments) != list(
            range(len(self.questions(study)))
        ):
            raise ValueError(
                "assessments must address every original question exactly once"
            )
        for item in assessments:
            self._current(study, item.ref, "question_assessment", direction)
            if item.body["decision"] == "continue":
                raise Conflict("research still has a meaningful next step: " + item.ref)
            for ref in item.body["findings"]:
                self._current(study, ref, "finding", direction)
        pending = self.pending(study, assessments)
        if pending:
            raise Conflict(
                "assess new research inputs before writing/publishing: "
                + ", ".join(a.ref for a in pending)
            )
        completed = {r.body["producer"] for r in self.store.list(study, "work_result")}
        unfinished = [
            w.ref
            for w in self.store.matching(study, "work", {"direction": direction})
            if w.body["role"] in {"investigator", "synthesizer"}
            and w.ref not in completed
        ]
        if unfinished:
            raise Conflict(
                "research helpers must deliver or be explicitly cancelled: "
                + ", ".join(unfinished)
            )

    def prepare_writing(
        self,
        study,
        work,
        epoch,
        *,
        assessments=(),
        updates=(),
        rationale,
        replaces=None,
        _operation=None,
    ):
        if not rationale.strip():
            raise ValueError(
                "explain readiness and the value of further feasible investigation"
            )
        with self.store.transaction():
            actor, direction = self._scope(study, work, epoch)
            if actor.body["role"] not in {"lead", "writer"} or (
                updates and actor.body["role"] != "lead"
            ):
                raise NotAllowed(
                    "only owner updates assessments; writer uses existing assessments"
                )
            request_hash = identity(assessments, updates, rationale, replaces)
            replay = self._receipt(study, "writing_basis", _operation, request_hash)
            if replay:
                return replay
            selected = [
                self._current(study, ref, "question_assessment", direction)
                for ref in assessments
            ]
            selected.extend(self._assess(study, work, direction, updates, _operation))
            self._ready(study, selected, direction)
            chosen = {
                ref: self._current(study, ref, "finding", direction)
                for a in selected
                for ref in a.body["findings"]
            }
            conflicts = self.current(study, "research_conflict", direction)
            if any(
                c.body["disposition"] == "open"
                or self.conflict_stale(study, c, direction)
                for c in conflicts
            ):
                raise Conflict("an open or stale conflict still needs investigation")
            current = self.current_basis(study, direction)
            if (current.ref if current else None) != replaces:
                raise Conflict(
                    "writing basis changed; replace the current basis explicitly"
                )
            sources = list(
                dict.fromkeys(ref for a in chosen.values() for ref in a.body["sources"])
            )
            coverage = [
                {
                    "question": a.body["question"],
                    "findings": a.body["findings"],
                    "limitation": "; ".join(
                        g["question"] + ": " + g["reason"] for g in a.body["remaining"]
                    ),
                }
                for a in selected
            ]
            body = {
                "direction": direction,
                "producer": work,
                "assessments": [a.ref for a in selected],
                "findings": list(chosen),
                "coverage": coverage,
                "rationale": rationale,
                "limitations": [c["limitation"] for c in coverage if c["limitation"]],
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
                    *body["assessments"],
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
        if "assessments" not in basis.body:
            raise Conflict(
                "historical writing basis predates the current research contract"
            )
        self._ready(
            study,
            [self.store.get(study, ref) for ref in basis.body["assessments"]],
            direction,
        )
        return basis

    def snapshot(self, study):
        direction = self.store.control(study).direction
        basis = self.current_basis(study, direction)
        stale = False
        if basis:
            try:
                self.require_basis(study, basis.ref, direction)
            except (Conflict, NotAllowed, ValueError):
                stale = True
        assessments = {
            a.body["question"]: a
            for a in self.current(study, "question_assessment", direction)
        }
        return {
            "pending_inputs": [
                {"ref": a.ref, "kind": a.kind} for a in self.pending(study)
            ],
            "questions": [
                {
                    "index": i,
                    "question": q,
                    **(
                        {
                            "assessment": assessments[i].ref,
                            **{
                                key: assessments[i].body[key]
                                for key in (
                                    "answer_target",
                                    "decision",
                                    "remaining",
                                    "reason",
                                )
                            },
                        }
                        if i in assessments
                        else {}
                    ),
                }
                for i, q in enumerate(self.questions(study))
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
