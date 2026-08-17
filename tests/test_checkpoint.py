from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
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
from deep_research_agent.content_store import SqliteContentStore, hydrate_source
from deep_research_agent.state import ResearchContract, SourceDocument


class ApprovalState(TypedDict, total=False):
    """Minimal durable state for exercising interrupt/resume round-trips."""

    task_id: str
    question: str
    stage: str
    research_contract: ResearchContract
    source_corpus: dict[str, SourceDocument]


def approval_graph(checkpointer: object):
    def approval(state: ApprovalState) -> ApprovalState:
        response = interrupt({"type": "approval"})
        if response != "approve":
            raise ValueError("unexpected response")
        return {
            "research_contract": replace(
                state["research_contract"], approved=True
            ),
            "stage": "approved",
        }

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
                source = SourceDocument.create(
                    title="Durable source",
                    url="https://example.com/source",
                    body_ref=body_ref,
                )
                paused = await graph.ainvoke(
                    {
                        "task_id": "durable-thread",
                        "question": "test",
                        "research_contract": ResearchContract("contract"),
                        "source_corpus": {source.source_id: source},
                    },
                    config,
                )
                self.assertIn("__interrupt__", paused)

            async with sqlite_checkpointer(database) as saver:
                graph = approval_graph(saver)
                resumed = await graph.ainvoke(Command(resume="approve"), config)
                content_store = SqliteContentStore(saver.conn)
                restored_source = resumed["source_corpus"][source.source_id]
                hydrated = await hydrate_source(restored_source, content_store)

            self.assertEqual("approved", resumed["stage"])
            self.assertTrue(resumed["research_contract"].approved)
            self.assertEqual(body_ref, restored_source.body_ref)
            self.assertFalse(hasattr(restored_source, "content"))
            self.assertEqual(
                "Exact source text must live outside graph state.", hydrated.content
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
