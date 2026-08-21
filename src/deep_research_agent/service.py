"""The application service: one place that runs a study, for every interface.

A CLI, an MCP server and a web UI must not each reimplement governance.  They
differ only in how they collect a request and render progress, so this module
owns the whole lifecycle and they stay thin adapters over it.

**No interface holds state.**  Everything durable lives in the artifact store and
the operation ledger, so "resume" is opening the same database again -- proven in
Phase 1e, where a killed run continued across three separate processes and
published.  An interface that cached task state would become a second account of
truth, which §2.3 bars.

Progress is emitted as :class:`Event` values rather than printed.  A service that
writes to stdout cannot be used by a server, and a service that returns only a
final answer cannot show a 90-minute study making progress.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import aiosqlite

from .agents import AgentProtocolError, invoke_agent
from .agents import architect as architect_agent
from .agents import lead as lead_agent
from .application import build_runtimes
from .approval import ApprovalBody, approval_card, decision_for, record_decision
from .artifact_store import SqliteArtifactStore
from .artifacts import Provenance
from .config import RuntimeConfig, load_config
from .content_store import SqliteContentStore
from .context import RoleContext, latest_body, lead_context, load_evidence
from .contract import CommissionBody, ResearchContract, SourceAccess
from .operations import SqliteOperationLedger
from .providers import build_search_providers
from .providers.local import LocalCorpusReader
from .providers.reader import PublicHttpReader, extract_pdf_in_subprocess
from .reporting import RoleRuntime, run_reporting
from .tools import TransparentSearchBroker
from .wave import run_wave

TaskState = Literal[
    "clarification_requested",
    "awaiting_approval",
    "researching",
    "published",
    "halted",
    "paused",
]

#: Consecutive Waves that may add no Material before governance pauses.  This is
#: not a research budget: the Lead decides when evidence is sufficient, and this
#: only catches the case where waves have stopped producing anything at all.
STALL_TOLERANCE = 2

#: Runaway guard only, set far above anything an observed run has needed (the
#: deepest so far used three waves).  Reaching it is a pause, never "finished".
RUNAWAY_WAVE_GUARD = 24


@dataclass(frozen=True, slots=True)
class Event:
    """One thing worth telling the user about, in their terms.

    ``detail`` carries structured values an interface may want to render richly
    (a web UI showing a progress bar, say) without parsing the message text.
    """

    kind: str
    message: str
    detail: Mapping[str, Any] = field(default_factory=dict)


Listener = Callable[[Event], None]


def _ignore(_event: Event) -> None:
    return None


@dataclass(frozen=True, slots=True)
class Task:
    """What a caller needs to show a task in a list."""

    task_id: str
    request: str
    language: str
    source_access: tuple[str, ...]
    state: TaskState
    materials: int = 0
    sources: int = 0


def new_task_id(commission: CommissionBody, *, created_at: str) -> str:
    """Runtime-owned task identity.

    Derived rather than random so the same commission at the same instant is the
    same task, and stamped with time so asking the same question twice starts two
    studies rather than silently resuming the first.
    """

    digest = hashlib.sha256(
        f"{commission.encode()}\n{created_at}".encode()
    ).hexdigest()
    return f"t_{digest[:12]}"


@dataclass(slots=True)
class ResearchService:
    """Runs studies against one database that may hold many tasks.

    The artifact store and ledger are already task-isolated, so one file holds
    every study a user has started -- which is what makes "list my tasks" and
    "resume that one" trivial rather than a directory convention.
    """

    connection: aiosqlite.Connection
    environ: Mapping[str, str]
    config: RuntimeConfig | None = None
    corpus_root: Path | None = None
    _runtimes: dict[str, RoleRuntime] | None = field(default=None, repr=False)
    _content: SqliteContentStore | None = field(default=None, repr=False)
    _ledger: SqliteOperationLedger | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self.config is None:
            self.config = load_config(self.environ)

    # ---------------------------------------------------------------- plumbing

    async def setup(self) -> None:
        content = SqliteContentStore(self.connection)
        await content.setup()
        self._content = content
        ledger = SqliteOperationLedger(self.connection, content)
        await ledger.setup()
        self._ledger = ledger
        # The artifacts table is shared by every task and filtered by task_id, so
        # its DDL belongs to service setup.  Leaving it to the first per-task
        # store meant reading the task list on a fresh database failed before any
        # study had been written -- an empty list is the correct answer there.
        await SqliteArtifactStore(
            self.connection, content, task_id="__schema__"
        ).setup()

    @property
    def ledger(self) -> SqliteOperationLedger:
        if self._ledger is None:
            raise RuntimeError("call setup() before using the service")
        return self._ledger

    def _store(self, task_id: str) -> SqliteArtifactStore:
        if self._content is None:
            raise RuntimeError("call setup() before using the service")
        return SqliteArtifactStore(self.connection, self._content, task_id=task_id)

    def runtimes(self) -> dict[str, RoleRuntime]:
        """Bind roles to models once per service, not once per call."""

        if self._runtimes is None:
            self._runtimes = build_runtimes(self.environ, config=self.config)
        return self._runtimes

    def _local_reader(self, access: Sequence[str]) -> LocalCorpusReader | None:
        """Built only when the Commission authorises reading local files."""

        if not ({"user_files", "local_only"} & set(access)):
            return None
        if self.corpus_root is None:
            raise ValueError(
                "this commission authorises local files but no corpus root was given"
            )
        return LocalCorpusReader(
            root=self.corpus_root, extract_pdf=extract_pdf_in_subprocess
        )

    def _broker(self, access: Sequence[str]):  # noqa: ANN202
        """No network client at all when the Commission forbids the network.

        Returning None rather than an empty broker keeps the prohibition
        mechanical: there is no object present that could reach a vendor.
        """

        assert self.config is not None
        if "local_only" in access:
            return None, None
        providers = build_search_providers(
            self.config.search_providers,
            self.config.academic_providers,
            environ=self.environ,
            ncbi_api_key=self.config.ncbi_api_key,
            contact_email=self.config.contact_email,
        )
        return TransparentSearchBroker(providers), PublicHttpReader()

    # ------------------------------------------------------------------ public

    async def open_task(
        self,
        request: str,
        *,
        language: str,
        source_access: Sequence[SourceAccess],
        constraints: Sequence[str] = (),
        created_at: str,
        listen: Listener = _ignore,
    ) -> Task:
        """Commit the commission and let the Architect propose or ask.

        Both outcomes are legitimate ends to this step: a commission too vague to
        plan earns one question instead of a guess.
        """

        commission = CommissionBody(
            request=request,
            source_access=tuple(source_access),
            language=language,
            constraints=tuple(constraints),
        )
        task_id = new_task_id(commission, created_at=created_at)
        store = self._store(task_id)
        await store.setup()

        head = (await store.active_view()).head("commission")
        if head is None:
            envelope = await store.put(
                kind="commission",
                body=commission.encode(),
                provenance=Provenance(producer="user", produced_at=created_at),
            )
            commission_ref = envelope.artifact_id
        else:
            commission_ref = head

        contract = await self._propose(store, commission, commission_ref, listen)
        if contract is None:
            return await self.task(task_id)

        listen(
            Event(
                "contract_proposed",
                approval_card(contract),
                {"task_id": task_id},
            )
        )
        return await self.task(task_id)

    async def approve(self, task_id: str, note: str = "") -> None:
        """Record the user's approval against the exact Contract they read."""

        store = self._store(task_id)
        view = await store.active_view()
        head = view.head("research_contract")
        if head is None:
            raise ValueError(f"task {task_id} has no Contract to approve")
        await record_decision(
            store, head, ApprovalBody(decision="approved", note=note)
        )

    async def advance(
        self, task_id: str, *, listen: Listener = _ignore
    ) -> TaskState:
        """Govern until the study reaches a terminal state.

        Safe to call again after any interruption: completed provider calls
        replay from the ledger and committed artifacts are simply read back.
        """

        store = self._store(task_id)
        contract = await self._approved_contract(store)
        commission = await self._commission(store)
        broker, reader = self._broker(commission.source_access)
        local_reader = self._local_reader(commission.source_access)
        return await self._govern(
            store,
            contract=contract,
            commission=commission,
            broker=broker,
            reader=reader,
            local_reader=local_reader,
            listen=listen,
        )

    async def task(self, task_id: str) -> Task:
        """Derive the task's state from heads and the ledger, never from a flag."""

        store = self._store(task_id)
        view = await store.active_view()
        commission = await self._commission(store)
        materials = len(view.active("material"))
        sources = len(view.active("source_snapshot"))

        contract_head = view.head("research_contract")
        state: TaskState
        if contract_head is None:
            state = "clarification_requested"
        elif view.head("publication_receipt") is not None:
            state = "published"
        else:
            decision = await decision_for(store, contract_head)
            if decision is None or decision.decision != "approved":
                state = "awaiting_approval"
            else:
                state = "paused" if materials or sources else "researching"
        return Task(
            task_id=task_id,
            request=commission.request,
            language=commission.language,
            source_access=tuple(commission.source_access),
            state=state,
            materials=materials,
            sources=sources,
        )

    async def tasks(self) -> tuple[Task, ...]:
        rows = await self.connection.execute_fetchall(
            "SELECT DISTINCT task_id FROM artifacts ORDER BY task_id"
        )
        return tuple([await self.task(str(row[0])) for row in rows])

    async def report(self, task_id: str) -> str | None:
        """The published report, or None if this task has not published one."""

        published = await latest_body(self._store(task_id), "publication_receipt")
        return None if published is None else published[1]

    async def delete_research(self, task_id: str) -> bool:
        """Remove a study and everything it produced.  Irreversible.

        One operation serves both "cancel this unfinished research" and "delete
        this finished research" -- they differ only in what the interface calls
        them, because in both cases the user is saying the study should stop
        existing.  Keeping them as separate mechanisms would invite one of them to
        leave data behind.

        Valid from **any** state, including mid-research: a user who no longer
        wants a study must not have to wait for it to finish first.  What it is
        not is a pause -- pausing keeps everything and can be resumed, and the
        interface must never offer these two as if they were the same choice.

        Content blobs are left alone. They are content-addressed and shared
        between tasks, so deleting them by task would corrupt whatever else
        referenced the same bytes; an unreferenced blob is inert.
        """

        rows = await self.connection.execute_fetchall(
            "SELECT COUNT(*) FROM artifacts WHERE task_id = ?", (task_id,)
        )
        if not rows or not int(rows[0][0]):
            return False
        for table in ("artifacts", "artifact_dispositions", "operations"):
            await self.connection.execute(
                f"DELETE FROM {table} WHERE task_id = ?", (task_id,)
            )
        await self.connection.commit()
        return True

    async def approval_card(self, task_id: str) -> str:
        """The exact card the user must read before approving."""

        return approval_card(await self._contract(self._store(task_id)))

    # ----------------------------------------------------------------- private

    async def _commission(self, store: SqliteArtifactStore) -> CommissionBody:
        found = await latest_body(store, "commission")
        if found is None:
            raise ValueError(f"task {store.task_id} does not exist")
        return CommissionBody.decode(found[1])

    async def _contract(self, store: SqliteArtifactStore) -> ResearchContract:
        found = await latest_body(store, "research_contract")
        if found is None:
            raise ValueError(f"task {store.task_id} has no Contract")
        return ResearchContract.decode(found[1])

    async def _approved_contract(
        self, store: SqliteArtifactStore
    ) -> ResearchContract:
        view = await store.active_view()
        head = view.head("research_contract")
        if head is None:
            raise ValueError(f"task {store.task_id} has no Contract")
        decision = await decision_for(store, head)
        if decision is None or decision.decision != "approved":
            raise ValueError(
                f"task {store.task_id} has not been approved; research must not "
                "start before the user accepts the Contract"
            )
        return ResearchContract.decode(await store.body(head))

    async def _propose(
        self,
        store: SqliteArtifactStore,
        commission: CommissionBody,
        commission_ref: str,
        listen: Listener,
    ) -> ResearchContract | None:
        existing = (await store.active_view()).head("research_contract")
        if existing is not None:
            return ResearchContract.decode(await store.body(existing))

        runtimes = self.runtimes()
        body = architect_agent.architect_context_body(
            commission.request,
            source_access=commission.source_access,
            language=commission.language,
            constraints=commission.constraints,
            pack_menu="（本次运行不启用任何能力包。）",
        )
        action = await invoke_agent(
            architect_agent.SPEC,
            RoleContext(
                role="architect",
                purpose="把用户委托转化为可审批的研究合同",
                body=body,
                input_refs=(commission_ref,),
            ),
            model=runtimes["architect"].model,
            ledger=self.ledger,
            task_id=store.task_id,
            execution=runtimes["architect"].execution,
            validate=architect_agent.make_validator(None),
        )
        if action.name == "ask_scope_question":
            listen(
                Event(
                    "clarification_requested",
                    str(action.arguments["question"]),
                    {
                        "why": str(action.arguments["why_it_changes_the_plan"]),
                        "task_id": store.task_id,
                    },
                )
            )
            return None

        contract = architect_agent.contract_from_action(
            action.arguments, language=commission.language
        )
        await store.put(
            kind="research_contract",
            body=contract.encode(),
            parent_refs=(commission_ref,),
            provenance=Provenance(producer="architect"),
        )
        return contract

    async def _govern(
        self,
        store: SqliteArtifactStore,
        *,
        contract: ResearchContract,
        commission: CommissionBody,
        broker: Any,
        reader: Any,
        local_reader: Any,
        listen: Listener,
    ) -> TaskState:
        latest_outcome = ""
        progress: list[int] = []

        for round_index in range(1, RUNAWAY_WAVE_GUARD + 1):
            evidence = await load_evidence(store)
            synthesis = await latest_body(store, "synthesis")
            memory = await latest_body(store, "research_memory")
            previous = lead_agent.MemoryBody.decode(memory[1]) if memory else None

            try:
                action = await invoke_agent(
                    lead_agent.SPEC,
                    lead_context(
                        contract,
                        evidence,
                        synthesis=synthesis[1] if synthesis else "",
                        memory=previous.render() if previous else "",
                        latest_outcome=latest_outcome,
                    ),
                    model=self.runtimes()["lead"].model,
                    ledger=self.ledger,
                    task_id=store.task_id,
                    execution=self.runtimes()["lead"].execution,
                    validate=lead_agent.make_validator(contract),
                )
            except AgentProtocolError as error:
                # A role that cannot act is the recoverable pause §8.2 requires.
                # Every artifact is already committed, so nothing is lost and a
                # later call to advance() continues from here.
                listen(
                    Event(
                        "paused",
                        f"治理暂停：{error}。已保全 {len(evidence.materials)} 份素材，"
                        "重新继续同一任务即可。",
                        {"round": round_index},
                    )
                )
                return "paused"

            await self._commit_memory(store, action.arguments, previous)

            if action.name == "commission_report":
                return await self._report(store, action.arguments, listen)

            if action.name != "commission_wave":
                listen(
                    Event(
                        "paused",
                        "研究负责人请求人工判断。",
                        dict(action.arguments),
                    )
                )
                return "paused"

            if len(progress) >= STALL_TOLERANCE and not any(
                progress[-STALL_TOLERANCE:]
            ):
                # Measured from the Trust Plane's MaterialDelta, never from the
                # Lead's own claim to be making progress.
                listen(
                    Event(
                        "paused",
                        f"连续 {STALL_TOLERANCE} 个批次没有产生任何素材，"
                        "研究已停止发现新证据。",
                        {"round": round_index},
                    )
                )
                return "paused"

            drafts = lead_agent.parse_assignments(
                contract, action.arguments["assignments"]
            )
            listen(
                Event(
                    "wave_started",
                    str(action.arguments["wave_intent"]),
                    {
                        "round": round_index,
                        "assignments": [draft.focus for draft in drafts],
                    },
                )
            )
            wave = await run_wave(
                store,
                self.ledger,
                self.runtimes(),
                contract=contract,
                wave_intent=str(action.arguments["wave_intent"]),
                assignments=drafts,
                broker=broker,
                reader=reader,
                source_access=commission.source_access,
                local_reader=local_reader,
            )
            progress.append(len(wave.new_material_refs))
            latest_outcome = wave.render()
            listen(
                Event(
                    "wave_finished",
                    f"新增素材 {len(wave.new_material_refs)} 份"
                    f"（{'已重新综合' if wave.analyst_ran else '证据未变化，未综合'}）",
                    {
                        "round": round_index,
                        "new_materials": len(wave.new_material_refs),
                        "analyst_ran": wave.analyst_ran,
                    },
                )
            )

        listen(
            Event(
                "paused",
                f"已达 {RUNAWAY_WAVE_GUARD} 个批次的失控保护上限；这是暂停，不是完成。",
                {},
            )
        )
        return "paused"

    async def _report(
        self, store: SqliteArtifactStore, arguments: Mapping[str, Any], listen: Listener
    ) -> TaskState:
        outcome = await run_reporting(
            store,
            self.ledger,
            self.runtimes(),
            report_brief=str(arguments["report_brief"]),
            stop_rationale=str(arguments["stop_rationale"]),
        )
        for index, review in enumerate(outcome.reviews, start=1):
            listen(
                Event(
                    "review",
                    ("通过" if review.approved else "阻断")
                    + f"（第 {index} 轮，{len(review.findings)} 项阻断）",
                    {
                        "approved": review.approved,
                        "findings": list(review.findings),
                    },
                )
            )

        if not outcome.published:
            listen(
                Event("halted", f"未发布：{outcome.halted_reason}", {}),
            )
            return "halted"

        assert outcome.rendered is not None
        listen(
            Event(
                "published",
                f"已发布：{len(outcome.rendered.markdown):,} 字符，"
                f"{len(outcome.rendered.references)} 条参考，"
                f"引用 {len(outcome.rendered.used_material_refs)} 份素材。",
                {
                    "publication_ref": outcome.publication_ref,
                    "characters": len(outcome.rendered.markdown),
                    "references": len(outcome.rendered.references),
                },
            )
        )
        return "published"

    async def _commit_memory(
        self,
        store: SqliteArtifactStore,
        arguments: Mapping[str, Any],
        previous: lead_agent.MemoryBody | None,
    ) -> None:
        body = lead_agent.memory_after(arguments, previous)
        await store.put(
            kind="research_memory",
            body=body.encode(),
            provenance=Provenance(producer="lead"),
        )


__all__ = [
    "RUNAWAY_WAVE_GUARD",
    "STALL_TOLERANCE",
    "Event",
    "Listener",
    "ResearchService",
    "Task",
    "TaskState",
    "new_task_id",
]
