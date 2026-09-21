"""One resumable Agent loop shared by all research responsibilities."""

from __future__ import annotations

import asyncio
import math
import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

from .analysis_runtime import AnalysisRuntime
from .calculation import calculate
from .citations import render as render_citations
from .context import assemble, fit_provider, fit_read_result, page, source_ranges
from .domain import (
    INLINE_TOOL_RESULT_CHARS,
    Artifact,
    Call,
    NotAllowed,
    RecoveryExhausted,
    RepeatedFailure,
    Reply,
    bounded_json,
    encode,
    identity,
)
from .prompts import PROMPT_VERSION, ROLES, ROUTE_PROMPT, TOOLS, WRITING_GUIDES
from .research import DISPOSITIONS, RESEARCH_KINDS, STATUSES, ResearchLedger
from .review import report_metrics, text_metrics, units
from .scheduling import Scheduler
from .storage import Store
from .workspace import Workspace
from .writing import WritingWorkspace


class Model(Protocol):
    identity: str

    async def complete(self, request: dict[str, Any]) -> dict[str, Any]: ...


@dataclass(frozen=True)
class Tool:
    description: str
    schema: dict[str, Any]
    invoke: Callable[[dict[str, Any]], Awaitable[Any]]
    roles: tuple[str, ...] = ("reviewer", "investigator")
    identity: str = "v1"
    permission: str | None = None
    observe: Callable[[Any, dict[str, str]], Any] | None = None
    check: Callable[[dict[str, Any]], None] | None = None
    validate_arguments: Callable[[dict[str, Any]], None] | None = None
    invoke_received: (
        Callable[[dict[str, Any], Callable[[Any], None]], Awaitable[Any]] | None
    ) = None
    retry_delay: Callable[[Any, int], float | None] | None = None
    cooldown: Callable[[Any], float | None] | None = None
    retry_on_resume: Callable[[Any], bool] | None = None
    parallel_safe: bool = False
    resource: str = "external"
    resource_map: dict[str, str] | None = None
    reuse: Callable[[dict[str, Any]], dict | None] | None = None

    @property
    def binding(self) -> str:
        return identity(
            self.identity,
            self.roles,
            self.permission,
            self.schema,
            self.parallel_safe,
            self.resource,
            *([self.resource_map] if self.resource_map is not None else []),
        )


