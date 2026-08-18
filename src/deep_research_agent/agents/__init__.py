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
from ..model import (
    ChatModel,
    ModelReply,
    ModelRequestRejected,
    ModelToolCall,
    ToolSpec,
)
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


class ToolHandler(Protocol):
    """Execute one non-terminal tool and return what the role should read back.

    Handlers own their own durability.  A search or fetch is a paid external
    call, so a handler routes it through the operation ledger itself rather than
    relying on the model call's ledger entry -- otherwise a crash between the
    model's request and the tool's execution would replay the model turn while
    silently re-charging the tool.
    """

    async def __call__(
        self, name: str, arguments: Mapping[str, Any]
    ) -> str: ...


@dataclass(frozen=True, slots=True)
class AgentSpec:
    """One role's complete, independently readable invocation contract."""

    role: str
    system_prompt: str
    tools: tuple[ToolSpec, ...]
    terminal_tools: frozenset[str]
    #: Reasoning-mode models reject a forced tool choice, so the default is
    #: "auto" and the runner relies on its own correction path when no terminal
    #: action arrives.  Forcing the provider was a crutch for a check the runner
    #: already performs.
    tool_choice: str = "auto"
    #: Ceiling on non-terminal tool turns.  This bounds *automation liveness*,
    #: never research sufficiency: reaching it is a recoverable pause for the
    #: caller to judge, not a signal that the investigation is complete.
    max_tool_turns: int = 24

    def __post_init__(self) -> None:
        names = {tool.name for tool in self.tools}
        unknown = sorted(self.terminal_tools - names)
        if unknown:
            raise ValueError(f"{self.role} declares unknown terminal tools {unknown}")
        if not self.terminal_tools:
            raise ValueError(f"{self.role} must declare at least one terminal tool")
        if self.max_tool_turns < 1:
            raise ValueError(f"{self.role} max_tool_turns must be positive")

    @property
    def working_tools(self) -> frozenset[str]:
        """Tools that do work and hand control back, rather than ending the turn."""

        return frozenset(tool.name for tool in self.tools) - self.terminal_tools


class AgentToolBudgetExhausted(AgentProtocolError):
    """A role used its tool-turn ceiling without submitting a terminal action.

    Distinct from a protocol error because the role was behaving legitimately --
    it simply ran out of automated budget, which the caller may resolve by
    pausing for a human rather than by correcting the role.
    """


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
    handlers: Mapping[str, ToolHandler] | None = None,
    max_corrections: int = 1,
) -> TerminalAction:
    """Run one role until it submits a valid terminal action.

    Roles with working tools -- an Investigator searching and reading -- loop
    here: each working call is executed by its handler and the result appended,
    until the role submits a terminal action or exhausts ``max_tool_turns``.

    Each provider call goes through the operation ledger, so a crash replays a
    completed call rather than paying for it twice, and an unknown outcome
    freezes the operation instead of being retried.
    """

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": spec.system_prompt},
        {"role": "user", "content": context.body},
    ]
    available = handlers or {}
    corrections = 0
    tool_turns = 0
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
                messages, tools=spec.tools, tool_choice=spec.tool_choice
            )
            return _encode_reply(reply)

        reply = _decode_reply(
            await run_once(
                ledger, request, send, not_executed=(ModelRequestRejected,)
            )
        )

        error = _reject_multiple_terminals(reply.tool_calls, spec.terminal_tools)
        call = None
        if error is None:
            call = next(
                (c for c in reply.tool_calls if c.name in spec.terminal_tools), None
            )

        # No terminal action yet: run whatever working tools the role asked for
        # and let it continue. This is the normal path for an Investigator.
        if error is None and call is None and reply.tool_calls:
            working = [c for c in reply.tool_calls if c.name in available]
            if working:
                if tool_turns >= spec.max_tool_turns:
                    raise AgentToolBudgetExhausted(
                        f"{spec.role} used its {spec.max_tool_turns} tool turns "
                        "without submitting a terminal action"
                    )
                tool_turns += 1
                messages.append(reply.assistant_message())
                for item in working:
                    messages.append(
                        await _tool_result(item, available[item.name])
                    )
                continue

        if error is None and call is None:
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
        messages.extend(_correction_turn(reply, rendered))


def _correction_turn(reply: ModelReply, rendered: str) -> list[dict[str, Any]]:
    """Deliver a correction in the shape the protocol requires.

    Both the OpenAI and Anthropic protocols require every tool call to be
    answered by a result carrying its own call id; a plain user turn after
    ``tool_calls`` is rejected outright.  A correction *is* a failed tool
    result, so it is sent as one -- which is both what the wire format demands
    and what the turn actually means.
    """

    if not reply.tool_calls:
        return [{"role": "user", "content": rendered}]
    return [
        {"role": "tool", "tool_call_id": call.call_id, "content": rendered}
        for call in reply.tool_calls
    ]


async def _tool_result(
    call: ModelToolCall, handler: ToolHandler
) -> dict[str, Any]:
    """Execute one working tool, returning its result as a tool message.

    A handler failure is returned to the role as an error result rather than
    raised: a provider that rejected one query is an operational fact the
    Investigator should adapt to, not a reason to lose the whole assignment.
    """

    try:
        arguments = call.parsed_arguments()
        content = await handler(call.name, arguments)
    except Exception as exc:  # noqa: BLE001 - reported to the role as a result
        content = f"工具执行失败（{type(exc).__name__}）：{exc}。这是运行结果，不是证据结论。"
    return {
        "role": "tool",
        "tool_call_id": call.call_id,
        "content": content,
    }


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
    "AgentToolBudgetExhausted",
    "TerminalAction",
    "TerminalValidator",
    "ToolError",
    "ToolHandler",
    "invoke_agent",
]
