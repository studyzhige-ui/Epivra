from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import aiosqlite

from deep_research_agent.artifact_store import ArtifactStoreError, SqliteArtifactStore
from deep_research_agent.artifacts import (
    ArtifactDisposition,
    Provenance,
    evidence_set_id,
)
from deep_research_agent.content_store import SqliteContentStore
from deep_research_agent.sources import ArtifactValidationError


class ArtifactStoreFixture(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._directory = tempfile.TemporaryDirectory()
        self._path = Path(self._directory.name) / "artifacts.sqlite3"
        self._connection = await aiosqlite.connect(self._path)
        self.content_store = SqliteContentStore(self._connection)
        await self.content_store.setup()
        self.store = SqliteArtifactStore(
            self._connection, self.content_store, task_id="task-1"
        )
        await self.store.setup()

    async def asyncTearDown(self) -> None:
        await self._connection.close()
        self._directory.cleanup()

    async def reopen(self, task_id: str = "task-1") -> SqliteArtifactStore:
        await self._connection.close()
        self._connection = await aiosqlite.connect(self._path)
        self.content_store = SqliteContentStore(self._connection)
        self.store = SqliteArtifactStore(
            self._connection, self.content_store, task_id=task_id
        )
        return self.store


class CommitTest(ArtifactStoreFixture):
    async def test_committing_returns_a_runtime_assigned_identity(self) -> None:
        envelope = await self.store.put(
            kind="source_snapshot", body="Exact source body."
        )

        self.assertTrue(envelope.artifact_id.startswith("src_"))
        self.assertEqual("Exact source body.", await self.store.body(envelope.artifact_id))

    async def test_committing_the_same_artifact_twice_is_idempotent(self) -> None:
        first = await self.store.put(kind="material", body="An excerpt.")
        second = await self.store.put(kind="material", body="An excerpt.")

        self.assertEqual(first.artifact_id, second.artifact_id)
        self.assertEqual(1, len(await self.store.envelopes()))

    async def test_provenance_is_stored_without_entering_identity(self) -> None:
        bare = await self.store.put(kind="synthesis", body="Analysis.")
        await self.reopen()
        attributed = await self.store.put(
            kind="synthesis",
            body="Analysis.",
            provenance=Provenance(producer="analyst", operation_ref="op-1"),
        )

        self.assertEqual(bare.artifact_id, attributed.artifact_id)
        stored = await self.store.get(bare.artifact_id)
        self.assertEqual("", stored.provenance.producer)

    async def test_lineage_is_verified_before_a_child_is_committed(self) -> None:
        source = await self.store.put(kind="source_snapshot", body="Body.")
        material = await self.store.put(
            kind="material", body="Excerpt.", parent_refs=(source.artifact_id,)
        )

        self.assertEqual((source.artifact_id,), material.parent_refs)

        orphan = "syn_000000000000000000000001"
        with self.assertRaisesRegex(ArtifactStoreError, "not committed"):
            await self.store.put(
                kind="report", body="Report.", parent_refs=(orphan,)
            )

    async def test_reading_an_unknown_artifact_fails_closed(self) -> None:
        with self.assertRaisesRegex(ArtifactStoreError, "not committed"):
            await self.store.get("mat_000000000000000000000001")
        with self.assertRaises(ArtifactValidationError):
            await self.store.get("not-an-artifact-id")

    async def test_artifacts_survive_a_restart_in_commit_order(self) -> None:
        first = await self.store.put(kind="synthesis", body="First synthesis.")
        second = await self.store.put(kind="synthesis", body="Second synthesis.")

        store = await self.reopen()
        view = await store.active_view()

        self.assertEqual(
            (first.artifact_id, second.artifact_id), view.active("synthesis")
        )
        self.assertEqual(second.artifact_id, view.head("synthesis"))


class DispositionTest(ArtifactStoreFixture):
    async def test_a_superseded_artifact_leaves_the_active_view(self) -> None:
        original = await self.store.put(kind="material", body="Original excerpt.")
        corrected = await self.store.put(kind="material", body="Corrected excerpt.")

        await self.store.dispose(
            ArtifactDisposition(
                target_ref=original.artifact_id,
                status="superseded",
                reason="Publisher issued a correction.",
                replacement_ref=corrected.artifact_id,
            )
        )
        view = await self.store.active_view()

        self.assertEqual((corrected.artifact_id,), view.active("material"))
        self.assertEqual(2, len(await self.store.envelopes()))

    async def test_history_stays_readable_after_disposition(self) -> None:
        original = await self.store.put(kind="material", body="Original excerpt.")
        await self.store.dispose(
            ArtifactDisposition(
                target_ref=original.artifact_id,
                status="withdrawn",
                reason="Curator retracted an over-broad paraphrase.",
            )
        )

        self.assertEqual(
            "Original excerpt.", await self.store.body(original.artifact_id)
        )
        self.assertEqual((), (await self.store.active_view()).active("material"))

    async def test_disposition_requires_both_ends_to_exist(self) -> None:
        target = await self.store.put(kind="material", body="Target.")
        absent = "mat_000000000000000000000001"

        with self.assertRaisesRegex(ArtifactStoreError, "not committed"):
            await self.store.dispose(
                ArtifactDisposition(
                    target_ref=absent, status="withdrawn", reason="Absent target."
                )
            )
        with self.assertRaisesRegex(ArtifactStoreError, "not committed"):
            await self.store.dispose(
                ArtifactDisposition(
                    target_ref=target.artifact_id,
                    status="superseded",
                    reason="Absent replacement.",
                    replacement_ref=absent,
                )
            )

    async def test_repeating_an_identical_disposition_is_idempotent(self) -> None:
        target = await self.store.put(kind="material", body="Target.")
        disposition = ArtifactDisposition(
            target_ref=target.artifact_id,
            status="quarantined",
            reason="Body failed an integrity check.",
        )

        await self.store.dispose(disposition)
        await self.store.dispose(disposition)

        self.assertEqual(1, len(await self.store.dispositions()))

    async def test_a_conflicting_second_disposition_is_refused(self) -> None:
        target = await self.store.put(kind="material", body="Target.")
        await self.store.dispose(
            ArtifactDisposition(
                target_ref=target.artifact_id,
                status="withdrawn",
                reason="Retracted.",
            )
        )

        with self.assertRaisesRegex(ArtifactStoreError, "conflicting"):
            await self.store.dispose(
                ArtifactDisposition(
                    target_ref=target.artifact_id,
                    status="quarantined",
                    reason="A different verdict.",
                )
            )


class EvidenceSetTest(ArtifactStoreFixture):
    async def test_the_evidence_set_tracks_the_active_material_set(self) -> None:
        kept = await self.store.put(kind="material", body="Kept.")
        dropped = await self.store.put(kind="material", body="Dropped.")

        before = (await self.store.active_view()).evidence_set_id()
        await self.store.dispose(
            ArtifactDisposition(
                target_ref=dropped.artifact_id,
                status="withdrawn",
                reason="Not source-faithful.",
            )
        )
        after = (await self.store.active_view()).evidence_set_id()

        self.assertNotEqual(before, after)
        self.assertEqual(evidence_set_id((kept.artifact_id,)), after)


class TaskIsolationTest(ArtifactStoreFixture):
    async def test_tasks_never_see_each_other_artifacts(self) -> None:
        mine = await self.store.put(kind="research_memory", body="My memory.")

        other = SqliteArtifactStore(
            self._connection, self.content_store, task_id="task-2"
        )

        self.assertEqual((), await other.envelopes())
        with self.assertRaisesRegex(ArtifactStoreError, "task-2"):
            await other.get(mine.artifact_id)

    async def test_the_same_body_in_two_tasks_stays_separately_owned(self) -> None:
        shared = "An identical memory body."
        mine = await self.store.put(kind="research_memory", body=shared)

        other = SqliteArtifactStore(
            self._connection, self.content_store, task_id="task-2"
        )
        theirs = await other.put(kind="research_memory", body=shared)

        self.assertEqual(mine.artifact_id, theirs.artifact_id)
        self.assertEqual(1, len(await self.store.envelopes()))
        self.assertEqual(1, len(await other.envelopes()))

    async def test_an_empty_task_id_is_rejected(self) -> None:
        with self.assertRaises(ArtifactValidationError):
            SqliteArtifactStore(self._connection, self.content_store, task_id="  ")


if __name__ == "__main__":
    unittest.main()
