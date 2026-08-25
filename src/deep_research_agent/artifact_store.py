"""Durable storage for artifact envelopes and their dispositions.

The store owns two things the domain layer deliberately does not: commit order
and persistence.  Commit order matters because a singleton head ("the current
Synthesis") is defined as the newest active artifact of its kind, so the
sequence has to survive a restart rather than depend on dictionary iteration.

Bodies live in the content store, addressed by hash, so an artifact row stays
small and one body shared by several lineages is stored once.  Artifacts are
insert-only: correcting a mistake means committing a new artifact and recording
a disposition, never rewriting history.

Everything is scoped by ``task_id``.  Two research tasks in one database never
see each other's evidence, memory, or heads.
"""

from __future__ import annotations

import aiosqlite

from .artifacts import (
    ActiveView,
    ArtifactDisposition,
    ArtifactEnvelope,
    ArtifactKind,
    Provenance,
    project_active_view,
    require_artifact_id,
)
from .content_store import ContentStore
from .sources import ArtifactValidationError, BodyRef


class ArtifactStoreError(RuntimeError):
    """A durable artifact operation cannot be trusted as requested."""


class SqliteArtifactStore:
    """SQLite-backed insert-only artifact storage for one task."""

    def __init__(
        self,
        connection: aiosqlite.Connection,
        content_store: ContentStore,
        *,
        task_id: str,
    ) -> None:
        if not isinstance(task_id, str) or not task_id.strip():
            raise ArtifactValidationError("task_id must be a non-empty string")
        self._connection = connection
        self._content_store = content_store
        self._task_id = task_id.strip()

    @property
    def task_id(self) -> str:
        """The task whose artifacts this store exposes."""

        return self._task_id

    async def setup(self) -> None:
        """Create only the artifact and disposition tables."""

        await self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS artifacts (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                artifact_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                body_hash TEXT NOT NULL,
                body_chars INTEGER NOT NULL CHECK (body_chars > 0),
                parent_refs TEXT NOT NULL,
                produced_at TEXT NOT NULL DEFAULT '',
                producer TEXT NOT NULL DEFAULT '',
                operation_ref TEXT NOT NULL DEFAULT '',
                model_id TEXT NOT NULL DEFAULT '',
                UNIQUE (task_id, artifact_id)
            )
            """
        )
        await self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS artifact_dispositions (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                target_ref TEXT NOT NULL,
                status TEXT NOT NULL,
                reason TEXT NOT NULL,
                replacement_ref TEXT,
                UNIQUE (task_id, target_ref)
            )
            """
        )
        await self._connection.execute(
            "CREATE INDEX IF NOT EXISTS artifacts_task_kind "
            "ON artifacts(task_id, kind, sequence)"
        )
        await self._connection.commit()

    async def put(
        self,
        *,
        kind: ArtifactKind,
        body: str,
        parent_refs: tuple[str, ...] = (),
        provenance: Provenance | None = None,
    ) -> ArtifactEnvelope:
        """Persist one artifact, assigning the identity the runtime owns.

        Parents are verified to exist in this task first: a dangling lineage is
        an integrity failure, not something a later reader should discover.
        """

        for ref in parent_refs:
            await self.get(ref)

        body_ref = await self._content_store.put(body)
        envelope = ArtifactEnvelope.create(
            kind=kind,
            body_ref=body_ref,
            parent_refs=parent_refs,
            provenance=provenance,
        )
        existing = await self._row(envelope.artifact_id)
        if existing is not None:
            return envelope

        await self._connection.execute(
            """
            INSERT INTO artifacts(
                task_id, artifact_id, kind, body_hash, body_chars, parent_refs,
                produced_at, producer, operation_ref, model_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(task_id, artifact_id) DO NOTHING
            """,
            (
                self._task_id,
                envelope.artifact_id,
                envelope.kind,
                envelope.body_ref.content_hash,
                envelope.body_ref.char_count,
                "\n".join(envelope.parent_refs),
                envelope.provenance.produced_at,
                envelope.provenance.producer,
                envelope.provenance.operation_ref,
                envelope.provenance.model_id,
            ),
        )
        await self._connection.commit()
        return envelope

    async def get(self, artifact_id: str) -> ArtifactEnvelope:
        require_artifact_id(artifact_id)
        row = await self._row(artifact_id)
        if row is None:
            raise ArtifactStoreError(
                f"artifact {artifact_id} is not committed in task {self._task_id}"
            )
        return row

    async def body(self, artifact_id: str) -> str:
        envelope = await self.get(artifact_id)
        return await self._content_store.get(envelope.body_ref)

    async def dispose(self, disposition: ArtifactDisposition) -> None:
        """Record a disposition, verifying both ends exist in this task."""

        await self.get(disposition.target_ref)
        if disposition.replacement_ref is not None:
            await self.get(disposition.replacement_ref)

        existing = await self._disposition(disposition.target_ref)
        if existing is not None:
            if existing != disposition:
                raise ArtifactStoreError(
                    f"artifact {disposition.target_ref} already has a conflicting "
                    f"disposition ({existing.status})"
                )
            return

        await self._connection.execute(
            """
            INSERT INTO artifact_dispositions(
                task_id, target_ref, status, reason, replacement_ref
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                self._task_id,
                disposition.target_ref,
                disposition.status,
                disposition.reason,
                disposition.replacement_ref,
            ),
        )
        await self._connection.commit()

    async def envelopes(self) -> tuple[ArtifactEnvelope, ...]:
        """Every committed artifact in this task, in commit order."""

        cursor = await self._connection.execute(
            "SELECT artifact_id, kind, body_hash, body_chars, parent_refs, "
            "produced_at, producer, operation_ref, model_id "
            "FROM artifacts WHERE task_id = ? ORDER BY sequence",
            (self._task_id,),
        )
        rows = await cursor.fetchall()
        await cursor.close()
        return tuple(_envelope_from_row(row) for row in rows)

    async def dispositions(self) -> tuple[ArtifactDisposition, ...]:
        """Every recorded disposition in this task, in commit order."""

        cursor = await self._connection.execute(
            "SELECT target_ref, status, reason, replacement_ref "
            "FROM artifact_dispositions WHERE task_id = ? ORDER BY sequence",
            (self._task_id,),
        )
        rows = await cursor.fetchall()
        await cursor.close()
        return tuple(_disposition_from_row(row) for row in rows)

    async def active_view(self) -> ActiveView:
        """Project the current heads and active sets from durable state."""

        return project_active_view(await self.envelopes(), await self.dispositions())

    async def _row(self, artifact_id: str) -> ArtifactEnvelope | None:
        cursor = await self._connection.execute(
            "SELECT artifact_id, kind, body_hash, body_chars, parent_refs, "
            "produced_at, producer, operation_ref, model_id "
            "FROM artifacts WHERE task_id = ? AND artifact_id = ?",
            (self._task_id, artifact_id),
        )
        row = await cursor.fetchone()
        await cursor.close()
        return None if row is None else _envelope_from_row(row)

    async def _disposition(self, target_ref: str) -> ArtifactDisposition | None:
        cursor = await self._connection.execute(
            "SELECT target_ref, status, reason, replacement_ref "
            "FROM artifact_dispositions WHERE task_id = ? AND target_ref = ?",
            (self._task_id, target_ref),
        )
        row = await cursor.fetchone()
        await cursor.close()
        return None if row is None else _disposition_from_row(row)


def _envelope_from_row(row: tuple[object, ...]) -> ArtifactEnvelope:
    (
        artifact_id,
        kind,
        body_hash,
        body_chars,
        parent_refs,
        produced_at,
        producer,
        operation_ref,
        model_id,
    ) = row
    stored_parents = str(parent_refs)
    parents = tuple(line for line in stored_parents.split("\n") if line)
    return ArtifactEnvelope(
        artifact_id=str(artifact_id),
        kind=str(kind),  # type: ignore[arg-type]
        body_ref=BodyRef(content_hash=str(body_hash), char_count=int(body_chars)),
        parent_refs=parents,
        provenance=Provenance(
            produced_at=str(produced_at or ""),
            producer=str(producer or ""),
            operation_ref=str(operation_ref or ""),
            model_id=str(model_id or ""),
        ),
    )


def _disposition_from_row(row: tuple[object, ...]) -> ArtifactDisposition:
    target_ref, status, reason, replacement_ref = row
    return ArtifactDisposition(
        target_ref=str(target_ref),
        status=str(status),  # type: ignore[arg-type]
        reason=str(reason),
        replacement_ref=None if replacement_ref is None else str(replacement_ref),
    )


__all__ = [
    "ArtifactStoreError",
    "SqliteArtifactStore",
]
