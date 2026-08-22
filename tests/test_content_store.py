from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import aiosqlite

from deep_research_agent.content_store import (
    ContentIntegrityError,
    InMemoryContentStore,
    SqliteContentStore,
)
from deep_research_agent.sources import (
    BodyRef,
    SourceAnchor,
    locate_quote,
    validate_anchor,
)


class InMemoryContentStoreTest(unittest.IsolatedAsyncioTestCase):
    async def test_put_is_idempotent_and_returns_exact_unicode_text(self) -> None:
        store = InMemoryContentStore()
        content = "研究证据🙂\nsecond line"

        first = await store.put(content)
        second = await store.put(content)

        self.assertEqual(first, second)
        self.assertEqual(len(content), first.char_count)
        self.assertEqual(content, await store.get(first))

    async def test_missing_and_corrupt_content_fail_explicitly(self) -> None:
        store = InMemoryContentStore()
        ref = BodyRef.from_content("expected")
        with self.assertRaisesRegex(ContentIntegrityError, "missing"):
            await store.get(ref)

        store._content[ref.content_hash] = "tampered"  # noqa: SLF001
        with self.assertRaisesRegex(ContentIntegrityError, "mismatch"):
            await store.get(ref)

    async def test_stored_text_can_be_anchored_after_retrieval(self) -> None:
        store = InMemoryContentStore()
        ref = await store.put("Before exact evidence after.")

        text = await store.get(ref)
        locator = locate_quote(text, "exact evidence")
        anchor = SourceAnchor(
            source_ref="src_000000000000000000000001",
            exact_quote="exact evidence",
            locator=locator,
        )
        validate_anchor(anchor, text)

        self.assertEqual(7, locator.start)
        self.assertEqual("exact evidence", text[locator.start : locator.end])

class SqliteContentStoreTest(unittest.IsolatedAsyncioTestCase):
    async def test_put_if_absent_persists_one_verified_row(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "content.sqlite3"
            async with aiosqlite.connect(database) as connection:
                store = SqliteContentStore(connection)
                await store.setup()
                content = "one immutable source body"

                first = await store.put(content)
                second = await store.put(content)
                cursor = await connection.execute("SELECT COUNT(*) FROM content_blobs")
                row = await cursor.fetchone()
                await cursor.close()

                self.assertEqual(first, second)
                self.assertEqual(1, row[0])
                self.assertEqual(content, await store.get(first))

    async def test_corrupt_row_and_conflicting_put_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "content.sqlite3"
            async with aiosqlite.connect(database) as connection:
                store = SqliteContentStore(connection)
                await store.setup()
                ref = BodyRef.from_content("trusted")
                await connection.execute(
                    "INSERT INTO content_blobs(hash, char_count, content) VALUES (?, ?, ?)",
                    (ref.content_hash, ref.char_count, "corrupt"),
                )
                await connection.commit()

                with self.assertRaisesRegex(ContentIntegrityError, "collision|corrupt"):
                    await store.put("trusted")
                with self.assertRaises(ContentIntegrityError):
                    await store.get(ref)

    async def test_missing_body_is_not_silently_refetched(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "content.sqlite3"
            async with aiosqlite.connect(database) as connection:
                store = SqliteContentStore(connection)
                await store.setup()
                ref = BodyRef.from_content("not stored")

                with self.assertRaisesRegex(ContentIntegrityError, "missing"):
                    await store.get(ref)


if __name__ == "__main__":
    unittest.main()
