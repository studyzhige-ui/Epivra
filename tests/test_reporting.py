"""The reporting transaction, driven by scripted models.

These tests pin the properties that the previous implementation got wrong: a
bounded review loop, an approval receipt tied to one exact report body, and a
publication path that fails closed rather than emitting an unverifiable claim.
Scripted models make the role behaviour explicit, so a failure points at the
pipeline rather than at a provider's mood.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import aiosqlite

from deep_research_agent.agents import AgentProtocolError
from deep_research_agent.artifact_store import SqliteArtifactStore
from deep_research_agent.content_store import SqliteContentStore
from deep_research_agent.contract import build_contract
from deep_research_agent.model import ModelReply, ModelToolCall, ToolSpec
from deep_research_agent.operations import ExecutionIdentity, SqliteOperationLedger
from deep_research_agent.reporting import (
    REVIEW_ROUNDS,
    ReportingHalted,
    RoleRuntime,
    publication_blocked,
    run_reporting,
)
from deep_research_agent.sources import (
    MaterialBody,
    SourceAnchor,
    SourceSnapshotBody,
    locate_quote,
)

CONTRACT = """\
## 目的与用途

为医院母婴护理团队选择婴儿 RSV 预防路径提供依据。

## 问题模型

### Q1. 母源疫苗与单克隆抗体应如何组合使用？
### Q2. 两条路径的效力证据强度如何？

## 范围与定义

时点 2026 年 8 月。

## 证据与分析方法

优先监管标签与 ACIP 记录。

## 交付与保证

决策简报，独立审查。

## 自适应边界与已知限制

