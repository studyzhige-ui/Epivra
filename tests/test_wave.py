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
from dataclasses import replace
from pathlib import Path
from unittest import mock

import aiosqlite

from deep_research_agent.agents import investigator as investigator_agent
from deep_research_agent.agents.lead import AssignmentDraft
from deep_research_agent.artifact_store import SqliteArtifactStore
from deep_research_agent.citations import render_citations
from deep_research_agent.content_store import SqliteContentStore
from deep_research_agent.context import load_evidence
from deep_research_agent.contract import build_contract
from deep_research_agent.model import ModelAuthError, ModelReply, ModelToolCall
from deep_research_agent.operations import (
    ExecutionIdentity,
    OperationReconciliationRequired,
    SqliteOperationLedger,
)
from deep_research_agent.providers._http import SourceReadError
from deep_research_agent.reporting import RoleRuntime
from deep_research_agent.sources import SourceSnapshotBody
from deep_research_agent.tools import ReadResult, SearchResponse, SearchResult
from deep_research_agent.wave import run_wave, stalled

CONTRACT = build_contract(
    "## 问题模型\n\n"
    "- Q1. 本院应如何选择婴儿 RSV 预防路径？\n"
    "- Q2. 两条路径的住院终点证据强度如何？\n"
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
        self.seen: list[str] = []

    async def complete(self, messages, **kwargs) -> ModelReply:  # noqa: ANN001
        self.calls += 1
        self.seen.append(str(messages[1].get("content", "")) if len(messages) > 1 else "")
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
            ),
            attempts=(),
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



