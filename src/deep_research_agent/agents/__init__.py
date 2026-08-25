"""Role agents: independent prompts, bound tools, and one terminal action each.

Every invocation uses a fresh private context with exactly the tools its role may
use.  The model selects semantic actions and references already exposed to it;
the runtime owns artifact IDs, operation IDs, and other execution identity.

A malformed action returns a structured :class:`ToolError` and receives one
correction opportunity inside the same operation.  Repeating the invalid action
pauses the study without inventing another control protocol.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

from ..context import RoleContext, require_fits
from ..model import (
    CAPACITY_FAILURES,
    ChatModel,
    ModelAuthError,
    ModelProtocolError,
    ModelRateLimitError,
    ModelReply,
    ModelRequestRejected,
    ModelToolCall,
    TokenUsage,
    ToolSpec,
)
from ..operations import (
    ExecutionIdentity,
    OperationReconciliationRequired,
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
    def digest(self) -> str:
        """Exact identity of the instructions this role was invoked with.

        The ledger replays a completed call when *the same work* is requested
        again, so the instructions have to be part of what "the same" means.
        Without this, editing a role's prompt or a tool's schema replays the
        previous wording's answer on any task already part-way through -- and
        calibration does nothing but edit prompts and re-run, so the stale
        reply would arrive looking exactly like a real result.

        It covers what the provider actually receives, which is why the tool
        list is hashed in declaration order rather than sorted: a reordering
        is sent to the provider, so it counts.  Erring this way re-runs a call
        that might have been reusable, which is the safe direction.
        """

        payload = json.dumps(
            {
                "system_prompt": self.system_prompt,
                "tool_choice": self.tool_choice,
                "tools": [tool.as_api_value() for tool in self.tools],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class AgentToolBudgetExhausted(AgentProtocolError):
    """A role used its tool-turn ceiling without submitting a terminal action.

    Distinct from a protocol error because the role was behaving legitimately --
    it simply ran out of automated budget, which the caller may resolve by
    pausing for a human rather than by correcting the role.
    """


#: How many turns before the ceiling the runtime says so.  Three is enough for a
#: role to finish reading what it already fetched and still submit.
_BUDGET_NOTICE_TURNS = 3

#: One correction inside the same operation, then the run pauses for a human.
_MAX_CORRECTIONS = 1


def _budget_notice(remaining: int) -> str:
    """Tell a role its remaining budget, because it cannot see it otherwise.

    The prompts already say when to stop -- when queries stop producing anything
    new -- but a role has no view of the hard ceiling, and reaching it discards
    everything the branch found: the summary, the paths tried, the limitations
    hit, all of it, recorded only as an operational failure.  One live run lost
    seven assignments that way and roughly 170 model calls with them, on a topic
    where "the official text exists but this tooling cannot reach it" was the
    single most valuable thing the run had learned.

    Remaining turns are a resource fact the runtime owns, so reporting one is
    not a research judgment: what to do with the last turns stays the role's
    decision, and an empty-handed investigation is a legitimate thing to submit.
    """

    if remaining <= 0:
        return (
            "预算提示（运行时事实，不是研究结论）：工具回合已用尽，本回合必须提交终结"
            "动作。把已经查到的内容、尝试过的路径与遇到的限制如实交回——空手而归是合法"
            "结果，耗尽预算却什么都不交回会让这一分支的全部发现丢失。"
        )
    return (
        f"预算提示（运行时事实，不是研究结论）：还剩 {remaining} 个工具回合。"
        "如果检索已经反复返回同类结果，现在就提交终结动作，把尝试过的路径与限制写清楚；"
        "不要为了用完预算继续检索——耗尽预算而未提交终结动作，这一分支的全部发现都会丢失。"
    )


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
    context_limit: int = 0,
) -> TerminalAction:
    """Run one role until it submits a valid terminal action.

    Roles with working tools -- an Investigator searching and reading -- loop
    here: each working call is executed by its handler and the result appended,
    until the role submits a terminal action or exhausts ``max_tool_turns``.

    Each provider call goes through the operation ledger, so a crash replays a
    completed call rather than paying for it twice, and an unknown outcome
    freezes the operation instead of being retried.

    ``context_limit`` is the input ceiling this role runs under, and the capacity
    red line is checked against the **whole outgoing request** before every call
    (§8.3).  Inside the loop rather than once at entry, because a tool loop grows:
    the opening context is not the largest thing this function ever sends.
    """

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": spec.system_prompt},
        {"role": "user", "content": context.body},
    ]
    available = handlers or {}
    corrections = 0
    tool_turns = 0
    seen_errors: list[str] = []
    # The tool schemas travel with every request, so they count against the
    # ceiling.  Hashed already for the spec digest; measured here for capacity.
    instructions = json.dumps(
        [tool.as_api_value() for tool in spec.tools], ensure_ascii=False
    )

    while True:
        attempt = len(messages)
        require_fits(
            spec.role,
            instructions + "".join(str(message.get("content", "")) for message in messages),
            context_limit,
        )
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
                # The instructions are basis too: an edited prompt is different
                # work, and replaying the old answer would hide the edit.
                "spec": spec.digest,
                "turn": str(attempt),
            },
        )

        async def send() -> str:
            try:
                reply = await model.complete(
                    messages, tools=spec.tools, tool_choice=spec.tool_choice
                )
            except ModelProtocolError as error:
                # The provider was paid for a reply whose shape cannot be
                # trusted.  Recording it as the operation's real outcome is the
                # honest entry -- the call happened and was billed -- and it
                # makes recovery replay the same unusable answer deterministically
                # instead of freezing the operation for a human to adjudicate.
                return _encode_unusable(str(error))
            return _encode_reply(reply)

        payload = await run_once(
            ledger,
            request,
            send,
            not_executed=(
                ModelRequestRejected,
                ModelAuthError,
                ModelRateLimitError,
            ),
            # Decided and billed, or decided and unbillable: either way the cause
            # is a ceiling.  Never frozen, because raising the ceiling is a
            # different operation (§8.2).
            capacity=CAPACITY_FAILURES,
            usage_of=_usage_of,
        )

        unusable = _unusable_reason(payload)
        if unusable is not None:
            # §8.2's bounded structural self-correction: ask once for a
            # well-formed reply, then pause.  No assistant turn is echoed back --
            # there is no trustworthy assistant content to echo.
            if unusable in seen_errors or corrections >= _MAX_CORRECTIONS:
                raise AgentProtocolError(
                    f"{spec.role} could not return a usable reply: {unusable}"
                )
            seen_errors.append(unusable)
            corrections += 1
            messages.append({"role": "user", "content": _UNUSABLE_CORRECTION})
            continue

        reply = _decode_reply(payload)

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
                remaining = spec.max_tool_turns - tool_turns
                if 0 <= remaining <= _BUDGET_NOTICE_TURNS:
                    messages.append(
                        {"role": "user", "content": _budget_notice(remaining)}
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
        if rendered in seen_errors or corrections >= _MAX_CORRECTIONS:
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
    except OperationReconciliationRequired:
        # An unknown paid-call outcome is a trust-plane stop, not an observation
        # the role may reinterpret and work around.
        raise
    except Exception as exc:  # noqa: BLE001 - reported to the role as a result
        content = f"工具执行失败（{type(exc).__name__}）：{exc}。这是运行结果，不是证据结论。"
    return {
        "role": "tool",
        "tool_call_id": call.call_id,
        "content": content,
    }


def _encode_reply(reply: ModelReply) -> str:
    """Serialise a reply for the ledger so recovery replays it exactly."""

    payload: dict[str, Any] = {
        "content": reply.content,
        "tool_calls": [
            {"call_id": c.call_id, "name": c.name, "arguments": c.arguments}
            for c in reply.tool_calls
        ],
    }
    if reply.usage is not None:
        payload["usage"] = {
            "input_tokens": reply.usage.input_tokens,
            "output_tokens": reply.usage.output_tokens,
            "cached_input_tokens": reply.usage.cached_input_tokens,
        }
    return json.dumps(payload, ensure_ascii=False)


#: What the role is told after an untrustworthy reply.  Deliberately says nothing
#: about the malformed content: the fault is in the wire shape, and quoting a
#: broken payload back at a model invites it to reason about the payload instead
#: of simply answering again.
_UNUSABLE_CORRECTION = (
    "上一次回复的结构无法解析（运行时事实，不是对你判断的评价）。"
    "请重新提交一次格式正确的工具调用，内容不必改变。"
)


def _encode_unusable(reason: str) -> str:
    """Record a billed call whose reply could not be trusted.

    Stored as the operation's outcome rather than raised, so the ledger keeps its
    at-most-once guarantee: the call really did happen and really was charged,
    and a later replay returns this same verdict instead of paying again.
    """

    return json.dumps({"unusable": reason}, ensure_ascii=False)


def _unusable_reason(payload: str) -> str | None:
    """The recorded reason a reply was unusable, or None for a normal reply."""

    try:
        value = json.loads(payload)
    except json.JSONDecodeError:
        return "provider outcome was not valid JSON"
    if isinstance(value, Mapping) and value.get("unusable"):
        return str(value["unusable"])
    return None


def _usage_of(outcome: str) -> Mapping[str, int] | None:
    """Read spend off an encoded reply, for the ledger to record.

    Only called when a call really executed, so the ledger's summed totals are
    tokens actually paid for rather than tokens the work would have cost.
    """

    try:
        value = json.loads(outcome).get("usage")
    except (json.JSONDecodeError, AttributeError):
        return None
    if not isinstance(value, Mapping):
        return None
    return {
        key: int(value[key])
        for key in ("input_tokens", "output_tokens", "cached_input_tokens")
        if isinstance(value.get(key), int)
    } or None


def _decode_reply(payload: str) -> ModelReply:
    value = json.loads(payload)
    usage = value.get("usage")
    return ModelReply(
        usage=(
            TokenUsage(
                input_tokens=int(usage.get("input_tokens", 0)),
                output_tokens=int(usage.get("output_tokens", 0)),
                cached_input_tokens=int(usage.get("cached_input_tokens", 0)),
            )
            if isinstance(usage, Mapping)
            else None
        ),
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
