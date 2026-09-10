"""One resumable Agent loop shared by planner, researcher and reviewer."""

from __future__ import annotations

import asyncio
import math
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Protocol

from .context import assemble, source_ranges
from .domain import (
    Artifact,
    Call,
    Conflict,
    NotAllowed,
    Reply,
    encode,
    identity,
)
from .prompts import ROLES, TOOLS
from .scheduling import Scheduler
from .storage import Store
from .workspace import Workspace


class Model(Protocol):
    identity: str

    async def complete(self, request: dict[str, Any]) -> dict[str, Any]: ...


@dataclass(frozen=True)
class Tool:
    description: str
    schema: dict[str, Any]
    invoke: Callable[[dict[str, Any]], Awaitable[Any]]
    roles: tuple[str, ...] = ("researcher", "reviewer", "investigator")
    identity: str = "v1"
    permission: str | None = None
    observe: Callable[[Any], Any] | None = None
    check: Callable[[dict[str, Any]], None] | None = None
    retry_delay: Callable[[Any, int], float | None] | None = None
    retry_on_resume: Callable[[Any], bool] | None = None
    parallel_safe: bool = False
    resource: str = "external"

    @property
    def binding(self) -> str:
        return identity(
            self.identity,
            self.roles,
            self.permission,
            self.schema,
            self.parallel_safe,
            self.resource,
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
BUILTINS = {
    "pin_evidence": ("all", object_schema({"refs": STRINGS})),
    "delegate_research": (
        "researcher",
        object_schema({"task": STRING, "refs": STRINGS}),
    ),
    "finish_investigation": (
        "investigator",
        object_schema(
            {
                "text": STRING,
                "refs": STRINGS,
            }
        ),
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
    "discover_local": ("researcher", object_schema({"root": STRING})),
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
        "researcher",
        object_schema(
            {
                "catalog": STRING,
                "path": STRING,
            }
        ),
    ),
    "propose_plan": ("planner", object_schema({"text": STRING})),
    "save_note": ("researcher", object_schema({"text": STRING, "refs": STRINGS})),
    "draft_report": (
        "researcher",
        object_schema(
            {
                "text": STRING,
                "evidence": STRINGS,
            }
        ),
    ),
    "submit_review": (
        "reviewer",
        object_schema(
            {
                "accepted": {"type": "boolean"},
                "reason": STRING,
                "checks": {
                    "type": "array",
                    "items": object_schema(
                        {
                            "claim": STRING,
                            "evidence": STRINGS,
                            "assessment": STRING,
                            "requires_revision": {"type": "boolean"},
                        }
                    ),
                },
            }
        ),
    ),
    "publish_report": (
        "researcher",
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


def validate(value: Any, schema: dict[str, Any]) -> None:
    """Validate the deliberately small tool-schema subset used by this slice."""
    kind = schema["type"]
    if kind == "object":
        if not isinstance(value, dict):
            raise ValueError("expected object")
        props = schema["properties"]
        if set(value) != set(props):
            raise ValueError("unexpected or missing fields")
        for key, subschema in props.items():
            validate(value[key], subschema)
    elif kind == "array":
        if not isinstance(value, list):
            raise ValueError("expected array")
        for item in value:
            validate(item, schema["items"])
    elif kind == "string":
        if not isinstance(value, str) or len(value.strip()) < schema.get(
            "minLength", 0
        ):
            raise ValueError("expected non-empty text")
    elif kind == "boolean":
        if type(value) is not bool:
            raise ValueError("expected boolean")
    elif kind == "integer":
        if type(value) is not int:
            raise ValueError("expected integer")
    else:
        raise ValueError("unsupported schema type")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError("expected one of: " + ", ".join(schema["enum"]))


class Harness:
    def __init__(
        self,
        store: Store,
        model: Model,
        tools: dict[str, Tool] | None = None,
        context_chars: int = 48000,
        scheduler: Scheduler | None = None,
    ):
        self.store, self.model = store, model
        self.scheduler = scheduler or Scheduler()
        self.tools = tools or {}
        self.workspace = Workspace(store)
        if set(self.tools) & set(BUILTINS):
            raise ValueError("external tools may not replace runtime tools")
        if context_chars < 4000:
            raise ValueError("context capacity too small")
        self.context_chars = context_chars
        self._locks: dict[str, asyncio.Lock] = {}

    def _schema(self, role: str, policy: dict[str, Any]) -> dict[str, dict[str, Any]]:
        result = {
            name: {"description": TOOLS.get(name, name), "parameters": schema}
            for name, (allowed, schema) in BUILTINS.items()
            if allowed in (role, "all")
            or (role == "planner" and name == "discover_local")
            or (
                role == "investigator"
                and name in {"save_note", "discover_local", "snapshot_local"}
            )
        }
        for name, tool in self.tools.items():
            if role in tool.roles and (
                tool.permission is None or policy.get(tool.permission) is True
            ):
                result[name] = {
                    "description": tool.description,
                    "parameters": tool.schema,
                }
        return result

    def _request(self, study: str, work: Artifact) -> dict[str, Any]:
        direction = self.store.get(study, work.body["direction"])
        anchors = self._steps(study, "evidence_anchor", work.ref)
        catalogs = {}
        for item in self.store.list(study, "catalog"):
            catalogs[item.body["root"]] = {
                "ref": item.ref,
                "kind": "catalog",
                "root": item.body["root"],
                "entries": len(item.body["entries"]),
            }
        mandatory = {
            "provider": self.model.identity,
            "system": ROLES[work.body["role"]],
            "task": work.body["task"],
            "direction": direction.body,
            "inputs": [
                {"ref": ref, "kind": self.store.get(study, ref).kind}
                for ref in work.body["inputs"]
            ],
            "catalogs": list(catalogs.values()),
            "pinned_evidence": anchors[-1].body["refs"] if anchors else [],
            "tools": self._schema(work.body["role"], direction.body["policy"]),
            "tool_versions": {name: tool.binding for name, tool in self.tools.items()},
        }
        candidates = [
            x for x in self.store.list(study, "observation") if work.ref in x.parents
        ]
        candidates.extend(
            x for x in self.store.list(study, "note") if work.ref in x.parents
        )
        memories = self._steps(study, "memory", work.ref)
        request = assemble(
            mandatory,
            candidates,
            memories[-1] if memories else None,
            self.context_chars,
        )
        prepare = getattr(self.model, "prepare", None)
        if prepare:
            previous = None
            steps = self._steps(study, "step", work.ref)
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
                            for a in self._steps(study, "observation", work.ref)
                            if a.body.get("step") == last.ref
                        ],
                    }
                    if any("error" in o for o in previous["observations"]):
                        previous = None
            request["wire"] = prepare(request, previous)
        return request

    def _attempt(self, study: str, operation: str):
        retries = [
            a
            for a in self.store.list(study, "retry")
            if a.body["operation"] == operation
        ]
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
                async with self.scheduler.slot(
                    resource, lambda: self.store.require_work(study, work, epoch)
                ):
                    raw = self.store.admit(study, work, epoch, key, request)
                    if raw is None:
                        raw = await invoke()
                        self.store.settle(key, raw)
            else:
                raw = self.store.admit(study, work, epoch, key, request)
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
                    "not_before": time.time() + delay,
                    "resource": resource,
                },
                (work, step),
            )
            self.scheduler.defer(resource, retry.body["not_before"])
            self.store.require_work(study, work, epoch)
            key = next_key

    def _steps(self, study: str, kind: str, work: str) -> list[Artifact]:
        return [a for a in self.store.list(study, kind) if work in a.parents]

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
            steps = self._steps(study, "step", work_ref)
            done = {a.body["step"] for a in self._steps(study, "step_done", work_ref)}
            pending = [s for s in steps if s.ref not in done]
            if pending:
                step = pending[-1]
            else:
                if (
                    steps
                    and steps[0].body["request"]["provider"] != self.model.identity
                ):
                    raise NotAllowed("work is bound to its original model")
                step = self.store.put(
                    study,
                    "step",
                    {
                        "number": len(steps),
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
            if step.body["request"]["tools"] != self._schema(
                work.body["role"], direction.body["policy"]
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
                getattr(self.model, "resource", "model"),
            )
            # Always save the external result; only then check the admission fence.
            self.store.require_work(study, work_ref, control.epoch)
            try:
                decode = getattr(self.model, "decode", None)
                reply = Reply.from_json(decode(raw) if decode else raw)
                if not reply.complete:
                    raise ValueError("incomplete response; no tool was executed")
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
                self._done(study, work_ref, step.ref)
                return "continue"
            schema = step.body["request"]["tools"]
            prefetched = set()
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
                            validate(
                                candidate.arguments,
                                schema[candidate.name]["parameters"],
                            )
                            if tool.check:
                                tool.check(candidate.arguments)
                        except (ValueError, NotAllowed):
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
                    for a in self._steps(study, "observation", work_ref)
                    if a.body.get("step") == step.ref and a.body.get("index") == index
                ]
                if previous:
                    continue
                self.store.require_work(study, work_ref, control.epoch)
                try:
                    if call.name not in schema:
                        raise NotAllowed("tool not available to this work")
                    validate(call.arguments, schema[call.name]["parameters"])
                    if call.name in self.tools and self.tools[call.name].check:
                        self.tools[call.name].check(call.arguments)
                except (ValueError, NotAllowed) as exc:
                    result = {"error": str(exc)}
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
                            else:
                                result = self._builtin(
                                    study,
                                    work,
                                    control.epoch,
                                    step.ref,
                                    index,
                                    call,
                                )
                        except (ValueError, NotAllowed, Conflict) as exc:
                            result = {"error": str(exc)}
                    else:
                        envelope = await self._external(
                            study, work_ref, control.epoch, step.ref, index, call
                        )
                        observe = self.tools[call.name].observe
                        result = observe(envelope["value"]) if observe else envelope
                self.store.observation(
                    study,
                    work_ref,
                    control.epoch,
                    {
                        "step": step.ref,
                        "index": index,
                        "tool": call.name,
                        "result": result,
                    },
                    (step.ref,),
                )
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
                    },
                    (step.ref,),
                )
            self._done(study, work_ref, step.ref)
            return "finished" if self.finished(study, work_ref) else "continue"

    async def _external(self, study, work, epoch, step, index, call):
        tool = self.tools[call.name]

        async def invoke():
            return {"value": await tool.invoke(call.arguments)}

        return await self._invoke(
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
            tool.resource,
        )

    def _done(self, study: str, work: str, step: str) -> None:
        self.store.put(study, "step_done", {"step": step}, (work, step))

    def _builtin(
        self, study: str, work: Artifact, epoch: int, step: str, index: int, call: Call
    ) -> Any:
        self.store.require_work(study, work.ref, epoch)
        direction = work.body["direction"]
        args = call.arguments
        parents = (work.ref, direction, step)
        if call.name == "pin_evidence":
            refs = list(dict.fromkeys(args["refs"]))
            if len(encode(refs)) > self.context_chars // 4:
                raise ValueError("pinned evidence exceeds context allocation")
            if any(self.store.get(study, ref).kind != "source" for ref in refs):
                raise ValueError("evidence anchors must name source snapshots")
            item = self.store.put(
                study, "evidence_anchor", {"refs": refs}, (*parents, *refs)
            )
            return {"ref": item.ref}
        if call.name == "delegate_research":
            child = self.store.work(
                study,
                self.store.control(study).ref,
                "investigator",
                args["task"],
                tuple(args["refs"]),
                work.ref,
            )
            return {"work": child.ref}
        if call.name == "finish_investigation":
            item = self.store.put(study, "work_result", args, (*parents, *args["refs"]))
            return {"ref": item.ref}
        if call.name == "save_memory":
            if len(encode(args)) > self.context_chars // 4:
                raise ValueError(
                    "memory too large; preserve critical facts and references"
                )
            item = self.store.put(study, "memory", args, (*parents, *args["refs"]))
            return {"ref": item.ref}
        if call.name == "read_artifact_range":
            artifact = self.store.get(study, args["ref"])
            if artifact.kind in {"step", "step_done", "control", "material_bytes"}:
                raise NotAllowed(
                    "execution and provider-private records are not research materials"
                )
            body = encode(artifact.body)
            offset, limit = args["offset"], args["limit"]
            if offset < 0 or not 1 <= limit <= self.context_chars // 3:
                raise ValueError("invalid artifact range")
            return {
                "ref": artifact.ref,
                "kind": artifact.kind,
                "encoding": "canonical-json",
                "text": body[offset : offset + limit],
                "offset": offset,
                "end": min(len(body), offset + limit),
                "total": len(body),
            }
        if call.name == "discover_local":
            catalog = self.workspace.discover(study, args["root"])
            return {
                "ref": catalog.ref,
                "kind": "catalog",
                "count": len(catalog.body["entries"]),
            }
        if call.name == "read_catalog":
            return self.workspace.catalog_page(
                study, args["ref"], args["offset"], args["limit"]
            )
        if call.name == "find_artifacts":
            page = self.store.search(
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
                    for a in page
                ],
                "next_after": page[-1].seq if page else None,
            }
        if call.name == "read_source":
            source = self.store.get(study, args["ref"])
            if source.kind != "source":
                raise ValueError("expected source")
            text = source.body["text"]
            offset, limit = args["offset"], args["limit"]
            if offset < 0 or not 1 <= limit <= self.context_chars // 3:
                raise ValueError("invalid source range")
            return {
                "ref": source.ref,
                "kind": "source",
                "offset": offset,
                "end": min(len(text), offset + limit),
                "total": len(text),
                "text": text[offset : offset + limit],
                "coverage": source.body.get("coverage"),
                "issues": source.body.get("issues", []),
                "segments": [
                    s
                    for s in source.body.get("segments", [])
                    if s["start"] < offset + limit and s["end"] > offset
                ],
            }
        if call.name == "read_artifact":
            artifact = self.store.get(study, args["ref"])
            if artifact.kind in {"step", "step_done", "control", "material_bytes"}:
                raise NotAllowed(
                    "execution and provider-private records are not research materials"
                )
            if len(encode(artifact.body)) > self.context_chars // 2:
                return {
                    "error": "use read_artifact_range to retrieve this body",
                    "ref": artifact.ref,
                }
            return {"kind": artifact.kind, "body": artifact.body}
        if call.name == "save_note":
            item = self.store.put(study, "note", args, (*parents, *args["refs"]))
        elif call.name == "propose_plan":
            item = self.store.put(study, "plan", args, parents)
            self.store.put(
                study, "work_result", {"ref": item.ref}, (work.ref, item.ref)
            )
        elif call.name == "draft_report":
            for ref in args["evidence"]:
                if self.store.get(study, ref).kind != "source":
                    raise ValueError("evidence must reference source snapshots")
            item = self.store.put(study, "report", args, (*parents, *args["evidence"]))
        elif call.name == "submit_review":
            reports = [
                self.store.get(study, ref)
                for ref in work.body["inputs"]
                if self.store.get(study, ref).kind == "report"
            ]
            if len(reports) != 1:
                raise ValueError("review requires one bound report")
            if not args["checks"]:
                raise ValueError("review requires claim-level checks")
            for check in args["checks"]:
                if check["claim"] not in reports[0].body["text"]:
                    raise ValueError(
                        "checked claim must quote the bound report exactly"
                    )
                for ref in check["evidence"]:
                    if self.store.get(study, ref).kind != "source":
                        raise ValueError("review evidence must name source snapshots")
                if args["accepted"] and check["requires_revision"]:
                    raise ValueError("cannot accept a report requiring revision")
            item = self.store.put(
                study, "review", {**args, "work": work.ref}, (*parents, reports[0].ref)
            )
            self.store.put(
                study, "work_result", {"ref": item.ref}, (work.ref, item.ref)
            )
        elif call.name == "publish_report":
            item = self.store.publish(
                study, work.ref, epoch, args["report"], args["review"]
            )
            self.store.put(
                study, "work_result", {"ref": item.ref}, (work.ref, item.ref)
            )
        else:
            raise ValueError("unknown built-in tool")
        return {"ref": item.ref}
