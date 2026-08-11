"""Narrow role contracts and context projections for the research graph.

The graph owns routing and artifact commits.  Role implementations receive only
the context required for their cognitive responsibility and return typed
proposals; they never receive the authoritative parent state itself.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal, Protocol

from .state import (
    Amendment,
    BranchHandoff,
    CuratedMaterial,
    JournalEntry,
    PublicationGateStatus,
    ResearchContract,
    ResearchState,
    ResearchSynthesis,
    ResearchTask,
    SourceDocument,
    ValidationFinding,
    validate_anchors,
)


RoleName = Literal[
    "planner",
    "supervisor",
    "researcher",
    "curator",
    "synthesizer",
    "writer",
    "validator",
    "editor",
]
ActionTarget = Literal[
    "researcher",
    "curator",
    "synthesizer",
    "writer",
    "validator",
    "editor",
    "citation_renderer",
    "planner",
    "user",
    "finish",
]


class RoleContractError(ValueError):
    """A role output violates its semantic or routing contract."""


@dataclass(frozen=True, slots=True)
class PlannerContext:
    question: str
    guide_catalog: tuple[str, ...] = ()
    presearch: tuple[str, ...] = ()
    revision_feedback: str = ""


@dataclass(frozen=True, slots=True)
class SupervisorContext:
    contract: ResearchContract
    stage: str
    research_tasks: tuple[ResearchTask, ...]
    branch_handoffs: tuple[BranchHandoff, ...]
    source_ids: tuple[str, ...]
    journal_summary: tuple[str, ...]
    material_ids: tuple[str, ...]
    research_synthesis: ResearchSynthesis | None
    draft_available: bool
    findings: tuple[ValidationFinding, ...]
    edited_report_available: bool
    final_report_available: bool
    amendments: tuple[Amendment, ...]
    stage_note: str = ""
    tool_errors: tuple[str, ...] = ()
    publication_gate_status: PublicationGateStatus = "unready"
    source_index: tuple[str, ...] = ()
    material_index: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ResearcherContext:
    task: ResearchTask
    contract: ResearchContract
    guide_text: str
    branch_journal: tuple[JournalEntry, ...]
    relevant_sources: Mapping[str, SourceDocument]
    provider_catalog: tuple[str, ...] = ()
    search_trace: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CuratorContext:
    contract: ResearchContract
    guide_text: str
    branch_handoffs: tuple[BranchHandoff, ...]
    candidate_journal: tuple[JournalEntry, ...]
    source_corpus: Mapping[str, SourceDocument]
    existing_materials: Mapping[str, CuratedMaterial]


@dataclass(frozen=True, slots=True)
class SynthesizerContext:
    contract: ResearchContract
    guide_text: str
    materials: Mapping[str, CuratedMaterial]


@dataclass(frozen=True, slots=True)
class WriterContext:
    contract: ResearchContract
    guide_text: str
    synthesis: ResearchSynthesis
    materials: Mapping[str, CuratedMaterial]


@dataclass(frozen=True, slots=True)
class ValidatorContext:
    scope: str
    contract: ResearchContract
    guide_text: str
    source_corpus: Mapping[str, SourceDocument]
    materials: Mapping[str, CuratedMaterial]
    synthesis: ResearchSynthesis | None
    report: str = ""


@dataclass(frozen=True, slots=True)
class EditorContext:
    contract: ResearchContract
    guide_text: str
    synthesis: ResearchSynthesis
    materials: Mapping[str, CuratedMaterial]
    draft: str
    findings: tuple[ValidationFinding, ...]


@dataclass(frozen=True, slots=True)
class PlanOutput:
    approval_card: str
    contract: ResearchContract | None = None
    status: Literal["plan_ready", "needs_clarification"] = "plan_ready"


@dataclass(frozen=True, slots=True)
class SupervisorAction:
    target: ActionTarget
    instruction: str = ""
    branch_id: str = ""
    relevant_source_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SupervisorDecision:
    assessment: str
    actions: tuple[SupervisorAction, ...]
    amendment: Amendment | None = None


@dataclass(frozen=True, slots=True)
class ResearcherOutput:
    sources: Mapping[str, SourceDocument]
    journal: tuple[JournalEntry, ...]
    handoff: BranchHandoff


@dataclass(frozen=True, slots=True)
class CuratorOutput:
    materials: Mapping[str, CuratedMaterial]
    summary: str
    blocking_issue: str = ""


@dataclass(frozen=True, slots=True)
class SynthesizerOutput:
    synthesis: ResearchSynthesis
    blocking_issue: str = ""


@dataclass(frozen=True, slots=True)
class WriterOutput:
    draft: str
    material_blocked: str = ""


@dataclass(frozen=True, slots=True)
class ValidatorOutput:
    status: Literal["pass", "findings"]
    findings: tuple[ValidationFinding, ...] = ()


@dataclass(frozen=True, slots=True)
class EditorOutput:
    status: Literal["edited", "needs_supervisor"]
    edited_report: str
    resolution_notes: str = ""
    substantive_change: bool = False
    closure_scope: str = ""


class PlannerRole(Protocol):
    async def __call__(self, context: PlannerContext) -> PlanOutput: ...


class SupervisorRole(Protocol):
    async def __call__(self, context: SupervisorContext) -> SupervisorDecision: ...


class ResearcherRole(Protocol):
    async def __call__(self, context: ResearcherContext) -> ResearcherOutput: ...


class CuratorRole(Protocol):
    async def __call__(self, context: CuratorContext) -> CuratorOutput: ...


class SynthesizerRole(Protocol):
    async def __call__(self, context: SynthesizerContext) -> SynthesizerOutput: ...


class WriterRole(Protocol):
    async def __call__(self, context: WriterContext) -> WriterOutput: ...


class ValidatorRole(Protocol):
    async def __call__(self, context: ValidatorContext) -> ValidatorOutput: ...


class EditorRole(Protocol):
    async def __call__(self, context: EditorContext) -> EditorOutput: ...


ValidatorFactory = Callable[[], ValidatorRole]


@dataclass(frozen=True, slots=True)
class RoleExecutors:
    """Eight separately constructed execution boundaries.

    A Validator factory is required so each assurance run starts from a fresh
    executor instance rather than reusing a producer's or prior review session.
    External tools belong inside the one executor that owns them; the graph does
    not hand a shared toolbox to this container.
    """

    planner: PlannerRole
    supervisor: SupervisorRole
    researcher: ResearcherRole
    curator: CuratorRole
    synthesizer: SynthesizerRole
    writer: WriterRole
    validator_factory: ValidatorFactory
    editor: EditorRole

    def __post_init__(self) -> None:
        for name in (
            "planner",
            "supervisor",
            "researcher",
            "curator",
            "synthesizer",
            "writer",
            "validator_factory",
            "editor",
        ):
            if not callable(getattr(self, name)):
                raise TypeError(f"{name} executor must be callable")


ROLE_CAPABILITIES = MappingProxyType(
    {
        "planner": frozenset({"presearch", "guide_catalog"}),
        "supervisor": frozenset({"route", "inspect_artifacts"}),
        "researcher": frozenset(
            {
                "inspect_providers",
                "inspect_source",
                "inspect_search_trace",
                "inspect_research_history",
                "search",
                "read_source",
                "save_source",
                "journal",
            }
        ),
        "curator": frozenset({"read_source", "write_material"}),
        "synthesizer": frozenset({"read_material", "write_synthesis"}),
        "writer": frozenset({"read_material", "write_draft"}),
        "validator": frozenset({"read_evidence_chain", "write_findings"}),
        "editor": frozenset({"read_material", "edit_report"}),
    }
)


def capabilities_for(role: str) -> frozenset[str]:
    try:
        return ROLE_CAPABILITIES[role]
    except KeyError as exc:
        raise RoleContractError(f"unknown role {role!r}") from exc


def _source_context_copy(source: SourceDocument) -> SourceDocument:
    """Detach nested provenance metadata at a read-only role boundary."""

    return SourceDocument(
        source_id=source.source_id,
        title=source.title,
        url=source.url,
        content=source.content,
        content_hash=source.content_hash,
        fetched_at=source.fetched_at,
        metadata=dict(source.metadata),
    )


def project_supervisor(state: ResearchState) -> SupervisorContext:
    contract = state.get("research_contract")
    if contract is None or not contract.approved:
        raise RoleContractError("Supervisor requires an approved Research Contract")
    corpus = state.get("source_corpus", {})
    materials = state.get("curated_material_library", {})
    source_index = tuple(
        "\n".join(
            (
                f"source_id: {source.source_id}",
                f"title: {source.title}",
                f"url: {source.url}",
                f"fetched_at: {source.fetched_at or 'unknown'}",
                "metadata: "
                + (
                    "; ".join(
                        f"{key}={value}"
                        for key, value in sorted(source.metadata.items())
                    )
                    or "none"
                ),
            )
        )
        for source in sorted(corpus.values(), key=lambda item: item.source_id)
    )
    material_index = tuple(
        "\n".join(
            (
                f"material_id: {material.material_id}",
                f"content: {material.content}",
                f"boundaries: {material.boundaries}",
                "source_ids: "
                + ", ".join(
                    dict.fromkeys(anchor.source_id for anchor in material.anchors)
                ),
            )
        )
        for material in sorted(
            materials.values(), key=lambda item: item.material_id
        )
    )
    return SupervisorContext(
        contract=contract,
        stage=state.get("stage", ""),
        research_tasks=tuple(state.get("research_tasks", ())),
        branch_handoffs=tuple(state.get("branch_handoffs", ())),
        source_ids=tuple(sorted(corpus)),
        journal_summary=tuple(entry.content for entry in state.get("research_journal", ())),
        material_ids=tuple(sorted(materials)),
        research_synthesis=state.get("research_synthesis"),
        draft_available=bool(state.get("draft")),
        findings=tuple(state.get("validation_findings", ())),
        edited_report_available=bool(state.get("edited_report")),
        final_report_available=bool(state.get("final_report")),
        amendments=tuple(state.get("amendments", ())),
        stage_note=state.get("stage_note", ""),
        tool_errors=tuple(state.get("tool_errors", ())),
        publication_gate_status=state.get("publication_gate_status", "unready"),
        source_index=source_index,
        material_index=material_index,
    )


def project_researcher(
    state: ResearchState,
    *,
    guide_text: str = "",
    provider_catalog: Sequence[str] = (),
    search_trace: Sequence[str] = (),
) -> ResearcherContext:
    task = state.get("active_research_task")
    contract = state.get("research_contract")
    if task is None or contract is None:
        raise RoleContractError("Researcher requires a task and Research Contract")
    journal = tuple(
        entry
        for entry in state.get("research_journal", ())
        if entry.branch_id == task.branch_id
    )
    corpus = state.get("source_corpus", {})
    relevant_source_ids = set(task.relevant_source_ids)
    relevant_source_ids.update(
        anchor.source_id for entry in journal for anchor in entry.anchors
    )
    relevant = {
        source_id: _source_context_copy(corpus[source_id])
        for source_id in relevant_source_ids
        if source_id in corpus
    }
    return ResearcherContext(
        task=task,
        contract=contract,
        guide_text=guide_text,
        branch_journal=journal,
        relevant_sources=MappingProxyType(relevant),
        provider_catalog=tuple(provider_catalog),
        search_trace=tuple(search_trace),
    )


def project_curator(state: ResearchState, *, guide_text: str = "") -> CuratorContext:
    contract = state.get("research_contract")
    if contract is None:
        raise RoleContractError("Curator requires a Research Contract")
    return CuratorContext(
        contract=contract,
        guide_text=guide_text,
        branch_handoffs=tuple(state.get("branch_handoffs", ())),
        candidate_journal=tuple(state.get("research_journal", ())),
        source_corpus=MappingProxyType(
            {
                source_id: _source_context_copy(source)
                for source_id, source in state.get("source_corpus", {}).items()
            }
        ),
        existing_materials=MappingProxyType(
            dict(state.get("curated_material_library", {}))
        ),
    )


def project_synthesizer(
    state: ResearchState, *, guide_text: str = ""
) -> SynthesizerContext:
    contract = state.get("research_contract")
    if contract is None:
        raise RoleContractError("Synthesizer requires a Research Contract")
    return SynthesizerContext(
        contract=contract,
        guide_text=guide_text,
        materials=MappingProxyType(dict(state.get("curated_material_library", {}))),
    )


def project_writer(state: ResearchState, *, guide_text: str = "") -> WriterContext:
    contract = state.get("research_contract")
    synthesis = state.get("research_synthesis")
    if contract is None or synthesis is None:
        raise RoleContractError("Writer requires a Contract and Research Synthesis")
    return WriterContext(
        contract=contract,
        guide_text=guide_text,
        synthesis=synthesis,
        materials=MappingProxyType(dict(state.get("curated_material_library", {}))),
    )


def project_validator(
    state: ResearchState, *, scope: str, guide_text: str = ""
) -> ValidatorContext:
    contract = state.get("research_contract")
    if contract is None:
        raise RoleContractError("Validator requires a Research Contract")
    report = (
        state.get("edited_report", "")
        if scope.startswith("closure")
        else state.get("draft", "")
    )
    if (scope.startswith("closure") or scope.startswith("draft")) and not report:
        raise RoleContractError("Validator requires the report under review")
    return ValidatorContext(
        scope=scope,
        contract=contract,
        guide_text=guide_text,
        source_corpus=MappingProxyType(
            {
                source_id: _source_context_copy(source)
                for source_id, source in state.get("source_corpus", {}).items()
            }
        ),
        materials=MappingProxyType(dict(state.get("curated_material_library", {}))),
        synthesis=state.get("research_synthesis"),
        report=report,
    )


def project_editor(state: ResearchState, *, guide_text: str = "") -> EditorContext:
    contract = state.get("research_contract")
    synthesis = state.get("research_synthesis")
    draft = state.get("edited_report") or state.get("draft", "")
    if contract is None or synthesis is None or not draft:
        raise RoleContractError("Editor requires Contract, Synthesis, and a report")
    return EditorContext(
        contract=contract,
        guide_text=guide_text,
        synthesis=synthesis,
        materials=MappingProxyType(dict(state.get("curated_material_library", {}))),
        draft=draft,
        findings=tuple(state.get("validation_findings", ())),
    )


def validate_supervisor_decision(decision: SupervisorDecision) -> None:
    if not decision.assessment.strip():
        raise RoleContractError("Supervisor assessment must not be empty")
    if not decision.actions:
        raise RoleContractError("Supervisor must emit at least one action")
    if len(decision.actions) > 1 and any(
        action.target != "researcher" for action in decision.actions
    ):
        raise RoleContractError("only independent Researcher actions may be parallel")
    branches: set[str] = set()
    for action in decision.actions:
        if action.target == "researcher":
            if not action.instruction.strip() or not action.branch_id.strip():
                raise RoleContractError(
                    "Researcher actions require instruction and branch_id"
                )
            if action.branch_id in branches:
                raise RoleContractError("parallel Researcher branch_ids must be unique")
            if any(
                not isinstance(source_id, str) or not source_id.strip()
                for source_id in action.relevant_source_ids
            ):
                raise RoleContractError(
                    "Researcher relevant_source_ids must contain non-empty strings"
                )
            if len(set(action.relevant_source_ids)) != len(
                action.relevant_source_ids
            ):
                raise RoleContractError(
                    "Researcher relevant_source_ids must not contain duplicates"
                )
            branches.add(action.branch_id)
        elif action.branch_id or action.relevant_source_ids:
            raise RoleContractError(
                "branch_id and relevant_source_ids are only valid for Researcher actions"
            )
    if decision.amendment is not None:
        target = decision.actions[0].target
        allowed = {
            "L0": {"curator", "synthesizer", "writer", "editor"},
            "L1": {"researcher"},
            "L2": {"planner"},
        }
        if target not in allowed[decision.amendment.level]:
            raise RoleContractError(
                f"{decision.amendment.level} amendment cannot route to {target}"
            )


def validate_researcher_output(
    output: ResearcherOutput,
    task: ResearchTask,
    existing_sources: Mapping[str, SourceDocument] | None = None,
) -> None:
    if output.handoff.branch_id != task.branch_id:
        raise RoleContractError("Researcher handoff branch differs from assigned branch")
    available_sources = dict(existing_sources or {})
    available_sources.update(output.sources)
    for entry in output.journal:
        if entry.branch_id != task.branch_id:
            raise RoleContractError("Researcher Journal entry escaped its branch")
        if entry.kind in {"finding", "conflict"} and not entry.anchors:
            raise RoleContractError(
                "Researcher findings and conflicts require at least one SourceAnchor"
            )
        validate_anchors(entry.anchors, available_sources)


def validate_curator_output(
    output: CuratorOutput, source_corpus: Mapping[str, SourceDocument]
) -> None:
    if not output.summary.strip():
        raise RoleContractError("Curator summary must not be empty")
    for material_id, material in output.materials.items():
        if material_id != material.material_id:
            raise RoleContractError("Material mapping key differs from material_id")
        validate_anchors(material.anchors, source_corpus)


def validate_validator_output(output: ValidatorOutput) -> None:
    if output.status == "pass" and output.findings:
        raise RoleContractError("passing validation cannot contain findings")
    if output.status == "findings" and not output.findings:
        raise RoleContractError("findings status requires at least one finding")


def validate_editor_output(output: EditorOutput) -> None:
    if not output.edited_report.strip():
        raise RoleContractError("Editor must return a complete report")
    if output.substantive_change and not output.closure_scope.strip():
        raise RoleContractError("substantive edits require a narrow closure scope")


__all__ = [
    "ActionTarget",
    "CuratorContext",
    "CuratorOutput",
    "EditorContext",
    "EditorOutput",
    "PlanOutput",
    "PlannerContext",
    "ROLE_CAPABILITIES",
    "ResearcherContext",
    "ResearcherOutput",
    "RoleContractError",
    "RoleExecutors",
    "RoleName",
    "SupervisorAction",
    "SupervisorContext",
    "SupervisorDecision",
    "SynthesizerContext",
    "SynthesizerOutput",
    "ValidatorContext",
    "ValidatorOutput",
    "WriterContext",
    "WriterOutput",
    "capabilities_for",
    "project_curator",
    "project_editor",
    "project_researcher",
    "project_supervisor",
    "project_synthesizer",
    "project_validator",
    "project_writer",
    "validate_curator_output",
    "validate_editor_output",
    "validate_researcher_output",
    "validate_supervisor_decision",
    "validate_validator_output",
]
