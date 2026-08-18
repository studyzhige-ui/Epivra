"""The importer must reject corruption, not merely run.

A clean import of the real corpus (123 sources, 166 materials, zero
quarantines) is only trustworthy if the verification it claims to perform can be
shown to fail.  Each test here builds a synthetic legacy database in the real
on-disk format, injects one specific corruption, and asserts the importer
quarantines exactly that record while importing the rest.
"""

from __future__ import annotations

import importlib.util
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

import ormsgpack

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "import_rsv_evidence", ROOT / "tools" / "import_rsv_evidence.py"
)
assert _spec is not None and _spec.loader is not None
importer = importlib.util.module_from_spec(_spec)
sys.modules["import_rsv_evidence"] = _spec.loader and importer
_spec.loader.exec_module(importer)

from deep_research_agent.sources import BodyRef, MaterialBody  # noqa: E402

SOURCE_TEXT = (
    "ACIP recommended nirsevimab for infants aged under eight months. "
    "Coverage in the first season reached a reported plateau."
)
QUOTE = "recommended nirsevimab for infants aged under eight months"


def _dataclass(name: str, fields: dict[str, object]) -> ormsgpack.Ext:
    """Encode one legacy dataclass exactly as LangGraph's serializer does."""

    payload = ormsgpack.packb(
        ["deep_research_agent.state", name, fields],
        default=_default,
        option=ormsgpack.OPT_PASSTHROUGH_DATACLASS,
    )
    return ormsgpack.Ext(2, payload)


def _default(value: object) -> object:
    if isinstance(value, ormsgpack.Ext):
        return value
    raise TypeError(type(value))


def legacy_source(source_id: str, text: str, url: str) -> ormsgpack.Ext:
    ref = BodyRef.from_content(text)
    return _dataclass(
        "SourceDocument",
        {
            "source_id": source_id,
            "title": f"Report {source_id}",
            "url": url,
            "body_ref": _dataclass(
                "BodyRef",
                {"content_hash": ref.content_hash, "char_count": ref.char_count},
            ),
            "fetched_at": "2026-08-12T10:30:51+00:00",
            "metadata": {"discovered_by": "tavily"},
        },
    )


def legacy_material(
    material_id: str, source_id: str, quote: str, start: int, end: int
) -> ormsgpack.Ext:
    return _dataclass(
        "CuratedMaterial",
        {
            "material_id": material_id,
            "content": f"A curated claim from {source_id}.",
            "boundaries": "US; first season only; no causal claim.",
            "anchors": [
                _dataclass(
                    "SourceAnchor",
                    {
                        "source_id": source_id,
                        "exact_quote": quote,
                        "locator": _dataclass(
                            "TextLocator", {"start": start, "end": end}
                        ),
                    },
                )
            ],
        },
    )


class LegacyFixture(unittest.IsolatedAsyncioTestCase):
    """Builds a synthetic legacy database in the real on-disk format."""

    def setUp(self) -> None:
        self._directory = tempfile.TemporaryDirectory()
        self.root = Path(self._directory.name)
        self.legacy = self.root / "legacy.sqlite3"

    def tearDown(self) -> None:
        self._directory.cleanup()

    def build(
        self,
        *,
        records: list[object],
        bodies: dict[str, tuple[int, str]],
    ) -> None:
        connection = sqlite3.connect(self.legacy)
        try:
            connection.execute(
                "CREATE TABLE writes (thread_id TEXT, checkpoint_ns TEXT, "
                "checkpoint_id TEXT, task_id TEXT, idx INTEGER, channel TEXT, "
                "type TEXT, value BLOB)"
            )
            connection.execute(
                "CREATE TABLE checkpoints (thread_id TEXT, checkpoint_ns TEXT, "
                "checkpoint_id TEXT, parent_checkpoint_id TEXT, type TEXT, "
                "checkpoint BLOB, metadata BLOB)"
            )
            connection.execute(
                "CREATE TABLE content_blobs (hash TEXT PRIMARY KEY, "
                "char_count INTEGER, content TEXT)"
            )
            blob = ormsgpack.packb(records, default=_default)
            connection.execute(
                "INSERT INTO writes VALUES ('t','', 'c1','task',0,'state','msgpack',?)",
                (blob,),
            )
            for digest, (count, text) in bodies.items():
                connection.execute(
                    "INSERT INTO content_blobs VALUES (?,?,?)", (digest, count, text)
                )
            connection.commit()
        finally:
            connection.close()

    def standard_corpus(self, text: str = SOURCE_TEXT) -> dict[str, tuple[int, str]]:
        ref = BodyRef.from_content(text)
        return {ref.content_hash: (ref.char_count, text)}

    async def run_import(self) -> importer.RecoveryManifest:
        return await importer.import_evidence(
            self.legacy, self.root / "new.sqlite3", task_id="task-under-test"
        )


