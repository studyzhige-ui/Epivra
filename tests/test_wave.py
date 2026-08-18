"""A Wave's guarantees are mechanical, so they are tested against scripted models.

The properties here hold no matter what a model returns: exactly one Analyst per
material-changing wave and none otherwise, a delta computed by the trust plane
rather than reported, branches merged by index rather than completion order, one
branch's failure never discarding another's evidence, and a quote that is not in
the saved text never becoming a Material.
"""

from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from pathlib import Path

import aiosqlite

from deep_research_agent.agents.lead import AssignmentDraft
from deep_research_agent.artifact_store import SqliteArtifactStore
from deep_research_agent.content_store import SqliteContentStore
from deep_research_agent.contract import build_contract
from deep_research_agent.model import ModelReply, ModelToolCall
from deep_research_agent.operations import ExecutionIdentity, SqliteOperationLedger
from deep_research_agent.reporting import RoleRuntime
from deep_research_agent.tools import ReadResult, SearchResponse, SearchResult
from deep_research_agent.wave import run_wave

CONTRACT = build_contract(
    "## 问题模型\n\n"
    "### Q1. 本院应如何选择婴儿 RSV 预防路径？\n"
    "### Q2. 两条路径的住院终点证据强度如何？\n"
)

PAGE = (
    "ACIP recommended nirsevimab for infants aged under eight months entering "
    "their first RSV season. Coverage reached a reported plateau in year two."
)
QUOTE = "recommended nirsevimab for infants aged under eight months"


def call(name: str, **arguments: object) -> ModelToolCall:
    return ModelToolCall(
        call_id=f"toolu_{name}",
        name=name,
        arguments=json.dumps(arguments, ensure_ascii=False),
    )


class ScriptedModel:
    """Replays a fixed sequence of replies and records how often it was called.

    A Curator cannot know a source's artifact ID in advance -- the runtime
    assigns it -- so a scripted reply writes ``__FIRST__`` and this stand-in
    resolves it against the store at call time, which is when the identity
    actually exists.
    """

    def __init__(self, replies: list[ModelReply], store=None) -> None:  # noqa: ANN001
        self._replies = list(replies)
        self._store = store
        self.calls = 0

    async def complete(self, messages, **kwargs) -> ModelReply:  # noqa: ANN001
        self.calls += 1
        if not self._replies:
            raise AssertionError("scripted model ran out of replies")
        reply = self._replies.pop(0)
        if self._store is None:
            return reply
        sources = (await self._store.active_view()).active("source_snapshot")
        if not sources:
            return reply
        return ModelReply(
            content=reply.content,
            tool_calls=tuple(
                ModelToolCall(
                    call_id=item.call_id,
                    name=item.name,
                    arguments=item.arguments.replace("__FIRST__", sources[0]),
                )
                for item in reply.tool_calls
            ),
        )


class StubBroker:
    def __init__(self) -> None:
        self.queries: list[str] = []

    async def search(self, request) -> SearchResponse:  # noqa: ANN001
        self.queries.append(request.query)
        return SearchResponse(
            results=(
                SearchResult(
                    title="ACIP recommendation",
                    url="https://cdc.example/acip",
                    snippet="A discovery snippet.",
                ),
            )
        )


class StubReader:
    def __init__(self, pages: dict[str, str] | None = None) -> None:
        self.pages = pages or {"https://cdc.example/acip": PAGE}
        self.reads: list[str] = []

    async def read(self, url: str) -> ReadResult:
        self.reads.append(url)
        if url not in self.pages:
            raise RuntimeError(f"unreachable: {url}")
        return ReadResult(title="ACIP recommendation", url=url, content=self.pages[url])


