"""The application service: one place that runs a study, for every interface.

An interface must not reimplement governance.  Interfaces differ only in how they
collect a request and render progress, so this module owns the whole lifecycle and
they stay thin adapters over it::

                        ResearchService
                              │
                  ┌───────────┴───────────┐
                  ▼                       ▼
        Interactive workspace      Other thin adapters

Every capability a caller could need is a method here, not something only one
interface knows how to do: :meth:`~ResearchService.open_task`,
:meth:`~ResearchService.approve`, :meth:`~ResearchService.advance`,
:meth:`~ResearchService.task`, :meth:`~ResearchService.tasks`,
:meth:`~ResearchService.report`, :meth:`~ResearchService.delete_research`,
:meth:`~ResearchService.approval_card`, :meth:`~ResearchService.request_revision`,
:meth:`~ResearchService.answer_clarification`, :meth:`~ResearchService.replan`,
:meth:`~ResearchService.plan_history`,
:meth:`~ResearchService.clarification_history` and
:meth:`~ResearchService.execution_summary`.

A study's plan may iterate before research starts: the user reads a candidate and
either approves it or says what to change.  A revision produces a new Contract
artifact under the **same task**, so the plan has versions while the study has
one identity, and the original Commission is never rewritten.  Both decisions
name the exact plan they are about, so a reply aimed at a superseded candidate is
refused rather than applied to a body the user never read.

Pausing is not among them, and that is a consequence of the design rather than an
omission: stopping means the caller stops awaiting :meth:`~ResearchService.advance`,
after which the state derives as ``paused`` from what is already committed.  A
``pause()`` method would need a flag to set, and a flag would be a second account
of truth about a state the store already answers.

**No interface holds state.**  Everything durable lives in the artifact store and
the operation ledger, so "resume" means opening the same database and projecting
the committed facts again.  An interface that cached task state would become a
second account of truth.

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

from .agents import AgentProtocolError, TerminalAction, invoke_agent
from .agents import architect as architect_agent
from .agents import lead as lead_agent
from .application import build_runtimes
from .approval import (
    ApprovalBody,
    ApprovalError,
    StaleClarificationError,
    StalePlanError,
    approval_card,
    approved_contract,
    decision_for,
    decision_receipt,
    record_decision,
)
from .artifact_store import SqliteArtifactStore
from .artifacts import ArtifactDisposition, Provenance
from .citations import CitationClosureError
from .config import ConfigError, RuntimeConfig, load_config
from .content_store import SqliteContentStore
from .context import (
    ContextCapacityError,
    RoleContext,
    latest_body,
    lead_context,
    load_evidence,
)
from .contract import (
    ClarificationBody,
    ClarificationReplyBody,
    CommissionBody,
    ResearchContract,
    SourceAccess,
)
from .execution_snapshot import capture as capture_execution
from .execution_snapshot import freeze as freeze_execution
from .execution_snapshot import load as load_execution
from .execution_snapshot import setup as setup_executions
from .model import MODEL_FAILURES
from .operations import OperationError, SqliteOperationLedger
from .providers import build_search_providers
from .providers.local import LocalCorpusReader
from .providers.reader import PublicHttpReader, extract_pdf_in_subprocess
from .reporting import (
    ReportingHalted,
    RoleRuntime,
    publication_blocked,
    run_reporting,
)
from .sources import ArtifactValidationError
from .tools import TransparentSearchBroker
from .wave import STALL_TOLERANCE, WaveOutcome, run_wave, stalled

#: Where a study stands, derived from committed artifacts and never stored.
#:
#: ``halted`` and ``paused`` are kept apart because they are not the same
#: situation: ``paused`` means the study can be continued as it is, while
#: ``halted`` means independent review still refuses to publish *and* the one
#: automatic revision it was entitled to is spent -- nothing the runtime can do
#: unaided will change that verdict.  Both are derived from what is committed, so
#: neither is a flag anyone can set: see
#: :func:`~deep_research_agent.reporting.publication_blocked`.
#:
#: ``needs_reconciliation`` is the third of that family: the ledger contains an
#: external operation whose outcome cannot be proven.  A study cannot advance
#: past that fact, and neither the projection nor its actions offer an automatic
#: retry.  State precedence lives in :func:`project_task_state` below.
TaskState = Literal[
    "clarification_requested",
    "awaiting_approval",
    "researching",
    "published",
    "halted",
    "needs_reconciliation",
    "paused",
]

TaskAction = Literal[
    "answer",
    "approve",
    "back",
    "delete",
    "export",
    "plan",
    "report",
    "replan",
    "resume",
    "revise",
]


def project_task_state(
    *,
    has_contract: bool,
    has_publication: bool,
    decision: str,
    needs_reconciliation: bool,
    review_blocked: bool,
    governed: bool,
    materials: int,
    sources: int,
) -> TaskState:
    """Derive one task state from durable facts, without storing the answer."""

    if not has_contract:
        return "clarification_requested"
    if has_publication:
        return "published"
    if decision != "approved":
        return "awaiting_approval"
    if needs_reconciliation:
        return "needs_reconciliation"
    if review_blocked:
        return "halted"
    return "paused" if governed or materials or sources else "researching"


def task_actions(
    state: TaskState, *, has_open_clarification: bool = False
) -> tuple[TaskAction, ...]:
    """Return the behaviour allowed by a derived state; never a stored policy."""

    if state == "awaiting_approval":
        # The task page already shows the exact direction in this state, so its
        # actions are the real decisions -- never a second "view" page whose
        # apparent choices are only prose.
        return ("approve", "revise", "back", "delete")
    if state in {"paused", "researching", "halted"}:
        return ("resume", "plan", "delete", "back")
    if state == "published":
        return ("report", "export", "delete", "back")
    if state == "clarification_requested":
        first: TaskAction = "answer" if has_open_clarification else "replan"
        return (first, "back", "delete")
    return ("back", "delete")


def _memory_after_wave(
    previous: lead_agent.MemoryBody, outcome: WaveOutcome
) -> lead_agent.MemoryBody:
    """Merge only operational facts that can change the Lead's next decision."""

    additions = [f"Wave 目标：{outcome.intent.strip()}"]
    for branch in outcome.branches:
        focus = branch.focus.strip() or f"任务 {branch.index}"
        additions.extend(
            f"{focus}：已尝试 {path.strip()}"
            for path in branch.attempted_paths
            if path.strip()
        )
        additions.extend(
            f"{focus}（运行限制）：{limitation.strip()}"
            for limitation in branch.limitations
            if limitation.strip()
        )
        if branch.detail.strip():
            additions.append(f"{focus}（运行失败）：{branch.detail.strip()}")

    return lead_agent.MemoryBody(
        tried_paths=tuple(dict.fromkeys((*previous.tried_paths, *additions))),
        decisions=previous.decisions,
        open_intents=previous.open_intents,
        user_items=previous.user_items,
    )

