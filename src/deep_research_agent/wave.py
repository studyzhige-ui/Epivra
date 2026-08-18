"""Research Wave: parallel investigation, curation, and one incremental Analyst.

A Wave is a set of assignments that can run at once, share no dependencies, and
serve the same next decision.  Branches run concurrently and are merged by
assignment index rather than completion order, so the same wave always produces
the same evidence set regardless of which provider was slow that day.

**Durability comes from the operation ledger and the artifact store, not from a
second graph state.**  Every paid call inside a branch is ledger-guarded, and a
branch that finished has already committed its Materials, so recovery is
recomputing what is missing rather than replaying a saved plan.  Adding graph
checkpoints for branch progress would create a second account of what happened,
which the architecture bars precisely because the two would drift.

The MaterialDelta is computed by the Trust Plane from the active Material set
before and after, never reported by a model.  It is what makes "exactly one
Analyst per material-changing wave" a mechanical fact.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from .agents import curator as curator_agent
from .agents import investigator as investigator_agent
from .agents import invoke_agent
from .agents.lead import AssignmentDraft
from .artifact_store import SqliteArtifactStore
from .artifacts import Provenance, evidence_set_id
from .context import (
    curator_context,
    investigator_context,
    load_evidence,
)
from .contract import ResearchContract
from .operations import (
    OperationRequest,
    SqliteOperationLedger,
    run_once,
)
from .reporting import RoleRuntime, synthesise
from .sources import (
    ArtifactValidationError,
    MaterialBody,
    SourceAnchor,
    SourceSnapshotBody,
    locate_quote,
)
from .tools import SearchRequest

BranchStatus = Literal["completed", "operational_failure"]


@dataclass(frozen=True, slots=True)
class BranchOutcome:
    """What one assignment produced, in a form the Lead can read quickly."""

    index: int
    focus: str
    status: BranchStatus
    material_refs: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    summary: str = ""
    attempted_paths: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    detail: str = ""

    def render(self) -> str:
        lines = [f"### 任务 {self.index}：{self.focus}", f"状态：{self.status}"]
        if self.summary:
            lines.append(self.summary)
        if self.material_refs:
            lines.append(f"新增正式素材：{len(self.material_refs)} 条")
        if self.attempted_paths:
            lines.append(
                "已尝试路径：\n" + "\n".join(f"- {p}" for p in self.attempted_paths)
            )
        if self.limitations:
            lines.append(
                "运行限制（不是证据结论）：\n"
                + "\n".join(f"- {item}" for item in self.limitations)
            )
        if self.detail:
            lines.append(f"失败详情：{self.detail}")
        return "\n".join(lines)


@dataclass
class WaveOutcome:
    """The compact result the Lead reads; raw traces stay out of its context."""

    intent: str
    branches: tuple[BranchOutcome, ...] = ()
    evidence_set_before: str = ""
    evidence_set_after: str = ""
    new_material_refs: tuple[str, ...] = ()
    analyst_ran: bool = False
    synthesis_ref: str = ""

    @property
    def changed_materials(self) -> bool:
        """Whether this wave produced a MaterialDelta at all."""

        return bool(self.new_material_refs)

    def render(self) -> str:
        header = [
            f"## Wave 结果：{self.intent}",
            f"证据集：{self.evidence_set_before or '(空)'} → {self.evidence_set_after}",
            f"新增素材：{len(self.new_material_refs)} 条",
        ]
        if not self.analyst_ran:
            header.append("本 Wave 没有产生素材变化，未运行 Analyst。")
        return "\n".join(header) + "\n\n" + "\n\n".join(
            branch.render() for branch in self.branches
        )


class _InvestigationTools:
    """Working tools for one Investigator branch, each ledger-guarded.

    A handler routes its own external call through the ledger rather than
    relying on the model call's entry: a crash between the model asking for a
    search and the search running would otherwise replay the model turn while
    re-charging the provider.
    """

    def __init__(
        self,
        store: SqliteArtifactStore,
        ledger: SqliteOperationLedger,
        runtime: RoleRuntime,
        *,
        broker: Any,
        reader: Any,
        branch: int,
    ) -> None:
        self._store = store
        self._ledger = ledger
        self._runtime = runtime
        self._broker = broker
        self._reader = reader
        self._branch = branch
        self.snapshots: dict[str, str] = {}
        self.candidates: dict[str, str] = {}

    async def __call__(self, name: str, arguments: Mapping[str, Any]) -> str:
        if name == "search":
            return await self._search(arguments)
        if name == "read":
            return await self._read(arguments)
        if name == "save_candidate_source":
            return self._save(arguments)
        return f"未知工具 {name!r}。"

    async def _search(self, arguments: Mapping[str, Any]) -> str:
        query = str(arguments.get("query", "")).strip()
        intent = str(arguments.get("intent", "")).strip() or "discovery"
        request = OperationRequest(
            task_id=self._store.task_id,
            kind="search",
            role="investigator",
            execution=self._runtime.execution,
            parameters={
                "query": query,
                "intent": intent,
                "branch": str(self._branch),
            },
        )

        async def send() -> str:
            response = await self._broker.search(
                SearchRequest(query=query, intent=intent)
            )
            lines = [
                f"{i}. {r.title}\n   {r.url}\n   {r.snippet[:300]}"
                for i, r in enumerate(response.results, start=1)
            ]
            return "\n".join(lines) if lines else "（本次检索没有返回结果）"

        found = await run_once(self._ledger, request, send)
        return f"检索「{query}」结果（摘要是线索，不是证据）：\n{found}"

    async def _read(self, arguments: Mapping[str, Any]) -> str:
        url = str(arguments.get("url", "")).strip()
        if url in self.snapshots:
            return f"已读取过，快照引用 `{self.snapshots[url]}`。"

        request = OperationRequest(
            task_id=self._store.task_id,
            kind="fetch",
            role="investigator",
            execution=self._runtime.execution,
            parameters={"url": url, "branch": str(self._branch)},
        )

        async def send() -> str:
            result = await self._reader.read(url)
            return f"{result.title}\n\n{result.content}"

        payload = await run_once(self._ledger, request, send)
        title, _, text = payload.partition("\n\n")
        if not text.strip():
            return f"读取 {url} 得到空正文，无法作为证据。"

        text_ref = await self._store_text(text)
        body = SourceSnapshotBody(
            url=url, title=title.strip() or url, text_ref=text_ref
        )
        envelope = await self._store.put(
            kind="source_snapshot",
            body=body.encode(),
            provenance=Provenance(producer="investigator"),
        )
        self.snapshots[url] = envelope.artifact_id
        preview = text[:1500]
        return (
            f"已保存快照 `{envelope.artifact_id}`（{len(text):,} 字符）。\n"
            f"正文开头：\n{preview}"
        )

    async def _store_text(self, text: str):
        # The artifact store owns the content store; reuse it so the body is
        # written once and addressed by hash.
        return await self._store._content_store.put(text)  # noqa: SLF001

    def _save(self, arguments: Mapping[str, Any]) -> str:
        url = str(arguments.get("url", "")).strip()
        ref = self.snapshots.get(url)
        if ref is None:
            return (
                f"{url} 还没有被 read 保存过，不能标记为候选。"
                "只有已保存正文的来源才能进入策展。"
            )
        self.candidates[ref] = str(arguments.get("relevance_note", "")).strip()
        return f"已标记候选来源 `{ref}`。"


class _CurationTools:
    """Working tools for one Curator branch; identity is assigned here, not asked for."""

    def __init__(
        self,
        store: SqliteArtifactStore,
        candidates: Mapping[str, SourceSnapshotBody],
    ) -> None:
        self._store = store
        self._candidates = candidates
        self.handled: dict[str, str] = {}
        self.material_refs: list[str] = []

    async def __call__(self, name: str, arguments: Mapping[str, Any]) -> str:
        if name == "read_saved_source":
            return await self._read(arguments)
        if name == "record_material":
            return await self._record(arguments)
        if name == "reject_candidate":
            return self._reject(arguments)
        return f"未知工具 {name!r}。"

    async def _text(self, ref: str) -> str:
        body = self._candidates[ref]
        return await self._store._content_store.get(body.text_ref)  # noqa: SLF001

    async def _read(self, arguments: Mapping[str, Any]) -> str:
        ref = str(arguments.get("source_ref", "")).strip()
        if ref not in self._candidates:
            return f"`{ref}` 不在本次候选来源中。"
        offset = int(arguments.get("offset", 0) or 0)
        text = await self._text(ref)
        window = text[offset : offset + 12_000]
        tail = "" if offset + 12_000 >= len(text) else "\n（正文未完，可用 offset 继续读取）"
        return f"`{ref}` 正文 [{offset}:{offset + len(window)}]：\n{window}{tail}"

    async def _record(self, arguments: Mapping[str, Any]) -> str:
        ref = str(arguments.get("source_ref", "")).strip()
        if ref not in self._candidates:
            return f"`{ref}` 不在本次候选来源中，无法据此创建素材。"
        quote = str(arguments.get("exact_quote", ""))
        text = await self._text(ref)
        try:
            locator = locate_quote(text, quote)
        except ArtifactValidationError:
            return (
                "引文在保存正文中不存在（必须逐字一致，含标点与空白）。"
                "请重新读取正文并原样复制一段。"
            )
        try:
            body = MaterialBody.create(
                content=str(arguments.get("content", "")),
                boundaries=str(arguments.get("boundaries", "")),
                anchors=(
                    SourceAnchor(
                        source_ref=ref, exact_quote=quote, locator=locator
                    ),
                ),
            )
            envelope = await self._store.put(
                kind="material",
                body=body.encode(),
                parent_refs=body.source_refs,
                provenance=Provenance(producer="curator"),
            )
        except ArtifactValidationError as error:
            return f"素材未被接受：{error}"

        self.handled[ref] = "recorded"
        self.material_refs.append(envelope.artifact_id)
        return f"已接纳为正式素材 `{envelope.artifact_id}`。"

    def _reject(self, arguments: Mapping[str, Any]) -> str:
        ref = str(arguments.get("source_ref", "")).strip()
        if ref not in self._candidates:
            return f"`{ref}` 不在本次候选来源中。"
        self.handled[ref] = "rejected"
        return f"已拒绝 `{ref}`：{str(arguments.get('reason', '')).strip()}"


async def _run_branch(
    store: SqliteArtifactStore,
    ledger: SqliteOperationLedger,
    runtimes: Mapping[str, RoleRuntime],
    *,
    contract: ResearchContract,
    draft: AssignmentDraft,
    index: int,
    broker: Any,
    reader: Any,
    known_claims: Sequence[str],
    source_access: Sequence[str],
) -> BranchOutcome:
    """Investigate, then curate, inside one assignment's boundary."""

    questions = contract.resolve(draft.question_labels)
    brief = draft.render(questions)

    tools = _InvestigationTools(
        store, ledger, runtimes["investigator"], broker=broker, reader=reader,
        branch=index,
    )
    action = await invoke_agent(
        investigator_agent.SPEC,
        investigator_context(
            contract,
            assignment=brief,
            question_labels=draft.question_labels,
            known_claims=known_claims,
            source_access=source_access,
        ),
        model=runtimes["investigator"].model,
        ledger=ledger,
        task_id=store.task_id,
        execution=runtimes["investigator"].execution,
        validate=investigator_agent.make_validator(tools.candidates),
        handlers={
            "search": tools,
            "read": tools,
            "save_candidate_source": tools,
        },
    )
    summary = str(action.arguments.get("summary", ""))
    attempted = tuple(str(x) for x in action.arguments.get("attempted_paths", ()))
    limitations = tuple(str(x) for x in action.arguments.get("limitations", ()))

    if not tools.candidates:
        # An empty-handed branch is a legitimate outcome, not a failure: the Lead
        # decides what it means, with the attempted paths in front of it.
        return BranchOutcome(
            index=index,
            focus=draft.focus,
            status="completed",
            summary=summary,
            attempted_paths=attempted,
            limitations=limitations,
        )

    candidates = {
        ref: SourceSnapshotBody.decode(await store.body(ref))
        for ref in sorted(tools.candidates)
    }
    curation = _CurationTools(store, candidates)
    await invoke_agent(
        curator_agent.SPEC,
        curator_context(
            contract,
            assignment=brief,
            candidates=candidates,
            notes=tools.candidates,
        ),
        model=runtimes["curator"].model,
        ledger=ledger,
        task_id=store.task_id,
        execution=runtimes["curator"].execution,
        validate=curator_agent.make_validator(curation.handled, len(candidates)),
        handlers={
            "read_saved_source": curation,
            "record_material": curation,
            "reject_candidate": curation,
        },
    )

    return BranchOutcome(
        index=index,
        focus=draft.focus,
        status="completed",
        material_refs=tuple(curation.material_refs),
        source_refs=tuple(sorted(candidates)),
        summary=summary,
        attempted_paths=attempted,
        limitations=limitations,
    )