def object_schema(properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


STRING = {"type": "string", "minLength": 1}
STRINGS = {"type": "array", "items": STRING}
REFERENCES = {
    "type": "array",
    "items": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
    "description": "Exact 64-character artifact refs returned by tools, not filenames, URLs, quotations or explanatory prose. Use [] when no reference exists.",
}
BUILTINS = {
    "read_context": (
        "all",
        object_schema(
            {
                "section": {
                    "type": "string",
                    "enum": [
                        "inputs",
                        "catalogs",
                        "delegated_work",
                        "clarifications",
                        "review_inputs",
                        "review_evidence",
                    ],
                },
                "offset": {"type": "integer", "minimum": 0},
                "limit": {"type": "integer", "minimum": 1},
            }
        ),
    ),
    "read_writing_guide": (
        "writer",
        object_schema({"genre": {"type": "string", "enum": list(WRITING_GUIDES)}}),
    ),
    "run_analysis": (
        "all",
        object_schema(
            {
                "purpose": STRING,
                "code": STRING,
                "inputs": {
                    "type": "array",
                    "items": object_schema({"name": STRING, "ref": STRING}),
                },
            }
        ),
    ),
    "request_clarification": ("all", object_schema({"text": STRING, "refs": STRINGS})),
    "answer_clarification": (
        "lead",
        object_schema({"question": STRING, "text": STRING, "refs": STRINGS}),
    ),
    "record_evidence": (
        "investigator",
        {
            **object_schema(
                {
                    "text": STRING,
                    "source": STRING,
                    "offset": {"type": "integer"},
                    "quote": STRING,
                    "limits": {"type": "string"},
                    "selection": {
                        **STRING,
                        "description": "Exact selection returned by read_source; supplies source and original quote without transcription.",
                    },
                }
            ),
            "required": ["text"],
            "oneOf": [{"required": ["selection"]}, {"required": ["source", "quote"]}],
        },
    ),
    "calculate": ("all", object_schema({"expression": STRING})),
    "measure_text": (
        "writer",
        {**object_schema({"text": STRING, "evidence": STRINGS}), "required": ["text"]},
    ),
    "wait_for_work": ("lead", object_schema({"refs": STRINGS})),
    "pin_evidence": ("all", object_schema({"refs": STRINGS})),
    "delegate_work": (
        "lead",
        {
            **object_schema(
                {
                    "role": {
                        **STRING,
                        "enum": ["investigator", "synthesizer", "writer", "reviewer"],
                    },
                    "task": STRING,
                    "refs": REFERENCES,
                    "review_mode": {"type": "string", "enum": ["final", "check"]},
                    "shared_context": {
                        "type": "string",
                        "description": "Evidence-based common scope/definitions for this work; do not prescribe unresearched conclusions.",
                    },
                    "deliverable": {
                        "type": "string",
                        "description": "User-facing purpose and required coverage; internal audit logs are not report sections.",
                    },
                }
            ),
            "required": ["role", "task", "refs"],
        },
    ),
    "finish_work": (
        "investigator",
        {
            **object_schema(
                {
                    "text": STRING,
                    "refs": STRINGS,
                    "supersedes": REFERENCES,
                }
            ),
            "required": ["text", "refs"],
        },
    ),
    "save_memory": (
        "all",
        object_schema(
            {
                "text": STRING,
                "refs": STRINGS,
            }
        ),
    ),
    "read_artifact_range": (
        "all",
        object_schema(
            {
                "ref": STRING,
                "offset": {"type": "integer"},
                "limit": {"type": "integer"},
            }
        ),
    ),
    "discover_local": ("lead", object_schema({"root": STRING})),
    "read_catalog": (
        "all",
        object_schema(
            {
                "ref": STRING,
                "offset": {"type": "integer"},
                "limit": {"type": "integer"},
            }
        ),
    ),
    "snapshot_local": (
        "lead",
        object_schema(
            {
                "catalog": STRING,
                "path": STRING,
            }
        ),
    ),
    "propose_plan": (
        "lead",
        object_schema(
            {
                "text": STRING,
                "brief": object_schema(
                    {
                        "subject": {
                            **STRING,
                            "description": "用户指定的研究对象或主题；不填写研究假设或预定结论。",
                        },
                        "given_context": STRINGS,
                        "questions": {**STRINGS, "minItems": 1},
                        "material_scope": object_schema(
                            {
                                "mode": {
                                    **STRING,
                                    "enum": [
                                        "case_materials",
                                        "library",
                                        "unspecified",
                                    ],
                                },
                                "basis": STRING,
                            }
                        ),
                    }
                ),
            }
        ),
    ),
    "save_note": ("lead", object_schema({"text": STRING, "refs": STRINGS})),
    "draft_report": (
        "writer",
        {
            **object_schema(
                {
                    "text": STRING,
                    "evidence": STRINGS,
                    "handoff": {"type": "string"},
                    "base": {
                        **STRING,
                        "pattern": "^[0-9a-f]{64}$",
                        "description": "Exact current report ref for a revision; omit only for a first draft.",
                    },
                }
            ),
            "required": ["text", "evidence"],
        },
    ),
    "read_report": (
        "reviewer",
        object_schema({"offset": {"type": "integer"}, "limit": {"type": "integer"}}),
    ),
    "submit_review": (
        "reviewer",
        {
            **object_schema(
                {"reason": STRING, "defects": STRINGS, "comments": STRINGS}
            ),
            "required": ["reason", "defects"],
        },
    ),
    "publish_report": (
        "lead",
        object_schema(
            {
                "report": STRING,
                "review": STRING,
            }
        ),
    ),
    "read_artifact": ("all", object_schema({"ref": STRING})),
    "find_artifacts": (
        "all",
        object_schema(
            {
                "kind": {
                    **STRING,
                    "enum": [
                        "source",
                        "note",
                        "report",
                        "review",
                        "clarification",
                        "clarification_answer",
                        "plan",
                        "observation",
                        "catalog",
                        "memory",
                        "work_result",
                        "work",
                    ],
                },
                "query": {"type": "string"},
                "after": {"type": "integer"},
                "limit": {"type": "integer"},
            }
        ),
    ),
    "read_source": (
        "all",
        object_schema(
            {
                "ref": STRING,
                "offset": {"type": "integer"},
                "limit": {"type": "integer"},
            }
        ),
    ),
}


# A shared workbench, not new workflow stages. Identity checks belong to the
# host; evidence interpretation and readiness belong to the research Agent.
BUILTINS.update(
    {
        "record_finding": (
            "research",
            {
                **object_schema(
                    {
                        "statement": STRING,
                        "status": {**STRING, "enum": list(STATUSES)},
                        "support": {**REFERENCES, "minItems": 1},
                        "conditions": STRINGS,
                        "limits": STRINGS,
                        "replaces": STRING,
                        "reason": {"type": "string"},
                    }
                ),
                "required": ["statement", "status", "support"],
            },
        ),
        "record_conflict": (
            "research",
            {
                **object_schema(
                    {
                        "question": STRING,
                        "findings": {**REFERENCES, "minItems": 1},
                        "disposition": {**STRING, "enum": list(DISPOSITIONS)},
                        "explanation": {"type": "string"},
                        "evidence": REFERENCES,
                        "replaces": STRING,
                    }
                ),
                "required": ["question", "findings"],
            },
        ),
        "prepare_writing": (
            "research",
            {
                **object_schema(
                    {
                        "findings": REFERENCES,
                        "coverage": {
                            "type": "array",
                            "minItems": 1,
                            "items": {
                                **object_schema(
                                    {
                                        "question": {"type": "integer", "minimum": 0},
                                        "findings": REFERENCES,
                                        "limitation": {"type": "string"},
                                    }
                                ),
                                "required": ["question", "findings"],
                            },
                        },
                        "rationale": STRING,
                        "limitations": STRINGS,
                        "replaces": STRING,
                    }
                ),
                "required": ["findings", "coverage", "rationale"],
            },
        ),
        "read_draft": (
            "research",
            {
                **object_schema(
                    {
                        "ref": STRING,
                        "offset": {"type": "integer", "minimum": 0},
                        "limit": {"type": "integer", "minimum": 1},
                    }
                ),
                "required": [],
            },
        ),
        "patch_draft": (
            "research",
            {
                **object_schema(
                    {
                        "base": STRING,
                        "basis": STRING,
                        "evidence": REFERENCES,
                        "edits": {
                            "type": "array",
                            "minItems": 1,
                            "items": object_schema(
                                {
                                    "old": STRING,
                                    "new": {"type": "string"},
                                }
                            ),
                        },
                        "handoff": {"type": "string"},
                    }
                ),
                "required": ["base"],
            },
        ),
    }
)
BUILTINS["patch_draft"][1]["properties"]["basis"] = {
    **STRING,
    "description": "New valid basis; required and different for basis-only updates.",
}
BUILTINS["patch_draft"][1]["properties"]["edits"]["description"] = (
    "Simultaneous edits against base; omit only for basis-only update."
)
BUILTINS["record_finding"][1]["properties"]["support"]["description"] = (
    "Only source or exact note refs; not summaries or control records."
)
BUILTINS["draft_report"][1]["properties"]["basis"] = STRING
BUILTINS["find_artifacts"][1]["properties"]["kind"]["enum"].extend(
    sorted(RESEARCH_KINDS)
)
BUILTINS["read_context"][1]["properties"]["section"]["enum"].extend(
    [
        "research_questions",
        "research_findings",
        "research_conflicts",
    ]
)


for _name in ("read_source", "read_artifact_range", "read_report"):
    _page = BUILTINS[_name][1]
    _page["required"] = [
        key for key in _page["required"] if key not in {"offset", "limit"}
    ]
    _page["properties"]["offset"].update(minimum=0, default=0)
    _page["properties"]["limit"].update(
        minimum=1,
        description="Desired maximum page size; the host may return a smaller complete page with next_offset.",
    )


def validate(value: Any, schema: dict[str, Any], path: str = "arguments") -> None:
    """Validate the deliberately small tool-schema subset used by this slice."""
    kind = schema["type"]
    if kind == "object":
        if not isinstance(value, dict):
            raise ValueError("expected object")
        props = schema["properties"]
        alternatives = schema.get("oneOf")
        if (
            alternatives
            and sum(
                set(option.get("required", ())).issubset(value)
                for option in alternatives
            )
            != 1
        ):
            raise ValueError(f"{path}: select exactly one documented argument form")
        if not set(schema.get("required", ())).issubset(value) or set(value) - set(
            props
        ):
            missing = sorted(set(schema.get("required", ())) - set(value))
            extra = sorted(set(value) - set(props))
            raise ValueError(
                f"{path}: missing fields {missing}; unexpected fields {extra}"
            )
        for key in value:
            validate(value[key], props[key], f"{path}.{key}")
    elif kind == "array":
        if not isinstance(value, list):
            raise ValueError("expected array")
        if len(value) < schema.get("minItems", 0):
            raise ValueError("too few items")
        for index, item in enumerate(value):
            validate(item, schema["items"], f"{path}[{index}]")
    elif kind == "string":
        if not isinstance(value, str) or len(value.strip()) < schema.get(
            "minLength", 0
        ):
            raise ValueError("expected non-empty text")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            raise ValueError(
                f"{path}: expected an exact artifact ref (64 lowercase hexadecimal characters), not prose; copy the ref returned by tools"
            )
    elif kind == "boolean":
        if type(value) is not bool:
            raise ValueError("expected boolean")
    elif kind == "integer":
        if type(value) is not int:
            raise ValueError("expected integer")
        if value < schema.get("minimum", value) or value > schema.get("maximum", value):
            raise ValueError(f"{path}: outside declared range")
    else:
        raise ValueError("unsupported schema type")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError("expected one of: " + ", ".join(schema["enum"]))


PRIVATE_ARTIFACT_KINDS = frozenset({"step", "step_done", "control", "material_bytes"})


class Harness:
    def _validate_call(self, call, schema):
        bounded_json(call.arguments)
        tool = self.tools.get(call.name)
        if tool is not None and tool.validate_arguments is not None:
            tool.validate_arguments(call.arguments)
        else:
            validate(call.arguments, schema[call.name]["parameters"])
        if tool is not None and tool.check is not None:
            tool.check(call.arguments)

    def __init__(
        self,
        store: Store,
        model: Model,
        tools: dict[str, Tool] | None = None,
        context_chars: int = 48000,
        scheduler: Scheduler | None = None,
        sandbox=None,
    ):
        self.store, self.model = store, model
        self.scheduler = scheduler or Scheduler(history=store.admissions())
        self.tools = tools or {}
        self.workspace = Workspace(store)
        self.research = ResearchLedger(store)
        self.writing = WritingWorkspace(store)
        self.analysis = AnalysisRuntime(store, self.scheduler, sandbox)
        if set(self.tools) & set(BUILTINS):
            raise ValueError("external tools may not replace runtime tools")
        if context_chars < 4000:
            raise ValueError("context capacity too small")
        self.context_chars = context_chars
        self._locks: dict[str, asyncio.Lock] = {}

    def _schema(self, role: str, policy: dict[str, Any]) -> dict[str, dict[str, Any]]:
        # "lead" is the persisted name of the continuous research owner, not a
        # coordinator that must outsource reading and authorship. External tools
        # still require their explicit role grant AND the study's authorization.
        research = role in {"lead", "investigator", "synthesizer", "writer"}
        shared_research = {
            "record_evidence",
            "draft_report",
            "read_writing_guide",
            "measure_text",
            "save_note",
            "discover_local",
            "snapshot_local",
        }
        result: dict[str, dict[str, Any]] = {
            name: {"description": TOOLS.get(name, name), "parameters": schema}
            for name, (allowed, schema) in BUILTINS.items()
            if allowed in (role, "all")
            or (research and (name in shared_research or allowed == "research"))
            or (role in {"synthesizer", "writer"} and name == "finish_work")
            or (
                role == "reviewer"
                and name in {"save_note", "discover_local", "snapshot_local"}
            )
        }
        if role == "reviewer" and policy.get("_review_mode") == "check":
            result.pop("submit_review")
            result["finish_work"] = {
                "description": TOOLS["finish_work"],
                "parameters": BUILTINS["finish_work"][1],
            }
        if not policy.get("analysis"):
            result.pop("run_analysis", None)
        if role == "lead":
            result.pop("request_clarification", None)  # No questions to the user.
            if policy.get("_approved"):
                result.pop("propose_plan", None)
            else:
                result = {
                    k: v
                    for k, v in result.items()
                    if k
                    in {
                        "read_context",
                        "propose_plan",
                        "discover_local",
                        "read_catalog",
                        "find_artifacts",
                        "read_artifact",
                        "read_artifact_range",
                        "save_memory",
                    }
                }
        denied = set(PRIVATE_ARTIFACT_KINDS)
        if not policy.get("_approved"):
            denied.add("source")
        for name in ("read_artifact", "read_artifact_range"):
            result[name]["description"] += (
                " Not readable with this tool: " + ", ".join(sorted(denied)) + "."
            )
        for name, tool in self.tools.items():
            if (
                policy.get("_approved")
                and role in tool.roles
                and (tool.permission is None or policy.get(tool.permission) is True)
            ):
                result[name] = {
                    "description": tool.description,
                    "parameters": tool.schema,
                }
        return result

    def _read_denial(self, study: str, kind: str) -> str | None:
        if kind == "source" and not self.store.control(study).approved:
            return "source examination requires initial route approval"
        if kind in PRIVATE_ARTIFACT_KINDS:
            return "execution and provider-private records are not research materials"
        return None

    def _review(self, study: str, work: Artifact):
        reports = [
            item
            for ref in work.body["inputs"]
            if (item := self.store.get(study, ref)).kind == "report"
        ]
        if len(reports) != 1:
            raise ValueError("review requires one bound report")
        return (
            reports[0],
            units(reports[0].body["text"]),
        )

    def _request(
        self,
        study: str,
        work: Artifact,
        *,
        memory_override=None,
        pins_override=None,
        prepare_wire=True,
        section=None,
        offset=0,
        limit=20,
    ) -> dict[str, Any]:
        from .domain import ContextCapacity

        options = dict(
            memory_override=memory_override,
            pins_override=pins_override,
            prepare_wire=prepare_wire,
            section=section,
            offset=offset,
            limit=limit,
        )
        try:
            return self._assemble_request(study, work, **options)
        except ContextCapacity:
            if section is not None:
                raise
            # Recover only previously accepted projections, never downgrade the
            # field currently being validated for a new write.
            for field, kind in (
                ("pins_override", "evidence_anchor"),
                ("memory_override", "memory"),
            ):
                if options[field] is not None:
                    continue
                originals = self._steps(study, kind, work.ref, limit=1)
                if not originals:
                    continue
                options[field] = {
                    "ref": originals[-1].ref,
                    "body_omitted": True,
                    "reason": "archived_context_exceeds_current_window",
                    "instruction": "Read this complete original with read_artifact_range before replacing its working projection; retain relevant evidence and the current task and direction.",
                }
                try:
                    return self._assemble_request(study, work, **options)
                except ContextCapacity:
                    continue
            raise

    def _focused_research_refs(self, study: str, work: Artifact) -> set[str]:
        """Follow explicit shared research dependencies, never private transcripts.

        Only focused helpers use this projection. Global directories remain
        explicitly readable and permissions are unchanged. Corrected versions
        travel alongside assigned historical records, rather than stale prose
        silently being treated as current evidence.
        """
        pending = list(self._handoff_inputs(study, work))
        memory = self._steps(study, "memory", work.ref, limit=1)
        if memory:
            pending.extend(memory[-1].body.get("refs", []))
        replacements = {
            item.body["replaces"]: item.ref
            for kind in ("finding", "research_conflict", "writing_basis")
            for item in self.store.list(study, kind)
            if item.body.get("replaces")
            and item.body.get("direction") == work.body["direction"]
        }
        visited: set[str] = set()
        while pending:
            ref = pending.pop()
            if ref in visited:
                continue
            item = self.store.get(study, ref)
            visited.add(ref)
            if ref in replacements:
                pending.append(replacements[ref])
            if item.kind not in {
                "work_result", "finding", "research_conflict", "writing_basis", "note", "report"
            }:
                continue
            for key in ("refs", "support", "sources", "findings", "evidence"):
                values = item.body.get(key, [])
                if isinstance(values, list):
                    pending.extend(
                        value for value in values
                        if isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value)
                    )
            if item.kind == "report" and item.body.get("basis"):
                pending.append(item.body["basis"])
        return visited

    def _assemble_request(
        self,
        study: str,
        work: Artifact,
        *,
        memory_override=None,
        pins_override=None,
        prepare_wire=True,
        section=None,
        offset=0,
        limit=20,
    ) -> dict[str, Any]:
        direction = self.store.get(study, work.body["direction"])
        control = self.store.control(study)
        plan = self.store.get(study, control.plan) if control.plan else None
        anchors = self._steps(study, "evidence_anchor", work.ref, limit=1)
        knowledge = self.research.snapshot(study)
        focused = work.body["role"] in {"investigator", "synthesizer"}
        related = self._focused_research_refs(study, work) if focused else set()
        mandatory = {
            "provider": self.model.identity,
            "system": (
                ROUTE_PROMPT
                if work.body["role"] == "lead" and not control.approved
                else ROLES[work.body["role"]]
            ),
            "prompt_version": PROMPT_VERSION,
            "phase": "research" if control.approved else "route_approval",
            "context_scope": "assigned_research_dependencies" if focused else "current_writing_basis",
            "role": work.body["role"],
            "work_ref": work.ref,
            "direction_ref": direction.ref,
            "task": work.body["task"],
            "shared_context": work.body.get("shared_context", ""),
            "deliverable": work.body.get("deliverable", ""),
            "draft": self._draft_head(study, work),
            "writing_basis": knowledge["basis"],
            "current_date": direction.body["policy"].get("as_of_date")
            or datetime.now(timezone.utc).date().isoformat(),
            "direction": direction.body,
            "research_scope": {
                "brief": plan.body.get("brief")
                if plan is not None and direction.ref in plan.parents
                else None,
                "approved_plan": None
                if plan is None
                else {
                    "ref": plan.ref,
                    "current_direction": direction.ref in plan.parents,
                },
                "available_sources": self.store.count(study, "source"),
                "source_lookup": "find_artifacts(kind='source', query='', after=0)",
            },
            "inputs": [
                {"ref": ref, "kind": self.store.get(study, ref).kind}
                for ref in self._handoff_inputs(study, work)
            ],
            "catalogs": self.store.catalog_index(study),
            "delegated_work": [
                {
                    "ref": child.ref,
                    "task": child.body["task"],
                    "role": child.body["role"],
                    **(
                        {"review_mode": child.body.get("review_mode", "final")}
                        if child.body["role"] == "reviewer"
                        else {}
                    ),
                    "results": [
                        a.ref for a in self._steps(study, "work_result", child.ref)
                    ],
                    "finished": self.finished(study, child.ref),
                }
                for child in self.store.matching(study, "work", {"owner": work.ref})
            ],
            "pinned_evidence": pins_override
            if pins_override is not None
            else (anchors[-1].body["refs"] if anchors else []),
            "tools": self._schema(
                work.body["role"],
                {
                    **direction.body["policy"],
                    "_approved": control.approved,
                    "_review_mode": work.body.get("review_mode", "final"),
                },
            ),
            "tool_versions": {name: tool.binding for name, tool in self.tools.items()},
        }
        if work.body["role"] == "reviewer":
            report, parts = self._review(study, work)
            mandatory["review_mode"] = work.body.get("review_mode", "final")
            mandatory["review_progress"] = {
                "report": report.ref,
                "evidence": report.body["evidence"],
                "total_units": len(parts),
                "inputs": self._relations(study, report),
            }
        candidates = self._steps(study, "observation", work.ref, limit=64)
        # Readiness and canonical findings arrive as original artifacts. The
        # editor sees the exact basis used by its bound report, not a new summary.
        basis_ref = (
            report.body.get("basis")
            if work.body["role"] == "reviewer"
            else knowledge["basis"]["ref"]
            if knowledge["basis"]
            else None
        )
        if basis_ref and not focused:
            basis_item = self.store.get(study, basis_ref)
            candidates.append(basis_item)
            candidates.extend(
                self.store.get(study, ref) for ref in basis_item.body["findings"]
            )

        if work.body["role"] == "reviewer":
            candidates.append(report)
        candidates.extend(self._steps(study, "note", work.ref, limit=64))
        if plan is not None and direction.ref in plan.parents:
            candidates.append(plan)
        if focused:
            candidates.extend(
                item for ref in related
                if (item := self.store.get(study, ref)).kind
                in {"finding", "research_conflict", "note", "work_result"}
            )
        candidates.extend(
            self.store.get(study, ref)
            for ref in self._handoff_inputs(study, work)
            if self.store.get(study, ref).kind
            in {
                "work_result",
                "plan",
                "note",
                "clarification_answer",
                "finding",
                "research_conflict",
                "writing_basis",
            }
            and not (
                work.body["role"] == "reviewer"
                and self.store.get(study, ref).kind == "work_result"
                and self.store.get(study, ref).body.get("report") != report.ref
            )
        )
        # Related inputs remain original artifacts, never an intermediate summary.
        if work.body["role"] == "reviewer":
            candidates.extend(
                self.store.get(study, x["ref"])
                for x in self._relations(study, report)
                if x["kind"] == "clarification_answer"
            )
        questions = (
            self.store.clarifications(study, owner=work.ref)
            if work.body["role"] == "lead"
            else self.store.clarifications(study, work=work.ref)
        )
        answers = {
            a.body["question"]: a
            for a in self.store.list(study, "clarification_answer")
        }
        mandatory["clarifications"] = [
            {
                "question": q.ref,
                "work": q.body["work"],
                "answer": answers[q.ref].ref if q.ref in answers else None,
            }
            for q in questions
        ]
        directories = {
            key: mandatory.pop(key)
            for key in ("inputs", "catalogs", "delegated_work", "clarifications")
        }
        directories.update(
            research_questions=knowledge["questions"],
            research_findings=knowledge["findings"],
            research_conflicts=knowledge["conflicts"],
        )
        if work.body["role"] == "reviewer":
            directories["review_inputs"] = mandatory["review_progress"].pop("inputs")
            directories["review_evidence"] = mandatory["review_progress"].pop(
                "evidence"
            )
        if section is not None:
            if section not in directories:
                raise ValueError("context section unavailable to this work")
            return page(directories[section], offset, limit, self.context_chars // 3)
        memories = self._steps(study, "memory", work.ref, limit=1)
        active_memory = (
            memory_override
            if memory_override is not None
            else (memories[-1] if memories else None)
        )
        revision_refs = list(self._handoff_inputs(study, work))
        if isinstance(active_memory, Artifact):
            revision_refs.extend(active_memory.body.get("refs", []))
        revisions = self.store.revisions(study, revision_refs, direction.ref)
        mandatory["input_revisions"] = revisions
        candidates.extend(
            self.store.get(study, ref) for ref in dict.fromkeys(revisions.values())
        )
        mandatory["navigation"] = {
            key: {"offset": 0, "total": len(items), "next_offset": 0 if items else None}
            for key, items in directories.items()
        }
        for key in directories:
            if key.startswith("review_"):
                mandatory["review_progress"][key.removeprefix("review_")] = []
            else:
                mandatory[key] = []
        # Reserve the complete task and memory before allocating any growing directory.
        essential = assemble(mandatory, [], active_memory, self.context_chars)
        allocation = min(
            self.context_chars // 32,
            max(0, self.context_chars - len(encode(essential)) - 256)
            // len(directories),
        )
        for key, items in directories.items():
            # Do not inject unrelated conclusions into a clean helper context.
            # read_context(section=...) above still returns the complete global
            # directory with its real cursor; no hidden retrieval restrictions.
            if focused and key in {"research_findings", "research_conflicts"}:
                continue
            first = (
                page(items, 0, 20, allocation)
                if allocation >= 256
                else {"items": [], **mandatory["navigation"][key]}
            )
            mandatory["navigation"][key] = {
                k: v for k, v in first.items() if k != "items"
            }
            if key.startswith("review_"):
                mandatory["review_progress"][key.removeprefix("review_")] = first[
                    "items"
                ]
            else:
                mandatory[key] = first["items"]
        for q in questions:
            candidates.append(q)
            if q.ref in answers:
                answer = answers[q.ref]
                candidates.append(answer)
                candidates.extend(
                    self.store.get(study, ref)
                    for ref in answer.body["refs"]
                    if self.store.get(study, ref).kind in {"work_result", "note"}
                )
        # Preserve the producer's original task boundary beside its answer.
        candidates.extend(
            self.store.get(study, item.body["producer"])
            for item in tuple(candidates)
            if item.kind == "work_result" and item.body.get("producer")
        )
        candidates = list({a.ref: a for a in candidates}.values())
        request = assemble(
            mandatory,
            candidates,
            active_memory,
            self.context_chars,
            direct_refs=[item["ref"] for item in directories["inputs"]],
        )
        prepare = getattr(self.model, "prepare", None)
        if prepare:
            request = fit_provider(request, prepare)
        if prepare and prepare_wire:
            previous = None
            steps = self._steps(study, "step", work.ref, limit=1)
            if steps:
                last = steps[-1]
                if "wire" in last.body["request"]:
                    previous = {
                        "request": last.body["request"]["wire"]["payload"],
                        "response": self._result(
                            study, identity("model", work.ref, last.ref)
                        ),
                        "observations": [
                            {**a.body, "_ref": a.ref}
                            for a in self.store.related(study, "observation", last.ref)
                        ],
                    }
                    if any("error" in o for o in previous["observations"]):
                        previous = None
            request["wire"] = prepare(request, previous)
        return request

    def _attempt(self, study: str, operation: str):
        retries = self.store.matching(study, "retry", {"operation": operation}, limit=1)
        return retries[-1] if retries else None

    def _result(self, study: str, operation: str):
        retry = self._attempt(study, operation)
        return self.store.result(study, retry.body["next"] if retry else operation)

    async def _invoke(
        self,
        study,
        work,
        epoch,
        step,
        operation,
        request,
        invoke,
        retry_delay=None,
        retry_on_resume=None,
        resource="external",
        request_step=None,
        invoke_received=None,
    ):
        retry = self._attempt(study, operation)
        attempt = retry.body["attempt"] if retry else 0
        key = retry.body["next"] if retry else operation
        while True:
            if retry:
                # Persisted wall-clock deadline survives process restart. Short
                # cooperative waits also fence pause/steer before another send.
                while retry.body["not_before"] > time.time():
                    self.store.require_work(study, work, epoch)
                    await asyncio.sleep(
                        min(0.25, retry.body["not_before"] - time.time())
                    )
            if self.store.operation_status(study, key) is None:
                queued_at = self.scheduler.clock()
                tokens = (
                    request.get("wire", {}).get("estimated_input_tokens", 0)
                    + getattr(self.model, "max_tokens", 0)
                    if request_step is not None
                    else 0
                )
                async with self.scheduler.slot(
                    resource,
                    lambda: self.store.require_work(study, work, epoch),
                    tokens,
                ) as admitted:
                    raw = self.store.admit(
                        study,
                        work,
                        epoch,
                        key,
                        request,
                        request_step=request_step,
                        admission={
                            "queued_at": queued_at,
                            "at": admitted,
                            "resource": resource,
                            "tokens": tokens,
                            "model": getattr(self.model, "model", None)
                            if request_step
                            else None,
                        },
                    )
                    if raw is None:
                        self.store.mark_invoked(key, self.scheduler.clock())
                        raw = (
                            await invoke_received(
                                lambda value: self.store.settle(
                                    key, value, settled_at=self.scheduler.clock()
                                )
                            )
                            if invoke_received
                            else await invoke()
                        )
                        self.store.settle(key, raw, settled_at=self.scheduler.clock())
            else:
                raw = self.store.admit(
                    study, work, epoch, key, request, request_step=request_step
                )
            delay = retry_delay(raw, attempt) if retry_delay else None
            if (
                delay is None
                and retry_on_resume
                and retry_on_resume(raw)
                and epoch > self.store.admission_epoch(study, key)
            ):
                delay = 0
            if delay is None:
                self.store.require_work(study, work, epoch)
                return raw
            if not math.isfinite(delay) or delay < 0:
                raise ValueError("invalid provider retry delay")
            epoch_attempt = (
                retry.body.get("epoch_attempt", retry.body["attempt"])
                if retry and retry.body.get("recovery_epoch", epoch) == epoch
                else 0
            )
            if epoch_attempt >= 5:
                raise RecoveryExhausted(
                    "automatic recovery exhausted for this operation; explicit resume required"
                )
            attempt += 1
            next_key = identity("retry", operation, attempt)
            retry = self.store.put(
                study,
                "retry",
                {
                    "operation": operation,
                    "previous": key,
                    "next": next_key,
                    "attempt": attempt,
                    "recovery_epoch": epoch,
                    "epoch_attempt": epoch_attempt + 1,
                    "not_before": time.time() + delay,
                    "resource": resource,
                },
                (work, step),
            )
            self.scheduler.defer(resource, retry.body["not_before"])
            self.store.require_work(study, work, epoch)
            key = next_key

    def _steps(self, study: str, kind: str, work: str, *, limit=None) -> list[Artifact]:
        return self.store.related(
            study,
            kind,
            work,
            producer=kind
            in {
                "work_result",
                "draft_saved",
                "note",
                "memory",
                "evidence_anchor",
                "work_wait",
            },
            # Only step has one parent; multi-parent artifacts are sorted by ref.
            first_parent=kind == "step",
            limit=limit,
        )

    def _handoff_inputs(self, study: str, work: Artifact) -> tuple[str, ...]:
        questions = {q.ref for q in self.store.clarifications(study, work=work.ref)}
        refs = list(work.body["inputs"])
        for answer in self.store.list(study, "clarification_answer"):
            if answer.body["question"] in questions:
                refs.extend((answer.ref, *answer.body["refs"]))
        refs.extend(self.store.revisions(study, refs, work.body["direction"]).values())
        return tuple(dict.fromkeys(refs))

    def _relations(self, study: str, item: Artifact) -> list[dict]:
        visible = {
            "source",
            "work",
            "work_result",
            "report",
            "review",
            "plan",
            "note",
            "memory",
            "catalog",
            "clarification",
            "clarification_answer",
            *RESEARCH_KINDS,
        }
        return [
            {"ref": a.ref, "kind": a.kind, "producer": a.body.get("producer")}
            for ref in item.parents
            if (a := self.store.get(study, ref)).kind in visible
        ]

    def waiting(self, study: str, work: str) -> bool:
        return bool(self.store.clarifications(study, work=work, open_only=True))

    def _draft_head(self, study: str, work: Artifact) -> dict | None:
        draft = self.writing.current(study, work.body["direction"])
        if draft is None:
            return None
        receipts = self.store.matching(study, "draft_saved", {"ref": draft.ref})
        return {
            "ref": draft.ref,
            "receipt": receipts[-1].ref if receipts else None,
            "basis": draft.body["basis"],
            "state": "saved_not_finished",
        }

    def finished(self, study: str, work: str) -> bool:
        return bool(self._steps(study, "work_result", work))

    async def step(self, study: str, work_ref: str) -> str:
        # One active sampler per work. User commands remain synchronous and do not
        # wait for this lock, so they can fence an in-flight external request.
        lock = self._locks.setdefault(work_ref, asyncio.Lock())
        async with lock:
            control = self.store.control(study)
            work = self.store.require_work(study, work_ref, control.epoch)
            if self.finished(study, work_ref):
                return "finished"
            steps = self._steps(study, "step", work_ref, limit=1)
            done = (
                {
                    a.body["step"]
                    for a in self.store.related(study, "step_done", steps[-1].ref)
                }
                if steps
                else set()
            )
            pending = [s for s in steps if s.ref not in done]
            if self.waiting(study, work_ref) and not pending:
                return "waiting"
            if pending:
                step = pending[-1]
            else:
                self._check_repeated(study, work_ref, control.epoch)
                if (
                    steps
                    and steps[0].body["request"]["provider"] != self.model.identity
                ):
                    raise NotAllowed("work is bound to its original model")
                step = self.store.put(
                    study,
                    "step",
                    {
                        "number": steps[-1].body["number"] + 1 if steps else 0,
                        "epoch": control.epoch,
                        "progress": self._progress(study),
                        "request": self._request(study, work),
                    },
                    (work_ref,),
                )
            operation = identity("model", work_ref, step.ref)
            if step.body["request"]["provider"] != self.model.identity:
                raise NotAllowed("pending work requires its original model binding")
            if step.body["request"]["tool_versions"] != {
                name: tool.binding for name, tool in self.tools.items()
            }:
                raise NotAllowed("pending work requires its original tool bindings")
            direction = self.store.get(study, work.body["direction"])
            current_schema = self._schema(
                work.body["role"],
                {
                    **direction.body["policy"],
                    "_approved": control.approved,
                    "_review_mode": work.body.get("review_mode", "final"),
                },
            )
            if any(
                current_schema.get(name) != spec
                for name, spec in step.body["request"]["tools"].items()
            ):
                raise NotAllowed("pending work requires its original tool contracts")
            raw = await self._invoke(
                study,
                work_ref,
                control.epoch,
                step.ref,
                operation,
                step.body["request"],
                lambda: self.model.complete(step.body["request"]),
                getattr(self.model, "retry_delay", None),
                getattr(self.model, "retry_on_resume", None),
                getattr(
                    self.model,
                    "quota_resource",
                    getattr(self.model, "resource", "model"),
                ),
                request_step=step.ref,
            )
            # Always save the external result; only then check the admission fence.
            self.store.require_work(study, work_ref, control.epoch)
            try:
                decode = getattr(self.model, "decode", None)
                reply = Reply.from_json(decode(raw) if decode else raw)
                if not reply.complete:
                    raise ValueError(
                        "incomplete response; no tool was executed. "
                        "Commit a small tool call next, split long text "
                        "into smaller batches; do not repeat the whole response."
                    )
            except (KeyError, TypeError, ValueError) as exc:
                self.store.observation(
                    study,
                    work_ref,
                    control.epoch,
                    {
                        "step": step.ref,
                        "error": str(exc),
                    },
                    (step.ref,),
                )
                self._done(study, work_ref, step.ref, identity("protocol", str(exc)))
                return "continue"
            schema = step.body["request"]["tools"]
            prefetched: set[int] = set()
            prefetch_errors = {}
            for index, call in enumerate(reply.calls):
                if index not in prefetched:
                    batch = []
                    for j in range(
                        index, min(len(reply.calls), index + self.scheduler.capacity)
                    ):
                        candidate = reply.calls[j]
                        tool = self.tools.get(candidate.name)
                        if (
                            tool is None
                            or not tool.parallel_safe
                            or candidate.name not in schema
                        ):
                            break
                        try:
                            self._validate_call(candidate, schema)
                        except ValueError:
                            break
                        batch.append((j, candidate))
                    if len(batch) > 1:
                        # Drain all admitted calls, even when one fails. Adoption
                        # below remains ordered and replays the persisted envelopes.
                        results = await asyncio.gather(
                            *[
                                self._external(
                                    study, work_ref, control.epoch, step.ref, j, c
                                )
                                for j, c in batch
                            ],
                            return_exceptions=True,
                        )
                        prefetch_errors.update(
                            {
                                j: result
                                for (j, _), result in zip(batch, results)
                                if isinstance(result, BaseException)
                            }
                        )
                        prefetched.update(j for j, _ in batch)
                if index in prefetch_errors:
                    raise prefetch_errors[index]
                previous = [
                    a
                    for a in self.store.related(study, "observation", step.ref)
                    if a.body.get("step") == step.ref and a.body.get("index") == index
                ]
                if previous:
                    if (
                        call.name == "request_clarification"
                        and "error" not in previous[-1].body["result"]
                    ):
                        self._defer_remaining(
                            study, work_ref, control.epoch, step.ref, reply.calls, index
                        )
                        break
                    continue
                self.store.require_work(study, work_ref, control.epoch)
                invalid = False
                try:
                    if call.name not in schema:
                        raise NotAllowed("tool not available to this work")
                    self._validate_call(call, schema)
                except ValueError as exc:
                    invalid = True
                    result: Any = {"error": str(exc)}
                else:
                    if call.name in BUILTINS:
                        try:
                            if call.name == "snapshot_local":
                                source = await self.workspace.snapshot_async(
                                    study,
                                    call.arguments["catalog"],
                                    call.arguments["path"],
                                )
                                result = {
                                    "ref": source.ref,
                                    "kind": "source",
                                    "characters": len(source.body["text"]),
                                    "coverage": source.body["coverage"],
                                    "issues": source.body["issues"],
                                }
                            elif call.name == "discover_local":
                                catalog = await self.workspace.discover_async(
                                    study, call.arguments["root"]
                                )
                                result = {
                                    "ref": catalog.ref,
                                    "kind": "catalog",
                                    "count": len(catalog.body["entries"]),
                                }
                            elif call.name == "run_analysis":
                                result = await self.analysis.run(
                                    study,
                                    work,
                                    control.epoch,
                                    step.ref,
                                    index,
                                    call.arguments,
                                )
                            else:
                                result = self._builtin(
                                    study,
                                    work,
                                    control.epoch,
                                    step.ref,
                                    index,
                                    call,
                                )
                        except ValueError as exc:
                            result = {"error": str(exc)}
                    else:
                        envelope = await self._external(
                            study, work_ref, control.epoch, step.ref, index, call
                        )
                        observe = self.tools[call.name].observe
                        operation = identity("tool", step.ref, index)
                        retry = self._attempt(study, operation)
                        acquisition = {
                            "work": work_ref,
                            "step": step.ref,
                            "operation": retry.body["next"] if retry else operation,
                        }
                        try:
                            result = (
                                observe(envelope["value"], acquisition)
                                if observe
                                else envelope
                            )
                            encode(result)
                        except ValueError:
                            result = {"error": "invalid_external_result", "instruction": "Saved provider response is unusable; use another source or revise the request."}
                self.store.observation(
                    study,
                    work_ref,
                    control.epoch,
                    {
                        "step": step.ref,
                        "index": index,
                        "tool": call.name,
                        "result": result,
                        "failure": identity("tool", call.name, call.arguments, result)
                        if (invalid or call.name in BUILTINS) and "error" in result
                        else None,
                    },
                    (step.ref,),
                )
                if call.name == "request_clarification" and "error" not in result:
                    self._defer_remaining(
                        study, work_ref, control.epoch, step.ref, reply.calls, index
                    )
                    break
                if self.finished(study, work_ref):
                    break
            if not reply.calls:
                self.store.observation(
                    study,
                    work_ref,
                    control.epoch,
                    {
                        "step": step.ref,
                        "text": reply.text,
                        "instruction": "Use a result tool; prose alone does not finish work.",
                        "failure": identity("no_action"),
                    },
                    (step.ref,),
                )
            self._done(study, work_ref, step.ref)
            return "finished" if self.finished(study, work_ref) else "continue"

    def _defer_remaining(self, study, work, epoch, step, calls, index):
        """Pair every call after a persistent wait, including crash replay."""
        for skipped in range(index + 1, len(calls)):
            self.store.observation(
                study,
                work,
                epoch,
                {
                    "step": step,
                    "index": skipped,
                    "tool": calls[skipped].name,
                    "result": {
                        "not_executed": "clarification requested; reconsider after answer"
                    },
                },
                (step,),
            )

    async def _external(self, study, work, epoch, step, index, call):
        tool = self.tools[call.name]
        if (
            tool.reuse
            and self.store.operation_status(study, identity("tool", step, index))
            is None
        ):
            reused = tool.reuse(call.arguments)
            if reused is not None:
                return {"value": reused}

        async def invoke():
            return {"value": await tool.invoke(call.arguments)}

        async def received(receive):
            assert tool.invoke_received is not None
            value = await tool.invoke_received(
                call.arguments, lambda value: receive({"value": value})
            )
            return {"value": value}

        resource = (
            tool.resource_map.get(call.arguments.get("provider", ""), tool.resource)
            if tool.resource_map
            else tool.resource
        )
        raw = await self._invoke(
            study,
            work,
            epoch,
            step,
            identity("tool", step, index),
            {"tool": call.name, "arguments": call.arguments},
            invoke,
            (lambda raw, n: tool.retry_delay(raw["value"], n))
            if tool.retry_delay
            else None,
            (lambda raw: tool.retry_on_resume(raw["value"]))
            if tool.retry_on_resume
            else None,
            resource,
            invoke_received=received if tool.invoke_received else None,
        )
        delay = tool.cooldown(raw["value"]) if tool.cooldown else None
        if delay is not None:
            previous = [
                a
                for a in self.store.list(study, "cooldown")
                if a.body["operation"] == identity("tool", step, index)
            ]
            event = (
                previous[0]
                if previous
                else self.store.put(
                    study,
                    "cooldown",
                    {
                        "operation": identity("tool", step, index),
                        "resource": resource,
                        "not_before": time.time() + delay,
                    },
                    (work, step),
                )
            )
            self.scheduler.defer(resource, event.body["not_before"])
        return raw

    def _progress(self, study):
        # Only new durable research inputs can invalidate a failed attempt.
        return self.store.latest_sequence(
            study,
            (
                "source",
                "work_result",
                "clarification_answer",
                "note",
                "report",
                "review",
                "finding",
                "research_conflict",
                "writing_basis",
            ),
        )

    def _check_repeated(self, study, work, epoch):
        recent = self._steps(study, "step_done", work, limit=3)
        if len(recent) != 3 or not recent[0].body.get("failure"):
            return
        steps = [self.store.get(study, a.body["step"]) for a in recent]
        progress = self._progress(study)
        if (
            len({a.body.get("failure") for a in recent}) == 1
            and all(s.body.get("epoch") == epoch for s in steps)
            and all(s.body.get("progress") == progress for s in steps)
        ):
            raise RepeatedFailure(
                "Three identical failed rounds without progress; change the input or method before resuming this work."
            )

    def _done(self, study: str, work: str, step: str, failure=None) -> None:
        if failure is None:
            observations = [
                a.body for a in self.store.related(study, "observation", step)
            ]
            failures = [a.get("failure") for a in observations]
            if failures and all(failures):
                failure = identity("failed_round", failures)
        self.store.put(
            study, "step_done", {"step": step, "failure": failure}, (work, step)
        )

    def _builtin(
        self, study: str, work: Artifact, epoch: int, step: str, index: int, call: Call
    ) -> Any:
        self.store.require_work(study, work.ref, epoch)
        direction = work.body["direction"]
        if not self.store.control(study).approved and call.name in {
            "read_source",
            "snapshot_local",
            "record_evidence",
            "draft_report",
            "delegate_work",
            "run_analysis",
            "publish_report",
            "record_finding",
            "record_conflict",
            "prepare_writing",
            "read_draft",
            "patch_draft",
        }:
            raise NotAllowed("initial research route approval required")
        args = call.arguments
        if call.name in {"read_source", "read_artifact_range", "read_report"}:
            args = {
                "offset": 0,
                "limit": 20 if call.name == "read_report" else self.context_chars // 3,
                **args,
            }
        parents = (work.ref, direction, step)
        if call.name == "read_context":
            return self._request(
                study,
                work,
                section=args["section"],
                offset=args["offset"],
                limit=args["limit"],
            )
        if call.name in {"record_finding", "record_conflict", "prepare_writing"}:
            method = getattr(self.research, call.name)
            item = method(
                study,
                work.ref,
                epoch,
                _operation=identity(step, index, call.name),
                **args,
            )
            return {
                "ref": item.ref,
                "kind": item.kind,
                "status": item.body.get("status", item.body.get("disposition")),
                "semantic_verification": "Agent judgment, not host certification",
                "replaces": item.body.get("replaces"),
                "writing_basis": self.research.snapshot(study)["basis"],
            }
        if call.name == "read_draft":
            return self.writing.read(
                study, work.ref, epoch, capacity=self.context_chars // 3, **args
            )
        if call.name in {"draft_report", "patch_draft"}:
            return self.writing.save(
                study,
                work.ref,
                epoch,
                step,
                index,
                research_refs=self._handoff_inputs(study, work),
                **args,
            )
        if call.name == "pin_evidence":
            refs = list(dict.fromkeys(args["refs"]))
            if len(encode(refs)) > self.context_chars // 4:
                raise ValueError("pinned evidence exceeds context allocation")
            if any(self.store.get(study, ref).kind != "source" for ref in refs):
                raise ValueError("evidence anchors must name source snapshots")
            self._request(study, work, pins_override=refs, prepare_wire=False)
            item = self.store.put(
                study,
                "evidence_anchor",
                {"refs": refs, "producer": work.ref},
                (*parents, *refs),
            )
            return {"ref": item.ref}
        if call.name == "wait_for_work":
            if not args["refs"]:
                raise ValueError("wait requires delegated work references")
            for ref in args["refs"]:
                child = self.store.get(study, ref)
                if child.kind != "work" or child.body["owner"] != work.ref:
                    raise ValueError("can only wait for own delegated work")
                if self.waiting(study, child.ref):
                    raise ValueError(
                        "answer this work's clarification before waiting for it"
                    )
            item = self.store.put(
                study,
                "work_wait",
                {**args, "producer": work.ref},
                (*parents, *args["refs"]),
            )
            return {"ref": item.ref}
        if call.name == "delegate_work":
            child = self.store.work(
                study,
                self.store.control(study).ref,
                args["role"],
                args["task"],
                tuple(args["refs"]),
                work.ref,
                review_mode=args.get("review_mode", "final"),
                shared_context=args.get("shared_context", ""),
                deliverable=args.get("deliverable", ""),
            )
            return {"work": child.ref}
        if call.name == "request_clarification":
            item = self.store.ask(
                study, work.ref, epoch, args["text"], args["refs"], step
            )
            return {"ref": item.ref, "waiting": True}
        if call.name == "answer_clarification":
            item = self.store.answer(
                study, work.ref, epoch, args["question"], args["text"], args["refs"]
            )
            return {
                "ref": item.ref,
                "resumed_work": self.store.get(study, args["question"]).body["work"],
            }
        if call.name == "finish_work":
            receipts = self.store.matching(study, "draft_saved", {"producer": work.ref})
            draft_binding = {}
            if receipts:
                saved_receipt = receipts[-1]
                if saved_receipt.body["ref"] not in args["refs"]:
                    raise ValueError(
                        "include your latest saved report ref when completing author work"
                    )
                draft_binding = {
                    key: saved_receipt.body[key]
                    for key in ("ref", "handoff", "report_metrics")
                }
            for ref in args.get("supersedes", []):
                old = self.store.get(study, ref)
                producer = self.store.get(study, old.body.get("producer", ref))
                if (
                    old.kind != "work_result"
                    or ref not in self._handoff_inputs(study, work)
                    or producer.kind != "work"
                    or producer.body["role"] != work.body["role"]
                    or producer.body["direction"] != direction
                ):
                    raise ValueError(
                        "revision must replace an assigned same-role result in this direction"
                    )
            binding = {}
            if work.body["role"] == "reviewer":
                if work.body.get("review_mode", "final") != "check":
                    raise NotAllowed("final reviewer must submit a whole-report review")
                report, _ = self._review(study, work)
                binding = {"report": report.ref}
            item = self.store.put(
                study,
                "work_result",
                {**args, "producer": work.ref, **draft_binding, **binding},
                (
                    *parents,
                    *self._handoff_inputs(study, work),
                    *args["refs"],
                    *args.get("supersedes", []),
                ),
            )
            return {"ref": item.ref}
        if call.name == "save_memory":
            if len(encode(args)) > self.context_chars // 4:
                raise ValueError(
                    "memory too large; preserve critical facts and references"
                )
            prospective = Artifact(
                identity("memory-preview", args),
                study,
                "memory",
                {**args, "producer": work.ref},
                parents,
                0,
            )
            try:
                self._request(
                    study, work, memory_override=prospective, prepare_wire=False
                )
            except ValueError as exc:
                raise ValueError(
                    "memory update exceeds remaining task context; shorten it or keep details in notes; previous memory retained"
                ) from exc
            item = self.store.put(
                study,
                "memory",
                {**args, "producer": work.ref},
                (*parents, *args["refs"]),
            )
            return {"ref": item.ref}
        if call.name == "read_artifact_range":
            artifact = self.store.get(study, args["ref"])
            denial = self._read_denial(study, artifact.kind)
            if denial:
                raise NotAllowed(denial)
            body = encode(artifact.body)
            offset, limit = args["offset"], args["limit"]
            if offset < 0 or limit < 1:
                raise ValueError("invalid artifact range")
            offset = min(offset, len(body))
            limit = min(limit, self.context_chars // 3)
            relations = self._relations(study, artifact)

            def artifact_page(count):
                end = offset + count
                return {
                    "ref": artifact.ref,
                    "kind": artifact.kind,
                    "parents": relations,
                    "encoding": "canonical-json",
                    "text": body[offset:end],
                    "offset": offset,
                    "end": end,
                    "total": len(body),
                    "next_offset": end if end < len(body) else None,
                }

            return fit_read_result(
                artifact_page,
                min(limit, len(body) - offset),
                min(INLINE_TOOL_RESULT_CHARS, self.context_chars // 3),
            )
        if call.name == "read_catalog":
            return self.workspace.catalog_page(
                study, args["ref"], args["offset"], args["limit"]
            )
        if call.name == "find_artifacts":
            found = self.store.search(
                study, args["kind"], args["query"], args["after"], args["limit"]
            )
            return {
                "items": [
                    {
                        "ref": a.ref,
                        "kind": a.kind,
                        **(
                            {
                                "origin": a.body.get("origin"),
                                "characters": len(a.body["text"]),
                                "coverage": a.body.get("coverage"),
                                "read_ranges": source_ranges(
                                    a, self._steps(study, "observation", work.ref)
                                ),
                            }
                            if a.kind == "source"
                            else {}
                        ),
                    }
                    for a in found
                ],
                "next_after": found[-1].seq if found else None,
            }
        if call.name == "read_source":
            source = self.store.get(study, args["ref"])
            if source.kind == "note":
                note = source
                source = self.store.get(study, note.body.get("source", ""))
                quote, start = note.body.get("quote"), note.body.get("offset")
                if (
                    source.ref not in note.parents
                    or not isinstance(quote, str)
                    or not quote
                    or type(start) is not int
                    or start < 0
                    or source.body.get("text", "")[start : start + len(quote)] != quote
                ):
                    raise ValueError("note must bind an exact source passage")
                if "offset" not in call.arguments:
                    args["offset"] = start
            if source.kind != "source":
                raise ValueError("expected source")
            text = source.body["text"]
            offset, limit = args["offset"], args["limit"]
            if offset < 0 or limit < 1:
                raise ValueError("invalid source range")
            offset = min(offset, len(text))
            limit = min(limit, self.context_chars // 3)

            def source_page(count):
                end = offset + count
                selections = []
                for match in re.finditer(
                    r"\S[^\n]*(?:\n(?!\s*\n)[^\n]+)*", text[offset:end]
                ):
                    start, stop = offset + match.start(), offset + match.end()
                    selections.append(
                        {
                            "selection": f"{source.ref}:{start}:{stop}",
                            "preview": text[start:stop][:100],
                        }
                    )
                return {
                    "ref": source.ref,
                    "kind": "source",
                    "offset": offset,
                    "end": end,
                    "total": len(text),
                    "next_offset": end if end < len(text) else None,
                    "selections": selections,
                    "text": text[offset:end],
                    "origin": source.body.get("origin"),
                    "coverage": source.body.get("coverage"),
                    "analysis": source.body.get("analysis"),
                    "execution_status": source.body.get("execution_status"),
                    "issues": source.body.get("issues", []),
                    "segments": [
                        seg
                        for seg in source.body.get("segments", [])
                        if seg["start"] < end and seg["end"] > offset
                    ],
                }

            return fit_read_result(
                source_page,
                min(limit, len(text) - offset),
                min(INLINE_TOOL_RESULT_CHARS, self.context_chars // 3),
            )
        if call.name == "read_artifact":
            artifact = self.store.get(study, args["ref"])
            denial = self._read_denial(study, artifact.kind)
            if denial:
                raise NotAllowed(denial)
            result = {
                "ref": artifact.ref,
                "kind": artifact.kind,
                "body": artifact.body,
                "parents": self._relations(study, artifact),
            }
            if len(encode(result)) > min(
                INLINE_TOOL_RESULT_CHARS, self.context_chars // 2
            ):
                return self._builtin(
                    study,
                    work,
                    epoch,
                    step,
                    index,
                    Call("read_artifact_range", {"ref": artifact.ref}),
                )
            return result
        if call.name == "calculate":
            return calculate(args["expression"])
        if call.name == "record_evidence":
            if "selection" in args:
                if any(key in args for key in ("source", "quote", "offset")):
                    raise ValueError("use selection OR source/quote, not both")
                selected = args["selection"]
                issued = any(
                    selected == item.get("selection")
                    for observation in self._steps(study, "observation", work.ref)
                    if observation.body.get("tool") == "read_source"
                    and isinstance(observation.body.get("result"), dict)
                    for item in observation.body.get("result", {}).get("selections", [])
                    if isinstance(item, dict)
                )
                if not issued:
                    raise ValueError(
                        "selection must come from this work's read_source result"
                    )
                source_ref, start_text, end_text = selected.split(":")
                source = self.store.get(study, source_ref)
                start, end = int(start_text), int(end_text)
                args = {
                    "text": args["text"],
                    "limits": args.get("limits", ""),
                    "source": source.ref,
                    "quote": source.body["text"][start:end],
                    "offset": start,
                }
            elif not all(key in args for key in ("source", "quote")):
                raise ValueError(
                    "choose a read_source selection or provide source and exact quote"
                )
            source = self.store.get(study, args["source"])
            if source.kind != "source":
                raise ValueError("expected source snapshot")
            text, quote = source.body["text"], args["quote"]
            if not quote.strip():
                raise ValueError("evidence requires a nonempty original quote")
            start = args.get("offset")
            if start is None or start < 0 or text[start : start + len(quote)] != quote:
                candidates: list[int] = []
                position = text.find(quote)
                while position != -1 and len(candidates) < 20:
                    candidates.append(position)
                    position = text.find(quote, position + 1)
                if start is None and len(candidates) == 1 and position == -1:
                    start = candidates[0]
                else:
                    return {
                        "error": "Quote must match an original passage; omit offset for a unique match, or select a candidate offset after checking its context.",
                        "candidate_offsets": candidates,
                        "more_candidates": position != -1,
                    }
            item = self.store.put(
                study,
                "note",
                {**args, "offset": start, "producer": work.ref},
                (*parents, source.ref),
            )
        elif call.name == "save_note":
            item = self.store.put(
                study, "note", {**args, "producer": work.ref}, (*parents, *args["refs"])
            )
        elif call.name == "propose_plan":
            if self.store.control(study).approved:
                raise NotAllowed("research route is already approved")
            item = self.store.put(study, "plan", args, parents)
            self.store.put(
                study,
                "work_result",
                {"ref": item.ref, "producer": work.ref},
                (work.ref, item.ref),
            )
        elif call.name == "measure_text":
            if "evidence" not in args:
                return text_metrics(args["text"])
            rendered = render_citations(
                args["text"], args["evidence"], lambda ref: self.store.get(study, ref)
            )
            return report_metrics(rendered)
        elif call.name == "read_writing_guide":
            return {
                "genre": args["genre"],
                "guidance": WRITING_GUIDES[args["genre"]],
                "status": "advisory; user requirements take precedence",
            }
        elif call.name == "read_report":
            report, parts = self._review(study, work)
            offset, limit = args["offset"], args["limit"]
            if offset < 0 or limit < 1:
                raise ValueError("invalid report page")
            offset = min(offset, len(parts))
            shown: list[dict] = []
            for part in parts[offset : offset + min(limit, 20)]:
                if shown and len(encode([*shown, part])) > min(
                    self.context_chars // 4, 6000
                ):
                    break
                shown.append(part)
            evidence = page(report.body["evidence"], 0, 20, self.context_chars // 32)[
                "items"
            ]
            inputs = page(
                self._relations(study, report), 0, 20, self.context_chars // 32
            )["items"]
            metrics = report_metrics(report.body)

            def report_page(count):
                delivered = shown[:count]
                end = offset + count
                return {
                    "report": report.ref,
                    "units": delivered,
                    "evidence": evidence,
                    "inputs": inputs,
                    "related_context": ["review_evidence", "review_inputs"],
                    "total": len(parts),
                    "text_metrics": text_metrics(report.body["text"]),
                    "report_metrics": metrics,
                    "displayed_units_metrics": text_metrics(
                        "".join(p["text"] for p in delivered)
                    ),
                    "unit_metrics": {
                        str(p["unit"]): text_metrics(p["text"]) for p in delivered
                    },
                    "next_offset": end if end < len(parts) else None,
                }

            return fit_read_result(
                report_page,
                len(shown),
                min(INLINE_TOOL_RESULT_CHARS, self.context_chars // 3),
            )
        elif call.name == "submit_review":
            if work.body.get("review_mode", "final") == "check":
                raise NotAllowed(
                    "argument check cannot accept or reject the whole report"
                )
            report, _ = self._review(study, work)
            if not args["defects"]:
                self.store.require_report_delivery(study, work.ref, report.ref)
            item = self.store.put(
                study,
                "review",
                {
                    **args,
                    "report": report.ref,
                    "comments": args.get("comments", []),
                    "work": work.ref,
                    "accepted": not args["defects"],
                },
                (*parents, report.ref),
            )
            self.store.put(
                study,
                "work_result",
                {"ref": item.ref, "producer": work.ref},
                (work.ref, item.ref),
            )
        elif call.name == "publish_report":
            item = self.store.publish(
                study, work.ref, epoch, args["report"], args["review"]
            )
            self.store.put(
                study,
                "work_result",
                {"ref": item.ref, "producer": work.ref},
                (work.ref, item.ref),
            )
        else:
            raise ValueError("unknown built-in tool")
        return {"ref": item.ref}
