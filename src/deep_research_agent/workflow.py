"""LangGraph orchestration for the agent-first research lifecycle.

Semantic decisions are delegated to narrow roles.  This module enforces stage
order, human approval, parallel Researcher isolation, artifact validation,
Supervisor-only cross-stage amendments, and deterministic publication.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, Overwrite, Send, interrupt

from .citations import (
    CitationClosureError,
    CitationRenderer,
    citation_marker_signature,
    extract_citation_ids,
)
from .planner import AgenticPlanner
from .roles import (
    EditorOutput,
    PlanOutput,
    PlannerContext,
    RoleContractError,
    RoleExecutors,
    SupervisorDecision,
    project_curator,
    project_editor,
    project_researcher,
    project_supervisor,
    project_synthesizer,
    project_validator,
    project_writer,
    validate_curator_output,
    validate_editor_output,
    validate_researcher_output,
    validate_supervisor_decision,
    validate_validator_output,
)
from .researcher import (
    ControlledResearcher,
    researcher_output_from_subgraph,
    researcher_subgraph_input,
)
from .state import (
    AssuranceEvent,
    ResearchContract,
    ResearchState,
    ResearchTask,
    validate_anchors,
)


GuideContextProvider = Callable[[str, ResearchContract], str]


def empty_guide_context(_role: str, _contract: ResearchContract) -> str:
    return ""


def _require_text(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RoleContractError(f"{label} must be a non-empty string")
    return value.strip()


def _artifact_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _assurance_artifact(state: ResearchState, report: str = "") -> str:
    contract = state.get("research_contract")
    synthesis = state.get("research_synthesis")
    payload = {
        "contract": contract.content if contract else "",
        "report": report,
        "synthesis": synthesis.content if synthesis else "",
        "materials": [
            {
                "material_id": material.material_id,
                "content": material.content,
                "boundaries": material.boundaries,
            }
            for material in sorted(
                state.get("curated_material_library", {}).values(),
                key=lambda item: item.material_id,
            )
        ],
        "sources": [
            {
                "source_id": source.source_id,
                "content_hash": source.content_hash,
            }
            for source in sorted(
                state.get("source_corpus", {}).values(),
                key=lambda item: item.source_id,
            )
        ],
    }
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def _assurance_event(
    *, actor: str, artifact: str, scope: str, outcome: str, details: str = ""
) -> AssuranceEvent:
    return AssuranceEvent(
        event_id="assr_" + uuid4().hex,
        actor=actor,  # type: ignore[arg-type]
        artifact_digest=_artifact_digest(artifact),
        scope=scope,
        outcome=outcome,
        details=details,
        recorded_at=datetime.now(UTC).isoformat(),
    )


def _approval_response(value: Any) -> tuple[str, str]:
    """Normalize an interrupt resume value into action and feedback."""

    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"approve", "approved", "批准", "同意"}:
            return "approve", ""
        if normalized in {"cancel", "cancelled", "取消"}:
            return "cancel", ""
        if normalized in {"revise", "修改"}:
            return "revise", "请根据用户要求修改计划。"
        if value.strip():
            return "revise", value.strip()
    if isinstance(value, Mapping):
        action = str(value.get("action", "")).strip().lower()
        feedback = str(value.get("feedback", "")).strip()
        aliases = {"批准": "approve", "同意": "approve", "修改": "revise", "取消": "cancel"}
        action = aliases.get(action, action)
        if action in {"approve", "cancel"}:
            return action, feedback
        if action == "revise" and feedback:
            return action, feedback
    raise RoleContractError(
        "approval response must approve, cancel, or revise with feedback"
    )


def _user_response(value: Any) -> str:
    if isinstance(value, Mapping):
        value = value.get("response", "")
    return _require_text(str(value), "user response")


def _guide_text(
    provider: GuideContextProvider, role: str, state: ResearchState
) -> str:
    contract = state.get("research_contract")
    return provider(role, contract) if contract is not None else ""


def _publication_gate_status(state: ResearchState) -> str:
    status = state.get("publication_gate_status", "unready")
    allowed = {
        "unready",
        "material_blocked",
        "full_validation_required",
        "full_validation_passed",
        "closure_validation_required",
        "closed",
    }
    if status not in allowed:
        raise RoleContractError(f"unsupported publication gate status {status!r}")
    return status


def _research_send_state(state: ResearchState, task: ResearchTask) -> ResearchState:
    """Project parent state before a parallel Worker receives it."""

    branch_journal = [
        entry
        for entry in state.get("research_journal", ())
        if entry.branch_id == task.branch_id
    ]
    relevant_source_ids = set(task.relevant_source_ids)
    relevant_source_ids.update(
        anchor.source_id for entry in branch_journal for anchor in entry.anchors
    )
    corpus = state.get("source_corpus", {})
    relevant_sources = {
        source_id: corpus[source_id]
        for source_id in relevant_source_ids
        if source_id in corpus
    }
    return {
        "task_id": state.get("task_id", ""),
        "question": state.get("question", ""),
        "stage": "researching",
        "research_contract": state["research_contract"],
        "active_research_task": task,
        "source_corpus": relevant_sources,
        "research_journal": branch_journal,
    }


def _clear_downstream(target: str) -> ResearchState:
    """Invalidate only artifacts downstream of a Supervisor-authorized return."""

    common: ResearchState = {
        "final_report": "",
    }
    if target in {"researcher", "curator"}:
        common.update(
            {
                "research_synthesis": None,  # type: ignore[typeddict-item]
                "draft": "",
                "validation_findings": [],
                "edited_report": "",
                "publication_gate_status": "unready",
                "closure_validation_scope": "",
            }
        )
    elif target == "synthesizer":
        common.update(
            {
                "research_synthesis": None,  # type: ignore[typeddict-item]
                "draft": "",
                "validation_findings": [],
                "edited_report": "",
                "publication_gate_status": "unready",
                "closure_validation_scope": "",
            }
        )
    elif target == "writer":
        common.update(
            {
                "draft": "",
                "validation_findings": [],
                "edited_report": "",
                "publication_gate_status": "unready",
                "closure_validation_scope": "",
            }
        )
    elif target == "editor":
        common.update({"edited_report": ""})
    elif target == "planner":
        common.update(
            {
                "research_tasks": [],
                "branch_handoffs": Overwrite([]),  # type: ignore[typeddict-item]
                "source_corpus": Overwrite({}),  # type: ignore[typeddict-item]
                "research_journal": Overwrite([]),  # type: ignore[typeddict-item]
                "curated_material_library": {},
                "research_synthesis": None,  # type: ignore[typeddict-item]
                "draft": "",
                "validation_findings": [],
                "edited_report": "",
                "tool_errors": Overwrite([]),  # type: ignore[typeddict-item]
                "publication_gate_status": "unready",
                "closure_validation_scope": "",
            }
        )
    return common


def validate_supervisor_transition(
    state: ResearchState, decision: SupervisorDecision
) -> None:
    """Enforce stage order independently of the Supervisor model."""

    target = decision.actions[0].target
    stage = state.get("stage", "")
    amendment = decision.amendment
    has_sources = bool(state.get("source_corpus"))
    has_materials = bool(state.get("curated_material_library"))
    has_synthesis = state.get("research_synthesis") is not None
    has_draft = bool(state.get("draft"))
    has_edited = bool(state.get("edited_report"))
    publication_gate = _publication_gate_status(state)
    known_source_ids = set(state.get("source_corpus", {}))

    for action in decision.actions:
        unknown_source_ids = sorted(
            set(action.relevant_source_ids) - known_source_ids
        )
        if unknown_source_ids:
            raise RoleContractError(
                "Researcher action references unknown source IDs: "
                + ", ".join(unknown_source_ids)
            )

    if stage == "editor_needs_supervisor":
        if target in {"validator", "citation_renderer", "finish"}:
            raise RoleContractError(
                "Editor escalation requires Supervisor L0/L1/L2 resolution; "
                f"it cannot route directly to {target}"
            )
        if target != "user":
            required_level = {
                "curator": "L0",
                "synthesizer": "L0",
                "writer": "L0",
                "editor": "L0",
                "researcher": "L1",
                "planner": "L2",
            }.get(target)
            if required_level is None:
                raise RoleContractError(
                    f"Editor escalation cannot route to unsupported target {target}"
                )
            if amendment is None or amendment.level != required_level:
                raise RoleContractError(
                    "Editor escalation requires a matching "
                    f"{required_level} amendment before routing to {target}"
                )

    if publication_gate == "material_blocked" and target in {
        "validator",
        "editor",
        "citation_renderer",
        "finish",
    }:
        raise RoleContractError(
            "Writer material block must be resolved by an authorized upstream return"
        )
    if target == "citation_renderer" and (
        stage not in {"edited_style_only", "closure_passed"}
        or publication_gate != "closed"
    ):
        raise RoleContractError(
            "Citation Renderer requires an edited report with publication assurance closed"
        )
    if target == "researcher" and has_synthesis and (
        amendment is None or amendment.level != "L1"
    ):
        raise RoleContractError(
            "reopening external research after synthesis requires an L1 amendment"
        )
    if target == "curator":
        if not has_sources:
            raise RoleContractError("Curator requires saved source content")
        if has_synthesis and (amendment is None or amendment.level != "L0"):
            raise RoleContractError("returning to Curator requires an L0 amendment")
    if target == "synthesizer":
        if not has_materials:
            raise RoleContractError("Synthesizer requires Curated Materials")
        if has_draft and (amendment is None or amendment.level != "L0"):
            raise RoleContractError("returning to Synthesizer requires an L0 amendment")
    if target == "writer":
        if not has_synthesis:
            raise RoleContractError("Writer requires a Research Synthesis")
        if has_edited and (amendment is None or amendment.level != "L0"):
            raise RoleContractError("returning to Writer requires an L0 amendment")
    if stage == "edited_substantive":
        if target != "validator":
            raise RoleContractError(
                "substantive Editor changes may route only to closure validation"
            )
        if not has_edited or publication_gate != "closure_validation_required":
            raise RoleContractError(
                "closure validation requires an edited report and pending closure"
            )
    if target == "editor" and not has_draft:
        raise RoleContractError("Editor requires a validated Draft")
    if target == "planner" and (amendment is None or amendment.level != "L2"):
        raise RoleContractError("returning an approved task to Planner requires L2")
    if target == "finish" and not state.get("final_report"):
        raise RoleContractError("finish requires a compiled final report")

    if stage == "approved" and target not in {"researcher", "validator", "user", "planner"}:
        raise RoleContractError(f"approved research cannot jump directly to {target}")
    if stage == "edited_substantive" and target == "citation_renderer":
        raise RoleContractError("substantive edits require closure validation")


def _assert_report_uses_formal_materials(
    state: ResearchState, report: str, *, require_citation: bool = False
) -> None:
    source_corpus = state.get("source_corpus", {})
    for material in state.get("curated_material_library", {}).values():
        validate_anchors(material.anchors, source_corpus)
    allowed_source_ids = {
        anchor.source_id
        for material in state.get("curated_material_library", {}).values()
        for anchor in material.anchors
    }
    cited = set(extract_citation_ids(report))
    if require_citation and state.get("curated_material_library") and not cited:
        raise CitationClosureError(
            "a report backed by the Curated Material Library must retain at "
            "least one formal citation"
        )
    outside = sorted(cited - allowed_source_ids)
    if outside:
        raise CitationClosureError(
            "report cites sources outside the Curated Material Library: "
            + ", ".join(outside)
        )


def build_research_graph(
    roles: RoleExecutors,
    *,
    checkpointer: Any = None,
    guide_context: GuideContextProvider = empty_guide_context,
    guide_catalog: Sequence[str] = (),
    presearch: Sequence[str] = (),
    provider_catalog: Sequence[str] = (),
    citation_renderer: CitationRenderer | None = None,
) -> Any:
    """Compile the v1 graph around supplied semantic role implementations.

    No model or search API is called by this function.  Callers choose role
    implementations and explicitly bind external tools outside the graph.
    """

    renderer = citation_renderer or CitationRenderer()
    researcher_subgraph = (
        roles.researcher.as_subgraph()
        if isinstance(roles.researcher, ControlledResearcher)
        else None
    )
    planner_subgraph = (
        roles.planner.as_subgraph()
        if isinstance(roles.planner, AgenticPlanner)
        else None
    )

    async def planner_node(
        state: ResearchState, config: RunnableConfig
    ) -> ResearchState:
        question = _require_text(state.get("question", ""), "research question")
        context = PlannerContext(
            question=question,
            guide_catalog=tuple(guide_catalog),
            presearch=tuple(presearch),
            revision_feedback=state.get("stage_note", "")
            if state.get("stage") == "planning_revision"
            else "",
        )
        if planner_subgraph is None:
            result = await roles.planner(context)
        else:
            result = await roles.planner.run_with_subgraph(
                context, planner_subgraph, config
            )
        if not isinstance(result, PlanOutput):
            raise RoleContractError("Planner must return PlanOutput")
        card = _require_text(result.approval_card, "approval card")
        if result.status == "needs_clarification":
            if result.contract is not None:
                raise RoleContractError(
                    "Planner clarification must not create a provisional Contract"
                )
            return {
                "approval_card": card,
                "stage": "planner_clarification",
                "stage_note": card,
            }
        if result.status != "plan_ready" or result.contract is None:
            raise RoleContractError("plan_ready requires a Research Contract")
        contract = replace(result.contract, approved=False)
        try:
            guide_context("planner", contract)
        except (KeyError, ValueError) as exc:
            raise RoleContractError(
                "Planner selected an unavailable or invalid Guide reference"
            ) from exc
        return {
            "research_contract": contract,
            "approval_card": card,
            "stage": "awaiting_approval",
            "stage_note": "",
            "publication_gate_status": "unready",
            "closure_validation_scope": "",
        }

    async def approval_node(state: ResearchState) -> Command:
        clarification = state.get("stage") == "planner_clarification"
        response = interrupt(
            {
                "type": "planner_clarification"
                if clarification
                else "research_plan_approval",
                **(
                    {"question": state.get("approval_card", "")}
                    if clarification
                    else {
                        "approval_card": state.get("approval_card", ""),
                        "actions": ("approve", "revise", "cancel"),
                    }
                ),
            }
        )
        if clarification:
            if isinstance(response, Mapping) and str(
                response.get("action", "")
            ).casefold() in {"cancel", "取消"}:
                return Command(
                    update={"stage": "cancelled", "stage_note": "Task cancelled."},
                    goto=END,
                )
            return Command(
                update={
                    "stage": "planning_revision",
                    "stage_note": _user_response(response),
                },
                goto="planner",
            )
        action, feedback = _approval_response(response)
        if action == "approve":
            contract = state.get("research_contract")
            if contract is None:
                raise RoleContractError("approval requires a Research Contract")
            return Command(
                update={
                    "research_contract": replace(contract, approved=True),
                    "stage": "approved",
                    "stage_note": "Research Contract approved by the user.",
                },
                goto="supervisor",
            )
        if action == "revise":
            return Command(
                update={"stage": "planning_revision", "stage_note": feedback},
                goto="planner",
            )
        return Command(
            update={
                "stage": "cancelled",
                "stage_note": feedback or "Task cancelled by the user.",
            },
            goto=END,
        )

    async def supervisor_node(state: ResearchState) -> Command:
        decision = await roles.supervisor(project_supervisor(state))
        if not isinstance(decision, SupervisorDecision):
            raise RoleContractError("Supervisor must return SupervisorDecision")
        validate_supervisor_decision(decision)
        validate_supervisor_transition(state, decision)

        first = decision.actions[0]
        updates: ResearchState = {
            "stage_note": decision.assessment,
            **_clear_downstream(first.target),
        }
        if decision.amendment is not None:
            updates["amendments"] = [decision.amendment]
            if decision.amendment.level == "L2":
                contract = state.get("research_contract")
                if contract is None:
                    raise RoleContractError("L2 requires an existing Research Contract")
                updates["research_contract"] = replace(contract, approved=False)
                updates["approval_card"] = ""

        if all(action.target == "researcher" for action in decision.actions):
            tasks = [
                ResearchTask(
                    branch_id=action.branch_id,
                    instruction=action.instruction,
                    relevant_source_ids=action.relevant_source_ids,
                )
                for action in decision.actions
            ]
            updates.update(
                {
                    "stage": "researching",
                    "stage_note": decision.assessment,
                    "research_tasks": tasks,
                    "branch_handoffs": Overwrite(
                        [
                            handoff
                            for handoff in state.get("branch_handoffs", ())
                            if handoff.branch_id
                            not in {task.branch_id for task in tasks}
                        ]
                    ),  # type: ignore[typeddict-item]
                }
            )
            sends = [
                Send("researcher", _research_send_state({**state, **updates}, task))
                for task in tasks
            ]
            return Command(update=updates, goto=sends)

        action = first
        directive = action.instruction.strip()
        updates["stage_note"] = (
            decision.assessment
            + (f"\n\nDirective: {directive}" if directive else "")
        )
        destinations = {
            "curator": ("curating", "curator"),
            "synthesizer": ("synthesizing", "synthesizer"),
            "writer": ("writing", "writer"),
            "editor": ("editing", "editor"),
            "citation_renderer": ("rendering", "citation_renderer"),
            "planner": ("planning_revision", "planner"),
            "user": ("awaiting_user", "user_input"),
        }
        if action.target == "validator":
            publication_gate = _publication_gate_status(state)
            if publication_gate == "closure_validation_required":
                updates["stage"] = "closure_validation_requested"
            elif publication_gate == "full_validation_required":
                updates["stage"] = "draft_validation_requested"
            else:
                updates["stage"] = "assurance_requested"
            return Command(update=updates, goto="validator")
        if action.target == "finish":
            if not state.get("final_report"):
                raise RoleContractError(
                    "Supervisor cannot finish before citation compilation"
                )
            return Command(update={"stage": "finished"}, goto=END)
        stage, destination = destinations[action.target]
        if action.target == "user" and state.get("stage") == "editor_needs_supervisor":
            stage = "editor_awaiting_user"
        updates["stage"] = stage
        return Command(update=updates, goto=destination)

    async def researcher_node(
        state: ResearchState, config: RunnableConfig
    ) -> ResearchState:
        context = project_researcher(
            state,
            guide_text=_guide_text(guide_context, "researcher", state),
            provider_catalog=provider_catalog,
        )
        if researcher_subgraph is None:
            result = await roles.researcher(context)
        else:
            child_state = await researcher_subgraph.ainvoke(
                researcher_subgraph_input(context), config
            )
            result = researcher_output_from_subgraph(child_state)
        validate_researcher_output(
            result, context.task, existing_sources=context.relevant_sources
        )
        return {
            "source_corpus": dict(result.sources),
            "research_journal": list(result.journal),
            "branch_handoffs": [result.handoff],
        }

    async def curator_node(state: ResearchState) -> ResearchState:
        result = await roles.curator(
            project_curator(
                state, guide_text=_guide_text(guide_context, "curator", state)
            )
        )
        validate_curator_output(result, state.get("source_corpus", {}))
        note = result.summary
        if result.blocking_issue:
            note += f"\n\nBlocking issue: {result.blocking_issue}"
        return {
            "curated_material_library": dict(result.materials),
            "stage": "evidence_review",
            "stage_note": note,
        }

    async def synthesizer_node(state: ResearchState) -> ResearchState:
        result = await roles.synthesizer(
            project_synthesizer(
                state, guide_text=_guide_text(guide_context, "synthesizer", state)
            )
        )
        note = result.blocking_issue or "Research Synthesis completed."
        return {
            "research_synthesis": result.synthesis,
            "stage": "analysis_review",
            "stage_note": note,
        }

    async def writer_node(state: ResearchState) -> Command:
        result = await roles.writer(
            project_writer(
                state, guide_text=_guide_text(guide_context, "writer", state)
            )
        )
        draft = _require_text(result.draft, "Writer draft")
        _assert_report_uses_formal_materials(state, draft)
        if result.material_blocked:
            return Command(
                update={
                    "draft": draft,
                    "stage": "writer_blocked",
                    "stage_note": result.material_blocked,
                    "publication_gate_status": "material_blocked",
                    "closure_validation_scope": "",
                },
                goto="supervisor",
            )
        return Command(
            update={
                "draft": draft,
                "validation_findings": [],
                "stage": "draft_validation_requested",
                "stage_note": "Full draft requires independent validation.",
                "publication_gate_status": "full_validation_required",
                "closure_validation_scope": "",
            },
            goto="validator",
        )

    async def validator_node(state: ResearchState) -> Command:
        stage = state.get("stage", "")
        publication_gate = _publication_gate_status(state)
        if stage == "closure_validation_requested":
            if publication_gate != "closure_validation_required":
                raise RoleContractError("closure validation was not required")
            scope = "closure: " + _require_text(
                state.get("closure_validation_scope", ""),
                "closure validation scope",
            )
        elif stage == "draft_validation_requested":
            if publication_gate != "full_validation_required":
                raise RoleContractError("full draft validation was not required")
            scope = "draft: full report audit"
        else:
            scope = "assurance: " + state.get("stage_note", "specified artifact")
        validator = roles.validator_factory()
        result = await validator(
            project_validator(
                state,
                scope=scope,
                guide_text=_guide_text(guide_context, "validator", state),
            )
        )
        validate_validator_output(result)
        report_under_review = (
            state.get("edited_report", "")
            if stage == "closure_validation_requested"
            else state.get("draft", "")
        )
        finding_details = "\n\n".join(
            " | ".join(
                value
                for value in (
                    f"location={finding.location}",
                    f"issue={finding.issue}",
                    "materials=" + ",".join(finding.related_material_ids),
                    "sources=" + ",".join(finding.related_source_ids),
                    f"reason={finding.severity_reason}"
                    if finding.severity_reason
                    else "",
                )
                if value
            )
            for finding in result.findings
        )
        updates: ResearchState = {
            "validation_findings": list(result.findings),
            "assurance_log": [
                _assurance_event(
                    actor="independent_validator",
                    artifact=_assurance_artifact(state, report_under_review),
                    scope=scope,
                    outcome=result.status,
                    details=finding_details,
                )
            ],
            "stage_note": "Independent validation passed."
            if result.status == "pass"
            else "Independent validation found concrete issues.",
        }
        if stage == "draft_validation_requested":
            updates["publication_gate_status"] = (
                "full_validation_passed"
                if result.status == "pass"
                else "full_validation_required"
            )
            updates["stage"] = (
                "draft_validation_passed"
                if result.status == "pass"
                else "draft_validation_findings"
            )
            return Command(update=updates, goto="editor")
        if stage == "closure_validation_requested":
            if result.status == "findings":
                updates["publication_gate_status"] = "closure_validation_required"
                updates["stage"] = "closure_findings"
                return Command(update=updates, goto="editor")
            updates["publication_gate_status"] = "closed"
            updates["stage"] = "closure_passed"
            return Command(update=updates, goto="supervisor")
        updates["stage"] = (
            "assurance_passed" if result.status == "pass" else "assurance_findings"
        )
        return Command(update=updates, goto="supervisor")

    async def editor_node(state: ResearchState) -> Command:
        incoming_stage = state.get("stage", "")
        prior_report = state.get("edited_report") or state.get("draft", "")
        result = await roles.editor(
            project_editor(
                state, guide_text=_guide_text(guide_context, "editor", state)
            )
        )
        if not isinstance(result, EditorOutput):
            raise RoleContractError("Editor must return EditorOutput")
        validate_editor_output(result)
        _assert_report_uses_formal_materials(state, result.edited_report)
        report_changed = result.edited_report != prior_report
        citation_association_changed = citation_marker_signature(
            prior_report
        ) != citation_marker_signature(result.edited_report)
        requires_closure = (
            result.substantive_change
            or report_changed
            or citation_association_changed
            or incoming_stage in {"draft_validation_findings", "closure_findings"}
        )
        closure_scope = result.closure_scope.strip()
        if requires_closure and not closure_scope:
            if citation_association_changed:
                closure_scope = "citation markers and their claim associations"
            elif incoming_stage in {"draft_validation_findings", "closure_findings"}:
                closure_scope = "changes addressing the independent validation findings"
            else:
                closure_scope = "all text changed by Editor since the validated report"

        gate_updates: ResearchState = {}
        if requires_closure:
            gate_updates = {
                "publication_gate_status": "closure_validation_required",
                "closure_validation_scope": closure_scope,
            }
        if result.status == "needs_supervisor":
            stage = "editor_needs_supervisor"
        elif requires_closure:
            stage = "edited_substantive"
        else:
            if _publication_gate_status(state) not in {
                "full_validation_passed",
                "closed",
            }:
                raise RoleContractError(
                    "unchanged Editor output requires a completed full validation"
                )
            gate_updates = {
                "publication_gate_status": "closed",
                "closure_validation_scope": "",
            }
            stage = "edited_style_only"
        note = result.resolution_notes
        if requires_closure:
            note += f"\n\nClosure scope: {closure_scope}"
        return Command(
            update={
                "edited_report": result.edited_report,
                "assurance_log": [
                    _assurance_event(
                        actor="editor",
                        artifact=_assurance_artifact(
                            state, result.edited_report
                        ),
                        scope=(
                            closure_scope
                            or f"editor response after {incoming_stage}"
                        ),
                        outcome=result.status,
                        details=result.resolution_notes,
                    )
                ],
                "stage": stage,
                "stage_note": note.strip() or "Editor completed the report.",
                **gate_updates,
            },
            goto="supervisor",
        )

    async def user_input_node(state: ResearchState) -> Command:
        response = interrupt(
            {
                "type": "supervisor_question",
                "question": state.get("stage_note", "User input required."),
            }
        )
        next_stage = (
            "editor_needs_supervisor"
            if state.get("stage") == "editor_awaiting_user"
            else "user_responded"
        )
        return Command(
            update={"stage": next_stage, "stage_note": _user_response(response)},
            goto="supervisor",
        )

    async def citation_renderer_node(state: ResearchState) -> ResearchState:
        if _publication_gate_status(state) != "closed":
            raise RoleContractError(
                "Citation Renderer requires the persistent Publication Gate to be closed"
            )
        report = _require_text(state.get("edited_report", ""), "edited report")
        _assert_report_uses_formal_materials(
            state, report, require_citation=True
        )
        rendered = renderer.render(report, state.get("source_corpus", {}))
        return {
            "final_report": rendered.markdown,
            "stage": "finished",
            "stage_note": "Citation closure compiled successfully.",
        }

    graph = StateGraph(ResearchState)
    graph.add_node("planner", planner_node)
    graph.add_node("approval", approval_node)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("curator", curator_node)
    graph.add_node("synthesizer", synthesizer_node)
    graph.add_node("writer", writer_node)
    graph.add_node("validator", validator_node)
    graph.add_node("editor", editor_node)
    graph.add_node("user_input", user_input_node)
    graph.add_node("citation_renderer", citation_renderer_node)

    graph.add_edge(START, "planner")
    graph.add_edge("planner", "approval")
    graph.add_edge("researcher", "curator")
    graph.add_edge("curator", "supervisor")
    graph.add_edge("synthesizer", "supervisor")
    graph.add_edge("citation_renderer", END)
    return graph.compile(checkpointer=checkpointer)


__all__ = [
    "GuideContextProvider",
    "build_research_graph",
    "empty_guide_context",
    "validate_supervisor_transition",
]
