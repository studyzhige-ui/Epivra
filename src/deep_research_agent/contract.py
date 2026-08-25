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

This module is pure domain logic: no provider, HTTP, or database imports.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal

from .sources import ArtifactValidationError

#: The five user-facing blocks a Contract must cover.  They are fixed because
#: these are the facts a user needs in order to decide whether the Agent is about
#: to research the right thing: goal, questions, scope, approach, and delivery.
CONTRACT_SECTIONS: tuple[str, ...] = (
    "research_goal",
    "focus_questions",
    "scope_and_exclusions",
    "research_approach",
    "deliverable",
)

_SECTION_TITLES: Mapping[str, str] = {
    "research_goal": "研究目标",
    "focus_questions": "重点问题",
    "scope_and_exclusions": "范围与排除",
    "research_approach": "研究方式",
    "deliverable": "交付内容",
}

QuestionRole = Literal["primary", "supporting"]

_LABEL_RE = re.compile(r"^Q([1-9][0-9]?)$")
#: Recognises a heading like "### Q2. Does uptake differ by subgroup?" and the
#: terser "Q2: ..." form, so Contract prose stays readable to the user.
_QUESTION_LINE_RE = re.compile(
    r"^\s{0,3}(?:#{1,6}\s*)?(?:[-*]\s*)?(Q[1-9][0-9]?)\s*[.:、．]\s*(.+?)\s*$"
)
_SECTION_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$")
_TITLE_HEADING_RE = re.compile(r"^\s{0,3}#\s+(.+?)\s*#*\s*$")


def _canonical_json(payload: object) -> str:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
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


#: A question long enough to stand on its own without a question mark.  Roles
#: receive only ``label + text``, never the Contract section a heading sat in,
#: so the text has to carry the whole question by itself.
_QUESTION_MIN_CHARS = 12


def question_text_problem(value: str, label: str) -> str:
    """Describe a section label standing where a question belongs, or "".

    A live Contract stated ``### Q1. 核心问题`` as a *heading* and put the real
    question in the prose beneath it.  The parser took the heading, so Q1 became
    the literal string "核心问题" -- and because roles are handed
    ``contract.resolve(labels)`` and nothing else, every Investigator downstream
    would have received "核心问题" as its assignment while the run looked
    perfectly healthy.  A silent misparse of the one thing the whole report must
    answer has to fail loudly instead.

    The bar is deliberately mechanical, not a judgment about quality: either the
    text is punctuated as a question, or it is long enough to be a clause rather
    than a topic.  Whether the question is a *good* one is the user's call at the
    approval card.

    **This is a semantic judgement, so it binds when a Contract is created and not
    when one is read back** (§2.3.1).  It was added after real runs, and a
    committed Contract cannot be improved to satisfy it -- rejecting one at decode
    time strands a study that was already planned, approved and part-way done,
    which is exactly what happened to one task in the calibration corpus.
    """

    text = value.strip()
    if "？" in text or "?" in text:
        return ""
    if len(text) >= _QUESTION_MIN_CHARS:
        return ""
    return (
        f"{label} reads as a section label rather than a question: {text!r}. "
        "State the question itself on the Q-line -- roles only ever receive the "
        "label and this text, never the prose around it."
    )


@dataclass(frozen=True, slots=True)
class ResearchQuestion:
    """One labelled question and the role it plays in answering the user."""

    label: str
    text: str
    role: QuestionRole
    supports: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        require_question_label(self.label)
        # Non-empty is mechanical and stays an invariant: a label with no text is
        # not a question anyone could act on.  Whether the text *reads* as a
        # question is semantic and lives in the construction path, so a Contract
        # committed before that check existed can still be read back (§2.3.1).
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
        Architect and the user; the runtime only rejects a support graph
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


#: Source families a Commission may authorise.  This is a *permission* the trust
#: plane enforces, not advice: an Investigator cannot reach a family the user did
#: not grant, regardless of what any prompt suggests.
SourceAccess = Literal["public_web", "user_files", "local_only"]