def investigator_script(*, find: bool = True) -> list[ModelReply]:
    if not find:
        return [
            ModelReply(tool_calls=(call("search", query="rsv", intent="discovery"),)),
            ModelReply(
                tool_calls=(
                    call(
                        "complete_investigation",
                        summary="没有找到可用的一手来源。",
                        attempted_paths=["ACIP 官方记录", "同行评议试验报告"],
                        limitations=["检索返回的结果都无法访问"],
                    ),
                )
            ),
        ]
    return [
        ModelReply(tool_calls=(call("search", query="rsv acip", intent="discovery"),)),
        ModelReply(tool_calls=(call("read", url="https://cdc.example/acip"),)),
        ModelReply(
            tool_calls=(
                call(
                    "save_candidate_source",
                    url="https://cdc.example/acip",
                    relevance_note="ACIP 对 nirsevimab 的正式建议与适用人群。",
                ),
            )
        ),
        ModelReply(
            tool_calls=(
                call(
                    "complete_investigation",
                    summary="找到 ACIP 的正式建议原文。",
                    attempted_paths=["ACIP 官方记录"],
                ),
            )
        ),
    ]


def curator_script() -> list[ModelReply]:
    """Curates the first candidate; ``__FIRST__`` is resolved at call time."""

    return [
        ModelReply(
            tool_calls=(
                call(
                    "record_material",
                    source_ref="__FIRST__",
                    exact_quote=QUOTE,
                    content="ACIP 建议 8 月龄以下婴儿在首个 RSV 季使用 nirsevimab。",
                    boundaries="仅美国 ACIP 建议；不涵盖其他国家，也不含效力数值。",
                ),
            )
        ),
        ModelReply(
            tool_calls=(call("complete_curation", summary="接纳一条 ACIP 建议素材。"),)
        ),
    ]


ANALYST_REPLY = ModelReply(
    tool_calls=(
        call(
            "publish_synthesis",
            synthesis_markdown=(
                "## 当前可支持的判断\n\n"
                "ACIP 已就 nirsevimab 的适用人群作出正式建议，这是监管与实践的基线。"
                "本轮证据不含头对头比较，也不含效力数值，因此不能据此对两条路径排序。\n\n"
                "## 反证与冲突\n\n本轮未发现与该建议冲突的来源。\n\n"
                "## 适用边界\n\n仅适用于美国、首个 RSV 季、8 月龄以下婴儿。\n\n"
                "## Evidence Frontier\n\n"
                "缺少住院终点的效力数值与真实世界数据；下一步应检索关键试验原文。"
            ),
        ),
    )
)