class HealthyImportTest(LegacyFixture):
    async def test_verified_records_are_imported_with_new_identity(self) -> None:
        start = SOURCE_TEXT.index(QUOTE)
        self.build(
            records=[
                legacy_source("src_legacy01", SOURCE_TEXT, "https://cdc.example/a"),
                legacy_material(
                    "mat_legacy01", "src_legacy01", QUOTE, start, start + len(QUOTE)
                ),
            ],
            bodies=self.standard_corpus(),
        )

        manifest = await self.run_import()

        self.assertEqual(
            {"observed": 1, "imported": 1, "quarantined": 0},
            manifest.counts("source_snapshot"),
        )
        self.assertEqual(
            {"observed": 1, "imported": 1, "quarantined": 0},
            manifest.counts("material"),
        )
        self.assertTrue(manifest.closure_holds())

        imported = {o.legacy_id: o for o in manifest.outcomes}
        # Legacy identity is provenance, never reused as artifact identity.
        self.assertNotEqual("src_legacy01", imported["src_legacy01"].artifact_id)
        self.assertTrue(imported["src_legacy01"].artifact_id.startswith("src_"))
        self.assertTrue(imported["mat_legacy01"].artifact_id.startswith("mat_"))

    async def test_the_import_never_claims_semantic_requalification(self) -> None:
        self.build(records=[], bodies={})
        manifest = await self.run_import()

        self.assertFalse(manifest.semantically_requalified)
        self.assertFalse(manifest.as_json()["semantically_requalified"])

    async def test_material_lineage_points_at_the_new_source_artifact(self) -> None:
        start = SOURCE_TEXT.index(QUOTE)
        self.build(
            records=[
                legacy_source("src_legacy01", SOURCE_TEXT, "https://cdc.example/a"),
                legacy_material(
                    "mat_legacy01", "src_legacy01", QUOTE, start, start + len(QUOTE)
                ),
            ],
            bodies=self.standard_corpus(),
        )
        await self.run_import()

        connection = sqlite3.connect(self.root / "new.sqlite3")
        try:
            parents, body_hash = connection.execute(
                "SELECT parent_refs, body_hash FROM artifacts WHERE kind='material'"
            ).fetchone()
            source_id = connection.execute(
                "SELECT artifact_id FROM artifacts WHERE kind='source_snapshot'"
            ).fetchone()[0]
            body = connection.execute(
                "SELECT content FROM content_blobs WHERE hash=?", (body_hash,)
            ).fetchone()[0]
        finally:
            connection.close()

        self.assertEqual(source_id, parents)
        self.assertEqual((source_id,), MaterialBody.decode(body).source_refs)


