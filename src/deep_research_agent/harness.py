"""One resumable Agent loop shared by planner, researcher and reviewer."""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Protocol

from .domain import Artifact, Call, Conflict, NotAllowed, Reply, identity
from .prompts import ROLES
from .storage import Store


class Model(Protocol):
    identity: str

    async def complete(self, request: dict[str, Any]) -> dict[str, Any]: ...


@dataclass(frozen=True)
class Tool:
    description: str
    schema: dict[str, Any]
    invoke: Callable[[dict[str, Any]], Awaitable[Any]]
    roles: tuple[str, ...] = ("researcher", "reviewer")
    identity: str = "v1"
    permission: str | None = None


def object_schema(properties: dict[str, Any]) -> dict[str, Any]:
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


STRING = {"type": "string", "minLength": 1}
STRINGS = {"type": "array", "items": STRING}
BUILTINS = {
    "propose_plan": ("planner", object_schema({"text": STRING})),
    "save_note": ("researcher", object_schema({"text": STRING, "refs": STRINGS})),
    "draft_report": ("researcher", object_schema({
        "text": STRING, "evidence": STRINGS,
    })),
    "submit_review": ("reviewer", object_schema({
        "accepted": {"type": "boolean"}, "reason": STRING,
    })),
    "publish_report": ("researcher", object_schema({
        "report": STRING, "review": STRING,
    })),
    "read_artifact": ("all", object_schema({"ref": STRING})),
    "find_artifacts": ("all", object_schema({
        "kind": STRING, "query": {"type": "string"},
        "after": {"type": "integer"}, "limit": {"type": "integer"},
    })),
    "read_source": ("all", object_schema({
        "ref": STRING, "offset": {"type": "integer"},
        "limit": {"type": "integer"},
    })),
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
        if not isinstance(value, str) or len(value.strip()) < schema.get("minLength", 0):
            raise ValueError("expected non-empty text")
    elif kind == "boolean":
        if type(value) is not bool:
            raise ValueError("expected boolean")
    elif kind == "integer":
        if type(value) is not int:
            raise ValueError("expected integer")
    else:
        raise ValueError("unsupported schema type")


class Harness:
    def __init__(self, store: Store, model: Model,
                 tools: dict[str, Tool] | None = None, context_chars: int = 48000):
        self.store, self.model = store, model
        self.tools = tools or {}
        if set(self.tools) & set(BUILTINS):
            raise ValueError("external tools may not replace runtime tools")
        if context_chars < 4000:
            raise ValueError("context capacity too small")
        self.context_chars = context_chars
        self._locks: dict[str, asyncio.Lock] = {}

    def _schema(self, role: str, policy: dict[str, Any]) -> dict[str, dict[str, Any]]:
        result = {name: {"description": name, "parameters": schema}
                  for name, (allowed, schema) in BUILTINS.items()
                  if allowed in (role, "all")}
        for name, tool in self.tools.items():
            if role in tool.roles and (
                    tool.permission is None or policy.get(tool.permission) is True):
                result[name] = {"description": tool.description,
                                "parameters": tool.schema}
        return result

    def _request(self, study: str, work: Artifact) -> dict[str, Any]:
        direction = self.store.get(study, work.body["direction"])
        mandatory = {
            "provider": self.model.identity,
            "system": ROLES[work.body["role"]], "task": work.body["task"],
            "direction": direction.body,
            "input_refs": work.body["inputs"],
            "tools": self._schema(work.body["role"], direction.body["policy"]),
            "tool_versions": {name: tool.identity for name, tool in self.tools.items()},
        }
        from .domain import encode
        used = len(encode(mandatory)) + 128
        if used > self.context_chars:
            raise ValueError("task and authority exceed this model context")
        # References stay retrievable; no claim that omitted history was reviewed.
        selected = []
        candidates = [
            x for x in self.store.list(study, "observation")
            if work.ref in x.parents
        ]
        for note in self.store.list(study, "note"):
            if direction.ref in note.parents:
                candidates.append(note)
        for artifact in sorted(candidates, key=lambda a: a.seq, reverse=True):
            entry = {"ref": artifact.ref, "kind": artifact.kind,
                     "body": artifact.body}
            size = len(encode(entry))
            if used + size > self.context_chars:
                continue
            selected.append(entry)
            used += size
        mandatory["context"] = selected
        mandatory["omitted_count"] = len(candidates) - len(selected)
        return mandatory

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
                if steps and steps[0].body["request"]["provider"] != self.model.identity:
                    raise NotAllowed("work is bound to its original model")
                step = self.store.put(study, "step", {
                    "number": len(steps), "request": self._request(study, work),
                }, (work_ref,))
            operation = identity("model", work_ref, step.ref)
            if step.body["request"]["provider"] != self.model.identity:
                raise NotAllowed("pending work requires its original model binding")
            if step.body["request"]["tool_versions"] != {
                    name: tool.identity for name, tool in self.tools.items()}:
                raise NotAllowed("pending work requires its original tool bindings")
            raw = self.store.admit(
                study, work_ref, control.epoch, operation, step.body["request"],
            )
            if raw is None:
                raw = await self.model.complete(step.body["request"])
                self.store.settle(operation, raw)
            # Always save the external result; only then check the admission fence.
            self.store.require_work(study, work_ref, control.epoch)
            try:
                reply = Reply.from_json(raw)
                if not reply.complete:
                    raise ValueError("incomplete response; no tool was executed")
            except (KeyError, TypeError, ValueError) as exc:
                self.store.observation(study, work_ref, control.epoch, {
                    "step": step.ref, "error": str(exc),
                }, (step.ref,))
                self._done(study, work_ref, step.ref)
                return "continue"
            schema = step.body["request"]["tools"]
            for index, call in enumerate(reply.calls):
                previous = [
                    a for a in self._steps(study, "observation", work_ref)
                    if a.body.get("step") == step.ref and a.body.get("index") == index
                ]
                if previous:
                    continue
                self.store.require_work(study, work_ref, control.epoch)
                try:
                    if call.name not in schema:
                        raise NotAllowed("tool not available to this work")
                    validate(call.arguments, schema[call.name]["parameters"])
                except (ValueError, NotAllowed) as exc:
                    result = {"error": str(exc)}
                else:
                    if call.name in BUILTINS:
                        try:
                            result = self._builtin(
                                study, work, control.epoch, step.ref, index, call,
                            )
                        except (ValueError, NotAllowed, Conflict) as exc:
                            result = {"error": str(exc)}
                    else:
                        key = identity("tool", step.ref, index)
                        req = {"tool": call.name, "arguments": call.arguments}
                        envelope = self.store.admit(
                            study, work_ref, control.epoch, key, req,
                        )
                        if envelope is None:
                            value = await self.tools[call.name].invoke(call.arguments)
                            envelope = {"value": value}
                            self.store.settle(key, envelope)
                        result = envelope
                self.store.observation(study, work_ref, control.epoch, {
                    "step": step.ref, "index": index,
                    "tool": call.name, "result": result,
                }, (step.ref,))
                if self.finished(study, work_ref):
                    break
            if not reply.calls:
                self.store.observation(study, work_ref, control.epoch, {
                    "step": step.ref, "text": reply.text,
                    "instruction": "Use a result tool; prose alone does not finish work.",
                }, (step.ref,))
            self._done(study, work_ref, step.ref)
            return "finished" if self.finished(study, work_ref) else "continue"

    def _done(self, study: str, work: str, step: str) -> None:
        self.store.put(study, "step_done", {"step": step}, (work, step))

    def _builtin(self, study: str, work: Artifact, epoch: int,
                 step: str, index: int, call: Call) -> Any:
        self.store.require_work(study, work.ref, epoch)
        direction = work.body["direction"]
        args = call.arguments
        parents = (work.ref, direction, step)
        if call.name == "find_artifacts":
            if args["kind"] not in {"source", "note", "report", "review", "plan"}:
                raise ValueError("unsupported research artifact kind")
            page = self.store.search(study, args["kind"], args["query"],
                                     args["after"], args["limit"])
            return {"items": [{"ref": a.ref, "kind": a.kind} for a in page],
                    "next_after": page[-1].seq if page else None}
        if call.name == "read_source":
            source = self.store.get(study, args["ref"])
            if source.kind != "source":
                raise ValueError("expected source")
            text = source.body["text"]
            offset, limit = args["offset"], args["limit"]
            if offset < 0 or not 1 <= limit <= self.context_chars // 3:
                raise ValueError("invalid source range")
            return {"ref": source.ref, "offset": offset,
                    "end": min(len(text), offset + limit), "total": len(text),
                    "text": text[offset:offset + limit]}
        if call.name == "read_artifact":
            artifact = self.store.get(study, args["ref"])
            from .domain import encode
            if len(encode(artifact.body)) > self.context_chars // 2:
                return {"error": "artifact needs a bounded range reader",
                        "ref": artifact.ref}
            return {"kind": artifact.kind, "body": artifact.body}
        if call.name == "save_note":
            item = self.store.put(study, "note", args, (*parents, *args["refs"]))
        elif call.name == "propose_plan":
            item = self.store.put(study, "plan", args, parents)
            self.store.put(study, "work_result", {"ref": item.ref}, (work.ref, item.ref))
        elif call.name == "draft_report":
            for ref in args["evidence"]:
                if self.store.get(study, ref).kind != "source":
                    raise ValueError("evidence must reference source snapshots")
            item = self.store.put(study, "report", args, (*parents, *args["evidence"]))
        elif call.name == "submit_review":
            reports = [self.store.get(study, ref) for ref in work.body["inputs"]
                       if self.store.get(study, ref).kind == "report"]
            if len(reports) != 1:
                raise ValueError("review requires one bound report")
            item = self.store.put(study, "review", {**args, "work": work.ref},
                                  (*parents, reports[0].ref))
            self.store.put(study, "work_result", {"ref": item.ref}, (work.ref, item.ref))
        elif call.name == "publish_report":
            item = self.store.publish(study, work.ref, epoch,
                                      args["report"], args["review"])
            self.store.put(study, "work_result", {"ref": item.ref}, (work.ref, item.ref))
        else:
            raise ValueError("unknown built-in tool")
        return {"ref": item.ref}