#: Failures an interface is expected to report and carry on from, as opposed to
#: crash on.  Named one by one on purpose: this used to be ``(ValueError,
#: RuntimeError)``, which is every base class this codebase's own errors derive
#: from -- and also what a typo raises.  A ``TypeError`` from a bad call or an
#: ``AttributeError`` from a missing field is a bug in this program, and dressing
#: one up as "a provider had a problem" hides it from the only people who can fix
#: it.
#:
#: It lives here because it is part of the service's contract with its
#: interfaces, not a terminal detail: the next interface must expect the same set.
#:
#: The provider vocabulary in :mod:`~deep_research_agent.providers` is absent by
#: design rather than by omission -- a search or fetch failure is a research
#: observation the broker records and hands to the role, so it never reaches a
#: caller.  Model failures do reach one, which is why they are listed.
EXPECTED_FAILURES: tuple[type[Exception], ...] = (
    # A role could not produce a valid action, or ran out of tool budget.
    AgentProtocolError,
    # The approval state as recorded forbids this, including a stale plan or a
    # stale clarification.
    ApprovalError,
    # A body the domain refuses: an empty revision note, a malformed Contract.
    ArtifactValidationError,
    # A finished report cannot be cited safely, so it is not published.
    CitationClosureError,
    # The installation's own configuration is unusable.
    ConfigError,
    # A role's basis does not fit, or an approved Contract is missing.
    ContextCapacityError,
    # A frozen operation, or an exhausted attempt budget.
    OperationError,
    # There is nothing to report on yet.
    ReportingHalted,
    # Every way a paid model call can fail.
    *MODEL_FAILURES,
)

#: Runaway guard only, set far above anything an observed run has needed (the
#: deepest so far used three waves).  Reaching it is a pause, never "finished".
#:
#: The stall rule that does the real stopping lives in
#: :func:`~deep_research_agent.wave.stalled`, beside the MaterialDelta it reads.
#: It used to be duplicated here as a second constant and an inline comparison,
#: which is two definitions of one rule -- and the fixture runner used one while
#: the product used the other.
RUNAWAY_WAVE_GUARD = 24


@dataclass(frozen=True, slots=True)
class Event:
    """One thing worth telling the user about, in their terms.

    ``detail`` carries structured values an interface may want to render without
    parsing the message text.
    """

    kind: str
    message: str
    detail: Mapping[str, Any] = field(default_factory=dict)


Listener = Callable[[Event], None]


def _ignore(_event: Event) -> None:
    return None


@dataclass(frozen=True, slots=True)
class Task:
    """What a caller needs to show a task in a list or decide on its plan.

    ``plan_id`` and ``plan_version`` identify the Contract candidate currently
    awaiting a decision.  Both are derived from the artifact history rather than
    stored: the version is that Contract's position in the task's plan chain, so
    nothing has to be kept in step with anything else.
    """

    task_id: str
    request: str
    language: str
    source_access: tuple[str, ...]
    state: TaskState
    materials: int = 0
    sources: int = 0
    plan_id: str = ""
    plan_version: int = 0
    #: The clarification still waiting for an answer, when the state is
    #: ``clarification_requested``.  Carried on the task so the question survives
    #: closing the terminal: it is a committed artifact, not a line that scrolled
    #: past in one session.
    clarification_id: str = ""
    clarification_question: str = ""
    clarification_why: str = ""

    @property
    def allowed_actions(self) -> tuple[TaskAction, ...]:
        """Actions projected from this view, not remembered on the task."""

        return task_actions(
            self.state, has_open_clarification=bool(self.clarification_id)
        )


