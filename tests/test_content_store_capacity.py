from __future__ import annotations

import json
import tempfile
import unittest
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from deep_research_agent.checkpoint import sqlite_runtime_storage
from deep_research_agent.model import (
    ModelReply,
    ModelToolCall,
    ToolSpec,
    hydrate_durable_tool_messages,
)
from deep_research_agent.researcher import (
    build_researcher_subgraph,
    researcher_output_from_subgraph,
    researcher_subgraph_input,
)
from deep_research_agent.roles import ResearcherContext
from deep_research_agent.state import ResearchContract, ResearchTask
from deep_research_agent.tools import (
    ProviderInfo,
    ProviderResult,
    ReadResult,
    TransparentSearchBroker,
)


def _tool_call(call_id: str, name: str, arguments: Mapping[str, Any]) -> ModelReply:
    return ModelReply(
        tool_calls=(
            ModelToolCall(
                call_id,
                name,
                json.dumps(arguments, ensure_ascii=False),
            ),
        )
    )


class _DuplicateBodyProvider:
    provider_id = "capacity-provider"

    def __init__(self, body: str) -> None:
        self._body = body

    async def describe(self) -> ProviderInfo:
        return ProviderInfo(self.provider_id, ("search", "raw_content"))

    async def search(self, *, query: str, intent: str, source_kind: str):
        del query, intent, source_kind
        return (
            ProviderResult(
                title="Primary publication",
                url="https://capacity.example/primary",
                snippet="Bounded search preview.",
                content=self._body,
            ),
            ProviderResult(
                title="Republished copy",
                url="https://capacity.example/republication",
                snippet="The same exact body at another source URL.",
                content=self._body,
            ),
        )


class _UnusedReader:
    async def read(self, url: str) -> ReadResult:
        raise AssertionError(f"the capacity scenario must not read {url}")


class _InspectingModel:
    """Drive one real Researcher subgraph without an external model API."""

    def __init__(self, forbidden_sentinel: str = "") -> None:
        self._turn = 0
        self._candidate_ids: tuple[str, ...] = ()
        self.saw_forbidden_sentinel = False
        self._forbidden_sentinel = forbidden_sentinel

    async def complete(
        self,
        messages: Sequence[Mapping[str, Any]],
        *,
        json_output: bool = False,
        tools: Sequence[ToolSpec] = (),
        tool_choice: str | None = None,
    ) -> ModelReply:
        del json_output, tools, tool_choice
        self._turn += 1
        if self._forbidden_sentinel and self._forbidden_sentinel in str(messages):
            self.saw_forbidden_sentinel = True
        if self._turn == 1:
            return _tool_call(
                "search",
                "search",
                {
                    "query": "capacity regression evidence",
                    "intent": "exercise durable candidate storage",
                    "source_kind": "web",
                },
            )
        if self._turn == 2:
            observation = json.loads(str(messages[-1]["content"]))
            self._candidate_ids = tuple(
                result["candidate_id"] for result in observation["results"]
            )
            return _tool_call(
                "inspect-0",
                "inspect_candidate",
                {"candidate_id": self._candidate_ids[0], "offset": 0},
            )
        if self._turn in {3, 4, 5}:
            offset = (self._turn - 2) * 8_000
            candidate_index = 1 if self._turn == 5 else 0
            return _tool_call(
                f"inspect-{self._turn - 2}",
                "inspect_candidate",
                {
                    "candidate_id": self._candidate_ids[candidate_index],
                    "offset": offset,
                },
            )
        if self._turn == 6:
            return _tool_call(
                "save-primary",
                "save_source",
                {"candidate_id": self._candidate_ids[0]},
            )
        if self._turn == 7:
            return _tool_call(
                "save-republication",
                "save_source",
                {"candidate_id": self._candidate_ids[1]},
            )
        if self._turn == 8:
            return _tool_call(
                "finish",
                "finish_turn",
                {"summary": "Inspected the bounded pages and saved both sources."},
            )
        raise AssertionError("the scripted Researcher should already be finished")


@dataclass(frozen=True)
class _RunMetrics:
    database_bytes: int
    serialized_bytes: int
    checkpoint_rows: int
    write_rows: int
    content_rows: int
    stored_chars: int
    source_count: int
    body_hash_count: int


def _as_bytes(value: object) -> bytes:
    if value is None:
        return b""
    if isinstance(value, bytes):
        return value
    if isinstance(value, memoryview):
        return value.tobytes()
    if isinstance(value, str):
        return value.encode("utf-8")
    raise AssertionError(f"unexpected serialized SQLite value: {type(value)!r}")


def _context() -> ResearcherContext:
    return ResearcherContext(
        task=ResearchTask("capacity-branch", "Exercise exact source persistence."),
        contract=ResearchContract(
            "Inspect and save the supplied source bodies.", approved=True
        ),
        guide_text="",
        branch_journal=(),
        relevant_sources={},
    )