async def run_wave(
    store: SqliteArtifactStore,
    ledger: SqliteOperationLedger,
    runtimes: Mapping[str, RoleRuntime],
    *,
    contract: ResearchContract,
    wave_intent: str,
    assignments: Sequence[AssignmentDraft],
    broker: Any,
    reader: Any,
    source_access: Sequence[str] = ("public_web",),
) -> WaveOutcome:
    """Run one wave to completion and, if it changed evidence, synthesise once."""

    if not assignments:
        raise ValueError("a wave needs at least one assignment")

    before = await load_evidence(store)
    known = [view.body.content for view in before.materials][:20]

    branches = await asyncio.gather(
        *(
            _run_branch(
                store,
                ledger,
                runtimes,
                contract=contract,
                draft=draft,
                index=index,
                broker=broker,
                reader=reader,
                known_claims=known,
                source_access=source_access,
            )
            for index, draft in enumerate(assignments, start=1)
        ),
        # One branch failing must not discard the others' evidence; the Lead is
        # told which failed and decides whether that changes the picture.
        return_exceptions=True,
    )

    outcomes: list[BranchOutcome] = []
    for index, result in enumerate(branches, start=1):
        if isinstance(result, BaseException):
            outcomes.append(
                BranchOutcome(
                    index=index,
                    focus=assignments[index - 1].focus,
                    status="operational_failure",
                    detail=f"{type(result).__name__}: {result}",
                )
            )
        else:
            outcomes.append(result)

    after = await load_evidence(store)
    delta = tuple(
        ref for ref in after.material_refs if ref not in set(before.material_refs)
    )
    outcome = WaveOutcome(
        intent=wave_intent,
        branches=tuple(outcomes),
        evidence_set_before=evidence_set_id(before.material_refs),
        evidence_set_after=evidence_set_id(after.material_refs),
        new_material_refs=delta,
    )

    # Exactly one Analyst per material-changing wave, and none otherwise. Both
    # halves are mechanical: the delta is computed here, not reported by a model.
    if outcome.changed_materials:
        await synthesise(
            store, ledger, runtimes["analyst"], store.task_id, contract, after
        )
        outcome.analyst_ran = True
        outcome.synthesis_ref = (await store.active_view()).head("synthesis") or ""
    return outcome


__all__ = [
    "BranchOutcome",
    "BranchStatus",
    "WaveOutcome",
    "run_wave",
]
