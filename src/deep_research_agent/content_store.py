"""Immutable, content-addressed storage for exact source bodies.

Large source text is deliberately kept outside LangGraph state.  Durable
artifacts carry only :class:`BodyRef`; agents hydrate a source at the narrow
runtime boundary where exact text is actually needed.
"""

from __future__ import annotations

from typing import Protocol

import aiosqlite

from .sources import BodyRef, content_digest


class ContentIntegrityError(RuntimeError):
    """Stored content is missing, corrupt, or inconsistent with its reference."""


class ContentReader(Protocol):
    """Read exact immutable content by its durable reference."""

    async def get(self, ref: BodyRef) -> str:
        """Return and verify the complete body."""

class ContentStore(ContentReader, Protocol):
    """Store exact immutable content once and return its durable reference."""

    async def put(self, content: str) -> BodyRef:
        """Persist content idempotently and return its content-addressed ref."""


def _verify_content(ref: BodyRef, content: str) -> str:
    if not isinstance(content, str):
        raise ContentIntegrityError("stored content is not UTF-8 text")
    if len(content) != ref.char_count:
        raise ContentIntegrityError(
            f"content length mismatch for {ref.content_hash}: expected "
            f"{ref.char_count}, found {len(content)}"
        )
    try:
        actual_hash = content_digest(content)
    except ValueError as exc:
        raise ContentIntegrityError(
            f"stored content for {ref.content_hash} is empty or invalid"
        ) from exc
    if actual_hash != ref.content_hash:
        raise ContentIntegrityError(
            f"content digest mismatch for {ref.content_hash}: found {actual_hash}"
        )
    return content


class InMemoryContentStore:
    """Small deterministic ContentStore for tests and ephemeral runtimes."""

    def __init__(self) -> None:
        self._content: dict[str, str] = {}

    async def put(self, content: str) -> BodyRef:
        ref = BodyRef.from_content(content)
        existing = self._content.get(ref.content_hash)
        if existing is not None and existing != content:
            raise ContentIntegrityError(
                f"content hash collision for {ref.content_hash}"
            )
        self._content.setdefault(ref.content_hash, content)
        return ref

    async def get(self, ref: BodyRef) -> str:
        content = self._content.get(ref.content_hash)
        if content is None:
            raise ContentIntegrityError(f"content {ref.content_hash} is missing")
        return _verify_content(ref, content)


class SqliteContentStore:
    """ContentStore sharing the runtime's existing aiosqlite connection."""

    def __init__(self, connection: aiosqlite.Connection) -> None:
        self._connection = connection

    async def setup(self) -> None:
        """Create only the independent immutable-body table."""

        await self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS content_blobs (
                hash TEXT PRIMARY KEY,
                char_count INTEGER NOT NULL CHECK (char_count > 0),
                content TEXT NOT NULL
            )
            """
        )
        await self._connection.commit()

    async def put(self, content: str) -> BodyRef:
        ref = BodyRef.from_content(content)
        await self._connection.execute(
            """
            INSERT INTO content_blobs(hash, char_count, content)
            VALUES (?, ?, ?)
            ON CONFLICT(hash) DO NOTHING
            """,
            (ref.content_hash, ref.char_count, content),
        )
        await self._connection.commit()
        stored_count, stored_content = await self._row(ref.content_hash)
        if stored_count != ref.char_count or stored_content != content:
            raise ContentIntegrityError(
                f"content hash collision or corrupt row for {ref.content_hash}"
            )
        _verify_content(ref, stored_content)
        return ref

    async def get(self, ref: BodyRef) -> str:
        stored_count, content = await self._row(ref.content_hash)
        if stored_count != ref.char_count:
            raise ContentIntegrityError(
                f"stored char_count mismatch for {ref.content_hash}: expected "
                f"{ref.char_count}, found {stored_count}"
            )
        return _verify_content(ref, content)

    async def _row(self, content_hash: str) -> tuple[int, str]:
        cursor = await self._connection.execute(
            "SELECT char_count, content FROM content_blobs WHERE hash = ?",
            (content_hash,),
        )
        row = await cursor.fetchone()
        await cursor.close()
        if row is None:
            raise ContentIntegrityError(f"content {content_hash} is missing")
        count, content = row
        if isinstance(content, bytes):
            try:
                content = content.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ContentIntegrityError(
                    f"stored content for {content_hash} is not UTF-8"
                ) from exc
        if isinstance(count, bool) or not isinstance(count, int):
            raise ContentIntegrityError(
                f"stored char_count for {content_hash} is invalid"
            )
        if not isinstance(content, str):
            raise ContentIntegrityError(f"stored content for {content_hash} is invalid")
        return count, content


__all__ = [
    "ContentIntegrityError",
    "ContentReader",
    "ContentStore",
    "InMemoryContentStore",
    "SqliteContentStore",
]
