"""The reporting pipeline: evidence to a published, citable report.

The pipeline is deliberately small and its liveness bound is explicit:

    Analyst -> Author -> preflight -> baseline review
        -> at most one revision -> closure review -> render -> publish

Exactly one automatic revision.  If closure still blocks, the reporting run ends
and returns to the Lead rather than looping: an unbounded Author/Reviewer edge
burns money without converging, and a Reviewer that can keep adding findings
will keep adding findings.

Every artifact commits before the next role reads it, so a crash resumes from
durable state and no completed model call is paid for twice.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from .agents import TerminalAction, invoke_agent
from .agents import analyst as analyst_agent
from .agents import author as author_agent
from .agents import reviewer as reviewer_agent
from .artifact_store import SqliteArtifactStore
from .artifacts import Provenance
from .citations import RenderedCitations, render_citations
from .context import (
    EvidenceView,
    analyst_context,
    author_context,
    load_contract,
    load_evidence,
    reviewer_context,
)
from .contract import ResearchContract
from .model import ChatModel
from .operations import ExecutionIdentity, SqliteOperationLedger


class ReportingHalted(RuntimeError):
    """The reporting run stopped and needs a Lead decision or human judgement."""


async def publication_blocked(store: SqliteArtifactStore) -> bool:
    """Whether review has finally blocked publication, from committed facts only.

    The current report's lineage answers this, so nothing new is stored.  A
    revised report names the blocked baseline report as its parent; reviews and
    approval receipts each name the exact report they judged.  A blocked review
    on both those report versions is exactly "the automatic revision is spent".

    A boolean field would have been a second account of the same truth -- and the
    one that could disagree with the artifacts, since the artifacts are what a
    later process reads after a crash.

    Reviews from an older report chain are irrelevant.  Counting them globally
    made a new baseline look terminal merely because an earlier report had used
    its revision.
    """

    view = await store.active_view()
    if view.head("publication_receipt") is not None:
        return False
    report_ref = view.head("report")
    if report_ref is None or await approved_review_receipt(store, report_ref):
        return False
    if not await _reviews_for_report(store, report_ref):
        return False

    report = await store.get(report_ref)
    prior_reports = []
    for parent_ref in report.parent_refs:
        parent = await store.get(parent_ref)
        if parent.kind == "report":
            prior_reports.append(parent_ref)
    for parent_ref in prior_reports:
        if await _reviews_for_report(
            store, parent_ref
        ) and not await approved_review_receipt(store, parent_ref):
            return True
    return False


async def approved_review_receipt(
    store: SqliteArtifactStore, report_ref: str
) -> str:
    """The active approval proof for one exact report, or an empty string."""

    view = await store.active_view()
    for receipt_ref in reversed(view.active("review_receipt")):
        receipt = await store.get(receipt_ref)
        if report_ref not in receipt.parent_refs:
            continue
        for parent_ref in receipt.parent_refs:
            parent = await store.get(parent_ref)
            if parent.kind == "review" and report_ref in parent.parent_refs:
                return receipt_ref
    return ""


async def _reviews_for_report(
    store: SqliteArtifactStore, report_ref: str
) -> tuple[str, ...]:
    view = await store.active_view()
    linked: list[str] = []
    for review_ref in view.active("review"):
        review = await store.get(review_ref)
        if report_ref in review.parent_refs:
            linked.append(review_ref)
    return tuple(linked)


@dataclass(frozen=True, slots=True)
class ReviewRound:
    """One reviewer verdict against one exact report version."""

    report_ref: str
    approved: bool
    rationale: str = ""
    findings: tuple[str, ...] = ()
    advisories: tuple[str, ...] = ()


@dataclass
class ReportingOutcome:
    """Everything the reporting run produced, whether or not it published."""

    synthesis_ref: str = ""
    commission_ref: str = ""
    report_refs: list[str] = field(default_factory=list)
    reviews: list[ReviewRound] = field(default_factory=list)
    publication_ref: str = ""
    rendered: RenderedCitations | None = None
    halted_reason: str = ""

    @property
    def published(self) -> bool:
        return bool(self.publication_ref)


@dataclass(frozen=True, slots=True)
class RoleRuntime:
    """One role's bound model and the execution identity recorded for it."""

    model: ChatModel
    execution: ExecutionIdentity
    #: Input ceiling this role must fit inside, in tokens.  Carried here because
    #: the runner needs it before every provider call (§8.3) and the transport is
    #: the wrong place to ask -- a ``ChatModel`` is a protocol with no opinion
    #: about how much its vendor will accept.  Zero means "unknown", which
    #: disables the check rather than guessing a ceiling.
    context_limit: int = 0