SOURCE_ACCESS: tuple[SourceAccess, ...] = ("public_web", "user_files", "local_only")


@dataclass(frozen=True, slots=True)
class CommissionBody:
    """The user's original request, preserved exactly as given.

    The Commission is the one artifact no model may rewrite.  Every Contract is
    derived from it and must remain answerable to it, which is what lets a
    reviewer ask "does this report answer what was actually asked" rather than
    "does it answer what the Architect decided it meant".
    """

    request: str
    source_access: tuple[SourceAccess, ...]
    language: str = "zh"
    constraints: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        # Validated for emptiness but deliberately *not* normalised: the request
        # is stored byte-for-byte as the user submitted it, so the artifact hash
        # covers exactly what they wrote. Stripping would be a small rewrite, and
        # this is the one artifact no rewrite may touch.
        _require_text(self.request, "commission request")
        if not self.source_access:
            raise ArtifactValidationError(
                "a commission must authorise at least one source family"
            )
        unknown = sorted(set(self.source_access) - set(SOURCE_ACCESS))
        if unknown:
            raise ArtifactValidationError(
                f"unknown source access {unknown}; allowed: {list(SOURCE_ACCESS)}"
            )
        if len(set(self.source_access)) != len(self.source_access):
            raise ArtifactValidationError("source_access must not repeat a family")
        if "local_only" in self.source_access and len(self.source_access) > 1:
            # "local only" and "the public web" are a contradiction, not a union.
            # Accepting both would leave the runtime guessing which the user
            # meant, on the one artifact no model may rewrite.
            raise ArtifactValidationError(
                "local_only forbids the network, so it cannot be combined with "
                f"another source family; got {list(self.source_access)}"
            )
        _require_text(self.language, "commission language")
        for item in self.constraints:
            _require_text(item, "commission constraint")

    @property
    def allows_external_search(self) -> bool:
        """Whether any external search is permitted at all."""

        return "public_web" in self.source_access

    @property
    def allows_local_corpus(self) -> bool:
        """Whether the user's own files may be read."""

        return "user_files" in self.source_access or "local_only" in self.source_access

    def encode(self) -> str:
        """Canonical body text; the request is stored verbatim."""

        return _canonical_json(
            {
                "request": self.request,
                "source_access": sorted(self.source_access),
                "language": self.language,
                "constraints": list(self.constraints),
            }
        )

    @classmethod
    def decode(cls, body: str) -> CommissionBody:
        value = json.loads(body)
        return cls(
            request=str(value["request"]),
            source_access=tuple(value["source_access"]),
            language=str(value.get("language", "zh")),
            constraints=tuple(str(item) for item in value.get("constraints", ())),
        )


@dataclass(frozen=True, slots=True)
class ClarificationBody:
    """One question the Architect must have answered before it can plan.

    Asking is a legitimate outcome of scoping, not a failure: a commission whose
    two readings would lead to two different studies cannot be planned honestly,
    and guessing which was meant is worse than asking.

    ``why_it_changes_the_plan`` is required because it is what makes the question
    answerable.  "Tell me more" wastes the user's time; "are you choosing a
    technology or explaining one, because the evidence differs entirely" can be
    answered in a sentence.
    """

    question: str
    why_it_changes_the_plan: str

    def __post_init__(self) -> None:
        _require_text(self.question, "clarification question")
        _require_text(
            self.why_it_changes_the_plan, "clarification rationale"
        )

    def encode(self) -> str:
        return _canonical_json(
            {
                "question": self.question,
                "why_it_changes_the_plan": self.why_it_changes_the_plan,
            }
        )

    @classmethod
    def decode(cls, body: str) -> ClarificationBody:
        value = json.loads(body)
        return cls(
            question=str(value["question"]),
            why_it_changes_the_plan=str(value["why_it_changes_the_plan"]),
        )


