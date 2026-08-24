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

from deep_research_agent.agents import AgentProtocolError, AgentSpec, invoke_agent
from deep_research_agent.agents.lead import MemoryBody as LeadMemory
from deep_research_agent.agents.lead import make_validator as lead_make_validator
from deep_research_agent.agents.lead import memory_after
from deep_research_agent.content_store import SqliteContentStore
from deep_research_agent.context import RoleContext
from deep_research_agent.contract import build_contract
from deep_research_agent.model import (
    ModelProtocolError,
    ModelReply,
    ModelToolCall,
    ToolSpec,
)
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


class UntrustworthyReplyTest(unittest.IsolatedAsyncioTestCase):
    """A billed reply whose shape cannot be parsed earns one correction.

    ARCHITECTURE §8.2 calls for a bounded structural self-correction here, but the
    protocol error used to escape to the ledger's catch-all and freeze the
    operation for reconciliation -- permanently, since the fingerprint is
    deterministic.  The call really did happen and really was charged, so the
    honest record is a completed operation whose outcome is the failure, which is
    also what makes recovery replay the same verdict rather than pay again.
    """

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

    class Flaky:
        """Fails to produce a parseable reply once, then answers properly."""

        def __init__(self) -> None:
            self.calls = 0
            self.prompts: list[object] = []

        async def complete(self, messages, **_kwargs):  # noqa: ANN001, ANN202
            self.calls += 1
            self.prompts.append([dict(m) for m in messages])
            if self.calls == 1:
                raise ModelProtocolError("model returned neither content nor tool calls")
            return ModelReply(
                tool_calls=(
                    ModelToolCall(
                        call_id="t1",
                        name="submit",
                        arguments=json.dumps({"answer": "结论"}, ensure_ascii=False),
                    ),
                )
            )

    async def _run(self, model: object) -> object:
        return await invoke_agent(
            SPEC,
            CONTEXT,
            model=model,  # type: ignore[arg-type]
            ledger=self.ledger,
            task_id="task-1",
            execution=self.execution,
        )

    async def test_one_correction_recovers_without_freezing(self) -> None:
        model = self.Flaky()
        action = await self._run(model)

        self.assertEqual("submit", action.name)
        self.assertEqual(2, model.calls)
        # The correction is a plain turn: there is no trustworthy assistant
        # content to echo back, so none is fabricated.
        self.assertEqual("user", model.prompts[1][-1]["role"])
        # And nothing is waiting on a human.
        self.assertEqual((), await self.ledger.pending_reconciliation("task-1"))

    async def test_the_billed_call_is_recorded_as_completed(self) -> None:
        await self._run(self.Flaky())

        rows = await self._connection.execute_fetchall(
            "select status from operations where kind='model_call' order by rowid"
        )
        # Two operations, both settled: the unusable one is completed because it
        # happened and was paid for, not failed and not frozen.
        self.assertEqual(["completed", "completed"], [str(r[0]) for r in rows])

    async def test_a_second_unparseable_reply_pauses_instead_of_looping(self) -> None:
        class AlwaysBroken:
            calls = 0

            async def complete(self, _messages, **_kwargs):  # noqa: ANN001, ANN202
                type(self).calls += 1
                raise ModelProtocolError("model response has an invalid shape")

        with self.assertRaises(AgentProtocolError):
            await self._run(AlwaysBroken())
        self.assertEqual(2, AlwaysBroken.calls, "exactly one correction, then stop")


class BudgetNoticeTest(unittest.IsolatedAsyncioTestCase):
    """A role cannot see its own ceiling, so the runtime has to say so.

    Reaching the ceiling raises AgentToolBudgetExhausted and the branch keeps
    nothing -- not the summary, not the paths tried, not the limitations hit. A
    live regulatory-timepoint run lost seven assignments that way, on a topic
    where "the official text exists but this tooling cannot reach it" was the
    most valuable thing the run had established.
    """

    async def asyncSetUp(self) -> None:
        self._directory = tempfile.TemporaryDirectory()
        path = Path(self._directory.name) / "budget.sqlite3"
        self._connection = await aiosqlite.connect(path)
        content = SqliteContentStore(self._connection)
        await content.setup()
        self.ledger = SqliteOperationLedger(self._connection, content)
        await self.ledger.setup()

    async def asyncTearDown(self) -> None:
        await self._connection.close()
        self._directory.cleanup()

    async def test_the_role_is_warned_before_the_ceiling_and_can_still_submit(
        self,
    ) -> None:
        search = ToolSpec(
            name="search",
            description="检索。",
            parameters={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
                "additionalProperties": False,
            },
        )
        spec = AgentSpec(
            role="investigator",
            system_prompt="你是调查者。",
            tools=(search, SUBMIT),
            terminal_tools=frozenset({"submit"}),
            max_tool_turns=5,
        )

        seen_notices: list[str] = []

        class Searcher:
            """Searches forever unless told the budget is nearly gone."""

            def __init__(self) -> None:
                self.calls = 0

            async def complete(
                self,
                messages: Sequence[Mapping[str, Any]],
                *,
                        tools: Sequence[ToolSpec] = (),
                tool_choice: str | None = None,
            ) -> ModelReply:
                self.calls += 1
                notices = [
                    str(m.get("content", ""))
                    for m in messages
                    if m.get("role") == "user"
                    and "预算提示" in str(m.get("content", ""))
                ]
                if notices:
                    seen_notices.extend(notices[len(seen_notices) :])
                    return ModelReply(
                        tool_calls=(
                            ModelToolCall(
                                call_id="toolu_submit",
                                name="submit",
                                arguments=json.dumps(
                                    {"answer": "检索反复返回同类结果，如实交回。"},
                                    ensure_ascii=False,
                                ),
                            ),
                        )
                    )
                return ModelReply(
                    tool_calls=(
                        ModelToolCall(
                            call_id=f"toolu_search_{self.calls}",
                            name="search",
                            arguments=json.dumps({"query": "q"}, ensure_ascii=False),
                        ),
                    )
                )

        async def handle(name: str, arguments: Mapping[str, Any]) -> str:
            return "（本次检索没有返回结果）"

        action = await invoke_agent(
            spec,
            CONTEXT,
            model=Searcher(),
            ledger=self.ledger,
            task_id="task-1",
            execution=ExecutionIdentity(provider="scripted", model_id="test"),
            handlers={"search": handle},
        )

        self.assertEqual("submit", action.name)
        self.assertTrue(seen_notices, "the runtime must state the remaining budget")
        self.assertIn("工具回合", seen_notices[0])
        # Warned with turns left over, not at the moment it was already too late.
        self.assertIn("还剩", seen_notices[0])


