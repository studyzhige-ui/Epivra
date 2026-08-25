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

from .agents import AgentProtocolError, AgentToolBudgetExhausted, invoke_agent
from .agents import curator as curator_agent
from .agents import investigator as investigator_agent
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
from .providers._http import (
    ProviderAuthError,
    ProviderQuotaError,
    ProviderRateLimitError,
    ProviderUnavailableError,
    SourceReadError,
    UnsafeUrlError,
)
from .reporting import RoleRuntime, synthesise
from .sources import (
    ArtifactValidationError,
    MaterialBody,
    SourceAnchor,
    SourceSnapshotBody,
    is_local_source,
    locate_quote,
    source_locator,
)
from .tools import SearchRequest, SearchRouting

#: Provider failures that are provably unbilled, so the ledger records a
#: retryable failure instead of freezing the operation.  A URL the policy
#: refused never left the process; a provider that returned an error served
#: no billable result.  Treating these as unknown outcomes would strand one
#: dead link as a terminal state for the rest of the task.
#:
#: An exhausted quota belongs here for the same reason -- "payment required" means
#: nothing was served.  It is currently unreachable through the broker, which
#: catches every provider exception upstream and reports it as a failed attempt
#: (:meth:`~deep_research_agent.tools.TransparentSearchBroker._call_provider`), so
#: this list carries no weight on the search path.  It is listed anyway because the
#: fetch path has no such catch, and because a reader should not have to discover
#: that the classification is load-bearing in one direction only.
_UNBILLED_SEARCH = (
    ProviderAuthError,
    ProviderQuotaError,
    ProviderRateLimitError,
    ProviderUnavailableError,
)
_UNBILLED_FETCH = (SourceReadError, UnsafeUrlError, *_UNBILLED_SEARCH)

BranchStatus = Literal["completed", "operational_failure"]


@dataclass(frozen=True, slots=True)
class SourcePermission:
    """What a branch may reach, enforced by code rather than described in prose.

    ``source_access`` used to travel to the Investigator only as a sentence in
    its context ("允许使用：public_web").  Nothing checked it, so under
    ``local_only`` -- the mode whose entire purpose is that the topic never
    reaches a search vendor -- the branch could still have searched Tavily and
    fetched any URL.  §2.2 puts tool permissions in the Trust Plane precisely
    because a permission a model is merely *told about* is not a permission.
    """

    network: bool
    local: bool

    @classmethod
    def of(cls, access: Sequence[str]) -> SourcePermission:
        families = set(access)
        return cls(
            network="public_web" in families and "local_only" not in families,
            local="user_files" in families or "local_only" in families,
        )

    def render(self) -> str:
        allowed = [
            name
            for name, ok in (("公开网络检索与抓取", self.network), ("用户本地资料库", self.local))
            if ok
        ]
        return "、".join(allowed) if allowed else "（无）"

#: What each research scope needs from a provider, resolved against the
#: capabilities providers declare about themselves.  The Investigator states the
#: need; the runtime picks the vendors, because which vendor to pay is a
#: deployment decision and not a research judgment.
_SCOPE_CAPABILITIES: Mapping[str, tuple[str, ...]] = {
    "academic": ("academic",),
    "web": ("web",),
    "both": (),
}


#: Consecutive waves that may add no Material before governance is paused.  Two
#: allows one genuinely exploratory wave that finds nothing -- a legitimate
#: outcome -- while refusing an endless run of them.
STALL_TOLERANCE = 2


def stalled(new_material_counts: Sequence[int], tolerance: int = STALL_TOLERANCE) -> bool:
    """Whether the recent waves have stopped producing evidence.

    This is the stopping rule, in place of a wave ceiling.  A preset limit on
    waves bounds *spending*, not sufficiency: it pauses converging runs early --
    two 1e fixtures were cut off mid-convergence that way -- while doing nothing
    about a run that circles forever adding nothing.

    ARCHITECTURE §8.2 already requires it: "无变化输出、A→B→A 振荡：进入可恢复暂停".
    Progress is measured from the MaterialDelta the Trust Plane computes, never
    from a model's claim to be making progress.
    """

    if tolerance < 1:
        raise ValueError("stall tolerance must be positive")
    recent = list(new_material_counts)[-tolerance:]
    return len(recent) >= tolerance and not any(recent)