async def run_reporting(
    store: SqliteArtifactStore,
    ledger: SqliteOperationLedger,
    runtimes: dict[str, RoleRuntime],
    *,
    report_brief: str,
    stop_rationale: str,
) -> ReportingOutcome:
    """Drive evidence through synthesis, writing, review, and publication."""

    task_id = store.task_id
    contract = await load_contract(store)
    evidence = await load_evidence(store)
    if not evidence.materials:
        raise ReportingHalted("the evidence set is empty; there is nothing to report")

    outcome = ReportingOutcome()

    synthesis_text = await synthesise(
        store, ledger, runtimes["analyst"], task_id, contract, evidence
    )
    outcome.synthesis_ref = (await store.active_view()).head("synthesis") or ""

    commission = await store.put(
        kind="report_commission",
        body=f"## 停止理由\n\n{stop_rationale}\n\n## 报告委托\n\n{report_brief}\n",
        parent_refs=_sorted((outcome.synthesis_ref,)),
        provenance=Provenance(producer="lead"),
    )
    outcome.commission_ref = commission.artifact_id

    handles = [handle.handle for handle in evidence.handles]
    action = await invoke_agent(
        author_agent.SPEC,
        author_context(contract, evidence, synthesis_text, report_brief),
        model=runtimes["author"].model,
        ledger=ledger,
        task_id=task_id,
        execution=runtimes["author"].execution,
        context_limit=runtimes["author"].context_limit,
        validate=author_agent.make_validator(handles),
    )
    if action.name == "raise_evidence_issue":
        outcome.halted_reason = str(action.arguments.get("description", ""))
        return outcome

    report_ref = await _commit_report(store, action, commission.artifact_id)
    outcome.report_refs.append(report_ref)

    verdict = await _review(
        store, ledger, runtimes["reviewer"], task_id, contract, evidence,
        synthesis_text, await store.body(report_ref), report_ref,
    )
    outcome.reviews.append(verdict)

    if not verdict.approved:
        revision = await invoke_agent(
            author_agent.REVISION_SPEC,
            reviewer_context(
                contract, evidence, synthesis_text,
                await store.body(report_ref),
                prior_findings=verdict.findings,
            ),
            model=runtimes["author"].model,
            ledger=ledger,
            task_id=task_id,
            execution=runtimes["author"].execution,
            context_limit=runtimes["author"].context_limit,
            validate=author_agent.make_validator(
                handles, finding_count=len(verdict.findings)
            ),
        )
        if revision.name == "raise_evidence_issue":
            outcome.halted_reason = str(revision.arguments.get("description", ""))
            return outcome

        revised_ref = await _commit_report(store, revision, report_ref)
        outcome.report_refs.append(revised_ref)

        disposition_by_index = {
            int(item.get("finding_index", 0)): str(item.get("response", ""))
            for item in revision.arguments.get("finding_dispositions", ())
            if isinstance(item, dict)
        }
        dispositions = tuple(
            disposition_by_index[index]
            for index in range(1, len(verdict.findings) + 1)
        )
        closure = await _review(
            store, ledger, runtimes["reviewer"], task_id, contract, evidence,
            synthesis_text, await store.body(revised_ref), revised_ref,
            prior_findings=verdict.findings, dispositions=dispositions,
        )
        outcome.reviews.append(closure)
        if not closure.approved:
            # One automatic revision, then stop. Continuing would spend money on
            # a basis that has not changed.
            outcome.halted_reason = (
                "closure review still blocks publication on an unchanged evidence "
                "basis; this needs a Lead decision, not another rewrite"
            )
            return outcome
        report_ref = revised_ref

    outcome.publication_ref, outcome.rendered = await _publish(
        store, evidence, report_ref
    )
    return outcome