class LeadMemoryTest(unittest.TestCase):
    """A correct governance decision must not die on a bookkeeping field.

    memory_snapshot is the largest thing the Lead emits, and it was required on
    every terminal action.  A live conflicting-primary-sources run chose
    commission_report -- the right call on 50 materials -- omitted the snapshot,
    got its one correction, omitted it again, and the whole run was lost.  That
    is the exact shape of the fifteen control-protocol failures this
    architecture was built to remove.

    Omission now means "unchanged", which is the only reading that is both
    unambiguous and safe: the previous memory is already durable, so carrying it
    forward loses nothing, while writing an empty one would leave the Lead
    governing with no record of what it had already tried.
    """

    PREVIOUS = LeadMemory(
        tried_paths=("Wave1 覆盖 Q1–Q3，仅得二手摘要",),
        decisions=("Wave2 定向探测条款级证据",),
        open_intents=("确认豁免门槛的精确数字",),
    )

    def test_a_supplied_snapshot_replaces_the_previous_memory(self) -> None:
        result = memory_after(
            {"memory_snapshot": {"tried_paths": ["新的一轮"], "decisions": []}},
            self.PREVIOUS,
        )
        self.assertEqual(("新的一轮",), result.tried_paths)
        self.assertEqual((), result.decisions)

    def test_an_omitted_snapshot_carries_the_previous_memory_forward(self) -> None:
        for arguments in ({}, {"memory_snapshot": None}, {"memory_snapshot": {}}):
            with self.subTest(arguments=arguments):
                self.assertEqual(self.PREVIOUS, memory_after(arguments, self.PREVIOUS))

    def test_an_omitted_snapshot_on_the_first_action_is_empty_not_an_error(
        self,
    ) -> None:
        self.assertEqual(LeadMemory(), memory_after({}, None))

    def test_no_terminal_action_is_rejected_for_omitting_the_snapshot(self) -> None:
        contract = build_contract(
            "Q1. 最低工资上调对就业的影响，研究结论之间存在哪些实质性冲突？\n"
        )
        validate = lead_make_validator(contract)
        error = validate(
            "commission_report",
            {
                "stop_rationale": "证据已合理穷尽，冲突根源已可归因。",
                "report_brief": "面向政策研究读者的系统综述，解释分歧根源。",
            },
        )
        self.assertIsNone(error)


class EmptyWaveTest(unittest.TestCase):
    """Refusing an action without naming the right one leaves nowhere to go.

    An empty wave is how the Lead reaches for "there is nothing left worth
    investigating".  The refusal used to state only that a wave needs an
    assignment, so a live regulatory-timepoint run submitted the empty wave,
    got that correction, submitted it again, and died with 183 Materials and
    three syntheses already committed.
    """

    CONTRACT = build_contract(
        "Q1. 截至 2026 年 8 月，中国 SaaS 公司将用户数据存于境外云服务，"
        "适用哪些数据出境合规要求？\n"
    )

    def test_an_empty_wave_is_told_which_action_does_mean_finished(self) -> None:
        error = lead_make_validator(self.CONTRACT)(
            "commission_wave", {"wave_intent": "无需进一步调查。", "assignments": []}
        )
        self.assertIsNotNone(error)
        self.assertIn("commission_report", error.allowed)

    def test_a_wave_with_an_assignment_is_accepted(self) -> None:
        error = lead_make_validator(self.CONTRACT)(
            "commission_wave",
            {
                "wave_intent": "确认现行有效的法规版本。",
                "assignments": [
                    {
                        "question_labels": ["Q1"],
                        "focus": "现行有效的数据出境法规与生效日期",
                        "why_it_matters": "决定全部后续义务的对象",
                        "evidence_sought": "官方发布的法规原文",
                    }
                ],
            },
        )
        self.assertIsNone(error)


if __name__ == "__main__":
    unittest.main()
