"""Role agents: independent prompts, bound tools, and one terminal action each.

Every agent invocation is a fresh private context with exactly the tools its
role may use.  The runner enforces the rule that the previous implementation
violated fifteen times in one task: **the model never authors runtime identity**.
It selects among references the context exposed; the runtime assigns every
artifact ID, operation ID, and finding ID afterwards.

A malformed action returns a structured :class:`ToolError` and the role gets one
correction inside the same operation.  Repeating the same invalid action is a
recoverable pause, not a protocol version bump -- the escalation path that
turned a research failure into ``supervisor-branch-mode-violations.v9``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

from ..context import RoleContext
from ..model import ChatModel, ModelReply, ModelToolCall, ToolSpec
from ..operations import (
    ExecutionIdentity,
    OperationRequest,
    SqliteOperationLedger,
    run_once,
)


class AgentProtocolError(RuntimeError):
    """A role could not produce a valid terminal action within its budget."""


@dataclass(frozen=True, slots=True)
class ToolError:
    """A short, actionable correction returned to the same role."""

    action: str
    problem: str
    allowed: str = ""

    def render(self) -> str:
        parts = [f"动作 {self.action!r} 无效：{self.problem}"]
        if self.allowed:
            parts.append(f"当前允许：{self.allowed}")
        return " ".join(parts)


@dataclass(frozen=True, slots=True)
class TerminalAction:
    """One accepted semantic action, with the arguments the role supplied."""

    name: str
    arguments: Mapping[str, Any]
    raw_reply: ModelReply = field(default_factory=ModelReply, repr=False)


class TerminalValidator(Protocol):
    """Validate one terminal action's arguments, or explain what is wrong."""

    def __call__(
        self, name: str, arguments: Mapping[str, Any]
    ) -> ToolError | None: ...


@dataclass(frozen=True, slots=True)
class AgentSpec:
    """One role's complete, independently readable invocation contract."""

    role: str
    system_prompt: str
    tools: tuple[ToolSpec, ...]
    terminal_tools: frozenset[str]

    def __post_init__(self) -> None:
        names = {tool.name for tool in self.tools}
        unknown = sorted(self.terminal_tools - names)
        if unknown:
            raise ValueError(f"{self.role} declares unknown terminal tools {unknown}")
        if not self.terminal_tools:
            raise ValueError(f"{self.role} must declare at least one terminal tool")


def _reject_multiple_terminals(
    calls: Sequence[ModelToolCall], terminal: frozenset[str]
) -> ToolError | None:
    """Two terminal actions in one turn are refused, never arbitrated.

    Picking one would let the runtime guess intent, which is how a deterministic
    boundary quietly becomes a semantic one.
    """

    submitted = [call.name for call in calls if call.name in terminal]
    if len(submitted) > 1:
        return ToolError(
            action=", ".join(sorted(submitted)),
            problem="一个回合只能提交一个终结动作，全部拒绝",
            allowed="重新只提交其中一个",
        )
    return None


async def invoke_agent(
    spec: AgentSpec,
    context: RoleContext,
    *,
    model: ChatModel,
    ledger: SqliteOperationLedger,
    task_id: str,
    execution: ExecutionIdentity,
    validate: TerminalValidator | None = None,
    max_corrections: int = 1,
) -> TerminalAction:
    """Run one role until it submits a valid terminal action.

    Each provider call goes through the operation ledger, so a crash replays a
    completed call rather than paying for it twice, and an unknown outcome
    freezes the operation instead of being retried.
    """

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": spec.system_prompt},
        {"role": "user", "content": context.body},
    ]
    corrections = 0
    seen_errors: list[str] = []

    while True:
        attempt = len(messages)
        request = OperationRequest(
            task_id=task_id,
            kind="model_call",
            role=spec.role,
            execution=execution,
            input_refs=context.input_refs,
            parameters={
                "purpose": context.purpose,
                # The basis, not just the role, decides whether two calls are the
                # same work. Without it a closure review would replay the
                # baseline verdict on a report body it never read.
                "context": context.digest,
                "turn": str(attempt),
            },
        )

        async def send() -> str:
            reply = await model.complete(
                messages, tools=spec.tools, tool_choice="required"
            )
            return _encode_reply(reply)

        reply = _decode_reply(await run_once(ledger, request, send))

        error = _reject_multiple_terminals(reply.tool_calls, spec.terminal_tools)
        call = None
        if error is None:
            call = next(
                (c for c in reply.tool_calls if c.name in spec.terminal_tools), None
            )
            if call is None:
                error = ToolError(
                    action=reply.tool_calls[0].name if reply.tool_calls else "(none)",
                    problem="本次调用必须提交一个终结动作",
                    allowed="、".join(sorted(spec.terminal_tools)),
                )

        arguments: Mapping[str, Any] = {}
        if error is None and call is not None:
            try:
                arguments = call.parsed_arguments()
            except Exception as exc:  # noqa: BLE001 - surfaced to the role verbatim
                error = ToolError(action=call.name, problem=str(exc))
            else:
                if validate is not None:
                    error = validate(call.name, arguments)

        if error is None and call is not None:
            return TerminalAction(
                name=call.name, arguments=arguments, raw_reply=reply
            )

        assert error is not None
        rendered = error.render()
        # Repeating the same invalid action is a pause, not another retry: the
        # role has demonstrated it cannot correct with the context it has.
        if rendered in seen_errors or corrections >= max_corrections:
            raise AgentProtocolError(
                f"{spec.role} could not submit a valid terminal action: {rendered}"
            )
        seen_errors.append(rendered)
        corrections += 1
        messages.append(reply.assistant_message())
        messages.append({"role": "user", "content": rendered})


def _encode_reply(reply: ModelReply) -> str:
    """Serialise a reply for the ledger so recovery replays it exactly."""

    import json

    return json.dumps(
        {
            "content": reply.content,
            "tool_calls": [
                {"call_id": c.call_id, "name": c.name, "arguments": c.arguments}
                for c in reply.tool_calls
            ],
        },
        ensure_ascii=False,
    )


def _decode_reply(payload: str) -> ModelReply:
    import json

    value = json.loads(payload)
    return ModelReply(
        content=str(value.get("content", "")),
        tool_calls=tuple(
            ModelToolCall(
                call_id=str(item["call_id"]),
                name=str(item["name"]),
                arguments=str(item["arguments"]),
            )
            for item in value.get("tool_calls", ())
        ),
    )


__all__ = [
    "AgentProtocolError",
    "AgentSpec",
    "TerminalAction",
    "TerminalValidator",
    "ToolError",
    "invoke_agent",
]
