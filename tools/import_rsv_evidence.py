"""One-time offline importer: legacy RSV evidence into the artifact model.

This tool exists because the previous implementation gathered a genuinely
expensive evidence base -- 123 source snapshots and 166 curated materials, about
30 million characters of regulatory labels, ACIP records, and trial reports --
and then never produced a report.  The evidence is worth recovering; the control
plane that surrounded it is not.

Three rules shape the design:

**It does not import legacy code.**  Legacy checkpoints are msgpack with
LangGraph's dataclass extension, so the decoder reconstructs plain dictionaries
from ``[module, class, fields]`` triples.  Reviving the old classes would drag
the old control plane back into a project that just deleted it.

**It does not reuse legacy identity.**  Every artifact gets a new identity from
the current rule, with the legacy ID preserved as provenance.  Legacy IDs were
computed under different rules and carry no lineage.

**It verifies what is mechanically verifiable, and claims nothing more.**  Body
hashes, character counts, and anchor offsets are checked exactly: a quote must
appear at its recorded locator in the saved text.  That proves the quotes are
real and correctly located.  It does *not* prove a material's paraphrase stays
within what its quotes support -- only a Curator reading the frozen snapshot can
establish that.  The manifest records this distinction rather than letting a
structural pass masquerade as semantic re-qualification.

The source database is opened read-only and immutable and is never written.

Usage::

    python tools/import_rsv_evidence.py --legacy <copy.sqlite3> --output <new.sqlite3>
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sqlite3
import sys
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import aiosqlite
import ormsgpack

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from deep_research_agent.artifact_store import SqliteArtifactStore  # noqa: E402
from deep_research_agent.artifacts import Provenance  # noqa: E402
from deep_research_agent.content_store import SqliteContentStore  # noqa: E402
from deep_research_agent.sources import (  # noqa: E402
    ArtifactValidationError,
    BodyRef,
    MaterialBody,
    SourceAnchor,
    SourceSnapshotBody,
    TextLocator,
    validate_anchor,
)

#: LangGraph encodes dataclasses as ext types 0-2 carrying [module, name, fields].
_DATACLASS_EXT_CODES = frozenset({0, 1, 2})

TYPE_KEY = "__type__"
FIELDS_KEY = "__fields__"


def _ext_hook(code: int, data: bytes) -> object:
    value = ormsgpack.unpackb(data, ext_hook=_ext_hook)
    if code in _DATACLASS_EXT_CODES and isinstance(value, list) and len(value) == 3:
        module, name, fields = value
        return {TYPE_KEY: f"{module}.{name}", FIELDS_KEY: fields}
    return {"__ext__": code, "__value__": value}


def _decode(blob: bytes) -> object:
    return ormsgpack.unpackb(blob, ext_hook=_ext_hook)


def _walk(node: object) -> Iterator[tuple[str, Mapping[str, Any]]]:
    """Yield every ``(legacy_type_name, fields)`` pair in a decoded structure."""

    if isinstance(node, dict):
        declared = node.get(TYPE_KEY)
        if isinstance(declared, str):
            fields = node.get(FIELDS_KEY)
            if isinstance(fields, dict):
                yield declared.rsplit(".", 1)[-1], fields
                yield from _walk(fields)
            return
        for value in node.values():
            yield from _walk(value)
    elif isinstance(node, (list, tuple)):
        for value in node:
            yield from _walk(value)


@dataclass(frozen=True, slots=True)
class ItemOutcome:
    """What happened to one observed legacy record."""

    legacy_id: str
    kind: str
    status: str
    artifact_id: str = ""
    reason: str = ""

    def as_json(self) -> Mapping[str, str]:
        return {
            "legacy_id": self.legacy_id,
            "kind": self.kind,
            "status": self.status,
            "artifact_id": self.artifact_id,
            "reason": self.reason,
        }


@dataclass
class RecoveryManifest:
    """The auditable closure over every legacy record the importer observed."""

    task_id: str
    legacy_database: str
    outcomes: list[ItemOutcome] = field(default_factory=list)
    evidence_set_id: str = ""
    semantically_requalified: bool = False

    def record(self, outcome: ItemOutcome) -> None:
        self.outcomes.append(outcome)

    def counts(self, kind: str) -> dict[str, int]:
        tally: dict[str, int] = {"observed": 0, "imported": 0, "quarantined": 0}
        for outcome in self.outcomes:
            if outcome.kind != kind:
                continue
            tally["observed"] += 1
            tally[outcome.status] += 1
        return tally

    def closure_holds(self) -> bool:
        """Every observed record must carry exactly one terminal disposition.

        This is the property that makes the import auditable: a record cannot be
        silently dropped, because ``imported + quarantined`` must equal
        ``observed`` for each kind.
        """

        for kind in ("source_snapshot", "material"):
            tally = self.counts(kind)
            if tally["imported"] + tally["quarantined"] != tally["observed"]:
                return False
        return True

    def as_json(self) -> Mapping[str, object]:
        return {
            "task_id": self.task_id,
            "legacy_database": self.legacy_database,
            "sources": self.counts("source_snapshot"),
            "materials": self.counts("material"),
            "evidence_set_id": self.evidence_set_id,
            # Structural verification is not semantic re-qualification; a Curator
            # reading the frozen snapshots is what establishes faithfulness.
            "semantically_requalified": self.semantically_requalified,
            "closure_holds": self.closure_holds(),
            "outcomes": [outcome.as_json() for outcome in self.outcomes],
        }


@dataclass(frozen=True, slots=True)
class LegacyEvidence:
    """Everything worth recovering, keyed by legacy identity."""

    sources: Mapping[str, Mapping[str, Any]]
    materials: Mapping[str, Mapping[str, Any]]
    bodies: Mapping[str, tuple[int, str]]


def scan_legacy(path: Path) -> LegacyEvidence:
    """Read every distinct source and material from a legacy database.

    The whole checkpoint history is scanned, not just the final state, because
    the observed universe must include records an old active/inactive filter
    would have hidden.  Old flags are provenance, not authority.
    """

    uri = f"file:{path.as_posix()}?mode=ro&immutable=1"
    connection = sqlite3.connect(uri, uri=True)
    try:
        sources: dict[str, Mapping[str, Any]] = {}
        materials: dict[str, Mapping[str, Any]] = {}
        bodies = {
            str(row[0]): (int(row[1]), str(row[2]))
            for row in connection.execute(
                "SELECT hash, char_count, content FROM content_blobs"
            )
        }

        queries = (
            "SELECT value FROM writes WHERE type = 'msgpack'",
            "SELECT checkpoint FROM checkpoints",
        )
        for query in queries:
            for (blob,) in connection.execute(query):
                if not isinstance(blob, (bytes, bytearray)):
                    continue
                try:
                    decoded = _decode(bytes(blob))
                except Exception:
                    # A row the current decoder cannot read is not evidence that
                    # can be recovered; scanning continues so one bad row never
                    # hides the rest of the corpus.
                    continue
                for name, fields in _walk(decoded):
                    if name == "SourceDocument" and "source_id" in fields:
                        sources.setdefault(str(fields["source_id"]), fields)
                    elif name == "CuratedMaterial" and "material_id" in fields:
                        materials.setdefault(str(fields["material_id"]), fields)
        return LegacyEvidence(sources=sources, materials=materials, bodies=bodies)
    finally:
        connection.close()


def _body_ref(value: object) -> BodyRef | None:
    if not isinstance(value, dict) or value.get(TYPE_KEY, "").rsplit(".", 1)[-1] != "BodyRef":
        return None
    fields = value.get(FIELDS_KEY, {})
    try:
        return BodyRef(
            content_hash=str(fields["content_hash"]),
            char_count=int(fields["char_count"]),
        )
    except (KeyError, TypeError, ValueError, ArtifactValidationError):
        return None


def _legacy_anchors(fields: Mapping[str, Any]) -> list[tuple[str, str, int, int]]:
    """Extract ``(legacy_source_id, quote, start, end)`` from a legacy material."""

    anchors: list[tuple[str, str, int, int]] = []
    for anchor in fields.get("anchors", ()) or ():
        if not isinstance(anchor, dict):
            continue
        anchor_fields = anchor.get(FIELDS_KEY, {})
        locator = anchor_fields.get("locator", {})
        locator_fields = (
            locator.get(FIELDS_KEY, {}) if isinstance(locator, dict) else {}
        )
        try:
            anchors.append(
                (
                    str(anchor_fields["source_id"]),
                    str(anchor_fields["exact_quote"]),
                    int(locator_fields["start"]),
                    int(locator_fields["end"]),
                )
            )
        except (KeyError, TypeError, ValueError):
            return []
    return anchors


async def import_evidence(
    legacy_path: Path,
    output_path: Path,
    *,
    task_id: str,
) -> RecoveryManifest:
    """Import verified legacy evidence into a fresh artifact database."""

    evidence = scan_legacy(legacy_path)
    manifest = RecoveryManifest(
        task_id=task_id, legacy_database=str(legacy_path)
    )

    connection = await aiosqlite.connect(output_path)
    try:
        content_store = SqliteContentStore(connection)
        await content_store.setup()
        store = SqliteArtifactStore(connection, content_store, task_id=task_id)
        await store.setup()

        source_map: dict[str, str] = {}
        text_cache: dict[str, str] = {}

        for legacy_id in sorted(evidence.sources):
            fields = evidence.sources[legacy_id]
            reason = ""
            ref = _body_ref(fields.get("body_ref"))
            if ref is None:
                reason = "legacy record has no usable body reference"
            else:
                stored = evidence.bodies.get(ref.content_hash)
                if stored is None:
                    reason = f"body {ref.content_hash[:12]} is absent from the legacy store"
                elif stored[0] != ref.char_count or len(stored[1]) != ref.char_count:
                    reason = "stored body length disagrees with its reference"
                elif BodyRef.from_content(stored[1]) != ref:
                    reason = "stored body does not hash to its reference"

            if reason:
                manifest.record(
                    ItemOutcome(legacy_id, "source_snapshot", "quarantined", reason=reason)
                )
                continue

            assert ref is not None
            text = evidence.bodies[ref.content_hash][1]
            try:
                text_ref = await content_store.put(text)
                body = SourceSnapshotBody(
                    url=str(fields.get("url", "")),
                    title=str(fields.get("title", "")) or "Untitled source",
                    text_ref=text_ref,
                    fetched_at=str(fields.get("fetched_at", "")),
                    metadata={
                        str(key): str(value)
                        for key, value in dict(fields.get("metadata", {})).items()
                    },
                )
                envelope = await store.put(
                    kind="source_snapshot",
                    body=body.encode(),
                    provenance=Provenance(
                        producer="legacy-import", operation_ref=legacy_id
                    ),
                )
            except (ArtifactValidationError, ValueError) as error:
                manifest.record(
                    ItemOutcome(
                        legacy_id, "source_snapshot", "quarantined", reason=str(error)
                    )
                )
                continue

            source_map[legacy_id] = envelope.artifact_id
            text_cache[envelope.artifact_id] = text
            manifest.record(
                ItemOutcome(
                    legacy_id, "source_snapshot", "imported", envelope.artifact_id
                )
            )

        for legacy_id in sorted(evidence.materials):
            fields = evidence.materials[legacy_id]
            legacy_anchors = _legacy_anchors(fields)
            if not legacy_anchors:
                manifest.record(
                    ItemOutcome(
                        legacy_id,
                        "material",
                        "quarantined",
                        reason="no decodable source anchors",
                    )
                )
                continue

            anchors: list[SourceAnchor] = []
            reason = ""
            for legacy_source_id, quote, start, end in legacy_anchors:
                new_source = source_map.get(legacy_source_id)
                if new_source is None:
                    reason = f"anchors source {legacy_source_id}, which was not imported"
                    break
                try:
                    anchor = SourceAnchor(
                        source_ref=new_source,
                        exact_quote=quote,
                        locator=TextLocator(start=start, end=end),
                    )
                    # The decisive check: the quote must still be exactly where
                    # the legacy record said it was, in the frozen text.
                    validate_anchor(anchor, text_cache[new_source])
                except ArtifactValidationError as error:
                    reason = str(error)
                    break
                anchors.append(anchor)

            if reason:
                manifest.record(
                    ItemOutcome(legacy_id, "material", "quarantined", reason=reason)
                )
                continue

            try:
                body = MaterialBody.create(
                    content=str(fields.get("content", "")),
                    boundaries=str(fields.get("boundaries", "")),
                    anchors=anchors,
                )
                envelope = await store.put(
                    kind="material",
                    body=body.encode(),
                    parent_refs=body.source_refs,
                    provenance=Provenance(
                        producer="legacy-import", operation_ref=legacy_id
                    ),
                )
            except (ArtifactValidationError, ValueError) as error:
                manifest.record(
                    ItemOutcome(
                        legacy_id, "material", "quarantined", reason=str(error)
                    )
                )
                continue

            manifest.record(
                ItemOutcome(legacy_id, "material", "imported", envelope.artifact_id)
            )

        view = await store.active_view()
        manifest.evidence_set_id = view.evidence_set_id()
        return manifest
    finally:
        await connection.close()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import legacy RSV evidence into the artifact model."
    )
    parser.add_argument(
        "--legacy", required=True, type=Path, help="read-only legacy database copy"
    )
    parser.add_argument(
        "--output", required=True, type=Path, help="new artifact database to create"
    )
    parser.add_argument("--task-id", default="rsv-infant-prevention-20260812")
    parser.add_argument(
        "--manifest", type=Path, help="where to write the recovery manifest JSON"
    )
    parser.add_argument(
        "--force", action="store_true", help="overwrite an existing output database"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if not args.legacy.is_file():
        print(f"legacy database not found: {args.legacy}", file=sys.stderr)
        return 2
    if args.output.exists() and not args.force:
        print(f"output already exists: {args.output} (use --force)", file=sys.stderr)
        return 2
    if args.output.exists():
        args.output.unlink()

    manifest = asyncio.run(
        import_evidence(args.legacy, args.output, task_id=args.task_id)
    )
    destination = args.manifest or args.output.with_suffix(".manifest.json")
    destination.write_text(
        json.dumps(manifest.as_json(), ensure_ascii=False, indent=2), encoding="utf-8"
    )

    sources = manifest.counts("source_snapshot")
    materials = manifest.counts("material")
    print(f"task:      {manifest.task_id}")
    print(
        f"sources:   {sources['observed']} observed, "
        f"{sources['imported']} imported, {sources['quarantined']} quarantined"
    )
    print(
        f"materials: {materials['observed']} observed, "
        f"{materials['imported']} imported, {materials['quarantined']} quarantined"
    )
    print(f"evidence set: {manifest.evidence_set_id}")
    print(f"manifest:  {destination}")
    if not manifest.closure_holds():
        print("closure FAILED: an observed record has no disposition", file=sys.stderr)
        return 1
    print("closure holds; structural verification only, not re-qualification")
    return 0


if __name__ == "__main__":
    sys.exit(main())