def _provider_notes(attempts: Sequence[Any]) -> str:
    """Tell the role which providers did not answer, and why.

    Without this an empty result set is indistinguishable from a provider that
    was skipped or errored, and the Investigator is required to report that
    difference as an operational limit instead of as absent evidence.
    """

    unfinished = [item for item in attempts if getattr(item, "status", "") != "success"]
    if not unfinished:
        return ""
    rendered = "、".join(
        f"{getattr(item, 'provider_id', '?')}"
        f"（{getattr(item, 'status', '?')}"
        f"{'：' + str(item.error_type) if getattr(item, 'error_type', '') else ''}）"
        for item in unfinished
    )
    return f"（未参与本次检索的来源：{rendered}。这是运行事实，不是证据判断。）"


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
        permission: SourcePermission,
        local_reader: Any = None,
    ) -> None:
        self._store = store
        self._ledger = ledger
        self._runtime = runtime
        self._broker = broker
        self._reader = reader
        self._branch = branch
        self._permission = permission
        self._local_reader = local_reader
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
        if not self._permission.network:
            # Refused here, before the ledger: nothing was sent, so there is no
            # operation to record or reconcile.
            return (
                "本次委托未授权公开网络检索（运行事实，不是证据判断）。"
                f"当前授权：{self._permission.render()}。"
                "请改用已授权的来源族，或在总结里如实记下这条限制。"
            )
        query = str(arguments.get("query", "")).strip()
        intent = str(arguments.get("intent", "")).strip() or "discovery"
        scope = str(arguments.get("scope", "both")).strip() or "both"
        if scope not in _SCOPE_CAPABILITIES:
            # An unrecognised scope must widen the search, never raise: an
            # exception here is not an unbilled provider failure, so the ledger
            # would freeze the operation over a typo in one tool argument.
            scope = "both"
        request = OperationRequest(
            task_id=self._store.task_id,
            kind="search",
            role="investigator",
            execution=self._runtime.execution,
            parameters={
                "query": query,
                "intent": intent,
                # Scope changes which providers are paid, so it is part of what
                # makes two searches the same work.
                "scope": scope,
                "branch": str(self._branch),
            },
        )

        async def send() -> str:
            response = await self._broker.search(
                SearchRequest(
                    query=query,
                    intent=intent,
                    routing=SearchRouting(capabilities=_SCOPE_CAPABILITIES[scope]),
                )
            )
            lines = [
                f"{i}. {r.title}\n   {r.url}\n   {r.snippet[:300]}"
                for i, r in enumerate(response.results, start=1)
            ]
            body = "\n".join(lines) if lines else "（本次检索没有返回结果）"
            # An empty result set and an unreachable provider look identical
            # without this, and the Investigator is required to report the
            # difference as an operational limit rather than as absent evidence.
            notes = _provider_notes(getattr(response, "attempts", ()))
            return f"{body}\n{notes}" if notes else body

        found = await run_once(
            self._ledger, request, send, not_executed=_UNBILLED_SEARCH
        )
        return f"检索「{query}」结果（摘要是线索，不是证据）：\n{found}"

    async def _read(self, arguments: Mapping[str, Any]) -> str:
        url = str(arguments.get("url", "")).strip()
        if url in self.snapshots:
            return f"已读取过，快照引用 `{self.snapshots[url]}`。"

        local = is_local_source(url)
        if local and not self._permission.local:
            return (
                "本次委托未授权读取用户本地资料（运行事实，不是证据判断）。"
                f"当前授权：{self._permission.render()}。"
            )
        if not local and not self._permission.network:
            return (
                "本次委托未授权抓取公开网络（运行事实，不是证据判断）。"
                f"当前授权：{self._permission.render()}。"
                "只能读取 local: 开头的本地来源。"
            )
        source_reader = self._local_reader if local else self._reader
        if source_reader is None:
            return "该来源族在本次部署中没有可用的读取器。"

        try:
            # Checked before the ledger reserves anything, for the same reason the
            # permission check above is: a URL the domain will refuse cannot become
            # a snapshot, so fetching it first would pay for text that has nowhere
            # to go.  The refusal happens later regardless -- SourceSnapshotBody
            # canonicalises its own url -- but by then the fetch is billed and the
            # role sees only "the tool failed".
            source_locator(url)
        except ArtifactValidationError as error:
            return (
                f"这个来源标识无法作为正式来源身份：{error}（运行事实，不是证据判断）。"
                "请改用检索结果里给出的规范 URL。"
            )

        request = OperationRequest(
            task_id=self._store.task_id,
            kind="fetch",
            role="investigator",
            execution=self._runtime.execution,
            parameters={"url": url, "branch": str(self._branch)},
        )

        async def send() -> str:
            result = await source_reader.read(url)
            return f"{result.title}\n\n{result.content}"

        payload = await run_once(
            self._ledger, request, send, not_executed=_UNBILLED_FETCH
        )
        title, _, text = payload.partition("\n\n")
        if not text.strip():
            return f"读取 {url} 得到空正文，无法作为证据。"

        text_ref = await self._store_text(text)
        body = SourceSnapshotBody(
            url=url,
            title=title.strip() or url,
            text_ref=text_ref,
            # Read back from the ledger rather than stamped from the wall clock.
            # It is part of the body, so it decides the artifact's identity: a
            # fresh timestamp on every replay would mint a *second* snapshot of
            # text the ledger already had, inflating the source count and
            # orphaning the first.  The ledger's settled_at is also the more
            # honest answer -- when the fetch happened, not when it was read back.
            fetched_at=await self._ledger.settled_at(request.operation_id()),
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
    local_reader: Any = None,
) -> BranchOutcome:
    """Investigate, then curate, inside one assignment's boundary."""

    questions = contract.resolve(draft.question_labels)
    brief = draft.render(questions)

    tools = _InvestigationTools(
        store, ledger, runtimes["investigator"], broker=broker, reader=reader,
        branch=index,
        permission=SourcePermission.of(source_access),
        local_reader=local_reader,
    )
    exhausted = ""
    try:
        action = await invoke_agent(
            investigator_agent.SPEC,
            investigator_context(
                contract,
                assignment=brief,
                question_labels=draft.question_labels,
                known_claims=known_claims,
                source_access=source_access,
                local_sources=(
                    local_reader.listing()
                    if local_reader is not None
                    and SourcePermission.of(source_access).local
                    else ()
                ),
            ),
            model=runtimes["investigator"].model,
            ledger=ledger,
            task_id=store.task_id,
            execution=runtimes["investigator"].execution,
            context_limit=runtimes["investigator"].context_limit,
            validate=investigator_agent.make_validator(tools.candidates),
            handlers={
                "search": tools,
                "read": tools,
                "save_candidate_source": tools,
            },
        )
    except AgentToolBudgetExhausted as error:
        # The ceiling is a bounded stop, not a void.  Candidates already saved
        # are paid facts sitting in the store, and letting the exception escape
        # orphaned every one of them: the branch never reached curation, so the
        # Lead saw an empty failure, re-commissioned the same ground, and spent
        # another full budget finding the same sources.  Across the 1e matrix
        # that loop was the single largest cost -- 382 searches for 5 Materials
        # on the worst fixture, with 4 of 4 branches ending exactly here.
        #
        # Harvesting does not soften the verdict.  The status stays an
        # operational failure and the exhaustion is reported verbatim, because
        # "the budget ran out" must never read as "the research is done".
        exhausted = str(error)
        action = None
    summary = "" if action is None else str(action.arguments.get("summary", ""))
    attempted = (
        ()
        if action is None
        else tuple(str(x) for x in action.arguments.get("attempted_paths", ()))
    )
    limitations = (
        (exhausted,)
        if action is None
        else tuple(str(x) for x in action.arguments.get("limitations", ()))
    )
    status: BranchStatus = "operational_failure" if exhausted else "completed"

    if not tools.candidates:
        # An empty-handed branch is a legitimate outcome, not a failure: the Lead
        # decides what it means, with the attempted paths in front of it.
        return BranchOutcome(
            index=index,
            focus=draft.focus,
            status=status,
            summary=summary,
            attempted_paths=attempted,
            limitations=limitations,
        )

    candidates = {
        ref: SourceSnapshotBody.decode(await store.body(ref))
        for ref in sorted(tools.candidates)
    }
    curation = _CurationTools(store, candidates)
    try:
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
            context_limit=runtimes["curator"].context_limit,
            validate=curator_agent.make_validator(curation.handled, len(candidates)),
            handlers={
                "read_saved_source": curation,
                "record_material": curation,
                "reject_candidate": curation,
            },
        )
    except AgentProtocolError as error:
        # The same harvest the Investigator side already does, for the same
        # reason.  A Curator that cannot close its turn has still committed every
        # Material it recorded -- those are durable artifacts, not pending work --
        # and letting the exception escape reported the branch as having produced
        # nothing while the wave's own delta counted them.  The Lead then read a
        # branch summary and an evidence count that disagreed.
        #
        # As on the Investigator side, harvesting does not soften the verdict: the
        # status stays an operational failure and the reason is reported verbatim.
        limitations = (*limitations, str(error))
        status = "operational_failure"

    return BranchOutcome(
        index=index,
        focus=draft.focus,
        status=status,
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
    local_reader: Any = None,
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
                local_reader=local_reader,
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
    "STALL_TOLERANCE",
    "BranchOutcome",
    "BranchStatus",
    "SourcePermission",
    "WaveOutcome",
    "run_wave",
    "stalled",
]
