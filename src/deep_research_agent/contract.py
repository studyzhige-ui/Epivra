"""The Research Contract: what the user approved, and the questions it asks.

The Contract is natural language, because research scope is a semantic
agreement rather than a schema.  One thing is structured: the **numbered
question model**.  Assignments, Synthesis sections, and report sections
reference questions by stable label (``Q1``, ``Q2``, ...), which is why this
module exists.

Why numbered questions rather than references derived from Contract prose:
an earlier design derived assignment targets from "text that must appear
verbatim in a Contract section".  That makes every reference break when the
Contract is regenerated, and forces the model to reproduce exact substrings --
precisely the class of runtime-identity bookkeeping that models fail at.  A
question label is authored once, is visible in the approved Contract the user
read, and survives editing of the surrounding prose.

This module is pure domain logic: no LangGraph, provider, HTTP, or database
imports.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from .state import ArtifactValidationError

#: The six semantic blocks a Contract must cover.  They are fixed because they
#: are the questions a reader of a research protocol needs answered, not because
#: they are a workflow: purpose, questions, scope, method, deliverable, limits.
CONTRACT_SECTIONS: tuple[str, ...] = (
    "purpose_and_use",
    "question_model",
    "scope_and_definitions",
    "evidence_and_method",
    "deliverable_and_assurance",
    "adaptation_and_limits",
)

_SECTION_TITLES: Mapping[str, str] = {
    "purpose_and_use": "目的与用途",
    "question_model": "问题模型",
    "scope_and_definitions": "范围与定义",
    "evidence_and_method": "证据与分析方法",
    "deliverable_and_assurance": "交付与保证",
    "adaptation_and_limits": "自适应边界与已知限制",
}

QuestionRole = Literal["primary", "supporting"]

_LABEL_RE = re.compile(r"^Q([1-9][0-9]?)$")
#: Recognises a heading like "### Q2. Does uptake differ by subgroup?" and the
#: terser "Q2: ..." form, so Contract prose stays readable to the user.
_QUESTION_LINE_RE = re.compile(
    r"^\s{0,3}(?:#{1,6}\s*)?(?:[-*]\s*)?(Q[1-9][0-9]?)\s*[.:、．]\s*(.+?)\s*$"
)


def require_question_label(value: str) -> str:
    """Reject anything that is not a canonical question label."""

    if not isinstance(value, str) or not _LABEL_RE.match(value):
        raise ArtifactValidationError(
            f"question label must look like 'Q1', got {value!r}"
        )
    return value


def _label_order(label: str) -> int:
    match = _LABEL_RE.match(label)
    if match is None:  # pragma: no cover - guarded by require_question_label
        raise ArtifactValidationError(f"invalid question label {label!r}")
    return int(match.group(1))


def _require_text(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ArtifactValidationError(f"{label} must be a non-empty string")
    return value.strip()


@dataclass(frozen=True, slots=True)
class ResearchQuestion:
    """One labelled question and the role it plays in answering the user."""

    label: str
    text: str
    role: QuestionRole
    supports: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        require_question_label(self.label)
        _require_text(self.text, f"{self.label} text")
        if self.role not in ("primary", "supporting"):
            raise ArtifactValidationError(
                f"{self.label} role must be 'primary' or 'supporting'"
            )
        for ref in self.supports:
            require_question_label(ref)
        if self.label in self.supports:
            raise ArtifactValidationError(f"{self.label} cannot support itself")
        if len(set(self.supports)) != len(self.supports):
            raise ArtifactValidationError(
                f"{self.label} supports duplicate question labels"
            )
        if self.role == "primary" and self.supports:
            raise ArtifactValidationError(
                "the primary question supports the user's decision directly and "
                "must not declare supports"
            )
        if self.role == "supporting" and not self.supports:
            raise ArtifactValidationError(
                f"{self.label} must declare which question it supports; a topic "
                "that cannot explain its role does not belong in the Contract"
            )


@dataclass(frozen=True, slots=True)
class QuestionModel:
    """The Contract's question structure: one primary question plus support."""

    questions: tuple[ResearchQuestion, ...]

    def __post_init__(self) -> None:
        if not self.questions:
            raise ArtifactValidationError("a Contract requires a question model")

        labels = [question.label for question in self.questions]
        if len(set(labels)) != len(labels):
            raise ArtifactValidationError("question labels must be unique")

        primaries = [q.label for q in self.questions if q.role == "primary"]
        if len(primaries) != 1:
            raise ArtifactValidationError(
                f"a Contract needs exactly one primary question, found {len(primaries)}"
            )
        if primaries[0] != "Q1":
            raise ArtifactValidationError("the primary question must be labelled Q1")

        expected = [f"Q{index}" for index in range(1, len(self.questions) + 1)]
        if sorted(labels, key=_label_order) != expected:
            raise ArtifactValidationError(
                f"question labels must be contiguous from Q1, got {sorted(labels)}"
            )

        known = set(labels)
        for question in self.questions:
            unknown = sorted(set(question.supports) - known)
            if unknown:
                raise ArtifactValidationError(
                    f"{question.label} supports unknown questions {unknown}"
                )
        self._require_support_reaches_primary()

    def _require_support_reaches_primary(self) -> None:
        """Every supporting question must transitively support the primary one.

        This is the mechanical half of "no orphan topics".  Whether a question
        genuinely informs the user's decision stays a semantic judgment for the
        Architect and Protocol Assurer; the runtime only rejects a support graph
        that cannot reach Q1 at all.
        """

        by_label = {question.label: question for question in self.questions}
        for question in self.questions:
            if question.role == "primary":
                continue
            seen: set[str] = set()
            pending = list(question.supports)
            while pending:
                current = pending.pop()
                if current in seen:
                    continue
                seen.add(current)
                pending.extend(by_label[current].supports)
            if "Q1" not in seen:
                raise ArtifactValidationError(
                    f"{question.label} does not transitively support Q1"
                )

    @property
    def primary(self) -> ResearchQuestion:
        """The single question the report must answer for the user."""

        return next(q for q in self.questions if q.role == "primary")

    @property
    def labels(self) -> tuple[str, ...]:
        """All question labels in canonical Q1..Qn order."""

        return tuple(
            question.label
            for question in sorted(self.questions, key=lambda q: _label_order(q.label))
        )

    def get(self, label: str) -> ResearchQuestion:
        """Look up one question, rejecting labels this Contract does not define."""

        require_question_label(label)
        for question in self.questions:
            if question.label == label:
                return question
        raise ArtifactValidationError(
            f"{label} is not a question in the current Contract; available: "
            f"{', '.join(self.labels)}"
        )

    def resolve(self, labels: Iterable[str]) -> tuple[ResearchQuestion, ...]:
        """Resolve a selection of labels, rejecting unknown or duplicate ones.

        Assignments call this.  It is the single gate that stops a model from
        inventing a target: it may only select labels this Contract exposes.
        """

        selected = tuple(labels)
        if not selected:
            raise ArtifactValidationError(
                "select at least one Contract question label"
            )
        if len(set(selected)) != len(selected):
            raise ArtifactValidationError(
                f"duplicate question labels selected: {sorted(selected)}"
            )
        return tuple(
            self.get(label)
            for label in sorted(selected, key=lambda value: _label_order(
                require_question_label(value)
            ))
        )