@dataclass(frozen=True, slots=True)
class Exchange:
    """One clarification: what the Architect asked, and what the user replied.

    ``answer`` is empty while the question is still open.  A task has at most one
    open question at a time -- the Architect asks, the user answers, and only then
    can it ask again -- so the open one is the last exchange without a reply.
    """

    clarification_id: str
    question: str
    why: str
    answer: str = ""

    @property
    def answered(self) -> bool:
        return bool(self.answer)


@dataclass(frozen=True, slots=True)
class PlanVersion:
    """One Contract candidate in a task's plan history.

    The provenance of a study starts here: what the user asked, what the
    Architect proposed, what the user sent back and why, and which version was
    finally approved.  It is a projection of committed artifacts, not a second
    record.
    """

    plan_id: str
    version: int
    decision: str = ""
    revision_note: str = ""

    @property
    def approved(self) -> bool:
        return self.decision == "approved"


@dataclass(frozen=True, slots=True)
class TaskExecution:
    """What one task runs with, resolved from its frozen snapshot.

    ``frozen`` is False only for a task created before configurations were
    snapshotted.  Those fall back to the installation's current settings, which
    the service reports rather than applying silently.
    """

    config: RuntimeConfig
    runtimes: dict[str, RoleRuntime]
    corpus_root: Path | None = None
    frozen: bool = True


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
    #: The installation's current configuration.  It governs **new** tasks only:
    #: every existing task runs from the snapshot frozen when it was created.
    config: RuntimeConfig | None = None
    corpus_root: Path | None = None
    _content: SqliteContentStore | None = field(default=None, repr=False)
    _ledger: SqliteOperationLedger | None = field(default=None, repr=False)
    _executions: dict[str, TaskExecution] = field(default_factory=dict, repr=False)

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
        await setup_executions(self.connection)
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

    def rebind_credentials(self, environ: Mapping[str, str]) -> None:
        """Re-read credentials and drop the bound transports.

        Frozen per-task configurations are untouched: rotating a key changes how
        a study authenticates, never which model it runs.
        """

        self.environ = environ
        self.config = load_config(environ)
        self._executions.clear()

    async def execution(
        self, task_id: str, *, listen: Listener = _ignore
    ) -> TaskExecution:
        """Bind this task's roles to the models frozen when it was created.

        Bound once per task per service, because building a runtime constructs a
        transport per role.  Two tasks in one database may legitimately run on
        different vendors, so the binding cannot be service-wide -- which it was,
        and that is what let a later settings change reach an existing study.
        """

        cached = self._executions.get(task_id)
        if cached is not None:
            return cached

        assert self.config is not None
        snapshot = await load_execution(self.connection, task_id)
        if snapshot is None:
            config = self.config
            corpus_root = self.corpus_root
            await self._report_unfrozen(task_id, config, listen)
        else:
            config = snapshot.to_config(self.config)
            corpus_root = (
                Path(snapshot.corpus_root) if snapshot.corpus_root else self.corpus_root
            )
        execution = TaskExecution(
            config=config,
            runtimes=build_runtimes(self.environ, config=config),
            corpus_root=corpus_root,
            frozen=snapshot is not None,
        )
        self._executions[task_id] = execution
        return execution

    async def _report_unfrozen(
        self, task_id: str, config: RuntimeConfig, listen: Listener
    ) -> None:
        """Say plainly that this task has no frozen configuration to restore.

        The ledger knows which models the task actually called, so where the
        current settings disagree with them the message names the difference.
        That is the whole risk of the fallback: continuing a study on a model that
        did not produce its existing evidence.
        """

        current: dict[str, str] = {
            name: chosen.model_id for name, chosen in config.role_models.items()
        }
        used = await self.ledger.models_used(task_id)
        differs = sorted(
            f"{role} {'、'.join(models)} → {current[role]}"
            for role, models in used.items()
            if role in current and current[role] not in models
        )
        message = (
            "这项研究创建于「执行配置冻结」之前，没有可恢复的配置，"
            "将使用当前的全局设置继续。"
        )
        if differs:
            message += "注意：以下角色与它此前实际调用的模型不同：" + "；".join(differs)
        listen(Event("configuration_not_frozen", message, {"models_changed": differs}))

    def _local_reader(
        self, commission: CommissionBody, corpus_root: Path | None
    ) -> LocalCorpusReader | None:
        """Built only when the Commission authorises reading local files."""

        if not commission.allows_local_corpus:
            return None
        if corpus_root is None:
            raise ConfigError(
                "this commission authorises local files but no corpus root was given"
            )
        return LocalCorpusReader(
            root=corpus_root, extract_pdf=extract_pdf_in_subprocess
        )

    def _broker(self, commission: CommissionBody, config: RuntimeConfig):  # noqa: ANN202
        """No network client at all when the Commission forbids the network.

        Returning None rather than an empty broker keeps the prohibition
        mechanical: there is no object present that could reach a vendor.  What
        counts as authorised is the Commission's own answer -- deciding it a second
        time here is how two readings of one permission start to drift.
        """

        if not commission.allows_external_search:
            return None, None
        providers = build_search_providers(
            config.search_providers,
            config.academic_providers,
            environ=self.environ,
            ncbi_api_key=config.ncbi_api_key,
            contact_email=config.contact_email,
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

        # Freeze before the first model call, so even the Architect runs under the
        # configuration this task will keep for the rest of its life.
        assert self.config is not None
        await freeze_execution(
            self.connection,
            task_id,
            capture_execution(
                self.config, corpus_root=self.corpus_root, frozen_at=created_at
            ),
        )

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

        task = await self.task(task_id)
        listen(
            Event(
                "contract_proposed",
                approval_card(contract),
                {"task_id": task_id, "plan_id": task.plan_id},
            )
        )
        return task

    async def approve(self, task_id: str, plan_id: str) -> None:
        """Start research from one exact direction.

        ``plan_id`` is required rather than convenient.  A user starts the
        direction they read, and if an adjustment has produced a newer one since,
        applying their "yes" to it would spend against a body they never saw.
        """

        store = self._store(task_id)
        current = await self._require_current_plan(store, plan_id)
        decided = await decision_for(store, current)
        if decided is not None:
            if decided.decision == "approved":
                return  # already approved; approving twice is not an error
            raise ApprovalError(
                "这一版方向已经要求调整，请查看新版本后再开始研究。"
            )
        await record_decision(store, current, ApprovalBody(decision="approved"))

    async def request_revision(
        self,
        task_id: str,
        plan_id: str,
        revision_note: str,
        *,
        listen: Listener = _ignore,
    ) -> Task:
        """Adjust one exact direction and get the next complete version.

        This is the same Research Task throughout.  The plan iterates; the study's
        identity, its original Commission and its frozen execution configuration
        do not.  Earlier versions are never rewritten -- the revised Contract
        carries the previous one and the request that produced it among its
        parents, so the whole chain stays readable afterwards.

        Recording the request before calling the Architect is what makes an
        interrupted revision recoverable: the instruction is already committed, so
        calling again with nothing new resumes it.  Saying something *different*
        about the same candidate supersedes the earlier request rather than being
        ignored -- otherwise an Architect that answered with a question instead of
        a plan would leave the study unable to move.
        """

        instruction = revision_note.strip()
        store = self._store(task_id)
        current = await self._require_current_plan(store, plan_id)

        found = await decision_receipt(store, current)
        if found is not None and found[1].decision != "revision_requested":
            raise ApprovalError("这一版方向已经开始执行，不能再调整。")

        if found is None:
            if not instruction:
                raise ArtifactValidationError(
                    "a revision request must say what to change"
                )
            receipt_ref = await record_decision(
                store,
                current,
                ApprovalBody(
                    decision="revision_requested", revision_note=instruction
                ),
            )
            recorded = instruction
        elif instruction and instruction != found[1].revision_note:
            # The user has said something new about the same candidate -- they
            # changed their mind, or the Architect came back with a question
            # instead of a plan.  The newest instruction is the live one, and the
            # superseded receipt stays readable as history.
            receipt_ref = await record_decision(
                store,
                current,
                ApprovalBody(
                    decision="revision_requested", revision_note=instruction
                ),
            )
            await store.dispose(
                ArtifactDisposition(
                    target_ref=found[0],
                    status="superseded",
                    reason="用户重新说明了要修改什么",
                    replacement_ref=receipt_ref,
                )
            )
            recorded = instruction
        else:
            # Nothing new to say: answer the request already on record.  This is
            # what makes an interrupted revision resumable rather than lost.
            receipt_ref, body = found
            recorded = body.revision_note

        commission = await self._commission(store)
        await self._propose_revision(
            store,
            commission=commission,
            previous_ref=current,
            receipt_ref=receipt_ref,
            revision_note=recorded,
            listen=listen,
        )
        return await self.task(task_id)

    async def answer_clarification(
        self,
        task_id: str,
        clarification_id: str,
        answer: str,
        *,
        listen: Listener = _ignore,
    ) -> Task:
        """Answer the Architect's open question and let it try again.

        The same Research Task throughout.  Answering used to build
        ``request + answer`` and call :meth:`open_task`, which derives task
        identity from the Commission -- so a study whose intent needed one
        clarification became two studies, the first stranded forever at
        ``clarification_requested``.

        The answer is a committed artifact bound to the exact question it answers,
        never folded into the Commission: the Commission is what the user actually
        asked, and it has to stay that way to be worth checking a report against.

        The Architect may ask again.  That is a new question in the same task, not
        a repeat of the old one -- the answered exchange is part of the next call's
        input refs, so the ledger cannot replay the question the user just
        answered.
        """

        reply = ClarificationReplyBody(answer=answer.strip())
        store = self._store(task_id)
        exchanges = await self._exchanges(store)
        open_question = next(
            (item for item in reversed(exchanges) if not item.answered), None
        )
        if open_question is None:
            raise ApprovalError("这项研究现在没有待回答的问题。")
        if not clarification_id:
            # The same rule as a plan decision: an answer has to name the question
            # it answers, or it could be recorded against one the user never read.
            raise StaleClarificationError(
                "必须指明回答的是哪一个澄清问题。"
            )
        if clarification_id != open_question.clarification_id:
            raise StaleClarificationError(
                "这个澄清问题已经发生变化。请查看最新的问题后回答。"
            )

        await store.put(
            kind="clarification_reply",
            body=reply.encode(),
            parent_refs=(open_question.clarification_id,),
            provenance=Provenance(producer="user"),
        )

        return await self._plan(store, listen)

    async def replan(self, task_id: str, *, listen: Listener = _ignore) -> Task:
        """Ask the Architect again for a task that has no plan yet.

        The planning call can fail for reasons that have nothing to do with the
        commission: a provider outage, an expired key, an exhausted quota.  Before
        this existed such a task was stuck for good -- it had a Commission but no
        plan and no question, so there was nothing to answer, nothing to approve,
        and nothing to continue, and deleting it was the only way forward.

        Safe on a task that already has a plan: proposing is idempotent, so it
        returns the task unchanged rather than paying for a second candidate.
        """

        return await self._plan(self._store(task_id), listen)

    async def clarification_history(self, task_id: str) -> tuple[Exchange, ...]:
        """Every question the Architect asked and every answer it was given."""

        return await self._exchanges(self._store(task_id))

    async def plan_history(self, task_id: str) -> tuple[PlanVersion, ...]:
        """Every plan this task has had, oldest first, with its decision."""

        store = self._store(task_id)
        view = await store.active_view()
        history: list[PlanVersion] = []
        for index, ref in enumerate(view.active("research_contract"), start=1):
            decision = await decision_for(store, ref)
            history.append(
                PlanVersion(
                    plan_id=ref,
                    version=index,
                    decision="" if decision is None else decision.decision,
                    revision_note="" if decision is None else decision.revision_note,
                )
            )
        return tuple(history)

    async def advance(
        self, task_id: str, *, listen: Listener = _ignore
    ) -> TaskState:
        """Govern until the study reaches a terminal state.

        Safe to call again after any interruption: completed provider calls
        replay from the ledger and committed artifacts are simply read back.
        Every call runs under the configuration frozen at creation, so resuming
        next week cannot pick up a model the study never used.
        """

        projected = await self.task(task_id)
        if projected.state == "published":
            raise ApprovalError("a published task cannot be advanced")
        if projected.state == "needs_reconciliation":
            raise OperationError(
                "a task with an unknown provider outcome cannot be advanced"
            )

        execution = await self.execution(task_id, listen=listen)
        store = self._store(task_id)
        _plan_ref, contract = await approved_contract(store)
        commission = await self._commission(store)
        broker, reader = self._broker(commission, execution.config)
        local_reader = self._local_reader(commission, execution.corpus_root)
        return await self._govern(
            store,
            contract=contract,
            commission=commission,
            runtimes=execution.runtimes,
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

        plans = view.active("research_contract")
        contract_head = view.head("research_contract")
        open_question: Exchange | None = None
        if contract_head is None:
            open_question = next(
                (
                    item
                    for item in reversed(await self._exchanges(store))
                    if not item.answered
                ),
                None,
            )

        decision = (
            None if contract_head is None else await decision_for(store, contract_head)
        )
        state = project_task_state(
            has_contract=contract_head is not None,
            has_publication=view.head("publication_receipt") is not None,
            decision="" if decision is None else decision.decision,
            needs_reconciliation=bool(
                await self.ledger.pending_reconciliation(task_id)
            ),
            review_blocked=await publication_blocked(store),
            governed=view.head("research_memory") is not None,
            materials=materials,
            sources=sources,
        )
        return Task(
            task_id=task_id,
            request=commission.request,
            language=commission.language,
            source_access=tuple(commission.source_access),
            state=state,
            materials=materials,
            sources=sources,
            plan_id=contract_head or "",
            plan_version=len(plans),
            clarification_id="" if open_question is None else open_question.clarification_id,
            clarification_question="" if open_question is None else open_question.question,
            clarification_why="" if open_question is None else open_question.why,
        )

    async def tasks(self) -> tuple[Task, ...]:
        # Newest first, keyed on the one Commission every task has.  Ordering by
        # task_id sorted by hash, so "the study I just started" landed anywhere in
        # the list and the home screen surfaced an arbitrary one of several.
        rows = await self.connection.execute_fetchall(
            "SELECT task_id FROM artifacts WHERE kind = 'commission' "
            "ORDER BY produced_at DESC, sequence DESC"
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
        for table in (
            "artifacts",
            "artifact_dispositions",
            "operations",
            "execution_snapshots",
        ):
            await self.connection.execute(
                f"DELETE FROM {table} WHERE task_id = ?", (task_id,)
            )
        await self.connection.commit()
        self._executions.pop(task_id, None)
        return True

    async def execution_summary(self, task_id: str) -> str:
        """The models this task is bound to, for an interface to show.

        Worth showing because the guarantee is otherwise invisible: a user who
        changed their default model needs to see that this study did not.
        """

        snapshot = await load_execution(self.connection, task_id)
        if snapshot is not None:
            return snapshot.render()
        assert self.config is not None
        # Rendered through the same code path so the two cases cannot disagree
        # about the format; only the caveat differs.
        return capture_execution(self.config).render() + "（创建时未冻结，用当前设置）"

    async def approval_card(self, task_id: str) -> str:
        """The exact card the user must read before deciding on the current plan."""

        store = self._store(task_id)
        return approval_card(await self._contract(store))

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

    async def _require_current_plan(
        self, store: SqliteArtifactStore, plan_id: str
    ) -> str:
        """Return the head plan, refusing any decision aimed at an older one.

        An empty ``plan_id`` is a missing one, not a wildcard.  It used to skip the
        staleness check entirely, so a caller that simply omitted it authorised
        whatever the current head happened to be -- exactly the "starting a body
        the user never read" this guard exists to prevent.  The interactive
        workspace always passes it, but the service is the shared contract, and the
        next interface should not be able to lose the check by leaving an argument
        blank.
        """

        head = (await store.active_view()).head("research_contract")
        if head is None:
            raise ValueError(f"task {store.task_id} has no Contract to decide on")
        if not plan_id:
            raise StalePlanError(
                "必须指明要开始的是哪一版方向：执行的必须是用户实际读过的正文。"
            )
        if plan_id != head:
            raise StalePlanError(
                "当前研究方向已经发生变化。请查看最新版本后重新操作。"
            )
        return head

    async def _ask_architect(
        self,
        store: SqliteArtifactStore,
        commission: CommissionBody,
        *,
        purpose: str,
        input_refs: tuple[str, ...],
        exchanges: Sequence[Exchange],
        previous_contract: str = "",
        revision_note: str = "",
        listen: Listener,
    ) -> TerminalAction:
        """One Architect call, with the context every plan version must carry.

        Both plan paths come through here so the invariant cannot hold in one of
        them: whichever version is being written, the Architect sees the original
        Commission and the *whole* clarification exchange.  It did not, and the
        asymmetry was invisible -- a revision was given the plan and the note but
        not the answers, so a user who had already said "for procurement, not
        education" could watch v2 drift back towards a tutorial.
        """

        runtimes = (await self.execution(store.task_id, listen=listen)).runtimes
        body = architect_agent.architect_context_body(
            commission.request,
            source_access=commission.source_access,
            language=commission.language,
            constraints=commission.constraints,
            clarifications=tuple(
                (item.question, item.answer) for item in exchanges if item.answered
            ),
            previous_contract=previous_contract,
            revision_note=revision_note,
        )
        return await invoke_agent(
            architect_agent.SPEC,
            RoleContext(
                role="architect",
                purpose=purpose,
                body=body,
                input_refs=input_refs,
            ),
            model=runtimes["architect"].model,
            ledger=self.ledger,
            task_id=store.task_id,
            execution=runtimes["architect"].execution,
            context_limit=runtimes["architect"].context_limit,
            validate=architect_agent.make_validator(),
        )

    async def _propose_revision(
        self,
        store: SqliteArtifactStore,
        *,
        commission: CommissionBody,
        previous_ref: str,
        receipt_ref: str,
        revision_note: str,
        listen: Listener,
    ) -> ResearchContract:
        """Ask the Architect to replace one candidate, given what to change.

        The Architect is given the original Commission, every clarification it has
        already been answered, the candidate being replaced, and the user's
        instruction -- not a request string with the instruction glued onto the
        end.  That is the difference between "revise this plan" and "here is a new,
        longer brief": only the first can be asked to keep what the user did not
        object to.

        Idempotent by construction.  If the revised Contract is already committed
        (an interrupted call, a repeated click) the store returns the existing
        envelope, and the ledger replays the Architect's answer instead of paying
        for it twice.
        """

        exchanges = await self._exchanges(store)
        parents = tuple(
            sorted(
                {
                    receipt_ref,
                    previous_ref,
                    *await self._commission_refs(store),
                    *(item.clarification_id for item in exchanges if item.answered),
                }
            )
        )
        action = await self._ask_architect(
            store,
            commission,
            purpose="根据用户对上一版方案的修改要求，提交完整的替代方案",
            # The receipt is an input, so this call fingerprints differently from
            # the one that produced the previous candidate.
            input_refs=parents,
            exchanges=exchanges,
            previous_contract=await store.body(previous_ref),
            revision_note=revision_note,
            listen=listen,
        )
        if action.name == "ask_scope_question":
            # The Architect may legitimately need one answer before it can
            # rewrite.  The request stays recorded, so answering it resumes.
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
            raise AgentProtocolError(
                "Architect 需要先澄清一个问题才能修改方案：" + str(
                    action.arguments["question"]
                )
            )

        contract = architect_agent.contract_from_action(
            action.arguments, language=commission.language
        )
        await store.put(
            kind="research_contract",
            body=contract.encode(),
            parent_refs=parents,
            provenance=Provenance(producer="architect"),
        )
        version = len((await store.active_view()).active("research_contract"))
        listen(
            Event(
                "plan_revised",
                approval_card(contract),
                {"task_id": store.task_id, "version": version},
            )
        )
        return contract

    async def _commission_refs(self, store: SqliteArtifactStore) -> tuple[str, ...]:
        return (await store.active_view()).active("commission")

    async def _plan(self, store: SqliteArtifactStore, listen: Listener) -> Task:
        """Run the planning step and report whichever outcome it reached.

        Shared by answering a clarification and by retrying a failed plan, because
        both end the same way: the Architect either proposes a candidate or asks
        one more question, and the caller wants the resulting task either way.
        """

        commission = await self._commission(store)
        commission_ref = (await store.active_view()).active("commission")[-1]
        contract = await self._propose(store, commission, commission_ref, listen)
        task = await self.task(store.task_id)
        if contract is not None:
            listen(
                Event(
                    "contract_proposed",
                    approval_card(contract),
                    {"task_id": task.task_id, "plan_id": task.plan_id},
                )
            )
        return task

    async def _propose(
        self,
        store: SqliteArtifactStore,
        commission: CommissionBody,
        commission_ref: str,
        listen: Listener,
    ) -> ResearchContract | None:
        """Plan, or ask one question.  Both are legitimate ends to this step.

        Asking is committed as an artifact rather than only announced, so the
        question survives the session that produced it and the answer has
        something to bind to.  Every answered exchange becomes part of the
        Architect's context *and* part of this call's input refs -- which is what
        stops the ledger replaying the first question forever once it has been
        answered.
        """

        existing = (await store.active_view()).head("research_contract")
        if existing is not None:
            return ResearchContract.decode(await store.body(existing))

        exchanges = await self._exchanges(store)
        if exchanges and not exchanges[-1].answered:
            # A question is still open; planning waits for the user, not the model.
            return None

        input_refs = tuple(
            sorted(
                {
                    commission_ref,
                    *(item.clarification_id for item in exchanges if item.answered),
                }
            )
        )
        action = await self._ask_architect(
            store,
            commission,
            purpose="把用户委托转化为可直接确认和执行的研究方向",
            input_refs=input_refs,
            exchanges=exchanges,
            listen=listen,
        )
        if action.name == "ask_scope_question":
            await self._ask_clarification(
                store,
                commission_ref=commission_ref,
                previous=exchanges,
                arguments=action.arguments,
                listen=listen,
            )
            return None

        contract = architect_agent.contract_from_action(
            action.arguments, language=commission.language
        )
        await store.put(
            kind="research_contract",
            body=contract.encode(),
            parent_refs=input_refs,
            provenance=Provenance(producer="architect"),
        )
        return contract

    async def _ask_clarification(
        self,
        store: SqliteArtifactStore,
        *,
        commission_ref: str,
        previous: Sequence[Exchange],
        arguments: Mapping[str, Any],
        listen: Listener,
    ) -> None:
        """Commit the Architect's question and tell the caller about it."""

        question = ClarificationBody(
            question=str(arguments["question"]),
            why_it_changes_the_plan=str(arguments["why_it_changes_the_plan"]),
        )
        parents = (
            commission_ref,
            *(item.clarification_id for item in previous if item.answered),
        )
        envelope = await store.put(
            kind="clarification",
            body=question.encode(),
            parent_refs=tuple(sorted(set(parents))),
            provenance=Provenance(producer="architect"),
        )
        listen(
            Event(
                "clarification_requested",
                question.question,
                {
                    "why": question.why_it_changes_the_plan,
                    "task_id": store.task_id,
                    "clarification_id": envelope.artifact_id,
                    "round": len(previous) + 1,
                },
            )
        )

    async def _exchanges(self, store: SqliteArtifactStore) -> tuple[Exchange, ...]:
        """The clarification history in order, each with its reply if answered."""

        view = await store.active_view()
        replies: dict[str, str] = {}
        for ref in view.active("clarification_reply"):
            envelope = await store.get(ref)
            answer = ClarificationReplyBody.decode(await store.body(ref)).answer
            for parent in envelope.parent_refs:
                replies[parent] = answer

        exchanges: list[Exchange] = []
        for ref in view.active("clarification"):
            body = ClarificationBody.decode(await store.body(ref))
            exchanges.append(
                Exchange(
                    clarification_id=ref,
                    question=body.question,
                    why=body.why_it_changes_the_plan,
                    answer=replies.get(ref, ""),
                )
            )
        return tuple(exchanges)

    async def _govern(
        self,
        store: SqliteArtifactStore,
        *,
        contract: ResearchContract,
        commission: CommissionBody,
        runtimes: dict[str, RoleRuntime],
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
                    model=runtimes["lead"].model,
                    ledger=self.ledger,
                    task_id=store.task_id,
                    execution=runtimes["lead"].execution,
                    context_limit=runtimes["lead"].context_limit,
                    validate=lead_agent.make_validator(contract),
                )
            except (AgentProtocolError, ContextCapacityError) as error:
                # A role that cannot act is the recoverable pause §8.2 requires,
                # and a basis that does not fit is the same situation for the same
                # reason: every artifact is already committed, so nothing is lost
                # and a later call to advance() continues from here.  Capacity is
                # grouped here rather than left to escape because the alternative
                # -- trimming the basis to fit -- is what §8.3 forbids.
                return await self._pause(
                    store,
                    listen,
                    f"治理暂停：{error}。已保全 {len(evidence.materials)} 份素材，"
                    "重新继续同一任务即可。",
                    {"round": round_index},
                )

            current_memory = await self._commit_memory(
                store, action.arguments, previous
            )

            if action.name == "commission_report":
                return await self._report(store, action.arguments, runtimes, listen)

            if action.name != "commission_wave":
                return await self._pause(
                    store, listen, "研究负责人请求人工判断。", dict(action.arguments)
                )

            if stalled(progress):
                # Measured from the Trust Plane's MaterialDelta, never from the
                # Lead's own claim to be making progress.  One definition, in
                # wave.py beside the delta it reads.
                return await self._pause(
                    store,
                    listen,
                    f"连续 {STALL_TOLERANCE} 个批次没有产生任何素材，"
                    "研究已停止发现新证据。",
                    {"round": round_index},
                )

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
                runtimes,
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
            await self._store_memory(
                store, _memory_after_wave(current_memory, wave)
            )
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

        return await self._pause(
            store,
            listen,
            f"已达 {RUNAWAY_WAVE_GUARD} 个批次的失控保护上限；这是暂停，不是完成。",
            {},
        )

    async def _pause(
        self,
        store: SqliteArtifactStore,
        listen: Listener,
        message: str,
        detail: Mapping[str, Any],
    ) -> TaskState:
        """Stop governing, and report the state the store actually derives.

        Every exit reads the state back rather than asserting one, so
        ``advance()`` and ``task()`` cannot disagree about the same study.  This
        also means a frozen operation surfaces here as
        ``needs_reconciliation`` rather than being flattened into a pause the user
        would be invited to retry forever.
        """

        state = (await self.task(store.task_id)).state
        listen(Event(state, message, dict(detail)))
        return state

    async def _report(
        self,
        store: SqliteArtifactStore,
        arguments: Mapping[str, Any],
        runtimes: dict[str, RoleRuntime],
        listen: Listener,
    ) -> TaskState:
        outcome = await run_reporting(
            store,
            self.ledger,
            runtimes,
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
            # What stopped the reporting run is not always the Reviewer: an Author
            # who says the evidence cannot support the report leaves a study that
            # is merely paused.  So the state is read back from what was
            # committed rather than assumed here, which is also the only way
            # advance() and task() cannot disagree about the same study.
            state = (await self.task(store.task_id)).state
            listen(Event(state, f"未发布：{outcome.halted_reason}", {}))
            return state

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
                    # How much of the evidence the report actually used.  Computed
                    # by the renderer and previously discarded, which left the
                    # interface reporting the evidence-set size under a label that
                    # said "cited" -- two different numbers, one of them wrong.
                    "cited_materials": len(outcome.rendered.used_material_refs),
                },
            )
        )
        return "published"

    async def _commit_memory(
        self,
        store: SqliteArtifactStore,
        arguments: Mapping[str, Any],
        previous: lead_agent.MemoryBody | None,
    ) -> lead_agent.MemoryBody:
        body = lead_agent.memory_after(arguments, previous)
        await self._store_memory(store, body)
        return body

    @staticmethod
    async def _store_memory(
        store: SqliteArtifactStore, body: lead_agent.MemoryBody
    ) -> None:
        await store.put(
            kind="research_memory",
            body=body.encode(),
            provenance=Provenance(producer="lead"),
        )


__all__ = [
    "EXPECTED_FAILURES",
    "RUNAWAY_WAVE_GUARD",
    "STALL_TOLERANCE",
    "Event",
    "Exchange",
    "Listener",
    "PlanVersion",
    "ResearchService",
    "Task",
    "TaskAction",
    "TaskExecution",
    "TaskState",
    "new_task_id",
    "project_task_state",
    "task_actions",
]