class CorruptionTest(LegacyFixture):
    """Each case proves one verification step actually rejects."""

    async def test_a_missing_body_quarantines_its_source(self) -> None:
        self.build(
            records=[legacy_source("src_a", SOURCE_TEXT, "https://cdc.example/a")],
            bodies={},
        )
        manifest = await self.run_import()

        self.assertEqual(1, manifest.counts("source_snapshot")["quarantined"])
        self.assertIn("absent", manifest.outcomes[0].reason)

    async def test_a_tampered_body_fails_its_hash(self) -> None:
        """Same length, different meaning -- only the digest can catch this."""

        ref = BodyRef.from_content(SOURCE_TEXT)
        tampered = SOURCE_TEXT.replace("eight months", "seven months")
        self.assertEqual(len(SOURCE_TEXT), len(tampered))
        self.build(
            records=[legacy_source("src_a", SOURCE_TEXT, "https://cdc.example/a")],
            bodies={ref.content_hash: (ref.char_count, tampered)},
        )
        manifest = await self.run_import()

        self.assertEqual(1, manifest.counts("source_snapshot")["quarantined"])
        self.assertIn("hash", manifest.outcomes[0].reason)

    async def test_a_length_mismatch_is_caught_before_hashing(self) -> None:
        ref = BodyRef.from_content(SOURCE_TEXT)
        self.build(
            records=[legacy_source("src_a", SOURCE_TEXT, "https://cdc.example/a")],
            bodies={ref.content_hash: (ref.char_count + 5, SOURCE_TEXT)},
        )
        manifest = await self.run_import()

        self.assertEqual(1, manifest.counts("source_snapshot")["quarantined"])
        self.assertIn("length", manifest.outcomes[0].reason)

    async def test_a_drifted_anchor_quarantines_its_material(self) -> None:
        """The decisive check: the quote must be exactly where it claims."""

        start = SOURCE_TEXT.index(QUOTE)
        self.build(
            records=[
                legacy_source("src_a", SOURCE_TEXT, "https://cdc.example/a"),
                legacy_material(
                    "mat_a", "src_a", QUOTE, start + 3, start + 3 + len(QUOTE)
                ),
            ],
            bodies=self.standard_corpus(),
        )
        manifest = await self.run_import()

        self.assertEqual(1, manifest.counts("source_snapshot")["imported"])
        self.assertEqual(1, manifest.counts("material")["quarantined"])
        material = next(o for o in manifest.outcomes if o.kind == "material")
        self.assertIn("does not match", material.reason)

    async def test_an_anchor_past_the_end_of_the_text_is_rejected(self) -> None:
        self.build(
            records=[
                legacy_source("src_a", SOURCE_TEXT, "https://cdc.example/a"),
                legacy_material("mat_a", "src_a", QUOTE, 0, len(SOURCE_TEXT) + 500),
            ],
            bodies=self.standard_corpus(),
        )
        manifest = await self.run_import()

        material = next(o for o in manifest.outcomes if o.kind == "material")
        self.assertEqual("quarantined", material.status)
        self.assertIn("exceeds", material.reason)

    async def test_a_material_orphaned_by_a_quarantined_source_is_quarantined(
        self,
    ) -> None:
        start = SOURCE_TEXT.index(QUOTE)
        self.build(
            records=[
                legacy_source("src_a", SOURCE_TEXT, "https://cdc.example/a"),
                legacy_material("mat_a", "src_missing", QUOTE, start, start + len(QUOTE)),
            ],
            bodies=self.standard_corpus(),
        )
        manifest = await self.run_import()

        material = next(o for o in manifest.outcomes if o.kind == "material")
        self.assertEqual("quarantined", material.status)
        self.assertIn("not imported", material.reason)

    async def test_one_corrupt_record_does_not_hide_the_healthy_ones(self) -> None:
        start = SOURCE_TEXT.index(QUOTE)
        other = "A second source body with its own distinct sentence."
        other_quote = "second source body"
        other_start = other.index(other_quote)
        bodies = self.standard_corpus()
        bodies.update(self.standard_corpus(other))
        self.build(
            records=[
                legacy_source("src_a", SOURCE_TEXT, "https://cdc.example/a"),
                legacy_source("src_b", other, "https://cdc.example/b"),
                legacy_material("mat_ok", "src_b", other_quote, other_start,
                                other_start + len(other_quote)),
                legacy_material("mat_bad", "src_a", QUOTE, start + 7,
                                start + 7 + len(QUOTE)),
            ],
            bodies=bodies,
        )
        manifest = await self.run_import()

        self.assertEqual(
            {"observed": 2, "imported": 1, "quarantined": 1},
            manifest.counts("material"),
        )
        self.assertTrue(manifest.closure_holds())


class ClosureTest(LegacyFixture):
    async def test_every_observed_record_receives_exactly_one_disposition(self) -> None:
        start = SOURCE_TEXT.index(QUOTE)
        self.build(
            records=[
                legacy_source("src_a", SOURCE_TEXT, "https://cdc.example/a"),
                legacy_source("src_gone", "Body absent from the store.",
                              "https://cdc.example/gone"),
                legacy_material("mat_a", "src_a", QUOTE, start, start + len(QUOTE)),
                legacy_material("mat_bad", "src_a", QUOTE, start + 2,
                                start + 2 + len(QUOTE)),
            ],
            bodies=self.standard_corpus(),
        )
        manifest = await self.run_import()

        self.assertTrue(manifest.closure_holds())
        self.assertEqual(4, len(manifest.outcomes))
        self.assertEqual(4, len({o.legacy_id for o in manifest.outcomes}))
        for outcome in manifest.outcomes:
            with self.subTest(legacy_id=outcome.legacy_id):
                self.assertIn(outcome.status, ("imported", "quarantined"))
                if outcome.status == "quarantined":
                    self.assertTrue(outcome.reason)
                    self.assertEqual("", outcome.artifact_id)


class ReadOnlyTest(LegacyFixture):
    async def test_the_legacy_database_is_never_written(self) -> None:
        import hashlib

        start = SOURCE_TEXT.index(QUOTE)
        self.build(
            records=[
                legacy_source("src_a", SOURCE_TEXT, "https://cdc.example/a"),
                legacy_material("mat_a", "src_a", QUOTE, start, start + len(QUOTE)),
            ],
            bodies=self.standard_corpus(),
        )
        before = hashlib.sha256(self.legacy.read_bytes()).hexdigest()

        await self.run_import()

        self.assertEqual(before, hashlib.sha256(self.legacy.read_bytes()).hexdigest())
        # An immutable read must not leave sidecar files behind either.
        self.assertFalse(self.legacy.with_suffix(".sqlite3-wal").exists())
        self.assertFalse(self.legacy.with_suffix(".sqlite3-shm").exists())


if __name__ == "__main__":
    unittest.main()