@dataclass(frozen=True, slots=True)
class ResearchContract:
    """The approved research agreement: prose the user read, plus its questions.

    ``body_markdown`` is the authoritative text shown on the approval card.  The
    question model is parsed from it so the structure the runtime enforces and
    the structure the user approved cannot drift apart.
    """

    body_markdown: str
    question_model: QuestionModel
    guide_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_text(self.body_markdown, "contract body")
        if not isinstance(self.question_model, QuestionModel):
            raise ArtifactValidationError("question_model must be a QuestionModel")
        for ref in self.guide_refs:
            _require_text(ref, "guide ref")
        if len(set(self.guide_refs)) != len(self.guide_refs):
            raise ArtifactValidationError("guide_refs must not contain duplicates")

    @property
    def labels(self) -> tuple[str, ...]:
        """Question labels a downstream role may select."""

        return self.question_model.labels

    def resolve(self, labels: Iterable[str]) -> tuple[ResearchQuestion, ...]:
        """Resolve selected question labels against this exact Contract."""

        return self.question_model.resolve(labels)


def parse_question_lines(body_markdown: str) -> tuple[tuple[str, str], ...]:
    """Extract ``(label, text)`` pairs from Contract prose, in document order."""

    found: list[tuple[str, str]] = []
    for line in body_markdown.splitlines():
        match = _QUESTION_LINE_RE.match(line)
        if match is not None:
            found.append((match.group(1), match.group(2).strip()))
    return tuple(found)


def build_question_model(
    body_markdown: str, supports: Mapping[str, Sequence[str]] | None = None
) -> QuestionModel:
    """Build the question model from Contract prose and a support mapping.

    ``Q1`` is the primary question by construction.  Every other question needs
    an entry in ``supports``; the default is to support ``Q1`` directly, so a
    flat set of supporting questions is expressible without ceremony while a
    layered structure stays available.
    """

    lines = parse_question_lines(body_markdown)
    if not lines:
        raise ArtifactValidationError(
            "the Contract body must state numbered questions as 'Q1. ...' lines"
        )
    seen: dict[str, str] = {}
    for label, text in lines:
        if label in seen:
            raise ArtifactValidationError(f"{label} is stated more than once")
        seen[label] = text

    declared = dict(supports or {})
    unknown = sorted(set(declared) - set(seen))
    if unknown:
        raise ArtifactValidationError(
            f"supports mapping names questions absent from the body: {unknown}"
        )

    questions: list[ResearchQuestion] = []
    for label, text in seen.items():
        if label == "Q1":
            questions.append(ResearchQuestion(label=label, text=text, role="primary"))
            continue
        targets = tuple(declared.get(label, ("Q1",)))
        questions.append(
            ResearchQuestion(
                label=label, text=text, role="supporting", supports=targets
            )
        )
    return QuestionModel(questions=tuple(questions))


def build_contract(
    body_markdown: str,
    *,
    supports: Mapping[str, Sequence[str]] | None = None,
    guide_refs: Iterable[str] = (),
) -> ResearchContract:
    """Parse Contract prose into the approved agreement the runtime enforces."""

    return ResearchContract(
        body_markdown=body_markdown,
        question_model=build_question_model(body_markdown, supports),
        guide_refs=tuple(guide_refs),
    )


def section_title(section: str) -> str:
    """Human-readable title for one Contract section."""

    if section not in _SECTION_TITLES:
        raise ArtifactValidationError(f"unknown Contract section {section!r}")
    return _SECTION_TITLES[section]


__all__ = [
    "CONTRACT_SECTIONS",
    "QuestionModel",
    "QuestionRole",
    "ResearchContract",
    "ResearchQuestion",
    "build_contract",
    "build_question_model",
    "parse_question_lines",
    "require_question_label",
    "section_title",
]
