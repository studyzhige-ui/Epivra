from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import TypedDict

import aiosqlite
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from deep_research_agent.checkpoint import (
    CHECKPOINT_SCHEMA_VERSION,
    CheckpointVersionError,
    readonly_sqlite_runtime_storage,
    sqlite_checkpointer,
    sqlite_runtime_storage,
)
from deep_research_agent.content_store import SqliteContentStore
from deep_research_agent.sources import SourceSnapshotBody


class ApprovalState(TypedDict, total=False):
    """Minimal durable state for exercising interrupt/resume round-trips."""

    task_id: str
    approved: bool
    sources: dict[str, SourceSnapshotBody]


def approval_graph(checkpointer: object):
    def approval(_state: ApprovalState) -> ApprovalState:
        response = interrupt({"type": "approval"})
        if response != "approve":
            raise ValueError("unexpected response")
        return {"approved": True}

    builder = StateGraph(ApprovalState)
    builder.add_node("approval", approval)
    builder.add_edge(START, "approval")
    builder.add_edge("approval", END)
    return builder.compile(checkpointer=checkpointer)


class SqliteCheckpointTest(unittest.IsolatedAsyncioTestCase):
    async def test_runtime_storage_shares_connection_and_reopens_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "shared.sqlite3"
            async with sqlite_runtime_storage(database) as storage:
                self.assertIs(
                    storage.checkpointer.conn,
                    storage.content_store._connection,  # noqa: SLF001
                )
                body_ref = await storage.content_store.put("shared exact body")

            async with readonly_sqlite_runtime_storage(database) as storage:
                self.assertEqual(
                    "shared exact body", await storage.content_store.get(body_ref)
                )

    async def test_interrupt_resumes_after_checkpointer_is_reopened(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "research.sqlite3"
            config = {"configurable": {"thread_id": "durable-thread"}}

            async with sqlite_checkpointer(database) as saver:
                graph = approval_graph(saver)
                content_store = SqliteContentStore(saver.conn)
                body_ref = await content_store.put(
                    "Exact source text must live outside graph state."
                )
                source = SourceSnapshotBody(
                    title="Durable source",
                    url="https://example.com/source",
                    text_ref=body_ref,
                )
                paused = await graph.ainvoke(
                    {
                        "task_id": "durable-thread",
                        "sources": {"src_a": source},
                    },
                    config,
                )
                self.assertIn("__interrupt__", paused)

            async with sqlite_checkpointer(database) as saver:
                graph = approval_graph(saver)
                resumed = await graph.ainvoke(Command(resume="approve"), config)
                content_store = SqliteContentStore(saver.conn)
                restored = resumed["sources"]["src_a"]
                text = await content_store.get(restored.text_ref)

            self.assertTrue(resumed["approved"])
            self.assertEqual(body_ref, restored.text_ref)
            # Exact text never entered graph state; only its reference survived.
            self.assertFalse(hasattr(restored, "content"))
            self.assertEqual(
                "Exact source text must live outside graph state.", text
            )

    async def test_database_is_bound_to_runtime_schema_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "versioned.sqlite3"
            async with sqlite_checkpointer(database):
                pass
            async with aiosqlite.connect(database) as connection:
                cursor = await connection.execute("PRAGMA user_version")
                row = await cursor.fetchone()
                await cursor.close()
                cursor = await connection.execute(
                    "SELECT name FROM sqlite_master WHERE name = 'content_blobs'"
                )
                content_table = await cursor.fetchone()
                await cursor.close()
            self.assertEqual(CHECKPOINT_SCHEMA_VERSION, row[0])
            self.assertEqual("content_blobs", content_table[0])

    async def test_incompatible_checkpoint_schema_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "future.sqlite3"
            async with aiosqlite.connect(database) as connection:
                await connection.execute("PRAGMA user_version = 999")
                await connection.commit()

            with self.assertRaises(CheckpointVersionError):
                async with sqlite_checkpointer(database):
                    pass


if __name__ == "__main__":
    unittest.main()
