"""The judge's mechanics, tested against a scripted model.

Nothing here calls a provider.  What is worth pinning is not the judge's taste --
that is what calibration against human spot-checks is for -- but the machinery
around it: an incomplete judgement must come back as a correction, the verdict
must bind to the exact report it was made about, and the judge must not be shown
the Reviewer's answer before forming its own.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

import aiosqlite

from deep_research_agent.artifact_store import SqliteArtifactStore
from deep_research_agent.content_store import SqliteContentStore
from deep_research_agent.contract import build_contract
from deep_research_agent.model import ModelReply, ModelToolCall
from deep_research_agent.operations import ExecutionIdentity, SqliteOperationLedger
from deep_research_agent.sources import (
    ArtifactValidationError,
    BodyRef,
    MaterialBody,
    SourceAnchor,
    SourceSnapshotBody,
    TextLocator,
)

ROOT = Path(__file__).resolve().parent.parent


def _load(name: str, filename: str):  # noqa: ANN202
    spec = importlib.util.spec_from_file_location(name, ROOT / "evals" / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


rubric = _load("eval_rubric", "rubric.py")
judge = _load("eval_judge", "judge.py")

CONTRACT = build_contract(
    "## 问题模型\n\n### Q1. 学校空气净化对呼吸道传染病传播的影响有多强的证据？\n"
)
PAGE = (
    "A cluster randomised trial reported no measurable reduction in absence rates "
    "after portable air cleaners were installed in classrooms."
)
QUOTE = "no measurable reduction in absence rates"


def _judgement(*, fail: str = "", omit: str = "") -> dict[str, object]:
    critical = [
        {"domain": domain.key, "passed": domain.key != fail, "reason": "有具体依据的理由"}
        for domain in rubric.CRITICAL
        if domain.key != omit
    ]
    supporting = [
        {"domain": domain.key, "passed": True, "reason": "有具体依据的理由"}
        for domain in rubric.SUPPORTING
    ]
    return {
        "critical": critical,
        "supporting": supporting,
        "summary": "结论与证据相称，检索透明度可以更好，整体可用。",
    }


class ScriptedJudge:
    def __init__(self, *payloads: dict[str, object]) -> None:
        self._payloads = list(payloads)
        self.calls = 0
        self.seen_bodies: list[str] = []

    async def complete(self, messages, **kwargs):  # noqa: ANN001, ANN201
        self.calls += 1
        self.seen_bodies.append(str(messages[-1].get("content", "")))
        payload = self._payloads.pop(0)
        return ModelReply(
            tool_calls=(
                ModelToolCall(
                    call_id=f"toolu_{self.calls}",
                    name="submit_judgement",
                    arguments=json.dumps(payload, ensure_ascii=False),
                ),
            )
        )


class JudgeFixture(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._directory = tempfile.TemporaryDirectory()
        path = Path(self._directory.name) / "judge.sqlite3"
        self._connection = await aiosqlite.connect(path)
        content = SqliteContentStore(self._connection)
        await content.setup()
        self.store = SqliteArtifactStore(self._connection, content, task_id="task-1")
        await self.store.setup()
        self.ledger = SqliteOperationLedger(self._connection, content)
        await self.ledger.setup()
        self.execution = ExecutionIdentity(provider="scripted", model_id="test")

        await self.store.put(kind="research_contract", body=CONTRACT.encode())
        text = await content.put(PAGE)
        source = await self.store.put(
            kind="source_snapshot",
            body=SourceSnapshotBody(
                url="https://trial.example/report",
                title="Classroom air cleaner trial",
                text_ref=BodyRef(text.content_hash, text.char_count),
            ).encode(),
        )
        # A Material that contradicts an optimistic conclusion, so a judge that
        # cannot see uncited evidence would miss the omission.
        await self.store.put(
            kind="material",
            body=MaterialBody.create(
                content="该整群随机试验未观察到缺勤率下降。",
                boundaries="单一试验，学校场景，仅缺勤结局。",
                anchors=(
                    SourceAnchor(
                        source_ref=source.artifact_id,
                        exact_quote=QUOTE,
                        locator=TextLocator(
                            start=PAGE.index(QUOTE),
                            end=PAGE.index(QUOTE) + len(QUOTE),
                        ),
                    ),
                ),
            ).encode(),
            parent_refs=(source.artifact_id,),
        )
        self.publication = await self.store.put(
            kind="publication_receipt", body="# 报告\n\n结论：证据不足以支持推荐。\n"
        )
        await self._connection.commit()

    async def asyncTearDown(self) -> None:
        await self._connection.close()
        self._directory.cleanup()

    async def _judge(self, model) -> object:  # noqa: ANN001
        return await judge.judge_report(
            self.store, self.ledger, model=model, execution=self.execution
        )


class JudgementTest(JudgeFixture):
    async def test_a_complete_judgement_yields_a_tiered_verdict(self) -> None:
        model = ScriptedJudge(_judgement())
        result = await self._judge(model)
        self.assertEqual("可发布·高", result.verdict.tier)
        self.assertTrue(result.verdict.publishable)
        self.assertEqual(self.publication.artifact_id, result.report_ref)

    async def test_a_critical_failure_blocks_publication(self) -> None:
        model = ScriptedJudge(_judgement(fail="within_evidence"))
        result = await self._judge(model)
        self.assertEqual("不可发布", result.verdict.tier)
        self.assertEqual(
            ("within_evidence",),
            tuple(item.key for item in result.verdict.critical_failures),
        )

    async def test_an_incomplete_judgement_is_corrected_not_fatal(self) -> None:
        model = ScriptedJudge(_judgement(omit="counter_evidence"), _judgement())
        result = await self._judge(model)
        self.assertEqual(2, model.calls, "the judge must get one correction")
        self.assertEqual("可发布·高", result.verdict.tier)

    async def test_the_judge_sees_uncited_evidence(self) -> None:
        """Selective omission is invisible from the report alone."""

        model = ScriptedJudge(_judgement())
        await self._judge(model)
        self.assertIn("含报告未引用的素材", model.seen_bodies[0])
        self.assertIn("未观察到缺勤率下降", model.seen_bodies[0])

    async def test_the_judge_is_not_shown_the_reviewers_verdict(self) -> None:
        """Showing it the answer first turns judgement into agreement."""

        await self.store.put(
            kind="review", body="approve_report：结论与证据相称，无阻断项。"
        )
        await self._connection.commit()
        model = ScriptedJudge(_judgement())
        await self._judge(model)
        self.assertNotIn("approve_report", model.seen_bodies[0])

    async def test_re_judging_an_unchanged_report_replays(self) -> None:
        first = ScriptedJudge(_judgement())
        await self._judge(first)
        second = ScriptedJudge(_judgement())
        await self._judge(second)
        self.assertEqual(1, first.calls)
        self.assertEqual(0, second.calls, "an unchanged judgement must not re-pay")

    async def test_a_task_with_no_published_report_is_refused(self) -> None:
        store = SqliteArtifactStore(
            self._connection, SqliteContentStore(self._connection), task_id="empty"
        )
        await store.put(kind="research_contract", body=CONTRACT.encode())
        await self._connection.commit()
        with self.assertRaisesRegex(ArtifactValidationError, "no published report"):
            await judge.judge_report(
                store,
                self.ledger,
                model=ScriptedJudge(_judgement()),
                execution=self.execution,
            )


class SpecTest(unittest.TestCase):
    def test_the_judge_has_exactly_one_terminal_tool_and_no_others(self) -> None:
        self.assertEqual({"submit_judgement"}, set(judge.SPEC.terminal_tools))
        self.assertEqual({"submit_judgement"}, {tool.name for tool in judge.SPEC.tools})

    def test_the_schema_requires_every_domain_exactly_once(self) -> None:
        properties = judge.SUBMIT_JUDGEMENT.parameters["properties"]
        for field, domains in (
            ("critical", rubric.CRITICAL),
            ("supporting", rubric.SUPPORTING),
        ):
            with self.subTest(field=field):
                self.assertEqual(len(domains), properties[field]["minItems"])
                self.assertEqual(len(domains), properties[field]["maxItems"])
                self.assertEqual(
                    [domain.key for domain in domains],
                    properties[field]["items"]["properties"]["domain"]["enum"],
                )

    def test_the_prompt_forbids_a_total_score(self) -> None:
        self.assertIn("不要输出总分或平均分", judge.SYSTEM_PROMPT)

    def test_the_prompt_protects_an_honest_low_certainty_report(self) -> None:
        self.assertIn("低确定性不是缺陷", judge.SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()