async def synthesise(
    store: SqliteArtifactStore,
    ledger: SqliteOperationLedger,
    runtime: RoleRuntime,
    task_id: str,
    contract: ResearchContract,
    evidence: EvidenceView,
) -> str:
    """Produce a Synthesis bound to this exact evidence set, reusing a current one.

    Re-analysing an unchanged evidence set would pay twice for the same answer,
    so a Synthesis whose parents already equal the active material set is kept.
    """

    view = await store.active_view()
    head = view.head("synthesis")
    if head is not None:
        existing = await store.get(head)
        if set(existing.parent_refs) == set(evidence.material_refs):
            return await store.body(head)

    prior = await store.body(head) if head is not None else ""
    action = await invoke_agent(
        analyst_agent.SPEC,
        analyst_context(contract, evidence, prior_synthesis=prior),
        model=runtime.model,
        ledger=ledger,
        task_id=task_id,
        execution=runtime.execution,
        context_limit=runtime.context_limit,
        validate=analyst_agent.validate,
    )
    text = str(action.arguments["synthesis_markdown"])
    await store.put(
        kind="synthesis",
        body=text,
        parent_refs=_sorted(evidence.material_refs),
        provenance=Provenance(producer="analyst"),
    )
    return text


async def _review(
    store: SqliteArtifactStore,
    ledger: SqliteOperationLedger,
    runtime: RoleRuntime,
    task_id: str,
    contract: ResearchContract,
    evidence: EvidenceView,
    synthesis: str,
    report: str,
    report_ref: str,
    *,
    prior_findings: Sequence[str] = (),
    dispositions: Sequence[str] = (),
) -> ReviewRound:
    """One fresh reviewer invocation bound to one exact report version."""

    action = await invoke_agent(
        reviewer_agent.SPEC,
        reviewer_context(
            contract, evidence, synthesis, report,
            prior_findings=prior_findings, dispositions=dispositions,
        ),
        model=runtime.model,
        ledger=ledger,
        task_id=task_id,
        execution=runtime.execution,
        context_limit=runtime.context_limit,
        validate=reviewer_agent.validate,
    )
    approved = action.name == "approve_report"
    body = (
        f"## 结论\n\n{'批准' if approved else '阻断'}\n\n"
        f"## 理由\n\n{action.arguments.get('rationale', '')}\n"
    )
    findings = () if approved else reviewer_agent.findings_as_text(action.arguments)
    if findings:
        body += "\n## 发布阻断项\n\n" + "\n\n".join(findings) + "\n"

    review = await store.put(
        kind="review",
        body=body,
        parent_refs=(report_ref,),
        provenance=Provenance(producer="reviewer"),
    )
    if approved:
        # The receipt binds the exact report; any later body change invalidates it.
        await store.put(
            kind="review_receipt",
            body=f"approved:{report_ref}\nreview:{review.artifact_id}\n",
            parent_refs=_sorted((report_ref, review.artifact_id)),
            provenance=Provenance(producer="trust-plane"),
        )
    return ReviewRound(
        report_ref=report_ref,
        approved=approved,
        rationale=str(action.arguments.get("rationale", "")),
        findings=findings,
        advisories=tuple(str(a) for a in action.arguments.get("advisories", ())),
    )


async def _commit_report(
    store: SqliteArtifactStore, action: TerminalAction, parent_ref: str
) -> str:
    envelope = await store.put(
        kind="report",
        body=str(action.arguments["report_markdown"]),
        parent_refs=(parent_ref,),
        provenance=Provenance(producer="author"),
    )
    return envelope.artifact_id


async def _publish(
    store: SqliteArtifactStore, evidence: EvidenceView, report_ref: str
) -> tuple[str, RenderedCitations]:
    """Render citations deterministically and commit the publication.

    Rendering happens only after an approval bound to this exact report, and it
    fails closed: an unresolvable handle aborts publication rather than emitting
    a document with an unverifiable claim in it.
    """

    receipt_ref = await approved_review_receipt(store, report_ref)
    if not receipt_ref:
        raise ReportingHalted(
            "the current report has no approval receipt bound to its review"
        )

    rendered = render_citations(
        await store.body(report_ref),
        evidence.handles,
        evidence_set=evidence.material_refs,
    )
    publication = await store.put(
        kind="publication_receipt",
        body=rendered.markdown,
        parent_refs=_sorted((report_ref, receipt_ref)),
        provenance=Provenance(producer="trust-plane"),
    )
    return publication.artifact_id, rendered


def _sorted(refs: Sequence[str]) -> tuple[str, ...]:
    return tuple(sorted({ref for ref in refs if ref}))


__all__ = [
    "ReportingHalted",
    "ReportingOutcome",
    "approved_review_receipt",
    "publication_blocked",
    "synthesise",
    "ReviewRound",
    "RoleRuntime",
    "run_reporting",
]