查询顺序由 Lead 自适应。
"""

SOURCE_TEXT = (
    "ACIP recommended nirsevimab for infants aged under eight months entering "
    "their first RSV season. Maternal RSVpreF vaccination is an alternative "
    "pathway with distinct timing requirements."
)
QUOTE = "recommended nirsevimab for infants aged under eight months"


class ScriptedModel:
    """Returns a queued tool call per turn and records what it was asked."""

    def __init__(self, script: Sequence[tuple[str, Mapping[str, Any]]]) -> None:
        self.script = list(script)
        self.calls: list[list[Mapping[str, Any]]] = []
        self.offered: list[tuple[str, ...]] = []

    async def complete(
        self,
        messages: Sequence[Mapping[str, Any]],
        *,
        tools: Sequence[ToolSpec] = (),
        tool_choice: str | None = None,
    ) -> ModelReply:
        self.calls.append([dict(m) for m in messages])
        self.offered.append(tuple(tool.name for tool in tools))
        if not self.script:
            raise AssertionError("scripted model exhausted")
        name, arguments = self.script.pop(0)
        return ModelReply(
            tool_calls=(
                ModelToolCall(
                    call_id=f"call-{len(self.calls)}",
                    name=name,
                    arguments=json.dumps(arguments, ensure_ascii=False),
                ),
            )
        )


def synthesis_text() -> str:
    return (
        "## Q1 组合使用\n\n两条路径互为替代而非叠加，选择取决于母亲接种时点与"
        "婴儿出生季节。\n\n## Q2 证据强度\n\n单克隆抗体在住院终点上有直接证据；"
        "母源疫苗的证据来自不同人群，二者不可直接比较。\n\n## 反证与冲突\n\n"
        "现有估计来自不同季节与不同监测体系，存在真实的不可比性。\n\n"
        "## Evidence Frontier\n\n缺少同一季节内的头对头比较；若出现，将改变强度判断。"
    ) * 2


def report_text(handle: str = "h1") -> str:
    return (
        "# 婴儿 RSV 预防路径决策简报\n\n## 执行摘要\n\n"
        f"对本院人群，两条路径应按出生季节与母亲接种时点二选一 [[cite:{handle}]]。\n\n"
        "## 证据与边界\n\n"
        f"ACIP 的建议限定于首个 RSV 季节的特定月龄区间 [[cite:{handle}]]，"
        "该限定不能外推到更大月龄人群。\n\n## 局限\n\n"
        "现有证据缺少同季节头对头比较，因此本简报不给出效力优劣排序。\n"
    ) * 3


class ReportingFixture(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._directory = tempfile.TemporaryDirectory()
        path = Path(self._directory.name) / "task.sqlite3"
        self.connection = await aiosqlite.connect(path)
        self.content = SqliteContentStore(self.connection)
        await self.content.setup()
        self.store = SqliteArtifactStore(
            self.connection, self.content, task_id="task-rsv"
        )
        await self.store.setup()
        self.ledger = SqliteOperationLedger(self.connection, self.content)
        await self.ledger.setup()

        await self.store.put(
            kind="research_contract", body=build_contract(CONTRACT).encode()
        )
        text_ref = await self.content.put(SOURCE_TEXT)
        source = await self.store.put(
            kind="source_snapshot",
            body=SourceSnapshotBody(
                url="https://cdc.example/acip",
                title="ACIP recommendation",
                text_ref=text_ref,
                fetched_at="2026-08-12",
            ).encode(),
        )
        anchor = SourceAnchor(
            source_ref=source.artifact_id,
            exact_quote=QUOTE,
            locator=locate_quote(SOURCE_TEXT, QUOTE),
        )
        body = MaterialBody.create(
            content="ACIP 建议 nirsevimab 用于首个 RSV 季节内未满八月龄的婴儿。",
            boundaries="美国；截至 2023-08-03；不覆盖更大月龄人群。",
            anchors=(anchor,),
        )
        await self.store.put(
            kind="material", body=body.encode(), parent_refs=body.source_refs
        )

    async def asyncTearDown(self) -> None:
        await self.connection.close()
        self._directory.cleanup()

    def runtimes(
        self,
        analyst: Sequence[tuple[str, Mapping[str, Any]]],
        author: Sequence[tuple[str, Mapping[str, Any]]],
        reviewer: Sequence[tuple[str, Mapping[str, Any]]],
    ) -> dict[str, RoleRuntime]:
        self.analyst_model = ScriptedModel(analyst)
        self.author_model = ScriptedModel(author)
        self.reviewer_model = ScriptedModel(reviewer)
        return {
            role: RoleRuntime(
                model=model,
                execution=ExecutionIdentity(provider="scripted", model_id=role),
            )
            for role, model in (
                ("analyst", self.analyst_model),
                ("author", self.author_model),
                ("reviewer", self.reviewer_model),
            )
        }

    async def run_transaction(self, runtimes: dict[str, RoleRuntime]):
        return await run_reporting(
            self.store,
            self.ledger,
            runtimes,
            report_brief="面向母婴护理团队的决策简报。",
            stop_rationale="公开证据已达当前能力边界。",
        )


class HappyPathTest(ReportingFixture):
    async def test_approved_report_is_rendered_and_published(self) -> None:
        outcome = await self.run_transaction(
            self.runtimes(
                analyst=[("publish_synthesis", {"synthesis_markdown": synthesis_text()})],
                author=[("submit_report", {"report_markdown": report_text()})],
                reviewer=[
                    (
                        "approve_report",
                        {
                            "rationale": "结论强度与证据相称，限制已在受影响结论附近披露，"
                            "不存在会改变用户判断的未披露缺陷。",
                            "advisories": ["可补充一张对照表"],
                        },
                    )
                ],
            )
        )

        self.assertTrue(outcome.published)
        self.assertEqual(1, len(outcome.report_refs))
        self.assertEqual(1, len(outcome.reviews))
        assert outcome.rendered is not None
        # Handles are replaced by deterministic numbers, never left raw.
        self.assertNotIn("[[cite:", outcome.rendered.markdown)
        self.assertIn("[1]", outcome.rendered.markdown)
        self.assertIn("## 参考资料", outcome.rendered.markdown)
        self.assertIn("https://cdc.example/acip", outcome.rendered.markdown)

    async def test_the_full_artifact_lineage_is_committed(self) -> None:
        outcome = await self.run_transaction(
            self.runtimes(
                analyst=[("publish_synthesis", {"synthesis_markdown": synthesis_text()})],
                author=[("submit_report", {"report_markdown": report_text()})],
                reviewer=[("approve_report", {"rationale": "证据与结论相称。" * 5})],
            )
        )
        view = await self.store.active_view()

        self.assertEqual(outcome.synthesis_ref, view.head("synthesis"))
        self.assertEqual(outcome.commission_ref, view.head("report_commission"))
        self.assertEqual(outcome.publication_ref, view.head("publication_receipt"))
        self.assertEqual(1, len(view.active("review_receipt")))

        # Synthesis binds the exact evidence set; report binds the commission.
        synthesis = await self.store.get(outcome.synthesis_ref)
        self.assertEqual(view.active("material"), synthesis.parent_refs)
        report = await self.store.get(outcome.report_refs[0])
        self.assertEqual((outcome.commission_ref,), report.parent_refs)

    async def test_each_role_sees_only_its_own_tools(self) -> None:
        await self.run_transaction(
            self.runtimes(
                analyst=[("publish_synthesis", {"synthesis_markdown": synthesis_text()})],
                author=[("submit_report", {"report_markdown": report_text()})],
                reviewer=[("approve_report", {"rationale": "证据与结论相称。" * 5})],
            )
        )

        self.assertEqual(("publish_synthesis",), self.analyst_model.offered[0])
        self.assertEqual(
            ("submit_report", "raise_evidence_issue"), self.author_model.offered[0]
        )
        self.assertEqual(
            ("approve_report", "block_report"), self.reviewer_model.offered[0]
        )

    async def test_the_reviewer_context_is_fresh_not_the_author_thread(self) -> None:
        await self.run_transaction(
            self.runtimes(
                analyst=[("publish_synthesis", {"synthesis_markdown": synthesis_text()})],
                author=[("submit_report", {"report_markdown": report_text()})],
                reviewer=[("approve_report", {"rationale": "证据与结论相称。" * 5})],
            )
        )

        reviewer_messages = self.reviewer_model.calls[0]
        self.assertEqual(2, len(reviewer_messages))
        joined = "\n".join(str(m.get("content", "")) for m in reviewer_messages)
        self.assertIn("Independent Reviewer", joined)
        self.assertNotIn("你是 Report Author", joined)

    async def test_an_unchanged_evidence_set_reuses_its_synthesis(self) -> None:
        runtimes = self.runtimes(
            analyst=[("publish_synthesis", {"synthesis_markdown": synthesis_text()})],
            author=[("submit_report", {"report_markdown": report_text()})],
            reviewer=[("approve_report", {"rationale": "证据与结论相称。" * 5})],
        )
        await self.run_transaction(runtimes)

        # A second transaction over the same materials must not re-analyse.
        runtimes["author"] = RoleRuntime(
            model=ScriptedModel([("submit_report", {"report_markdown": report_text()})]),
            execution=ExecutionIdentity(provider="scripted", model_id="author"),
        )
        runtimes["reviewer"] = RoleRuntime(
            model=ScriptedModel(
                [("approve_report", {"rationale": "证据与结论相称。" * 5})]
            ),
            execution=ExecutionIdentity(provider="scripted", model_id="reviewer"),
        )
        await self.run_transaction(runtimes)

        self.assertEqual(1, len(self.analyst_model.calls))


class BoundedReviewTest(ReportingFixture):
    def blocking(self) -> tuple[str, dict[str, Any]]:
        return (
            "block_report",
            {
                "findings": [
                    {
                        "location": "执行摘要",
                        "problem": "结论强度超出证据允许的范围",
                        "impact": "会让读者以为存在头对头比较",
                        "acceptance_condition": "限定为不可比，或删除该排序",
                    }
                ]
            },
        )

    async def test_a_blocked_report_gets_exactly_one_revision(self) -> None:
        outcome = await self.run_transaction(
            self.runtimes(
                analyst=[("publish_synthesis", {"synthesis_markdown": synthesis_text()})],
                author=[
                    ("submit_report", {"report_markdown": report_text()}),
                    (
                        "submit_revised_report",
                        {
                            "report_markdown": report_text(),
                            "finding_dispositions": [
                                {"finding_index": 1, "response": "已限定为不可比。"}
                            ],
                        },
                    ),
                ],
                reviewer=[
                    self.blocking(),
                    ("approve_report", {"rationale": "阻断项已充分处置。" * 5}),
                ],
            )
        )

        self.assertTrue(outcome.published)
        self.assertEqual(2, len(outcome.report_refs))
        self.assertEqual(2, len(outcome.reviews))
        self.assertFalse(outcome.reviews[0].approved)
        self.assertTrue(outcome.reviews[1].approved)

    async def test_a_second_block_ends_the_transaction_instead_of_looping(self) -> None:
        outcome = await self.run_transaction(
            self.runtimes(
                analyst=[("publish_synthesis", {"synthesis_markdown": synthesis_text()})],
                author=[
                    ("submit_report", {"report_markdown": report_text()}),
                    (
                        "submit_revised_report",
                        {
                            "report_markdown": report_text(),
                            "finding_dispositions": [
                                {"finding_index": 1, "response": "已修改。"}
                            ],
                        },
                    ),
                ],
                reviewer=[self.blocking(), self.blocking()],
            )
        )

        self.assertFalse(outcome.published)
        self.assertIn("Lead", outcome.halted_reason)
        # The author was never asked to write a third time.
        self.assertEqual(2, len(self.author_model.calls))

    async def test_the_final_block_is_readable_from_the_artifacts_alone(self) -> None:
        """Whoever opens this database next must be able to see what happened.

        The transaction's own return value lives in one process; the state a user
        is shown has to survive closing the terminal, and it does so by being
        derived rather than stored.  Anything else would be a second account of
        the same truth, and the artifacts are the one a later process reads.
        """

        self.assertFalse(await publication_blocked(self.store))

        await self.run_transaction(
            self.runtimes(
                analyst=[("publish_synthesis", {"synthesis_markdown": synthesis_text()})],
                author=[
                    ("submit_report", {"report_markdown": report_text()}),
                    (
                        "submit_revised_report",
                        {
                            "report_markdown": report_text(),
                            "finding_dispositions": [
                                {"finding_index": 1, "response": "已修改。"}
                            ],
                        },
                    ),
                ],
                reviewer=[self.blocking(), self.blocking()],
            )
        )

        view = await self.store.active_view()
        self.assertEqual(REVIEW_ROUNDS, len(view.active("review")))
        self.assertEqual((), view.active("review_receipt"))
        self.assertTrue(await publication_blocked(self.store))

    async def test_one_block_that_a_revision_answered_is_not_a_final_block(
        self,
    ) -> None:
        await self.run_transaction(
            self.runtimes(
                analyst=[("publish_synthesis", {"synthesis_markdown": synthesis_text()})],
                author=[
                    ("submit_report", {"report_markdown": report_text()}),
                    (
                        "submit_revised_report",
                        {
                            "report_markdown": report_text(),
                            "finding_dispositions": [
                                {"finding_index": 1, "response": "已限定为不可比。"}
                            ],
                        },
                    ),
                ],
                reviewer=[
                    self.blocking(),
                    ("approve_report", {"rationale": "阻断项已充分处置。" * 5}),
                ],
            )
        )

        self.assertFalse(await publication_blocked(self.store))

    async def test_closure_receives_the_findings_and_their_dispositions(self) -> None:
        await self.run_transaction(
            self.runtimes(
                analyst=[("publish_synthesis", {"synthesis_markdown": synthesis_text()})],
                author=[
                    ("submit_report", {"report_markdown": report_text()}),
                    (
                        "submit_revised_report",
                        {
                            "report_markdown": report_text(),
                            "finding_dispositions": [
                                {"finding_index": 1, "response": "已限定为不可比。"}
                            ],
                        },
                    ),
                ],
                reviewer=[
                    self.blocking(),
                    ("approve_report", {"rationale": "处置成立。" * 8}),
                ],
            )
        )

        closure = "\n".join(
            str(m.get("content", "")) for m in self.reviewer_model.calls[1]
        )
        self.assertIn("上一轮的发布阻断项", closure)
        self.assertIn("作者对每一项的处置", closure)
        self.assertIn("已限定为不可比", closure)

    async def test_a_revision_missing_a_disposition_is_corrected_then_refused(
        self,
    ) -> None:
        with self.assertRaises(AgentProtocolError):
            await self.run_transaction(
                self.runtimes(
                    analyst=[
                        ("publish_synthesis", {"synthesis_markdown": synthesis_text()})
                    ],
                    author=[
                        ("submit_report", {"report_markdown": report_text()}),
                        (
                            "submit_revised_report",
                            {
                                "report_markdown": report_text(),
                                "finding_dispositions": [],
                            },
                        ),
                        (
                            "submit_revised_report",
                            {
                                "report_markdown": report_text(),
                                "finding_dispositions": [],
                            },
                        ),
                    ],
                    reviewer=[self.blocking()],
                )
            )


class FailClosedTest(ReportingFixture):
    async def test_an_invented_citation_handle_is_corrected_not_published(self) -> None:
        outcome = await self.run_transaction(
            self.runtimes(
                analyst=[("publish_synthesis", {"synthesis_markdown": synthesis_text()})],
                author=[
                    ("submit_report", {"report_markdown": report_text("h99")}),
                    ("submit_report", {"report_markdown": report_text("h1")}),
                ],
                reviewer=[("approve_report", {"rationale": "证据与结论相称。" * 5})],
            )
        )

        self.assertTrue(outcome.published)
        correction = str(self.author_model.calls[1][-1]["content"])
        self.assertIn("h99", correction)
        self.assertIn("没有给出的标记", correction)

    async def test_a_report_citing_nothing_is_refused(self) -> None:
        with self.assertRaises(AgentProtocolError):
            await self.run_transaction(
                self.runtimes(
                    analyst=[
                        ("publish_synthesis", {"synthesis_markdown": synthesis_text()})
                    ],
                    author=[
                        ("submit_report", {"report_markdown": "无引用的报告。" * 100}),
                        ("submit_report", {"report_markdown": "仍然无引用。" * 100}),
                    ],
                    reviewer=[],
                )
            )

    async def test_an_evidence_issue_ends_the_transaction_without_a_report(self) -> None:
        outcome = await self.run_transaction(
            self.runtimes(
                analyst=[("publish_synthesis", {"synthesis_markdown": synthesis_text()})],
                author=[
                    (
                        "raise_evidence_issue",
                        {
                            "description": "合同要求头对头比较，但证据集中没有该数据。",
                            "affected_claims": ["两条路径的效力排序"],
                            "why_writing_cannot_resolve_it": "删除该结论会使核心交付缺失。",
                        },
                    )
                ],
                reviewer=[],
            )
        )

        self.assertFalse(outcome.published)
        self.assertEqual([], outcome.report_refs)
        self.assertIn("头对头", outcome.halted_reason)
        self.assertEqual(0, len(self.reviewer_model.calls))

    async def test_an_empty_evidence_set_cannot_reach_the_author(self) -> None:
        store = SqliteArtifactStore(
            self.connection, self.content, task_id="empty-task"
        )
        await store.put(
            kind="research_contract", body=build_contract(CONTRACT).encode()
        )
        with self.assertRaisesRegex(ReportingHalted, "evidence set is empty"):
            await run_reporting(
                store,
                self.ledger,
                self.runtimes(analyst=[], author=[], reviewer=[]),
                report_brief="brief",
                stop_rationale="reason",
            )


class LedgerTest(ReportingFixture):
    async def test_every_model_call_is_recorded_as_an_operation(self) -> None:
        await self.run_transaction(
            self.runtimes(
                analyst=[("publish_synthesis", {"synthesis_markdown": synthesis_text()})],
                author=[("submit_report", {"report_markdown": report_text()})],
                reviewer=[("approve_report", {"rationale": "证据与结论相称。" * 5})],
            )
        )

        cursor = await self.connection.execute(
            "SELECT role, status FROM operations ORDER BY role"
        )
        rows = await cursor.fetchall()
        await cursor.close()

        self.assertEqual(
            [("analyst", "completed"), ("author", "completed"), ("reviewer", "completed")],
            [(str(r[0]), str(r[1])) for r in rows],
        )

    async def test_two_reviews_of_different_reports_are_distinct_operations(
        self,
    ) -> None:
        """A closure review must never replay the baseline verdict.

        Both reviews share role, evidence set, and purpose, so only the report
        body distinguishes them. When it did not reach the fingerprint, the
        ledger replayed the baseline's block onto a revised report it had never
        read, and publication became unreachable.
        """

        await self.run_transaction(
            self.runtimes(
                analyst=[("publish_synthesis", {"synthesis_markdown": synthesis_text()})],
                author=[
                    ("submit_report", {"report_markdown": report_text()}),
                    (
                        "submit_revised_report",
                        {
                            "report_markdown": report_text() + "\n补充限定说明。\n",
                            "finding_dispositions": [
                                {"finding_index": 1, "response": "已限定为不可比。"}
                            ],
                        },
                    ),
                ],
                reviewer=[
                    (
                        "block_report",
                        {
                            "findings": [
                                {
                                    "location": "执行摘要",
                                    "problem": "结论强度超出证据",
                                    "impact": "会误导读者",
                                    "acceptance_condition": "限定为不可比",
                                }
                            ]
                        },
                    ),
                    ("approve_report", {"rationale": "阻断项已充分处置。" * 5}),
                ],
            )
        )

        cursor = await self.connection.execute(
            "SELECT operation_id FROM operations WHERE role = 'reviewer'"
        )
        rows = await cursor.fetchall()
        await cursor.close()

        self.assertEqual(2, len(rows))
        self.assertEqual(2, len({str(row[0]) for row in rows}))
        self.assertEqual(2, len(self.reviewer_model.calls))

    async def test_an_identical_basis_replays_instead_of_paying_again(self) -> None:
        """The other half of the same rule: same basis must not be re-billed."""

        from deep_research_agent.agents import analyst as analyst_agent
        from deep_research_agent.agents import invoke_agent
        from deep_research_agent.context import (
            analyst_context,
            load_contract,
            load_evidence,
        )

        model = ScriptedModel(
            [("publish_synthesis", {"synthesis_markdown": synthesis_text()})]
        )
        contract = await load_contract(self.store)
        evidence = await load_evidence(self.store)
        context = analyst_context(contract, evidence)
        execution = ExecutionIdentity(provider="scripted", model_id="analyst")

        for _ in range(3):
            await invoke_agent(
                analyst_agent.SPEC,
                context,
                model=model,
                ledger=self.ledger,
                task_id=self.store.task_id,
                execution=execution,
                validate=analyst_agent.validate,
            )

        self.assertEqual(1, len(model.calls))


if __name__ == "__main__":
    unittest.main()
