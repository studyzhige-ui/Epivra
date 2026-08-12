"""Minimal research artifacts and LangGraph state reducers.

The types in this module describe durable hand-offs between narrow agent roles.
They intentionally avoid claim ledgers, coverage scores, research budgets, and
other structures that would move semantic research decisions into the backend.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Annotated, Literal, TypedDict, TypeVar
from urllib.parse import parse_qsl, urlsplit, urlunsplit


JournalKind = Literal["finding", "conflict", "decision", "next_step"]
AmendmentLevel = Literal["L0", "L1", "L2"]
PublicationGateStatus = Literal[
    "unready",
    "material_blocked",
    "full_validation_required",
    "full_validation_passed",
    "closure_validation_required",
    "closed",
]
AssuranceActor = Literal["independent_validator", "editor"]


class ArtifactValidationError(ValueError):
    """A formal artifact cannot be trusted as constructed."""


class ArtifactConflictError(ValueError):
    """Parallel branches produced different artifacts under one stable ID."""


def _require_text(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ArtifactValidationError(f"{label} must be a non-empty string")
    return value.strip()


def _canonical_url(url: str) -> str:
    """Return a conservative URL identity without a document fragment."""

    value = _require_text(url, "url")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ArtifactValidationError("url must not contain control characters")
    parts = urlsplit(value)
    if parts.scheme.casefold() not in {"http", "https"} or not parts.hostname:
        raise ArtifactValidationError("url must be a public HTTP or HTTPS URL")
    if parts.username or parts.password:
        raise ArtifactValidationError("url must not contain credentials")
    hostname = parts.hostname.casefold().rstrip(".")
    if hostname == "localhost" or hostname.endswith(".localhost"):
        raise ArtifactValidationError("url must not identify a local host")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise ArtifactValidationError("url must not identify a private IP address")
    sensitive_query_names = {
        "access_token",
        "api_key",
        "apikey",
        "auth",
        "authorization",
        "credential",
        "key",
        "password",
        "sig",
        "signature",
        "token",
        "x-amz-credential",
        "x-amz-signature",
        "x-goog-credential",
        "x-goog-signature",
    }
    if any(
        key.casefold() in sensitive_query_names for key, _value in parse_qsl(parts.query)
    ):
        raise ArtifactValidationError("url query appears to contain a credential")
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), parts.path, parts.query, "")
    )


def content_digest(content: str) -> str:
    """Hash exact saved content; whitespace is evidence and is not normalized."""

    if not isinstance(content, str) or not content:
        raise ArtifactValidationError("source content must not be empty")
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _require_content_hash(value: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ArtifactValidationError(
            "body content_hash must be a lowercase SHA-256 digest"
        )
    return value


@dataclass(frozen=True, slots=True)
class BodyRef:
    """A durable reference to one exact immutable UTF-8 source body."""

    content_hash: str
    char_count: int

    def __post_init__(self) -> None:
        _require_content_hash(self.content_hash)
        if (
            isinstance(self.char_count, bool)
            or not isinstance(self.char_count, int)
            or self.char_count < 1
        ):
            raise ArtifactValidationError("body char_count must be a positive integer")

    @classmethod
    def from_content(cls, content: str) -> BodyRef:
        """Build the canonical reference for exact source text."""

        return cls(content_hash=content_digest(content), char_count=len(content))


def make_source_id(url: str, content_hash: str) -> str:
    """Create a stable ID for one URL/content version."""

    identity = f"{_canonical_url(url)}\n{_require_content_hash(content_hash)}"
    return "src_" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]


@dataclass(frozen=True, slots=True)
class TextLocator:
    """An end-exclusive character range in the exact saved source body."""

    start: int
    end: int

    def __post_init__(self) -> None:
        if isinstance(self.start, bool) or not isinstance(self.start, int):
            raise ArtifactValidationError("locator start must be an integer")
        if isinstance(self.end, bool) or not isinstance(self.end, int):
            raise ArtifactValidationError("locator end must be an integer")
        if self.start < 0 or self.end <= self.start:
            raise ArtifactValidationError(
                "locator must be a non-empty, end-exclusive character range"
            )

    def __str__(self) -> str:
        return f"chars:{self.start}-{self.end}"


@dataclass(frozen=True, slots=True)
class SourceAnchor:
    """A source-faithful quote and its exact location."""

    source_id: str
    exact_quote: str
    locator: TextLocator

    def __post_init__(self) -> None:
        _require_text(self.source_id, "anchor source_id")
        if not isinstance(self.exact_quote, str) or not self.exact_quote:
            raise ArtifactValidationError("anchor exact_quote must not be empty")
        if not isinstance(self.locator, TextLocator):
            raise ArtifactValidationError("anchor locator must be a TextLocator")


@dataclass(frozen=True, slots=True)
class SourceDocument:
    """One exact source snapshot in the Source Corpus."""

    source_id: str
    title: str
    url: str
    body_ref: BodyRef
    fetched_at: str = ""
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_text(self.title, "source title")
        canonical_url = _canonical_url(self.url)
        if not isinstance(self.body_ref, BodyRef):
            raise ArtifactValidationError("source body_ref must be a BodyRef")
        expected_id = make_source_id(canonical_url, self.body_ref.content_hash)
        if self.source_id != expected_id:
            raise ArtifactValidationError(
                "source_id does not match URL and body content_hash"
            )
        if not isinstance(self.fetched_at, str):
            raise ArtifactValidationError("fetched_at must be a string")
        if not isinstance(self.metadata, Mapping) or any(
            not isinstance(key, str) or not isinstance(value, str)
            for key, value in self.metadata.items()
        ):
            raise ArtifactValidationError("source metadata must map strings to strings")

    @property
    def content_hash(self) -> str:
        """Expose the referenced digest without duplicating it in durable state."""

        return self.body_ref.content_hash

    @classmethod
    def create(
        cls,
        *,
        title: str,
        url: str,
        body_ref: BodyRef,
        fetched_at: str = "",
        metadata: Mapping[str, str] | None = None,
    ) -> SourceDocument:
        canonical_url = _canonical_url(url)
        if not isinstance(body_ref, BodyRef):
            raise ArtifactValidationError("source body_ref must be a BodyRef")
        return cls(
            source_id=make_source_id(canonical_url, body_ref.content_hash),
            title=_require_text(title, "source title"),
            url=canonical_url,
            body_ref=body_ref,
            fetched_at=fetched_at,
            metadata=dict(metadata or {}),
        )


@dataclass(frozen=True, slots=True)
class HydratedSource:
    """Runtime-only source view carrying verified exact text for semantic work."""

    source_id: str
    title: str
    url: str
    content: str
    content_hash: str
    fetched_at: str = ""
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_text(self.title, "source title")
        canonical_url = _canonical_url(self.url)
        expected_hash = content_digest(self.content)
        if self.content_hash != expected_hash:
            raise ArtifactValidationError(
                "hydrated source content_hash does not match content"
            )
        if self.source_id != make_source_id(canonical_url, expected_hash):
            raise ArtifactValidationError(
                "hydrated source_id does not match URL and content"
            )
        if not isinstance(self.fetched_at, str):
            raise ArtifactValidationError("fetched_at must be a string")
        if not isinstance(self.metadata, Mapping) or any(
            not isinstance(key, str) or not isinstance(value, str)
            for key, value in self.metadata.items()
        ):
            raise ArtifactValidationError("source metadata must map strings to strings")


def locate_quote(
    source: HydratedSource, exact_quote: str, *, occurrence: int = 1
) -> SourceAnchor:
    """Locate a one-based occurrence of an exact quote in a saved source."""

    if isinstance(occurrence, bool) or not isinstance(occurrence, int) or occurrence < 1:
        raise ArtifactValidationError("occurrence must be a positive integer")
    if not isinstance(exact_quote, str) or not exact_quote:
        raise ArtifactValidationError("exact_quote must not be empty")

    start = -1
    search_from = 0
    for _ in range(occurrence):
        start = source.content.find(exact_quote, search_from)
        if start < 0:
            raise ArtifactValidationError(
                f"quote occurrence {occurrence} is not present in {source.source_id}"
            )
        search_from = start + 1
    return SourceAnchor(
        source_id=source.source_id,
        exact_quote=exact_quote,
        locator=TextLocator(start=start, end=start + len(exact_quote)),
    )


def validate_anchor(anchor: SourceAnchor, source: HydratedSource) -> None:
    """Require an anchor to select its exact quote from its declared source."""

    if anchor.source_id != source.source_id:
        raise ArtifactValidationError(
            f"anchor names {anchor.source_id}, not source {source.source_id}"
        )
    if anchor.locator.end > len(source.content):
        raise ArtifactValidationError("anchor locator exceeds the saved source body")
    located = source.content[anchor.locator.start : anchor.locator.end]
    if located != anchor.exact_quote:
        raise ArtifactValidationError(
            "anchor quote does not match the saved text at its locator"
        )


def validate_anchors(
    anchors: Sequence[SourceAnchor], source_corpus: Mapping[str, HydratedSource]
) -> None:
    """Validate every anchor and close its source reference."""

    for anchor in anchors:
        source = source_corpus.get(anchor.source_id)
        if source is None:
            raise ArtifactValidationError(
                f"anchor references unknown source {anchor.source_id}"
            )
        validate_anchor(anchor, source)


def _anchor_identity(anchor: SourceAnchor) -> tuple[str, int, int, str]:
    return (
        anchor.source_id,
        anchor.locator.start,
        anchor.locator.end,
        anchor.exact_quote,
    )


def make_material_id(
    content: str, boundaries: str, anchors: Sequence[SourceAnchor]
) -> str:
    """Create a stable ID for one normalized Curated Material entry."""

    material_content = _require_text(content, "material content")
    material_boundaries = _require_text(boundaries, "material boundaries")
    if not anchors:
        raise ArtifactValidationError(
            "curated material requires at least one SourceAnchor"
        )
    payload = {
        "content": material_content,
        "boundaries": material_boundaries,
        "anchors": [
            {
                "source_id": source_id,
                "start": start,
                "end": end,
                "quote": quote,
            }
            for source_id, start, end, quote in sorted(
                _anchor_identity(anchor) for anchor in anchors
            )
        ],
    }
    canonical = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return "mat_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]


@dataclass(frozen=True, slots=True)
class ResearchContract:
    """The single natural-language research agreement approved by the user."""

    content: str
    guide_refs: tuple[str, ...] = ()
    approved: bool = False

    def __post_init__(self) -> None:
        _require_text(self.content, "research contract")
        if any(not isinstance(item, str) or not item.strip() for item in self.guide_refs):
            raise ArtifactValidationError("guide_refs must contain non-empty strings")
        if not isinstance(self.approved, bool):
            raise ArtifactValidationError("approved must be a boolean")


@dataclass(frozen=True, slots=True)
class JournalEntry:
    """Narrow process memory; it is never a Writer input."""

    kind: JournalKind
    content: str
    anchors: tuple[SourceAnchor, ...] = ()
    branch_id: str = ""

    def __post_init__(self) -> None:
        if self.kind not in {"finding", "conflict", "decision", "next_step"}:
            raise ArtifactValidationError(f"unsupported journal kind {self.kind!r}")
        _require_text(self.content, "journal content")
        if not isinstance(self.branch_id, str):
            raise ArtifactValidationError("branch_id must be a string")


@dataclass(frozen=True, slots=True)
class CuratedMaterial:
    """Source-faithful material admitted for synthesis and writing."""

    material_id: str
    content: str
    boundaries: str
    anchors: tuple[SourceAnchor, ...]

    def __post_init__(self) -> None:
        expected_id = make_material_id(self.content, self.boundaries, self.anchors)
        if self.material_id != expected_id:
            raise ArtifactValidationError(
                "material_id does not match content, boundaries, and anchors"
            )

    @classmethod
    def create(
        cls,
        *,
        content: str,
        boundaries: str,
        anchors: Sequence[SourceAnchor],
    ) -> CuratedMaterial:
        ordered = tuple(sorted(anchors, key=_anchor_identity))
        return cls(
            material_id=make_material_id(content, boundaries, ordered),
            content=_require_text(content, "material content"),
            boundaries=_require_text(boundaries, "material boundaries"),
            anchors=ordered,
        )


@dataclass(frozen=True, slots=True)
class ResearchSynthesis:
    """Natural-language cross-source analysis, not a report outline."""

    content: str

    def __post_init__(self) -> None:
        _require_text(self.content, "research synthesis")


@dataclass(frozen=True, slots=True)
class ValidationFinding:
    """A precise, read-only independent assurance finding."""

    issue: str
    location: str
    related_material_ids: tuple[str, ...] = ()
    related_source_ids: tuple[str, ...] = ()
    severity_reason: str = ""

    def __post_init__(self) -> None:
        _require_text(self.issue, "validation issue")
        _require_text(self.location, "validation location")
        if not isinstance(self.severity_reason, str):
            raise ArtifactValidationError("severity_reason must be a string")


@dataclass(frozen=True, slots=True)
class AssuranceEvent:
    """One append-only validation or response-to-validation audit event."""

    event_id: str
    actor: AssuranceActor
    artifact_digest: str
    scope: str
    outcome: str
    details: str
    recorded_at: str

    def __post_init__(self) -> None:
        if not self.event_id.startswith("assr_") or len(self.event_id) < 10:
            raise ArtifactValidationError("assurance event_id is invalid")
        if self.actor not in {"independent_validator", "editor"}:
            raise ArtifactValidationError("assurance actor is invalid")
        if len(self.artifact_digest) != 64 or any(
            character not in "0123456789abcdef"
            for character in self.artifact_digest
        ):
            raise ArtifactValidationError("assurance artifact_digest is invalid")
        _require_text(self.scope, "assurance scope")
        _require_text(self.outcome, "assurance outcome")
        if not isinstance(self.details, str):
            raise ArtifactValidationError("assurance details must be a string")
        _require_text(self.recorded_at, "assurance recorded_at")


@dataclass(frozen=True, slots=True)
class Amendment:
    """A Supervisor-authorized, narrowly scoped cross-stage revision."""

    level: AmendmentLevel
    reason: str
    scope: str
    regenerate: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.level not in {"L0", "L1", "L2"}:
            raise ArtifactValidationError(f"unsupported amendment level {self.level!r}")
        _require_text(self.reason, "amendment reason")
        _require_text(self.scope, "amendment scope")
        if not self.regenerate or any(
            not isinstance(item, str) or not item.strip() for item in self.regenerate
        ):
            raise ArtifactValidationError(
                "amendment regenerate must contain affected artifact names"
            )


@dataclass(frozen=True, slots=True)
class ResearchTask:
    """One focused unit that a Researcher Worker can execute in isolation."""

    branch_id: str
    instruction: str
    relevant_source_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_text(self.branch_id, "research task branch_id")
        _require_text(self.instruction, "research task instruction")
        if any(
            not isinstance(source_id, str) or not source_id.strip()
            for source_id in self.relevant_source_ids
        ):
            raise ArtifactValidationError(
                "research task relevant_source_ids must contain non-empty strings"
            )
        if len(set(self.relevant_source_ids)) != len(self.relevant_source_ids):
            raise ArtifactValidationError(
                "research task relevant_source_ids must not contain duplicates"
            )


@dataclass(frozen=True, slots=True)
class BranchHandoff:
    """A filtered branch summary for the Supervisor and Curator."""

    branch_id: str
    summary: str
    unresolved: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_text(self.branch_id, "branch handoff branch_id")
        _require_text(self.summary, "branch handoff summary")


ArtifactT = TypeVar("ArtifactT")


def _append_distinct(
    current: Sequence[ArtifactT] | None, updates: Sequence[ArtifactT] | None
) -> list[ArtifactT]:
    merged = list(current or ())
    for item in updates or ():
        if item not in merged:
            merged.append(item)
    return merged


def merge_source_corpus(
    current: Mapping[str, SourceDocument] | None,
    updates: Mapping[str, SourceDocument] | None,
) -> dict[str, SourceDocument]:
    merged = dict(current or {})
    for source_id, source in (updates or {}).items():
        if source.source_id != source_id:
            raise ArtifactConflictError(
                f"source key {source_id!r} does not match declared ID {source.source_id!r}"
            )
        existing = merged.get(source_id)
        if existing is None:
            merged[source_id] = source
            continue
        if (
            existing.url != source.url
            or existing.body_ref != source.body_ref
        ):
            raise ArtifactConflictError(
                f"parallel branches produced conflicting source {source_id}"
            )
        titles = {existing.title.strip(), source.title.strip()}
        title = max(titles, key=lambda value: (len(value), value.casefold(), value))
        fetched_values = [
            value for value in (existing.fetched_at, source.fetched_at) if value
        ]
        metadata: dict[str, str] = {}
        for key in sorted(set(existing.metadata) | set(source.metadata)):
            values: set[str] = set()
            for item in (
                existing.metadata.get(key, ""),
                source.metadata.get(key, ""),
            ):
                values.update(
                    token.strip()
                    for token in str(item).split(" | ")
                    if token.strip()
                )
            metadata[key] = " | ".join(sorted(values))
        merged[source_id] = SourceDocument(
            source_id=source_id,
            title=title,
            url=existing.url,
            body_ref=existing.body_ref,
            fetched_at=min(fetched_values) if fetched_values else "",
            metadata=metadata,
        )
    return merged


def append_journal(
    current: Sequence[JournalEntry] | None,
    updates: Sequence[JournalEntry] | None,
) -> list[JournalEntry]:
    return _append_distinct(current, updates)


def append_handoffs(
    current: Sequence[BranchHandoff] | None,
    updates: Sequence[BranchHandoff] | None,
) -> list[BranchHandoff]:
    return _append_distinct(current, updates)


def append_findings(
    current: Sequence[ValidationFinding] | None,
    updates: Sequence[ValidationFinding] | None,
) -> list[ValidationFinding]:
    return _append_distinct(current, updates)


def append_assurance_events(
    current: Sequence[AssuranceEvent] | None,
    updates: Sequence[AssuranceEvent] | None,
) -> list[AssuranceEvent]:
    return _append_distinct(current, updates)


def append_amendments(
    current: Sequence[Amendment] | None,
    updates: Sequence[Amendment] | None,
) -> list[Amendment]:
    return _append_distinct(current, updates)


def append_errors(
    current: Sequence[str] | None, updates: Sequence[str] | None
) -> list[str]:
    return _append_distinct(current, updates)


class ResearchState(TypedDict, total=False):
    """Authoritative parent-graph state; nodes receive narrower projections."""

    task_id: str
    question: str
    stage: str
    stage_note: str
    publication_gate_status: PublicationGateStatus
    closure_validation_scope: str
    research_contract: ResearchContract
    approval_card: str
    research_tasks: list[ResearchTask]
    active_research_task: ResearchTask
    branch_handoffs: Annotated[list[BranchHandoff], append_handoffs]
    source_corpus: Annotated[dict[str, SourceDocument], merge_source_corpus]
    research_journal: Annotated[list[JournalEntry], append_journal]
    curated_material_library: dict[str, CuratedMaterial]
    research_synthesis: ResearchSynthesis
    draft: str
    validation_findings: list[ValidationFinding]
    assurance_log: Annotated[list[AssuranceEvent], append_assurance_events]
    edited_report: str
    final_report: str
    amendments: Annotated[list[Amendment], append_amendments]
    tool_errors: Annotated[list[str], append_errors]


__all__ = [
    "Amendment",
    "AmendmentLevel",
    "AssuranceActor",
    "AssuranceEvent",
    "ArtifactConflictError",
    "ArtifactValidationError",
    "BranchHandoff",
    "BodyRef",
    "CuratedMaterial",
    "HydratedSource",
    "JournalEntry",
    "JournalKind",
    "PublicationGateStatus",
    "ResearchContract",
    "ResearchState",
    "ResearchSynthesis",
    "ResearchTask",
    "SourceAnchor",
    "SourceDocument",
    "TextLocator",
    "ValidationFinding",
    "append_amendments",
    "append_assurance_events",
    "append_errors",
    "append_findings",
    "append_handoffs",
    "append_journal",
    "content_digest",
    "locate_quote",
    "make_material_id",
    "make_source_id",
    "merge_source_corpus",
    "validate_anchor",
    "validate_anchors",
]