@dataclass(frozen=True, slots=True)
class ClarificationReplyBody:
    """The user's answer to one exact question.

    Deliberately not merged into the Commission.  The Commission is the one
    artifact no rewrite may touch, and appending answers to the request string
    would both destroy that guarantee and hand the Architect an ever-longer brief
    instead of "here is what you asked, and here is what they said".
    """

    answer: str

    def __post_init__(self) -> None:
        _require_text(self.answer, "clarification answer")

    def encode(self) -> str:
        return _canonical_json({"answer": self.answer})

    @classmethod
    def decode(cls, body: str) -> ClarificationReplyBody:
        return cls(answer=str(json.loads(body)["answer"]))


@dataclass(frozen=True, slots=True)
class ResearchContract:
    """The approved research agreement: prose the user read, plus its questions.

    ``body_markdown`` is the authoritative text shown on the approval card.  The
    question model is parsed from it so the structure the runtime enforces and
    the structure the user approved cannot drift apart.
    """

    body_markdown: str
    question_model: QuestionModel
    supports: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    #: The language the deliverable is written in, carried structurally rather
    #: than only as prose in the delivery block.  Roles used to have "write in
    #: Chinese" fixed in their prompts while the context announced a delivery
    #: language beside it -- a direct contradiction, and the prompt won.
    language: str = "zh"
    #: Semantic checks this Contract would not pass if it were being created now.
    #:
    #: Empty for anything this version produced.  Non-empty means the Contract was
    #: committed before a check existed and was admitted anyway, because a
    #: committed artifact cannot be improved and refusing to read it strands a
    #: study that was already approved (§2.3.1).  Recorded rather than hidden: a
    #: reader can tell the difference, which is the whole point of admitting it.
    #:
    #: Deliberately absent from :meth:`encode` -- it is an observation made while
    #: reading, not part of what the user approved, and putting it in the body
    #: would change the artifact's identity.
    legacy_degraded: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_text(self.body_markdown, "contract body")
        _require_text(self.language, "contract language")
        if not isinstance(self.question_model, QuestionModel):
            raise ArtifactValidationError("question_model must be a QuestionModel")

    @property
    def labels(self) -> tuple[str, ...]:
        """Question labels a downstream role may select."""

        return self.question_model.labels

    @property
    def title(self) -> str:
        """The visible research topic, derived from the first non-empty line."""

        for line in self.body_markdown.splitlines():
            if not line.strip():
                continue
            match = _TITLE_HEADING_RE.match(line)
            if match is not None:
                return match.group(1).strip()
            return ""
        return ""

    def resolve(self, labels: Iterable[str]) -> tuple[ResearchQuestion, ...]:
        """Resolve selected question labels against this exact Contract."""

        return self.question_model.resolve(labels)

    def missing_sections(self) -> tuple[str, ...]:
        """Which required blocks are absent or contain no content.

        The five blocks are the facts a user needs to confirm the direction, so
        their absence is a mechanical defect the Architect can correct -- unlike
        whether the proposed direction is right, which is the user's judgment.
        """

        by_title: dict[str, bool] = {}
        current = ""
        required_titles = set(_SECTION_TITLES.values())
        for line in self.body_markdown.splitlines():
            heading = _SECTION_HEADING_RE.match(line)
            if heading is not None and heading.group(1).strip() in required_titles:
                current = heading.group(1).strip()
                by_title.setdefault(current, False)
                continue
            if current and line.strip():
                by_title[current] = True

        return tuple(
            section
            for section in CONTRACT_SECTIONS
            if not by_title.get(_SECTION_TITLES[section], False)
        )

    def encode(self) -> str:
        """Canonical body text.

        The support graph is stored because it is the one part of the question
        model that prose cannot express.
        """

        return _canonical_json(
            {
                "markdown": self.body_markdown,
                "supports": {
                    label: list(targets)
                    for label, targets in sorted(self.supports.items())
                },
                "language": self.language,
            }
        )

    @classmethod
    def decode(cls, body: str) -> ResearchContract:
        """Read a committed Contract back, admitting what it cannot now fix.

        Lenient about semantic checks and strict about everything mechanical, per
        §2.3.1.  The support graph, label contiguity, and the single primary
        question are all still enforced -- those are structure the runtime depends
        on to resolve an assignment at all.  Only judgements the Contract could
        never satisfy retroactively are downgraded, and they are recorded.
        """

        value = json.loads(body)
        # Older Contract bodies may contain a ``packs`` member.  It never affected
        # runtime behaviour, so reading it requires no replacement state: the
        # artifact body and hash remain intact while this projection ignores it.
        return build_contract(
            str(value["markdown"]),
            supports={
                str(label): tuple(str(item) for item in targets)
                for label, targets in dict(value.get("supports", {})).items()
            },
            # Contracts written before the language was carried structurally
            # were all Chinese deliverables, so that is the honest default.
            language=str(value.get("language") or "zh"),
            strict=False,
        )