async def _serialized_checkpoint_values(connection: Any) -> list[bytes]:
    values: list[bytes] = []
    selections = {
        "checkpoints": ("checkpoint", "metadata"),
        "writes": ("value", "blob"),
    }
    for table, possible_columns in selections.items():
        cursor = await connection.execute(f"PRAGMA table_info({table})")
        available = {row[1] for row in await cursor.fetchall()}
        await cursor.close()
        columns = tuple(column for column in possible_columns if column in available)
        if not columns:
            raise AssertionError(f"{table} has no serialized payload column")
        statement = f"SELECT {', '.join(columns)} FROM {table}"
        cursor = await connection.execute(statement)
        rows = await cursor.fetchall()
        await cursor.close()
        values.extend(_as_bytes(value) for row in rows for value in row)
    return values


class ContentStoreCapacityTest(unittest.IsolatedAsyncioTestCase):
    async def _run_researcher(
        self, database: Path, body: str, *, forbidden_sentinel: str = ""
    ) -> _RunMetrics:
        async with sqlite_runtime_storage(database) as storage:
            model = _InspectingModel(forbidden_sentinel)
            graph = build_researcher_subgraph(
                model,
                TransparentSearchBroker([_DuplicateBodyProvider(body)]),
                _UnusedReader(),
                content_store=storage.content_store,
                checkpointer=storage.checkpointer,
            )
            state = await graph.ainvoke(
                researcher_subgraph_input(_context()),
                {
                    "configurable": {"thread_id": database.stem},
                    "recursion_limit": 64,
                },
            )
            output = researcher_output_from_subgraph(state)

            first_ref = await storage.content_store.put(body)
            second_ref = await storage.content_store.put(body)
            self.assertEqual(first_ref, second_ref)

            connection = storage.checkpointer.conn
            cursor = await connection.execute(
                """
                SELECT COUNT(*), COALESCE(SUM(char_count), 0),
                       COUNT(DISTINCT hash)
                FROM content_blobs
                """
            )
            content_rows, stored_chars, body_hash_count = await cursor.fetchone()
            await cursor.close()

            cursor = await connection.execute("SELECT COUNT(*) FROM checkpoints")
            checkpoint_rows = (await cursor.fetchone())[0]
            await cursor.close()
            cursor = await connection.execute("SELECT COUNT(*) FROM writes")
            write_rows = (await cursor.fetchone())[0]
            await cursor.close()

            serialized_values = await _serialized_checkpoint_values(connection)
            if forbidden_sentinel:
                sentinel = forbidden_sentinel.encode("utf-8")
                self.assertTrue(sentinel)
                self.assertTrue(all(sentinel not in value for value in serialized_values))
                self.assertTrue(model.saw_forbidden_sentinel)

            body_refs = {source.body_ref for source in output.sources.values()}
            self.assertEqual(2, len(output.sources))
            self.assertEqual({first_ref}, body_refs)
            self.assertGreaterEqual(checkpoint_rows, 10)
            self.assertGreater(write_rows, 0)

            serialized_bytes = sum(len(value) for value in serialized_values)

            durable_messages = state["messages"]

        if forbidden_sentinel:
            self.assertNotIn(forbidden_sentinel, str(durable_messages))
            async with sqlite_runtime_storage(database) as reopened:
                hydrated = await hydrate_durable_tool_messages(
                    durable_messages, reopened.content_store
                )
            self.assertIn(forbidden_sentinel, str(hydrated))

        return _RunMetrics(
            database_bytes=database.stat().st_size,
            serialized_bytes=serialized_bytes,
            checkpoint_rows=checkpoint_rows,
            write_rows=write_rows,
            content_rows=content_rows,
            stored_chars=stored_chars,
            source_count=len(output.sources),
            body_hash_count=body_hash_count,
        )

    async def test_large_body_is_stored_once_outside_repeated_checkpoints(
        self,
    ) -> None:
        inspected_prefix = "P" * 8_100
        small_body = inspected_prefix + "|small-body-tail|" + "P" * 31_900
        sentinel = "|UNINSPECTED-LARGE-BODY-SENTINEL-7c2f81b4|"
        large_body = inspected_prefix + sentinel
        large_body += "Q" * (200_000 - len(large_body))

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            small = await self._run_researcher(root / "small.sqlite3", small_body)
            large = await self._run_researcher(
                root / "large.sqlite3",
                large_body,
                forbidden_sentinel=sentinel,
            )

        self.assertEqual(1, large.content_rows)
        self.assertEqual(1, large.body_hash_count)
        self.assertEqual(len(large_body), large.stored_chars)
        self.assertEqual(2, large.source_count)
        self.assertEqual(small.checkpoint_rows, large.checkpoint_rows)
        self.assertEqual(small.write_rows, large.write_rows)

        body_growth = len(large_body) - len(small_body)
        checkpoint_growth = abs(large.serialized_bytes - small.serialized_bytes)
        database_growth = large.database_bytes - small.database_bytes
        self.assertGreater(body_growth, 150_000)
        self.assertLess(checkpoint_growth, 16_384)
        self.assertLessEqual(abs(database_growth - body_growth), 65_536)


if __name__ == "__main__":
    unittest.main()