class WaveFixture(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._directory = tempfile.TemporaryDirectory()
        path = Path(self._directory.name) / "wave.sqlite3"
        self._connection = await aiosqlite.connect(path)
        content = SqliteContentStore(self._connection)
        await content.setup()
        self.store = SqliteArtifactStore(self._connection, content, task_id="task-1")
        await self.store.setup()
        self.ledger = SqliteOperationLedger(self._connection, content)
        await self.ledger.setup()
        await self.store.put(
            kind="research_contract", body=CONTRACT.encode()
        )
        self.broker = StubBroker()
        self.reader = StubReader()

    async def asyncTearDown(self) -> None:
        await self._connection.close()
        self._directory.cleanup()

    def runtimes(
        self,
        *,
        investigator: list[ModelReply],
        curator: list[ModelReply],
        analyst: list[ModelReply],
    ) -> dict[str, RoleRuntime]:
        execution = ExecutionIdentity(provider="scripted", model_id="test")
        self.models = {
            "investigator": ScriptedModel(investigator),
            "curator": ScriptedModel(curator, store=self.store),
            "analyst": ScriptedModel(analyst),
        }
        return {
            role: RoleRuntime(model=model, execution=execution)
            for role, model in self.models.items()
        }



class DeltaTest(WaveFixture):
    async def test_a_material_changing_wave_runs_exactly_one_analyst(self) -> None:
        curator_replies = curator_script()
        runtimes = self.runtimes(
            investigator=investigator_script(),
            curator=curator_replies,
            analyst=[ANALYST_REPLY],
        )

        outcome = await run_wave(
            self.store,
            self.ledger,
            runtimes,
            contract=CONTRACT,
            wave_intent="建立监管与建议基线，判断是否需要进一步检索效力证据。",
            assignments=[
                AssignmentDraft(
                    question_labels=("Q1",),
                    focus="ACIP 当前对婴儿 RSV 预防的正式建议是什么",
                    why_it_matters="它决定本院可选路径的合规基线",
                    evidence_sought="ACIP 或 CDC 的一手记录",
                )
            ],
            broker=self.broker,
            reader=self.reader,
        )

        self.assertTrue(outcome.changed_materials)
        self.assertEqual(1, len(outcome.new_material_refs))
        self.assertTrue(outcome.analyst_ran)
        self.assertEqual(1, self.models["analyst"].calls)
        self.assertNotEqual(
            outcome.evidence_set_before, outcome.evidence_set_after
        )

    async def test_a_wave_with_no_material_change_never_calls_the_analyst(self) -> None:
        runtimes = self.runtimes(
            investigator=investigator_script(find=False),
            curator=[],
            analyst=[],
        )

        outcome = await run_wave(
            self.store,
            self.ledger,
            runtimes,
            contract=CONTRACT,
            wave_intent="确认是否存在可用的一手来源。",
            assignments=[
                AssignmentDraft(
                    question_labels=("Q2",),
                    focus="是否存在住院终点的一手证据",
                    why_it_matters="没有它就无法比较两条路径",
                    evidence_sought="关键试验原文",
                )
            ],
            broker=self.broker,
            reader=self.reader,
        )

        self.assertFalse(outcome.changed_materials)
        self.assertFalse(outcome.analyst_ran)
        self.assertEqual(0, self.models["analyst"].calls)
        self.assertEqual(0, self.models["curator"].calls)
        # An empty-handed branch still reports what it tried.
        self.assertEqual("completed", outcome.branches[0].status)
        self.assertIn("ACIP 官方记录", outcome.branches[0].attempted_paths)
        self.assertEqual(
            outcome.evidence_set_before, outcome.evidence_set_after
        )


class FaithfulnessTest(WaveFixture):
    async def test_a_quote_absent_from_the_saved_text_cannot_become_material(
        self,
    ) -> None:
        replies = [
            ModelReply(
                tool_calls=(
                    call(
                        "record_material",
                        source_ref="__FIRST__",
                        exact_quote="ACIP recommended nirsevimab for ALL infants",
                        content="ACIP 建议所有婴儿使用 nirsevimab。",
                        boundaries="无。",
                    ),
                )
            ),
            ModelReply(
                tool_calls=(
                    call(
                        "reject_candidate",
                        source_ref="__FIRST__",
                        reason="原文不支持我最初的改写范围。",
                    ),
                )
            ),
            ModelReply(
                tool_calls=(call("complete_curation", summary="拒绝一条过度外推。"),)
            ),
        ]
        runtimes = self.runtimes(
            investigator=investigator_script(), curator=replies, analyst=[]
        )

        outcome = await run_wave(
            self.store,
            self.ledger,
            runtimes,
            contract=CONTRACT,
            wave_intent="核实建议的适用人群边界。",
            assignments=[
                AssignmentDraft(
                    question_labels=("Q1",),
                    focus="建议覆盖哪些婴儿",
                    why_it_matters="人群边界决定本院适用范围",
                    evidence_sought="ACIP 一手记录",
                )
            ],
            broker=self.broker,
            reader=self.reader,
        )

        # The widened quote was refused, so no Material exists and no Analyst ran.
        self.assertEqual((), outcome.new_material_refs)
        self.assertFalse(outcome.analyst_ran)
        self.assertEqual(0, self.models["analyst"].calls)


class BranchIsolationTest(WaveFixture):
    async def test_one_failing_branch_does_not_discard_another_s_evidence(
        self,
    ) -> None:
        good = investigator_script()
        # The second branch's model runs out of replies, which surfaces as an
        # operational failure for that branch alone.
        curator_replies = curator_script()
        execution = ExecutionIdentity(provider="scripted", model_id="test")

        class Router:
            """One model object serving two branches, by call order."""

            def __init__(self, scripts: list[list[ModelReply]]) -> None:
                self.scripts = scripts
                self.calls = 0

            async def complete(self, messages, **kwargs):  # noqa: ANN001
                self.calls += 1
                body = messages[1]["content"]
                index = 0 if "建议是什么" in body else 1
                script = self.scripts[index]
                if not script:
                    raise RuntimeError("branch 2 provider failure")
                return script.pop(0)

        investigator = Router([good, []])
        self.models = {
            "curator": ScriptedModel(curator_replies, store=self.store),
            "analyst": ScriptedModel([ANALYST_REPLY]),
        }
        runtimes = {
            "investigator": RoleRuntime(model=investigator, execution=execution),
            "curator": RoleRuntime(
                model=self.models["curator"], execution=execution
            ),
            "analyst": RoleRuntime(
                model=self.models["analyst"], execution=execution
            ),
        }

        outcome = await run_wave(
            self.store,
            self.ledger,
            runtimes,
            contract=CONTRACT,
            wave_intent="并行确认建议基线与效力证据。",
            assignments=[
                AssignmentDraft(
                    question_labels=("Q1",),
                    focus="ACIP 当前的正式建议是什么",
                    why_it_matters="合规基线",
                    evidence_sought="一手记录",
                ),
                AssignmentDraft(
                    question_labels=("Q2",),
                    focus="住院终点的效力数值",
                    why_it_matters="决定能否比较",
                    evidence_sought="关键试验",
                ),
            ],
            broker=self.broker,
            reader=self.reader,
        )

        statuses = {branch.index: branch.status for branch in outcome.branches}
        self.assertEqual("completed", statuses[1])
        self.assertEqual("operational_failure", statuses[2])
        # The healthy branch's material survived, and the Analyst still ran once.
        self.assertEqual(1, len(outcome.new_material_refs))
        self.assertTrue(outcome.analyst_ran)

    async def test_branches_are_merged_by_index_not_completion_order(self) -> None:
        """Assignment order is stable regardless of which branch finishes first."""

        execution = ExecutionIdentity(provider="scripted", model_id="test")
        scripts = {0: investigator_script(find=False), 1: investigator_script(find=False)}

        class Delayed:
            def __init__(self) -> None:
                self.calls = 0

            async def complete(self, messages, **kwargs):  # noqa: ANN001
                self.calls += 1
                body = messages[1]["content"]
                index = 0 if "第一个任务" in body else 1
                # Make the first assignment finish last.
                await asyncio.sleep(0.02 if index == 0 else 0)
                return scripts[index].pop(0)

        runtimes = {
            "investigator": RoleRuntime(model=Delayed(), execution=execution),
            "curator": RoleRuntime(model=ScriptedModel([]), execution=execution),
            "analyst": RoleRuntime(model=ScriptedModel([]), execution=execution),
        }

        outcome = await run_wave(
            self.store,
            self.ledger,
            runtimes,
            contract=CONTRACT,
            wave_intent="并行探查两个方向。",
            assignments=[
                AssignmentDraft(
                    question_labels=("Q1",),
                    focus="第一个任务",
                    why_it_matters="先声明的任务",
                    evidence_sought="一手记录",
                ),
                AssignmentDraft(
                    question_labels=("Q2",),
                    focus="第二个任务",
                    why_it_matters="后声明的任务",
                    evidence_sought="一手记录",
                ),
            ],
            broker=self.broker,
            reader=self.reader,
        )

        self.assertEqual((1, 2), tuple(b.index for b in outcome.branches))
        self.assertEqual("第一个任务", outcome.branches[0].focus)
        self.assertEqual("第二个任务", outcome.branches[1].focus)


class OutcomeRenderTest(WaveFixture):
    async def test_the_lead_sees_limitations_marked_as_operational(self) -> None:
        runtimes = self.runtimes(
            investigator=investigator_script(find=False), curator=[], analyst=[]
        )
        outcome = await run_wave(
            self.store,
            self.ledger,
            runtimes,
            contract=CONTRACT,
            wave_intent="探查可得性。",
            assignments=[
                AssignmentDraft(
                    question_labels=("Q1",),
                    focus="可得性",
                    why_it_matters="决定后续路径",
                    evidence_sought="一手记录",
                )
            ],
            broker=self.broker,
            reader=self.reader,
        )

        rendered = outcome.render()
        self.assertIn("运行限制（不是证据结论）", rendered)
        self.assertIn("未运行 Analyst", rendered)


if __name__ == "__main__":
    unittest.main()
