"""Immutable artifact envelopes: the only carriers of durable research truth.

Identity binds lineage.  ``artifact_id = H(kind + body content hash + sorted
parent refs)``, so two artifacts with identical bodies but different evidence
ancestry stay distinct and a downstream product can never silently adopt the
wrong basis.  Provenance (time, producer, model) is audit metadata and is
deliberately excluded from identity.

This module is pure domain logic.  It must not import LangGraph, providers,
HTTP clients, or database drivers; persistence lives in ``artifact_store``.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal

from .sources import ArtifactValidationError, BodyRef

ArtifactKind = Literal[
    "commission",
    "research_contract",
    "approval_receipt",
    "source_snapshot",
    "material",
    "research_memory",
    "synthesis",
    "report_commission",
    "report",
    "review",
    "review_receipt",
    "publication_receipt",
]

_KIND_PREFIX: Mapping[str, str] = {
    "commission": "cms",
    "research_contract": "ctr",
    "approval_receipt": "apr",
    "source_snapshot": "src",
    "material": "mat",
    "research_memory": "mem",
    "synthesis": "syn",
    "report_commission": "rcm",
    "report": "rpt",
    "review": "rvw",
    "review_receipt": "rvr",
    "publication_receipt": "pub",
}

ARTIFACT_KINDS: frozenset[str] = frozenset(_KIND_PREFIX)

#: Kinds where exactly one artifact is current at a time; the newest active one
#: is the head.  Superseding one of these invalidates everything derived from it.
SINGLETON_KINDS: frozenset[str] = frozenset(
    {
        "commission",
        "research_contract",
        "research_memory",
        "synthesis",
        "report_commission",
        "report",
        "publication_receipt",
    }
)

#: Kinds that accumulate: the whole active set matters, not the newest member.
COLLECTION_KINDS: frozenset[str] = frozenset(
    {"source_snapshot", "material", "review", "approval_receipt", "review_receipt"}
)

_ID_HASH_LENGTH = 24
_ARTIFACT_ID_RE = re.compile(
    rf"^(?:{'|'.join(sorted(_KIND_PREFIX.values()))})_[0-9a-f]{{{_ID_HASH_LENGTH}}}$"
)
_EVIDENCE_SET_ID_RE = re.compile(rf"^evs_[0-9a-f]{{{_ID_HASH_LENGTH}}}$")

#: A disposition always removes its target from the active view.  Admission is
#: expressed by creating an artifact, never by a disposition status, so there is
#: no ambiguous "active but disposed" state to reason about.
DispositionStatus = Literal["superseded", "withdrawn", "quarantined"]

_REQUIRES_REPLACEMENT: frozenset[str] = frozenset({"superseded"})
_DISPOSITION_STATUSES: frozenset[str] = frozenset(
    {"superseded", "withdrawn", "quarantined"}
)


def _canonical(payload: object) -> str:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def _digest(payload: object) -> str:
    return hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()


def _require_reason(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ArtifactValidationError("disposition reason must be a non-empty string")
    return value.strip()


def require_artifact_id(value: str, label: str = "artifact_id") -> str:
    """Reject anything that is not a well-formed runtime-issued artifact ID."""

    if not isinstance(value, str) or not _ARTIFACT_ID_RE.match(value):
        raise ArtifactValidationError(f"{label} is not a valid artifact ID: {value!r}")
    return value


def kind_of(artifact_id: str) -> str:
    """Recover the declared kind from an artifact ID prefix."""

    require_artifact_id(artifact_id)
    prefix = artifact_id.split("_", 1)[0]
    for kind, candidate in _KIND_PREFIX.items():
        if candidate == prefix:
            return kind
    raise ArtifactValidationError(f"unknown artifact prefix {prefix!r}")


def normalize_parent_refs(parent_refs: Iterable[str]) -> tuple[str, ...]:
    """Return the canonical parent set: validated, de-duplicated, sorted."""

    unique = {require_artifact_id(ref, "parent_ref") for ref in parent_refs}
    return tuple(sorted(unique))


def make_artifact_id(
    kind: str, body_ref: BodyRef, parent_refs: Iterable[str] = ()
) -> str:
    """Derive the content- and lineage-addressed identity for one artifact."""

    if kind not in ARTIFACT_KINDS:
        raise ArtifactValidationError(f"unsupported artifact kind {kind!r}")
    if not isinstance(body_ref, BodyRef):
        raise ArtifactValidationError("body_ref must be a BodyRef")
    identity = {
        "kind": kind,
        "body": body_ref.content_hash,
        "parents": list(normalize_parent_refs(parent_refs)),
    }
    return f"{_KIND_PREFIX[kind]}_{_digest(identity)[:_ID_HASH_LENGTH]}"


@dataclass(frozen=True, slots=True)
class Provenance:
    """Audit-only metadata; never an input to artifact identity."""

    produced_at: str = ""
    producer: str = ""
    operation_ref: str = ""
    model_id: str = ""

    def __post_init__(self) -> None:
        for name in ("produced_at", "producer", "operation_ref", "model_id"):
            if not isinstance(getattr(self, name), str):
                raise ArtifactValidationError(f"provenance {name} must be a string")


@dataclass(frozen=True, slots=True)
class ArtifactEnvelope:
    """One immutable formal product with a verifiable identity and lineage."""

    artifact_id: str
    kind: ArtifactKind
    body_ref: BodyRef
    parent_refs: tuple[str, ...] = ()
    provenance: Provenance = field(default_factory=Provenance)

    def __post_init__(self) -> None:
        if self.kind not in ARTIFACT_KINDS:
            raise ArtifactValidationError(f"unsupported artifact kind {self.kind!r}")
        if not isinstance(self.body_ref, BodyRef):
            raise ArtifactValidationError("body_ref must be a BodyRef")
        if not isinstance(self.provenance, Provenance):
            raise ArtifactValidationError("provenance must be a Provenance")
        canonical_parents = normalize_parent_refs(self.parent_refs)
        if canonical_parents != tuple(self.parent_refs):
            raise ArtifactValidationError(
                "parent_refs must be de-duplicated and sorted; use create()"
            )
        expected = make_artifact_id(self.kind, self.body_ref, canonical_parents)
        if self.artifact_id != expected:
            raise ArtifactValidationError(
                "artifact_id does not match kind, body hash, and parent refs"
            )

    @classmethod
    def create(
        cls,
        *,
        kind: ArtifactKind,
        body_ref: BodyRef,
        parent_refs: Iterable[str] = (),
        provenance: Provenance | None = None,
    ) -> ArtifactEnvelope:
        """Build an envelope, assigning the identity the runtime owns."""

        canonical_parents = normalize_parent_refs(parent_refs)
        return cls(
            artifact_id=make_artifact_id(kind, body_ref, canonical_parents),
            kind=kind,
            body_ref=body_ref,
            parent_refs=canonical_parents,
            provenance=provenance or Provenance(),
        )


@dataclass(frozen=True, slots=True)
class ArtifactDisposition:
    """Move one committed artifact out of the active view, keeping history.

    ``superseded`` names the replacement that takes over; ``withdrawn`` records a
    semantic retraction with no successor; ``quarantined`` records a
    deterministic integrity failure found by the trust plane.
    """

    target_ref: str
    status: DispositionStatus
    reason: str
    replacement_ref: str | None = None

    def __post_init__(self) -> None:
        require_artifact_id(self.target_ref, "disposition target_ref")
        if self.status not in _DISPOSITION_STATUSES:
            raise ArtifactValidationError(
                f"unsupported disposition status {self.status!r}"
            )
        _require_reason(self.reason)
        if self.status in _REQUIRES_REPLACEMENT:
            if self.replacement_ref is None:
                raise ArtifactValidationError(
                    f"{self.status} disposition requires a replacement_ref"
                )
            require_artifact_id(self.replacement_ref, "disposition replacement_ref")
            if self.replacement_ref == self.target_ref:
                raise ArtifactValidationError(
                    "disposition replacement_ref must differ from target_ref"
                )
        elif self.replacement_ref is not None:
            raise ArtifactValidationError(
                f"{self.status} disposition must not name a replacement_ref"
            )


@dataclass(frozen=True, slots=True)
class ActiveView:
    """The projection every role context is built from: what is current now."""

    by_kind: Mapping[str, tuple[str, ...]]

    def active(self, kind: str) -> tuple[str, ...]:
        """Return active artifact IDs of one kind in commit order."""

        if kind not in ARTIFACT_KINDS:
            raise ArtifactValidationError(f"unsupported artifact kind {kind!r}")
        return self.by_kind.get(kind, ())

    def head(self, kind: str) -> str | None:
        """Return the current head of a singleton kind, or None if absent."""

        if kind not in SINGLETON_KINDS:
            raise ArtifactValidationError(
                f"{kind!r} accumulates; use active() rather than head()"
            )
        active = self.active(kind)
        return active[-1] if active else None

    def evidence_set_id(self) -> str:
        """Identity of the current active Material set."""

        return evidence_set_id(self.active("material"))


def project_active_view(
    envelopes: Sequence[ArtifactEnvelope],
    dispositions: Sequence[ArtifactDisposition] = (),
) -> ActiveView:
    """Compute the active view from commit-ordered artifacts and dispositions.

    ``envelopes`` must be in commit order so that singleton heads are
    deterministic.  A disposition whose target is absent is an integrity error,
    not something to silently ignore.
    """

    known = {envelope.artifact_id for envelope in envelopes}
    disposed: set[str] = set()
    for disposition in dispositions:
        if disposition.target_ref not in known:
            raise ArtifactValidationError(
                f"disposition targets unknown artifact {disposition.target_ref}"
            )
        disposed.add(disposition.target_ref)

    by_kind: dict[str, list[str]] = {}
    for envelope in envelopes:
        if envelope.artifact_id in disposed:
            continue
        by_kind.setdefault(envelope.kind, []).append(envelope.artifact_id)
    return ActiveView(
        by_kind={kind: tuple(ids) for kind, ids in sorted(by_kind.items())}
    )


def evidence_set_id(material_ids: Iterable[str]) -> str:
    """Derive the stable identity of a set of Material artifacts.

    The EvidenceSet is not a stored artifact: it is the sorted set of active
    Material IDs.  Synthesis and report_commission bind it through their parent
    refs, so a changed set makes every downstream product stale by construction.
    """

    ordered = sorted({require_artifact_id(ref, "material ref") for ref in material_ids})
    for ref in ordered:
        if kind_of(ref) != "material":
            raise ArtifactValidationError(f"{ref} is not a Material artifact")
    return f"evs_{_digest(ordered)[:_ID_HASH_LENGTH]}"


def require_evidence_set_id(value: str) -> str:
    """Reject anything that is not a well-formed EvidenceSet identity."""

    if not isinstance(value, str) or not _EVIDENCE_SET_ID_RE.match(value):
        raise ArtifactValidationError(
            f"not a valid evidence set ID: {value!r}"
        )
    return value


def lineage_closure(
    artifact_id: str, envelopes: Mapping[str, ArtifactEnvelope]
) -> frozenset[str]:
    """Return an artifact and every ancestor it transitively depends on."""

    require_artifact_id(artifact_id)
    seen: set[str] = set()
    pending = [artifact_id]
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        envelope = envelopes.get(current)
        if envelope is None:
            raise ArtifactValidationError(
                f"lineage references unknown artifact {current}"
            )
        seen.add(current)
        pending.extend(envelope.parent_refs)
    return frozenset(seen)


__all__ = [
    "ARTIFACT_KINDS",
    "COLLECTION_KINDS",
    "SINGLETON_KINDS",
    "ActiveView",
    "ArtifactDisposition",
    "ArtifactEnvelope",
    "ArtifactKind",
    "DispositionStatus",
    "Provenance",
    "evidence_set_id",
    "kind_of",
    "lineage_closure",
    "make_artifact_id",
    "normalize_parent_refs",
    "project_active_view",
    "require_artifact_id",
    "require_evidence_set_id",
]
