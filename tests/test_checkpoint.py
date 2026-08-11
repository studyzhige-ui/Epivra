from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

import aiosqlite
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from deep_research_agent.checkpoint import (
    CHECKPOINT_SCHEMA_VERSION,
    CheckpointVersionError,
    sqlite_checkpointer,
)
from deep_research_agent.state import ResearchContract, ResearchState


def approval_graph(checkpointer: object):
    def approval(state: ResearchState) -> ResearchState:
        response = interrupt({"type": "approval"})
        if response != "approve":
            raise ValueError("unexpected response")
        return {
            "research_contract": replace(
                state["research_contract"], approved=True
            ),
            "stage": "approved",
        }

    builder = StateGraph(ResearchState)
    builder.add_node("approval", approval)
    builder.add_edge(START, "approval")
    builder.add_edge("approval", END)
    return builder.compile(checkpointer=checkpointer)


class SqliteCheckpointTest(unittest.IsolatedAsyncioTestCase):
    async def test_interrupt_resumes_after_checkpointer_is_reopened(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "research.sqlite3"
            config = {"configurable": {"thread_id": "durable-thread"}}

            async with sqlite_checkpointer(database) as saver:
                graph = approval_graph(saver)
                paused = await graph.ainvoke(
                    {
                        "task_id": "durable-thread",
                        "question": "test",
                        "research_contract": ResearchContract("contract"),
                    },
                    config,
                )
                self.assertIn("__interrupt__", paused)

            async with sqlite_checkpointer(database) as saver:
                graph = approval_graph(saver)
                resumed = await graph.ainvoke(Command(resume="approve"), config)

            self.assertEqual("approved", resumed["stage"])
            self.assertTrue(resumed["research_contract"].approved)

    async def test_database_is_bound_to_runtime_schema_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "versioned.sqlite3"
            async with sqlite_checkpointer(database):
                pass
            async with aiosqlite.connect(database) as connection:
                cursor = await connection.execute("PRAGMA user_version")
                row = await cursor.fetchone()
                await cursor.close()
            self.assertEqual(CHECKPOINT_SCHEMA_VERSION, row[0])

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
