"""The runner's identity rules, tested where they are cheapest to break.

The ledger's whole value is that it replays a completed call instead of paying
for it twice.  That makes "what counts as the same call" a correctness question:
too narrow and the system double-charges, too broad and it serves a stale answer
that looks exactly like a fresh one.  The tests here pin the second failure,
which is the quiet one.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from collections.abc import Mapping, Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

import aiosqlite

from deep_research_agent.agents import AgentSpec, invoke_agent
from deep_research_agent.content_store import SqliteContentStore
from deep_research_agent.context import RoleContext
from deep_research_agent.model import ModelReply, ModelToolCall, ToolSpec
from deep_research_agent.operations import ExecutionIdentity, SqliteOperationLedger

SUBMIT = ToolSpec(
    name="submit",
    description="提交结论。",
    parameters={
        "type": "object",
        "properties": {"answer": {"type": "string"}},
        "required": ["answer"],
        "additionalProperties": False,
    },
)

SPEC = AgentSpec(
    role="analyst",
    system_prompt="你是分析者。只做一件事：提交结论。",
    tools=(SUBMIT,),
    terminal_tools=frozenset({"submit"}),
)

CONTEXT = RoleContext(
    role="analyst",
    purpose="在给定素材上得出结论",
    body="## 素材\n\n一条素材。\n",
    input_refs=("mat_1",),
)


class CountingModel:
    """Returns a fixed answer and counts how often it was actually called."""

    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.calls = 0

    async def complete(
        self,
        messages: Sequence[Mapping[str, Any]],
        *,
        json_output: bool = False,
        tools: Sequence[ToolSpec] = (),
        tool_choice: str | None = None,
    ) -> ModelReply:
        self.calls += 1
        return ModelReply(
            tool_calls=(
                ModelToolCall(
                    call_id="toolu_submit",
                    name="submit",
                    arguments=json.dumps({"answer": self.answer}, ensure_ascii=False),
                ),
            )
        )


class SpecDigestTest(unittest.TestCase):
    def test_editing_the_prompt_changes_the_spec_digest(self) -> None:
        edited = replace(SPEC, system_prompt=SPEC.system_prompt + "\n再加一句要求。")
        self.assertNotEqual(SPEC.digest, edited.digest)

    def test_editing_a_tool_schema_changes_the_spec_digest(self) -> None:
        widened = replace(
            SPEC,
            tools=(
                replace(
                    SUBMIT,
                    parameters={
                        "type": "object",
                        "properties": {
                            "answer": {"type": "string"},
                            "certainty": {"type": "string"},
                        },
                        "required": ["answer", "certainty"],
                        "additionalProperties": False,
                    },
                ),
            ),
        )
        self.assertNotEqual(SPEC.digest, widened.digest)

    def test_an_unchanged_spec_keeps_its_digest(self) -> None:
        self.assertEqual(SPEC.digest, replace(SPEC).digest)


class ReplayScopeTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._directory = tempfile.TemporaryDirectory()
        path = Path(self._directory.name) / "runner.sqlite3"
        self._connection = await aiosqlite.connect(path)
        content = SqliteContentStore(self._connection)
        await content.setup()
        self.ledger = SqliteOperationLedger(self._connection, content)
        await self.ledger.setup()
        self.execution = ExecutionIdentity(provider="scripted", model_id="test")

    async def asyncTearDown(self) -> None:
        await self._connection.close()
        self._directory.cleanup()

    async def _run(self, spec: AgentSpec, model: CountingModel) -> str:
        action = await invoke_agent(
            spec,
            CONTEXT,
            model=model,
            ledger=self.ledger,
            task_id="task-1",
            execution=self.execution,
        )
        return str(action.arguments["answer"])

    async def test_the_same_call_replays_instead_of_paying_twice(self) -> None:
        first = CountingModel("原始结论")
        self.assertEqual("原始结论", await self._run(SPEC, first))

        second = CountingModel("不应该被调用")
        self.assertEqual("原始结论", await self._run(SPEC, second))
        self.assertEqual(1, first.calls)
        self.assertEqual(0, second.calls, "an identical call must replay, not re-send")

    async def test_an_edited_prompt_is_different_work_and_runs_again(self) -> None:
        """Calibration edits prompts and re-runs; replay would hide the edit.

        Without the spec in the operation's identity this returned the previous
        wording's answer while reporting success, so a prompt fix would look
        like it had changed nothing -- indistinguishable from a fix that was
        genuinely ineffective.
        """

        original = CountingModel("旧提示词的结论")
        self.assertEqual("旧提示词的结论", await self._run(SPEC, original))

        edited_spec = replace(
            SPEC, system_prompt=SPEC.system_prompt + "\n另外：先说明证据边界。"
        )
        revised = CountingModel("新提示词的结论")
        self.assertEqual("新提示词的结论", await self._run(edited_spec, revised))
        self.assertEqual(1, revised.calls)

        rows = await self._connection.execute_fetchall(
            "select count(*) from operations where kind='model_call'"
        )
        self.assertEqual(2, rows[0][0], "the edit must open a second operation")


if __name__ == "__main__":
    unittest.main()