def parse_question_lines(body_markdown: str) -> tuple[tuple[str, str], ...]:
    """Extract ``(label, text)`` pairs from Contract prose, in document order."""

    found: list[tuple[str, str]] = []
    for line in body_markdown.splitlines():
        match = _QUESTION_LINE_RE.match(line)
        if match is not None:
            found.append((match.group(1), match.group(2).strip()))
    return tuple(found)


def build_question_model(
    body_markdown: str,
    supports: Mapping[str, Sequence[str]] | None = None,
    *,
    strict: bool = True,
) -> QuestionModel:
    """Build the question model from Contract prose and a support mapping.

    ``Q1`` is the primary question by construction.  Every other question needs
    an entry in ``supports``; the default is to support ``Q1`` directly, so a
    flat set of supporting questions is expressible without ceremony while a
    layered structure stays available.

    ``strict`` governs only the semantic check on question text.  Everything else
    -- contiguous labels, exactly one primary, a support graph that reaches Q1 --
    is structure the runtime needs to resolve an assignment at all, so it is
    enforced either way (§2.3.1).
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
        if strict:
            problem = question_text_problem(text, f"{label} text")
            if problem:
                raise ArtifactValidationError(problem)
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


def degraded_checks(body_markdown: str) -> tuple[str, ...]:
    """Semantic checks this Contract text would fail if it were created now.

    Read by :meth:`ResearchContract.decode` so an admitted legacy Contract carries
    a record of what it was admitted despite.  Uses the same predicate the strict
    path raises on, so the two cannot drift into disagreeing about what counts.
    """

    return tuple(
        problem
        for label, text in parse_question_lines(body_markdown)
        if (problem := question_text_problem(text, f"{label} text"))
    )


def build_contract(
    body_markdown: str,
    *,
    supports: Mapping[str, Sequence[str]] | None = None,
    language: str = "zh",
    strict: bool = True,
) -> ResearchContract:
    """Parse Contract prose into the approved agreement the runtime enforces.

    ``strict`` is the create/decode boundary of §2.3.1: creating a Contract
    enforces every check, reading one back enforces only what it could still
    satisfy.  It defaults to strict so a new caller gets the safe behaviour without
    having to ask for it.
    """

    return ResearchContract(
        body_markdown=body_markdown,
        question_model=build_question_model(body_markdown, supports, strict=strict),
        supports={
            label: tuple(targets) for label, targets in dict(supports or {}).items()
        },
        language=language,
        legacy_degraded=() if strict else degraded_checks(body_markdown),
    )


def section_title(section: str) -> str:
    """Human-readable title for one Contract section."""

    if section not in _SECTION_TITLES:
        raise ArtifactValidationError(f"unknown Contract section {section!r}")
    return _SECTION_TITLES[section]


__all__ = [
    "ClarificationBody",
    "ClarificationReplyBody",
    "CONTRACT_SECTIONS",
    "SOURCE_ACCESS",
    "CommissionBody",
    "SourceAccess",
    "QuestionModel",
    "QuestionRole",
    "ResearchContract",
    "ResearchQuestion",
    "build_contract",
    "build_question_model",
    "degraded_checks",
    "parse_question_lines",
    "question_text_problem",
    "require_question_label",
    "section_title",
]
