"""Safe checkpoint factories for one research thread's durable state."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from typing import BinaryIO

import aiosqlite
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver


CHECKPOINT_SCHEMA_VERSION = 1


class CheckpointVersionError(RuntimeError):
    """A durable task belongs to an incompatible runtime schema."""


class CheckpointWriterBusyError(RuntimeError):
    """Another local process already owns the database's writer lease."""


_STATE_TYPES = (
    "Amendment",
    "AssuranceEvent",
    "BranchHandoff",
    "CuratedMaterial",
    "JournalEntry",
    "ResearchContract",
    "ResearchSynthesis",
    "ResearchTask",
    "SourceAnchor",
    "SourceDocument",
    "TextLocator",
    "ValidationFinding",
)


def research_serializer() -> JsonPlusSerializer:
    """Allow only this package's explicit durable dataclasses.

    Pickle fallback is intentionally disabled.  The allowlist avoids the
    permissive future-compatibility path warned about by LangGraph while still
    preserving typed artifacts across an interrupt.
    """

    allowed = [("deep_research_agent.state", name) for name in _STATE_TYPES]
    return JsonPlusSerializer(
        pickle_fallback=False,
        allowed_msgpack_modules=allowed,
    )


def memory_checkpointer() -> InMemorySaver:
    """Create an offline/test checkpointer with the production serializer."""

    return InMemorySaver(serde=research_serializer())


def _lock_writer_file(handle: BinaryIO) -> None:
    handle.seek(0)
    if not handle.read(1):
        handle.seek(0)
        handle.write(b"\0")
        handle.flush()
    handle.seek(0)
    try:
        import msvcrt
    except ImportError:  # pragma: no cover - exercised on non-Windows runtimes
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    else:
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)


def _unlock_writer_file(handle: BinaryIO) -> None:
    handle.seek(0)
    try:
        import msvcrt
    except ImportError:  # pragma: no cover - exercised on non-Windows runtimes
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    else:
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


@contextmanager
def sqlite_writer_lock(database_path: str | Path) -> Iterator[None]:
    """Enforce one modifying process per local SQLite checkpoint database."""

    path = Path(database_path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(path.name + ".writer.lock")
    handle = lock_path.open("a+b")
    try:
        try:
            _lock_writer_file(handle)
        except OSError as exc:
            raise CheckpointWriterBusyError(
                f"checkpoint database {path} already has an active writer"
            ) from exc
        try:
            yield
        finally:
            _unlock_writer_file(handle)
    finally:
        handle.close()


async def _checkpoint_schema_version(connection: aiosqlite.Connection) -> int:
    cursor = await connection.execute("PRAGMA user_version")
    row = await cursor.fetchone()
    await cursor.close()
    return int(row[0]) if row else 0


@asynccontextmanager
async def sqlite_checkpointer(
    database_path: str | Path,
) -> AsyncIterator[AsyncSqliteSaver]:
    """Open and initialize a SQLite checkpointer for one local runtime.

    The caller controls the lifecycle and chooses the explicit database path.
    This function never deletes, migrates, or searches for databases.
    """

    path = Path(database_path).expanduser().resolve()
    if path.exists() and path.is_dir():
        raise ValueError("database_path must name a SQLite file, not a directory")
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = await aiosqlite.connect(str(path))
    version = await _checkpoint_schema_version(connection)
    if version not in {0, CHECKPOINT_SCHEMA_VERSION}:
        await connection.close()
        raise CheckpointVersionError(
            f"checkpoint schema {version} is incompatible with runtime schema "
            f"{CHECKPOINT_SCHEMA_VERSION}"
        )
    saver = AsyncSqliteSaver(connection, serde=research_serializer())
    await saver.setup()
    if version == 0:
        await connection.execute(
            f"PRAGMA user_version = {CHECKPOINT_SCHEMA_VERSION}"
        )
        await connection.commit()
    try:
        yield saver
    finally:
        await connection.close()


@asynccontextmanager
async def readonly_sqlite_checkpointer(
    database_path: str | Path,
) -> AsyncIterator[AsyncSqliteSaver]:
    """Open an existing checkpoint database without creating or setting it up."""

    path = Path(database_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    connection = await aiosqlite.connect(f"{path.as_uri()}?mode=ro", uri=True)
    version = await _checkpoint_schema_version(connection)
    if version != CHECKPOINT_SCHEMA_VERSION:
        await connection.close()
        raise CheckpointVersionError(
            f"checkpoint schema {version} is incompatible with runtime schema "
            f"{CHECKPOINT_SCHEMA_VERSION}"
        )
    saver = AsyncSqliteSaver(connection, serde=research_serializer())
    try:
        yield saver
    finally:
        await connection.close()


__all__ = [
    "CHECKPOINT_SCHEMA_VERSION",
    "CheckpointVersionError",
    "CheckpointWriterBusyError",
    "memory_checkpointer",
    "readonly_sqlite_checkpointer",
    "research_serializer",
    "sqlite_checkpointer",
    "sqlite_writer_lock",
]
