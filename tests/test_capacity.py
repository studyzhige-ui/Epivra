"""The capacity red line: fail before the call, never trim the basis.

ARCHITECTURE §8.3 has always said the only permitted capacity behaviour is
failure, but the check had **zero callers** -- so overflow actually surfaced as a
vendor 400, which the ledger read as "provably not executed", retried to its
budget, and left as a dead task whose error named nothing useful.

Two properties matter here and they are easy to conflate.  The first is that the
check exists at all.  The second is *where*: it runs before every provider call
against the whole outgoing request, because a tool loop grows.  The opening
context is not the largest thing the runner ever sends -- a Curator reading
twelve thousand characters per call across twenty-four turns accumulates far
more -- and a check that only saw the opening projection would miss the role most
likely to overflow.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import aiosqlite
import httpx

from deep_research_agent.agents import AgentSpec, invoke_agent
from deep_research_agent.content_store import SqliteContentStore
from deep_research_agent.context import (
    ContextCapacityError,
    RoleContext,
    estimate_tokens,
    require_fits,
)
from deep_research_agent.model import (
    CAPACITY_FAILURES,
    MODEL_FAILURES,
    ModelContextOverflow,
    ModelReply,
    ModelRequestRejected,
    ModelToolCall,
    OpenAICompatibleClient,
    ToolSpec,
)
from deep_research_agent.operations import ExecutionIdentity, SqliteOperationLedger


class EstimateTest(unittest.TestCase):
    """The estimate must lean high, because leaning low defeats the purpose."""

    def test_chinese_costs_more_per_character_than_english(self) -> None:
        chinese_text = "证据不足时应当限定结论" * 100
        english_text = "evidence is insufficient here" * 100
        chinese = estimate_tokens(chinese_text) / len(chinese_text)
        english = estimate_tokens(english_text) / len(english_text)
        self.assertGreater(chinese, english * 2)
        self.assertGreaterEqual(chinese, 1.0)
        self.assertLess(english, 0.5)

    def test_the_measured_reviewer_basis_lands_near_its_real_cost(self) -> None:
        """Calibrated against the largest real basis: 121,978 chars, 80% CJK."""

        text = "研究证据的边界与冲突解释" * 8_133 + "evidence boundary " * 1_315
        estimate = estimate_tokens(text)
        self.assertGreater(estimate, 90_000)
        self.assertLess(estimate, 130_000)

    def test_an_empty_string_costs_nothing(self) -> None:
        self.assertEqual(0, estimate_tokens(""))

    def test_a_basis_known_to_fit_is_not_blocked(self) -> None:
        """The calibration guard, and the reason it exists.

        A first attempt at this estimator leaned high on the theory that
        over-estimating "fails safe".  It does not.  The largest real basis in the
        calibration corpus -- a 198-material Reviewer context of 121,978 characters,
        97,670 of them CJK -- ran on a 128k-window vendor and published, so any
        estimate that rejects it is simply wrong, and shipping one would have
        blocked research that demonstrably works.

        Over-estimating is not the safe direction here because the residual case
        has its own handling: a vendor that refuses an oversized request is now
        classified as a capacity failure, so the gap this calibration leaves open
        pauses readably instead of retrying to death.
        """

        basis = "研究证据的边界与冲突解释" * 8_140 + "evidence boundary " * 1_350
        self.assertGreater(len(basis), 120_000)
        require_fits("reviewer", basis, limit=128_000)


class RedLineTest(unittest.TestCase):
    def test_an_oversized_basis_is_refused_with_an_actionable_message(self) -> None:
        with self.assertRaises(ContextCapacityError) as raised:
            require_fits("reviewer", "证据" * 100_000, limit=1_000)
        message = str(raised.exception)
        self.assertIn("reviewer", message)
        # It must say what to do, and must not read as a research conclusion.
        self.assertIn("上下文上限", message)
        self.assertIn("不是研究结论", message)

    def test_headroom_is_reserved_for_the_reply(self) -> None:
        """A basis that fits with nothing left over still fails: the answer needs
        somewhere to go."""

        text = "a" * 10_000  # ~3,000 tokens
        require_fits("analyst", text, limit=10_000)
        with self.assertRaises(ContextCapacityError):
            require_fits("analyst", text, limit=3_100)

    def test_an_unknown_ceiling_disables_the_check_rather_than_guessing(self) -> None:
        """Guessing is the worse failure: a wrong low guess blocks real research,
        and this check has to be trustworthy enough that nobody routes around it."""

        require_fits("author", "证据" * 500_000, limit=0)


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
READ = ToolSpec(
    name="read_saved_source",
    description="读取已保存正文。",
    parameters={
        "type": "object",
        "properties": {"source_ref": {"type": "string"}},
        "required": ["source_ref"],
        "additionalProperties": False,
    },
)

SPEC = AgentSpec(
    role="curator",
    system_prompt="你是策展者。",
    tools=(READ, SUBMIT),
    terminal_tools=frozenset({"submit"}),
)


def _call(name: str, **arguments: object) -> ModelToolCall:
    return ModelToolCall(
        call_id=f"t_{name}",
        name=name,
        arguments=json.dumps(arguments, ensure_ascii=False),
    )


class ToolLoopCapacityTest(unittest.IsolatedAsyncioTestCase):
    """The half a check on the opening projection cannot see.

    A Curator's initial context is small -- a candidate list, not the bodies.  The
    overflow comes from what the loop appends: each ``read_saved_source`` returns a
    twelve-thousand-character window, up to twenty-four times.  This is why the red
    line lives inside the loop.
    """

    async def asyncSetUp(self) -> None:
        self._directory = tempfile.TemporaryDirectory()
        path = Path(self._directory.name) / "capacity.sqlite3"
        self._connection = await aiosqlite.connect(path)
        content = SqliteContentStore(self._connection)
        await content.setup()
        self.ledger = SqliteOperationLedger(self._connection, content)
        await self.ledger.setup()
        self.execution = ExecutionIdentity(provider="scripted", model_id="test")

    async def asyncTearDown(self) -> None:
        await self._connection.close()
        self._directory.cleanup()

    class Reader:
        """Keeps asking to read, which is how a real Curator fills its context."""

        def __init__(self) -> None:
            self.calls = 0

        async def complete(
            self,
            messages: Sequence[Mapping[str, Any]],
            **_kwargs: Any,
        ) -> ModelReply:
            self.calls += 1
            return ModelReply(tool_calls=(_call("read_saved_source", source_ref="s1"),))

    async def _big_read(self, _name: str, _arguments: Mapping[str, Any]) -> str:
        return "来源正文片段" * 2_000  # ~12k characters, as the real tool returns

    async def test_a_growing_tool_loop_is_stopped_by_the_red_line(self) -> None:
        model = self.Reader()
        context = RoleContext(
            role="curator",
            purpose="判断候选来源",
            body="## 候选来源\n\n1. `src_1`\n",
            input_refs=(),
        )

        with self.assertRaises(ContextCapacityError):
            await invoke_agent(
                SPEC,
                context,
                model=model,
                ledger=self.ledger,
                task_id="task-1",
                execution=self.execution,
                handlers={"read_saved_source": self._big_read},
                context_limit=30_000,
            )

        # It stopped part-way through the loop, not at entry: the opening context
        # fits comfortably, so a check that only ran once would never have fired.
        self.assertGreater(model.calls, 1)
        self.assertLess(model.calls, SPEC.max_tool_turns)

    async def test_the_same_loop_runs_when_the_ceiling_allows_it(self) -> None:
        """The red line must not be so eager that it blocks ordinary curation."""

        class Prompt:
            calls = 0

            async def complete(self, _messages, **_kwargs):  # noqa: ANN001, ANN202
                type(self).calls += 1
                if type(self).calls == 1:
                    return ModelReply(
                        tool_calls=(_call("read_saved_source", source_ref="s1"),)
                    )
                return ModelReply(tool_calls=(_call("submit", answer="接纳"),))

        action = await invoke_agent(
            SPEC,
            RoleContext(
                role="curator",
                purpose="判断候选来源",
                body="## 候选来源\n\n1. `src_1`\n",
                input_refs=(),
            ),
            model=Prompt(),
            ledger=self.ledger,
            task_id="task-2",
            execution=self.execution,
            handlers={"read_saved_source": self._big_read},
            context_limit=1_000_000,
        )
        self.assertEqual("submit", action.name)

    async def test_nothing_is_charged_for_a_request_that_never_went_out(self) -> None:
        """The check runs before the ledger reserves, so an overflow leaves no
        operation to reconcile or replay."""

        with self.assertRaises(ContextCapacityError):
            await invoke_agent(
                SPEC,
                RoleContext(
                    role="curator",
                    purpose="判断候选来源",
                    body="证据" * 100_000,
                    input_refs=(),
                ),
                model=self.Reader(),
                ledger=self.ledger,
                task_id="task-3",
                execution=self.execution,
                context_limit=10_000,
            )

        rows = await self._connection.execute_fetchall(
            "select count(*) from operations where task_id = 'task-3'"
        )
        self.assertEqual(0, rows[0][0])


class VendorRefusalTest(unittest.IsolatedAsyncioTestCase):
    """The backstop for what the pre-flight estimate deliberately lets through.

    The estimate is calibrated not to block workloads that are known to fit, which
    leaves a band where the vendor discovers the overflow.  A too-large request and
    a malformed one are both HTTP 400, so the vendor's own text is the only thing
    that tells them apart -- and classified as an ordinary rejection it would be
    retried as "provably not executed" until the budget ran out, leaving a dead
    task whose error named nothing useful.
    """

    async def _refuse(self, message: str):  # noqa: ANN202
        async def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(400, json={"error": {"message": message}})

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        model = OpenAICompatibleClient("secret", client=client)
        try:
            return await model.complete([{"role": "user", "content": "x"}])
        finally:
            await client.aclose()

    async def test_an_overflow_refusal_is_a_capacity_failure(self) -> None:
        for message in (
            "This model's maximum context length is 128000 tokens",
            "prompt is too long: 210000 tokens > 200000 maximum",
            "Input length exceeds the limit",
        ):
            with self.subTest(message=message), self.assertRaises(ModelContextOverflow):
                await self._refuse(message)

    async def test_an_ordinary_rejection_stays_retryable(self) -> None:
        """The narrowing must not swallow the case it borrowed the status from."""

        with self.assertRaises(ModelRequestRejected):
            await self._refuse("unknown field 'temperature'")

    def test_a_capacity_failure_is_never_a_plain_rejection(self) -> None:
        """They are handled differently by the ledger, so they must not overlap."""

        self.assertNotIsInstance(ModelContextOverflow(""), ModelRequestRejected)
        for failure in CAPACITY_FAILURES:
            self.assertIn(failure, MODEL_FAILURES)


if __name__ == "__main__":
    unittest.main()