class CaptureTimeTest(WaveFixture):
    """A published reference has to say when its source was read.

    `citations._reference_line` renders a capture date and explains why -- a reader
    judges currency from it -- but nothing on the live path ever set `fetched_at`,
    so every reference in every published report came out bare.  Snapshots are
    immutable, which makes it unrecoverable after the fact: seven published reports
    are permanently missing it.
    """

    async def _snapshot(self) -> SourceSnapshotBody:
        runtimes = self.runtimes(
            investigator=investigator_script(),
            curator=curator_script(),
            analyst=[ANALYST_REPLY],
        )
        await run_wave(
            self.store,
            self.ledger,
            runtimes,
            contract=CONTRACT,
            wave_intent="建立机制层面的基线证据",
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
        refs = (await self.store.active_view()).active("source_snapshot")
        self.assertTrue(refs, "the wave should have saved a snapshot")
        return SourceSnapshotBody.decode(await self.store.body(refs[0]))

    async def test_a_live_fetch_records_when_it_happened(self) -> None:
        body = await self._snapshot()
        self.assertTrue(body.fetched_at, "a snapshot must carry its capture time")
        # A date is what the reference list renders; the rest is precision nobody
        # reads, but it must at least start with one.
        self.assertRegex(body.fetched_at[:10], r"^\d{4}-\d{2}-\d{2}$")

    async def test_the_rendered_reference_carries_the_date(self) -> None:
        """End to end: the field is only worth setting if it reaches the reader."""

        body = await self._snapshot()
        evidence = await load_evidence(self.store)
        rendered = render_citations(
            "# 报告\n\n结论句 [[cite:h1]]。\n",
            evidence.handles,
            evidence_set=evidence.material_refs,
        )
        self.assertEqual(1, len(rendered.references))
        self.assertIn(f"({body.fetched_at[:10]})", rendered.references[0])

    async def test_replaying_a_fetch_does_not_mint_a_second_snapshot(self) -> None:
        """Why the stamp comes from the ledger and not the clock.

        `fetched_at` is part of the body, so it decides the artifact's identity.  A
        wall-clock stamp would differ on every replay, so a resumed run would
        commit a *second* snapshot of text the ledger already held -- inflating the
        source count and orphaning the first.
        """

        before = await self._snapshot()
        count_before = len((await self.store.active_view()).active("source_snapshot"))

        # Same task, same URL: the fetch replays from the ledger rather than
        # calling the reader again.
        await run_wave(
            self.store,
            self.ledger,
            self.runtimes(
                investigator=investigator_script(),
                curator=curator_script(),
                analyst=[ANALYST_REPLY],
            ),
            contract=CONTRACT,
            wave_intent="建立机制层面的基线证据",
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

        refs = (await self.store.active_view()).active("source_snapshot")
        self.assertEqual(count_before, len(refs))
        self.assertEqual(
            before.fetched_at,
            SourceSnapshotBody.decode(await self.store.body(refs[0])).fetched_at,
        )


class CuratorHarvestTest(WaveFixture):
    """A Curator that cannot close its turn still committed what it recorded.

    Materials are durable artifacts the moment `record_material` returns, not
    pending work.  Letting the protocol error escape reported the branch as having
    produced nothing while the wave's own MaterialDelta counted them -- so the Lead
    read a branch summary and an evidence count that contradicted each other.  The
    Investigator side already harvested for exactly this reason; the Curator side
    did not.
    """

    async def test_a_curator_that_cannot_close_keeps_its_materials(self) -> None:
        # Two candidates, one curated.  Closing with the other untouched is what
        # the validator refuses, so the role burns its single correction and the
        # runner gives up -- with one Material already committed.
        self.reader = StubReader(
            {
                "https://cdc.example/acip": PAGE,
                "https://cdc.example/second": PAGE,
            }
        )

        class TwoResults:
            async def search(self, request):  # noqa: ANN001, ANN202
                return SearchResponse(
                    results=(
                        SearchResult(title="a", url="https://cdc.example/acip"),
                        SearchResult(title="b", url="https://cdc.example/second"),
                    ),
                    attempts=(),
                )

        incomplete = ModelReply(
            tool_calls=(call("complete_curation", summary="草率结束，还有候选没处置。"),)
        )
        runtimes = self.runtimes(
            investigator=[
                ModelReply(tool_calls=(call("search", query="rsv", intent="d"),)),
                ModelReply(tool_calls=(call("read", url="https://cdc.example/acip"),)),
                ModelReply(
                    tool_calls=(call("read", url="https://cdc.example/second"),)
                ),
                ModelReply(
                    tool_calls=(
                        call(
                            "save_candidate_source",
                            url="https://cdc.example/acip",
                            relevance_note="ACIP 的正式建议原文。",
                        ),
                    )
                ),
                ModelReply(
                    tool_calls=(
                        call(
                            "save_candidate_source",
                            url="https://cdc.example/second",
                            relevance_note="第二份候选来源。",
                        ),
                    )
                ),
                ModelReply(
                    tool_calls=(
                        call(
                            "complete_investigation",
                            summary="保存了两份候选来源。",
                            attempted_paths=["ACIP 官方记录"],
                        ),
                    )
                ),
            ],
            curator=[curator_script()[0], incomplete, incomplete],
            analyst=[ANALYST_REPLY],
        )

        outcome = await run_wave(
            self.store,
            self.ledger,
            runtimes,
            contract=CONTRACT,
            wave_intent="建立机制层面的基线证据",
            assignments=[
                AssignmentDraft(
                    question_labels=("Q1",),
                    focus="ACIP 当前对婴儿 RSV 预防的正式建议是什么",
                    why_it_matters="它决定本院可选路径的合规基线",
                    evidence_sought="ACIP 或 CDC 的一手记录",
                )
            ],
            broker=TwoResults(),
            reader=self.reader,
        )

        branch = outcome.branches[0]
        # The verdict is not softened: it failed, and says why.
        self.assertEqual("operational_failure", branch.status)
        self.assertTrue(any("curator" in item for item in branch.limitations))
        # But the paid-for, committed evidence is reported rather than orphaned,
        # and the branch agrees with the wave.
        self.assertEqual(1, len(branch.material_refs))
        self.assertEqual(
            set(outcome.new_material_refs), set(branch.material_refs)
        )


class FetchGuardTest(WaveFixture):
    """A source identity the domain will refuse must not be paid for first.

    `SourceSnapshotBody` canonicalises its own url, so a URL carrying credentials
    is refused either way -- but refused *after* the fetch it means the text is
    already bought and has nowhere to go, and the role is told only that "the tool
    failed".  Checking the shape first is the same discipline as refusing an
    unauthorised source family before the ledger records anything.
    """

    async def test_an_unusable_url_is_refused_before_the_fetch(self) -> None:
        runtimes = self.runtimes(
            investigator=[
                ModelReply(
                    tool_calls=(
                        call("read", url="https://example.org/doc?api_key=secret"),
                    )
                ),
                ModelReply(
                    tool_calls=(
                        call(
                            "complete_investigation",
                            summary="候选来源的标识不可用，未能取得正文。",
                            attempted_paths=["带凭据参数的直链"],
                            limitations=["该 URL 携带凭据参数，不能作为来源身份"],
                        ),
                    )
                ),
            ],
            curator=curator_script(),
            analyst=[ANALYST_REPLY],
        )

        await run_wave(
            self.store,
            self.ledger,
            runtimes,
            contract=CONTRACT,
            wave_intent="尝试读取一个不合规的来源标识",
            assignments=[
                AssignmentDraft(
                    question_labels=("Q1",),
                    focus="能否读取带凭据的直链",
                    why_it_matters="它决定来源身份是否可用",
                    evidence_sought="一手文件",
                )
            ],
            broker=self.broker,
            reader=self.reader,
        )

        # Never fetched, so never charged, and no orphan snapshot.
        self.assertEqual([], self.reader.reads)
        self.assertEqual(
            (), (await self.store.active_view()).active("source_snapshot")
        )
        rows = await self._connection.execute_fetchall(
            "select count(*) from operations where kind = 'fetch'"
        )
        self.assertEqual(0, rows[0][0])


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
        # The second branch gets a definite authentication rejection, which is a
        # known operational failure for that branch alone rather than an unknown
        # provider outcome that must stop the whole wave.
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
                    raise ModelAuthError("branch 2 authentication rejected")
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


class LedgerClassificationTest(WaveFixture):
    """A dead link is a known outcome, so it must never freeze the ledger.

    ``needs_reconciliation`` means "we may have been billed and cannot tell",
    and it is terminal until a human clears it.  A live run spent it on 52
    unreadable URLs -- HTML served as PDF, hosts the policy refused -- every
    one of which is a decided, unbilled outcome.  Had a genuine unknown
    occurred in that run it would have been indistinguishable from the noise,
    which is the whole value of the signal.
    """

    async def test_an_unreadable_source_records_a_retryable_failure(self) -> None:
        class FailingReader:
            reads: list[str] = []

            async def read(self, url: str) -> ReadResult:
                self.reads.append(url)
                raise SourceReadError("invalid pdf header: b'<!DOC'")

        runtimes = self.runtimes(
            investigator=investigator_script(find=False)[:1]
            + [
                ModelReply(tool_calls=(call("read", url="https://cdc.example/acip"),)),
                ModelReply(
                    tool_calls=(
                        call(
                            "complete_investigation",
                            summary="唯一候选来源无法读取。",
                            attempted_paths=["ACIP 官方记录"],
                            limitations=["该 URL 返回的内容无法解析为文本"],
                        ),
                    )
                ),
            ],
            curator=[],
            analyst=[],
        )

        outcome = await run_wave(
            self.store,
            self.ledger,
            runtimes,
            contract=CONTRACT,
            wave_intent="确认候选来源是否可读。",
            assignments=[
                AssignmentDraft(
                    question_labels=("Q1",),
                    focus="ACIP 记录能否读取",
                    why_it_matters="它是唯一的一手入口",
                    evidence_sought="ACIP 官方记录",
                )
            ],
            broker=self.broker,
            reader=FailingReader(),
        )

        # The branch survives: an unreadable URL is something to report, not a
        # reason to lose the assignment.
        self.assertEqual("completed", outcome.branches[0].status)
        rows = await self._connection.execute_fetchall(
            "select status, attempts, max_attempts from operations where kind='fetch'"
        )
        self.assertEqual(1, len(rows))
        status, attempts, max_attempts = rows[0]
        self.assertEqual("failed", status)
        self.assertLess(attempts, max_attempts, "the failure must stay retryable")

    async def test_an_unknown_search_outcome_stops_the_wave(self) -> None:
        class UnknownBroker:
            async def search(self, request) -> SearchResponse:  # noqa: ANN001
                raise TimeoutError("provider response was lost")

        runtimes = self.runtimes(
            investigator=investigator_script(find=False), curator=[], analyst=[]
        )
        with self.assertRaises(OperationReconciliationRequired):
            await run_wave(
                self.store,
                self.ledger,
                runtimes,
                contract=CONTRACT,
                wave_intent="探查不可确认的检索。",
                assignments=[
                    AssignmentDraft(
                        question_labels=("Q1",),
                        focus="未知结果",
                        why_it_matters="不能重复计费",
                        evidence_sought="供应商结果",
                    )
                ],
                broker=UnknownBroker(),
                reader=self.reader,
            )

        self.assertEqual(
            1, len(await self.ledger.pending_reconciliation(self.store.task_id))
        )


class BudgetHarvestTest(WaveFixture):
    """Running out of budget must not throw away evidence already paid for.

    The ceiling used to raise out of the branch before curation, so every
    candidate the Investigator had already saved was orphaned: snapshots in the
    store that no Curator ever judged.  The Lead then saw an empty failure,
    re-commissioned the same ground, and spent another full budget rediscovering
    the same sources.  Across the 1e matrix that loop dominated cost -- the worst
    fixture ran 382 searches for 5 Materials with 4 of 4 branches ending here.

    Harvesting must not soften the verdict: the branch is still an operational
    failure and the exhaustion is still reported, because a budget that ran out
    is never evidence that the research is finished.
    """

    async def test_an_exhausted_branch_still_curates_what_it_paid_for(self) -> None:
        # Two working turns are allowed, so the branch saves a candidate and is
        # then cut off mid-search with that candidate already committed.
        spec = replace(investigator_agent.SPEC, max_tool_turns=2)
        runtimes = self.runtimes(
            investigator=[
                ModelReply(tool_calls=(call("read", url="https://cdc.example/acip"),)),
                ModelReply(
                    tool_calls=(
                        call(
                            "save_candidate_source",
                            url="https://cdc.example/acip",
                            relevance_note="ACIP 的正式建议原文。",
                        ),
                    )
                ),
                ModelReply(tool_calls=(call("search", query="more", intent="gap"),)),
            ],
            curator=curator_script(),
            analyst=[ANALYST_REPLY],
        )

        with mock.patch.object(investigator_agent, "SPEC", spec):
            outcome = await run_wave(
                self.store,
                self.ledger,
                runtimes,
                contract=CONTRACT,
                wave_intent="确认预算耗尽时证据不被丢弃。",
                assignments=[
                    AssignmentDraft(
                        question_labels=("Q1",),
                        focus="ACIP 记录",
                        why_it_matters="唯一的一手入口",
                        evidence_sought="ACIP 官方记录",
                    )
                ],
                broker=self.broker,
                reader=self.reader,
            )

        branch = outcome.branches[0]
        # The verdict stays honest ...
        self.assertEqual("operational_failure", branch.status)
        self.assertTrue(
            any("tool turns" in item for item in branch.limitations),
            f"the exhaustion must be reported, got {branch.limitations}",
        )
        # ... and the evidence already bought is kept.
        self.assertEqual(1, len(branch.source_refs))
        self.assertEqual(1, len(branch.material_refs))
        self.assertTrue(outcome.changed_materials)


class SourceAccessEnforcementTest(WaveFixture):
    """The permission has to stop the call, not merely be described to the role.

    Under local_only the whole point is that the topic never reaches a search
    vendor. Before this was enforced, source_access reached the Investigator only
    as a sentence in its context and nothing checked it.
    """

    async def _run(self, access: tuple[str, ...], replies, local_reader=None):  # noqa: ANN001
        runtimes = self.runtimes(investigator=replies, curator=[], analyst=[])
        return await run_wave(
            self.store,
            self.ledger,
            runtimes,
            contract=CONTRACT,
            wave_intent="检验来源权限。",
            assignments=[
                AssignmentDraft(
                    question_labels=("Q1",),
                    focus="来源权限",
                    why_it_matters="决定可用来源族",
                    evidence_sought="任意可用来源",
                )
            ],
            broker=self.broker,
            reader=self.reader,
            source_access=access,
            local_reader=local_reader,
        )

    async def test_local_only_never_reaches_the_search_vendor(self) -> None:
        replies = [
            ModelReply(tool_calls=(call("search", query="x", intent="i", scope="both"),)),
            ModelReply(
                tool_calls=(
                    call(
                        "complete_investigation",
                        summary="本次委托未授权公开网络，改用本地资料。",
                        attempted_paths=["尝试公开检索，被权限拒绝"],
                        limitations=["未授权公开网络检索"],
                    ),
                )
            ),
        ]
        await self._run(("local_only",), replies)

        self.assertEqual([], self.broker.queries, "the broker must not be called")
        rows = await self._connection.execute_fetchall(
            "select count(*) from operations where kind='search'"
        )
        # Nothing was sent, so there is no operation to record or reconcile.
        self.assertEqual(0, rows[0][0])

    async def test_a_local_read_is_refused_without_the_local_grant(self) -> None:
        replies = [
            ModelReply(tool_calls=(call("read", url="local:notes.md"),)),
            ModelReply(
                tool_calls=(
                    call(
                        "complete_investigation",
                        summary="本地资料未获授权。",
                        attempted_paths=["尝试读取本地资料"],
                        limitations=["未授权读取用户本地资料"],
                    ),
                )
            ),
        ]
        await self._run(("public_web",), replies)

        rows = await self._connection.execute_fetchall(
            "select count(*) from operations where kind='fetch'"
        )
        self.assertEqual(0, rows[0][0])
        self.assertEqual([], self.reader.reads, "the web reader must not see a local ref")

    async def test_a_granted_local_read_becomes_a_snapshot(self) -> None:
        class StubLocal:
            def __init__(self) -> None:
                self.reads: list[str] = []

            def listing(self, limit: int = 500) -> tuple[str, ...]:
                return ("local:notes.md",)

            async def read(self, url: str) -> ReadResult:
                self.reads.append(url)
                return ReadResult(title="notes.md", url=url, content=PAGE)

        local = StubLocal()
        replies = [
            ModelReply(tool_calls=(call("read", url="local:notes.md"),)),
            ModelReply(
                tool_calls=(
                    call(
                        "save_candidate_source",
                        url="local:notes.md",
                        relevance_note="用户自己的记录，直接相关。",
                    ),
                )
            ),
            ModelReply(
                tool_calls=(
                    call(
                        "complete_investigation",
                        summary="读取了用户本地记录一份。",
                        attempted_paths=["用户本地资料库"],
                    ),
                )
            ),
        ]
        runtimes = self.runtimes(
            investigator=replies, curator=curator_script(), analyst=[ANALYST_REPLY]
        )
        outcome = await run_wave(
            self.store,
            self.ledger,
            runtimes,
            contract=CONTRACT,
            wave_intent="读取用户本地资料。",
            assignments=[
                AssignmentDraft(
                    question_labels=("Q1",),
                    focus="本地资料",
                    why_it_matters="用户提供的一手材料",
                    evidence_sought="用户记录",
                )
            ],
            broker=self.broker,
            reader=self.reader,
            source_access=("local_only",),
            local_reader=local,
        )

        self.assertEqual(["local:notes.md"], local.reads)
        self.assertEqual([], self.broker.queries)
        self.assertEqual(1, len(outcome.branches[0].source_refs))

    async def test_the_corpus_listing_is_shown_so_names_are_not_invented(self) -> None:
        class StubLocal:
            def listing(self, limit: int = 500) -> tuple[str, ...]:
                return ("local:notes.md", "local:sub/data.csv")

            async def read(self, url: str) -> ReadResult:  # pragma: no cover
                raise AssertionError("not read in this test")

        replies = [
            ModelReply(
                tool_calls=(
                    call(
                        "complete_investigation",
                        summary="先查看可用的本地资料清单。",
                        attempted_paths=["列出用户本地资料库"],
                        limitations=["尚未读取任何一份"],
                    ),
                )
            )
        ]
        await self._run(("user_files",), replies, local_reader=StubLocal())
        body = self.models["investigator"].seen[0]
        self.assertIn("local:sub/data.csv", body)


class StallRuleTest(unittest.TestCase):
    """The stopping rule is non-progress, not a wave ceiling.

    A preset wave limit bounds spending rather than sufficiency: it cut two 1e
    fixtures off mid-convergence while doing nothing about a run that circles
    forever adding nothing. §8.2 already required the non-progress pause.
    """

    def test_one_empty_wave_is_tolerated(self) -> None:
        """An exploratory wave that finds nothing is a legitimate outcome."""

        self.assertFalse(stalled([5, 0]))

    def test_two_consecutive_empty_waves_pause(self) -> None:
        self.assertTrue(stalled([5, 0, 0]))

    def test_progress_resets_the_count(self) -> None:
        self.assertFalse(stalled([0, 0, 3]))

    def test_a_short_history_never_stalls(self) -> None:
        self.assertFalse(stalled([]))
        self.assertFalse(stalled([0]))

    def test_a_converging_run_is_never_cut_off(self) -> None:
        """The observed trajectory of the fixture that had been paused early."""

        self.assertFalse(stalled([121, 49, 13, 15]))

    def test_the_tolerance_must_be_positive(self) -> None:
        with self.assertRaises(ValueError):
            stalled([0, 0], tolerance=0)


if __name__ == "__main__":
    unittest.main()
