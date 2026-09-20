"""Provider-neutral values and identities; no I/O."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any


class Conflict(ValueError):
    """A command or result was based on a different control version."""


class ContextCapacity(ValueError):
    """The essential task cannot fit the configured model input allowance."""


class NotAllowed(ValueError):
    """The requested action is outside the current authority."""


class RuntimeMismatch(NotAllowed):
    """An archived research protocol cannot resume under different semantics."""


class UnknownOutcome(RuntimeError):
    """A request may have run; automatic resubmission would risk duplication."""


class RepeatedFailure(RuntimeError):
    """Repeated identical failures without progress; preserve work for correction."""


class RecoveryExhausted(RuntimeError):
    """Explicit provider rejections exhausted recovery for this control epoch."""


class OwnershipError(RuntimeError):
    """Another host owns this database."""


# Existing public tool-result envelope limit, not a document/LLM budget.
INLINE_TOOL_RESULT_CHARS = 12000


def encode(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def identity(*values: Any) -> str:
    return hashlib.sha256(encode(values).encode()).hexdigest()


def bounded_json(value, *, max_bytes=16 * 1024 * 1024, max_depth=64):
    """Bound external structures before recursive encoders/schema validators."""
    pending = [(value, 0)]
    nodes = 0
    while pending:
        item, depth = pending.pop()
        nodes += 1
        if depth > max_depth or nodes > 1_000_000:
            raise ValueError("JSON nesting or element capacity exceeded")
        if isinstance(item, dict):
            pending.extend((v, depth + 1) for v in item.values())
        elif isinstance(item, list):
            pending.extend((v, depth + 1) for v in item)
    if len(encode(value).encode("utf-8")) > max_bytes:
        raise ValueError("JSON byte capacity exceeded")


@dataclass(frozen=True)
class Artifact:
    ref: str
    study: str
    kind: str
    body: Any
    parents: tuple[str, ...]
    seq: int


@dataclass(frozen=True)
class Control:
    ref: str
    epoch: int
    direction: str
    approved: bool
    paused: bool
    cancelled: bool
    plan: str | None = None

    @property
    def runnable(self) -> bool:
        return self.approved and not self.paused and not self.cancelled


@dataclass(frozen=True)
class Call:
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class Reply:
    text: str
    calls: tuple[Call, ...]
    complete: bool = True

    def to_json(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "calls": [{"name": c.name, "arguments": c.arguments} for c in self.calls],
            "complete": self.complete,
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Reply:
        if not isinstance(data, dict):
            raise ValueError("model reply must be an object")
        if not isinstance(data.get("text"), str):
            raise ValueError("model text must be a string")
        if type(data.get("complete")) is not bool:
            raise ValueError("model completion marker missing")
        calls = data.get("calls")
        if not isinstance(calls, list):
            raise ValueError("model calls must be a list")
        if len(calls) > 1024:
            raise ValueError("single response exceeds tool-call capacity")
        parsed = []
        for item in calls:
            if (
                not isinstance(item, dict)
                or not isinstance(item.get("name"), str)
                or not isinstance(item.get("arguments"), dict)
            ):
                raise ValueError("malformed model tool call")
            parsed.append(Call(item["name"], item["arguments"]))
        return cls(data["text"], tuple(parsed), data["complete"])
