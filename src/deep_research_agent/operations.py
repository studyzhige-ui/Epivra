"""Durable ledger making every external call at-most-once across restarts.

One boundary serves every model and tool call, so no role needs its own replay
machinery.  The ordering rule that makes this safe is uncomfortable but
unavoidable: an external provider cannot join a local SQLite transaction, so
the ledger commits *"a request is about to go out"* **before** the request goes
out.  A crash in that window therefore leaves an operation whose outcome is
genuinely unknown, and the ledger refuses to guess -- it moves to
``needs_reconciliation`` and stops.  Paying twice is worse than pausing.

State machine::

    reserved ──mark_sent──▶ in_flight ──complete──────────▶ completed (replay only)
        │                       │
        │                       ├──fail(not_executed)─────▶ failed (retryable)
        │                       ├──fail(capacity|…)───────▶ failed (terminal)
        │                       └──flag_reconciliation────▶ needs_reconciliation
        └──fail(…)──────────────────────────────────────▶ failed

Which transition applies is decided by what the caller can *prove*.  ``fail``
records a failure the provider confirmed; an outcome nobody can confirm is not a
failure category at all, it is ``flag_reconciliation``.

``completed`` is terminal and idempotent: recovery replays the stored outcome
and never calls out again.  ``needs_reconciliation`` is terminal for automation:
ordinary resume, continue, and retry must all refuse it.

This module is trust-plane infrastructure.  It stores no secrets, no provider
payloads, and no research semantics -- only identities, fingerprints, and
content-addressed outcome references.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Awaitable, Callable, Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal, Protocol

import aiosqlite

from .content_store import ContentStore
from .sources import ArtifactValidationError, BodyRef

OperationStatus = Literal[
    "reserved",
    "in_flight",
    "completed",
    "failed",
    "needs_reconciliation",
    "cancelled",
]

#: Why an attempt ended.  Every category here describes a failure the caller can
#: *prove*; an outcome the caller cannot prove is not a failure category at all,
#: it is ``flag_reconciliation``.  Only ``not_executed`` permits a bounded retry
#: on the same operation key, because it is the only one where the provider has
#: told us nothing ran.
FailureCategory = Literal[
    "not_executed",
    "capacity",
    "integrity",
    "terminal",
    "cancelled",
]

_TERMINAL_STATUSES: frozenset[str] = frozenset(
    {"completed", "needs_reconciliation", "cancelled"}
)
_RETRYABLE_CATEGORIES: frozenset[str] = frozenset({"not_executed"})
_STATUSES: frozenset[str] = frozenset(
    {
        "reserved",
        "in_flight",
        "completed",
        "failed",
        "needs_reconciliation",
        "cancelled",
    }
)
_CATEGORIES: frozenset[str] = frozenset(
    {"not_executed", "capacity", "integrity", "terminal", "cancelled"}
)

_ID_HASH_LENGTH = 24
_OPERATION_ID_RE = re.compile(rf"^op_[0-9a-f]{{{_ID_HASH_LENGTH}}}$")

#: Field names that must never reach the ledger.  Execution identity records
#: *which* provider and model ran, never how to authenticate to it.
_SECRET_HINTS: tuple[str, ...] = (
    "key",
    "token",
    "secret",
    "password",
    "credential",
    "authorization",
    "auth",
    "cookie",
    "session",
    "signature",
    "sig",
    "bearer",
)


class OperationError(RuntimeError):
    """The ledger refuses an operation transition."""


class OperationReconciliationRequired(OperationError):
    """An external call may have executed; a human or a provider query decides.

    Raised instead of retrying.  Clearing this state requires querying the
    provider for the real outcome, submitting a recovered outcome, or explicitly
    authorising a new operation with the double-charge risk acknowledged.
    """

    def __init__(self, operation_id: str, detail: str = "") -> None:
        self.operation_id = operation_id
        self.detail = detail
        suffix = f": {detail}" if detail else ""
        super().__init__(
            f"operation {operation_id} has an unknown provider outcome and needs "
            f"reconciliation{suffix}"
        )


class OperationBudgetExhausted(OperationError):
    """A bounded retry budget is spent; pause rather than keep paying."""


def _canonical(payload: object) -> str:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def _digest(payload: object) -> str:
    return hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()


def _utc_now() -> str:
    """Wall-clock stamp for spend and latency accounting, never for identity."""

    return datetime.now(UTC).isoformat(timespec="milliseconds")


def _require_text(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ArtifactValidationError(f"{label} must be a non-empty string")
    return value.strip()


def _reject_secretlike(mapping: Mapping[str, str], label: str) -> None:
    for key in mapping:
        lowered = key.casefold()
        if any(hint in lowered for hint in _SECRET_HINTS):
            raise ArtifactValidationError(
                f"{label} field {key!r} looks like a credential and must not be "
                "recorded in the operation ledger"
            )


def require_operation_id(value: str, label: str = "operation_id") -> str:
    """Reject anything that is not a well-formed runtime-issued operation ID."""

    if not isinstance(value, str) or not _OPERATION_ID_RE.match(value):
        raise ArtifactValidationError(f"{label} is not a valid operation ID: {value!r}")
    return value


@dataclass(frozen=True, slots=True)
class ExecutionIdentity:
    """Which provider and configuration ran, with no way to authenticate to it."""

    provider: str
    endpoint: str = ""
    model_id: str = ""
    limits: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_text(self.provider, "execution provider")
        for name in ("endpoint", "model_id"):
            if not isinstance(getattr(self, name), str):
                raise ArtifactValidationError(f"execution {name} must be a string")
        if not isinstance(self.limits, Mapping) or any(
            not isinstance(key, str) or not isinstance(value, str)
            for key, value in self.limits.items()
        ):
            raise ArtifactValidationError("execution limits must map strings to strings")
        _reject_secretlike(self.limits, "execution limits")

    def identity(self) -> Mapping[str, object]:
        """The identity contribution of this execution configuration."""

        return {
            "provider": self.provider,
            "endpoint": self.endpoint,
            "model_id": self.model_id,
            "limits": dict(sorted(self.limits.items())),
        }


@dataclass(frozen=True, slots=True)
class OperationRequest:
    """Everything that determines whether two calls are the same work.

    ``input_refs`` are artifact IDs, and ``parameters`` holds the small
    non-secret knobs that change the request.  Together with the execution
    identity and the task, they form the fingerprint: identical work replays
    rather than paying twice.
    """

    task_id: str
    kind: str
    role: str
    execution: ExecutionIdentity
    input_refs: tuple[str, ...] = ()
    parameters: Mapping[str, str] = field(default_factory=dict)
    parent_refs: tuple[str, ...] = ()
    idempotency_key: str = ""
    max_attempts: int = 3

    def __post_init__(self) -> None:
        _require_text(self.task_id, "task_id")
        _require_text(self.kind, "operation kind")
        _require_text(self.role, "operation role")
        if not isinstance(self.execution, ExecutionIdentity):
            raise ArtifactValidationError("execution must be an ExecutionIdentity")
        for ref in self.input_refs:
            _require_text(ref, "input ref")
        for ref in self.parent_refs:
            require_operation_id(ref, "parent operation ref")
        if not isinstance(self.parameters, Mapping) or any(
            not isinstance(key, str) or not isinstance(value, str)
            for key, value in self.parameters.items()
        ):
            raise ArtifactValidationError("parameters must map strings to strings")
        _reject_secretlike(self.parameters, "operation parameters")
        if not isinstance(self.idempotency_key, str):
            raise ArtifactValidationError("idempotency_key must be a string")
        if (
            isinstance(self.max_attempts, bool)
            or not isinstance(self.max_attempts, int)
            or self.max_attempts < 1
        ):
            raise ArtifactValidationError("max_attempts must be a positive integer")

    def fingerprint(self) -> str:
        """Deterministic identity of this exact work, scoped to one task."""

        return _digest(
            {
                "task": self.task_id,
                "kind": self.kind,
                "role": self.role,
                "execution": self.execution.identity(),
                "inputs": sorted(set(self.input_refs)),
                "parameters": dict(sorted(self.parameters.items())),
            }
        )

    def operation_id(self) -> str:
        """The runtime-owned operation ID derived from the fingerprint."""

        return f"op_{self.fingerprint()[:_ID_HASH_LENGTH]}"


@dataclass(frozen=True, slots=True)
class OperationRecord:
    """The durable state of one external call."""

    operation_id: str
    fingerprint: str
    task_id: str
    kind: str
    role: str
    execution: ExecutionIdentity
    input_refs: tuple[str, ...]
    parent_refs: tuple[str, ...]
    status: OperationStatus
    attempts: int
    max_attempts: int
    idempotency_key: str = ""
    outcome_ref: BodyRef | None = None
    failure: str = ""
    detail: str = ""

    def __post_init__(self) -> None:
        require_operation_id(self.operation_id)
        if self.status not in _STATUSES:
            raise ArtifactValidationError(f"unsupported status {self.status!r}")
        if self.failure and self.failure not in _CATEGORIES:
            raise ArtifactValidationError(f"unsupported failure {self.failure!r}")
        if self.status == "completed" and self.outcome_ref is None:
            raise ArtifactValidationError(
                "a completed operation must reference its stored outcome"
            )
        if self.status != "completed" and self.outcome_ref is not None:
            raise ArtifactValidationError(
                "only a completed operation may reference an outcome"
            )

    @property
    def is_terminal(self) -> bool:
        """Whether automation may no longer transition this operation."""

        return self.status in _TERMINAL_STATUSES

    @property
    def may_retry(self) -> bool:
        """Whether a bounded retry on this same operation key is provably safe."""

        return (
            self.status == "failed"
            and self.failure in _RETRYABLE_CATEGORIES
            and self.attempts < self.max_attempts
        )


class OperationLedger(Protocol):
    """Durable at-most-once boundary for external calls."""

    async def get(self, operation_id: str) -> OperationRecord | None:
        """Return the durable record, or None if the operation is unknown."""

    async def reserve(self, request: OperationRequest) -> OperationRecord:
        """Persist the intent to call before any request leaves the process."""

    async def mark_sent(self, operation_id: str) -> OperationRecord:
        """Record that a request is going out and its outcome is not yet known."""

    async def complete(
        self,
        operation_id: str,
        outcome: str,
        *,
        usage: Mapping[str, int] | None = None,
    ) -> OperationRecord:
        """Store the outcome in the content store, then mark the call done."""

    async def fail(
        self,
        operation_id: str,
        *,
        category: FailureCategory,
        detail: str = "",
    ) -> OperationRecord:
        """Record a *known* failure; unknown outcomes use flag_reconciliation."""

    async def flag_reconciliation(
        self, operation_id: str, detail: str = ""
    ) -> OperationRecord:
        """Freeze an operation whose provider outcome cannot be determined."""

    async def pending_reconciliation(
        self, task_id: str
    ) -> tuple[OperationRecord, ...]:
        """Every operation in one task that blocks ordinary resume."""


class SqliteOperationLedger:
    """OperationLedger sharing the runtime's aiosqlite connection.

    Outcomes live in the content store, so the ledger row stays small and the
    same body is never duplicated across replays.
    """

    def __init__(
        self, connection: aiosqlite.Connection, content_store: ContentStore
    ) -> None:
        self._connection = connection
        self._content_store = content_store

    async def setup(self) -> None:
        """Create only the ledger table."""

        await self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS operations (
                operation_id TEXT PRIMARY KEY,
                fingerprint TEXT NOT NULL,
                task_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                role TEXT NOT NULL,
                execution TEXT NOT NULL,
                input_refs TEXT NOT NULL,
                parent_refs TEXT NOT NULL,
                status TEXT NOT NULL,
                attempts INTEGER NOT NULL CHECK (attempts >= 0),
                max_attempts INTEGER NOT NULL CHECK (max_attempts >= 1),
                idempotency_key TEXT NOT NULL DEFAULT '',
                outcome_hash TEXT,
                outcome_chars INTEGER,
                failure TEXT NOT NULL DEFAULT '',
                detail TEXT NOT NULL DEFAULT '',
                started_at TEXT NOT NULL DEFAULT '',
                settled_at TEXT NOT NULL DEFAULT '',
                input_tokens INTEGER,
                output_tokens INTEGER,
                cached_input_tokens INTEGER
            )
            """
        )
        # Databases written before spend accounting existed are still readable
        # and resumable; the new columns simply stay NULL for their rows, which
        # is the honest record -- those calls really were unmeasured.
        existing = {
            row[1]
            for row in await self._connection.execute_fetchall(
                "PRAGMA table_info(operations)"
            )
        }
        for column, definition in (
            ("started_at", "TEXT NOT NULL DEFAULT ''"),
            ("settled_at", "TEXT NOT NULL DEFAULT ''"),
            ("input_tokens", "INTEGER"),
            ("output_tokens", "INTEGER"),
            ("cached_input_tokens", "INTEGER"),
        ):
            if column not in existing:
                await self._connection.execute(
                    f"ALTER TABLE operations ADD COLUMN {column} {definition}"
                )
        await self._connection.execute(
            "CREATE INDEX IF NOT EXISTS operations_task_status "
            "ON operations(task_id, status)"
        )
        await self._connection.commit()

    async def get(self, operation_id: str) -> OperationRecord | None:
        require_operation_id(operation_id)
        cursor = await self._connection.execute(
            "SELECT operation_id, fingerprint, task_id, kind, role, execution, "
            "input_refs, parent_refs, status, attempts, max_attempts, "
            "idempotency_key, outcome_hash, outcome_chars, failure, detail "
            "FROM operations WHERE operation_id = ?",
            (operation_id,),
        )
        row = await cursor.fetchone()
        await cursor.close()
        return None if row is None else _record_from_row(row)

    async def reserve(self, request: OperationRequest) -> OperationRecord:
        operation_id = request.operation_id()
        existing = await self.get(operation_id)
        if existing is not None:
            return existing
        execution = _canonical(request.execution.identity())
        await self._connection.execute(
            """
            INSERT INTO operations(
                operation_id, fingerprint, task_id, kind, role, execution,
                input_refs, parent_refs, status, attempts, max_attempts,
                idempotency_key, failure, detail
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'reserved', 0, ?, ?, '', '')
            ON CONFLICT(operation_id) DO NOTHING
            """,
            (
                operation_id,
                request.fingerprint(),
                request.task_id,
                request.kind,
                request.role,
                execution,
                _canonical(sorted(set(request.input_refs))),
                _canonical(sorted(set(request.parent_refs))),
                request.max_attempts,
                request.idempotency_key,
            ),
        )
        await self._connection.commit()
        stored = await self.get(operation_id)
        if stored is None:  # pragma: no cover - insert just committed
            raise OperationError(f"operation {operation_id} could not be reserved")
        return stored

    async def mark_sent(self, operation_id: str) -> OperationRecord:
        record = await self._require(operation_id)
        if record.status == "in_flight":
            return record
        if record.status not in ("reserved", "failed"):
            raise OperationError(
                f"operation {operation_id} cannot be sent from status "
                f"{record.status!r}"
            )
        if record.status == "failed" and not record.may_retry:
            raise OperationBudgetExhausted(
                f"operation {operation_id} exhausted its retry budget "
                f"({record.attempts}/{record.max_attempts})"
            )
        await self._update(
            operation_id,
            status="in_flight",
            attempts=record.attempts + 1,
            started_at=_utc_now(),
            failure="",
            detail="",
        )
        return await self._require(operation_id)

    async def complete(
        self,
        operation_id: str,
        outcome: str,
        *,
        usage: Mapping[str, int] | None = None,
    ) -> OperationRecord:
        record = await self._require(operation_id)
        if record.status == "completed":
            return record
        if record.status != "in_flight":
            raise OperationError(
                f"operation {operation_id} cannot complete from status "
                f"{record.status!r}"
            )
        # The outcome is durable and verified before the ledger claims success,
        # so a crash between these two writes leaves a replayable body and a
        # still-in_flight row rather than a completed row pointing at nothing.
        ref = await self._content_store.put(outcome)
        counts = dict(usage or {})
        await self._update(
            operation_id,
            status="completed",
            outcome_hash=ref.content_hash,
            outcome_chars=ref.char_count,
            settled_at=_utc_now(),
            # Only written on real execution.  A replayed call returns above
            # without touching these, so summing them gives tokens actually
            # paid for rather than tokens the work would have cost.
            input_tokens=counts.get("input_tokens"),
            output_tokens=counts.get("output_tokens"),
            cached_input_tokens=counts.get("cached_input_tokens"),
            failure="",
            detail="",
        )
        return await self._require(operation_id)

    async def fail(
        self,
        operation_id: str,
        *,
        category: FailureCategory,
        detail: str = "",
    ) -> OperationRecord:
        record = await self._require(operation_id)
        if record.status == "completed":
            raise OperationError(
                f"operation {operation_id} already completed and cannot fail"
            )
        if category not in _CATEGORIES:
            raise ArtifactValidationError(f"unsupported failure {category!r}")
        status: OperationStatus = "cancelled" if category == "cancelled" else "failed"
        await self._update(
            operation_id,
            status=status,
            failure=category,
            detail=detail,
            settled_at=_utc_now(),
        )
        return await self._require(operation_id)

    async def flag_reconciliation(
        self, operation_id: str, detail: str = ""
    ) -> OperationRecord:
        record = await self._require(operation_id)
        if record.status == "needs_reconciliation":
            return record
        if record.status == "completed":
            raise OperationError(
                f"operation {operation_id} already completed; nothing to reconcile"
            )
        await self._update(
            operation_id,
            status="needs_reconciliation",
            failure="terminal",
            detail=detail,
            settled_at=_utc_now(),
        )
        return await self._require(operation_id)

    async def pending_reconciliation(
        self, task_id: str
    ) -> tuple[OperationRecord, ...]:
        cursor = await self._connection.execute(
            "SELECT operation_id FROM operations "
            "WHERE task_id = ? AND status = 'needs_reconciliation' "
            "ORDER BY operation_id",
            (task_id,),
        )
        rows = await cursor.fetchall()
        await cursor.close()
        records = [await self._require(row[0]) for row in rows]
        return tuple(records)

    async def models_used(self, task_id: str) -> Mapping[str, tuple[str, ...]]:
        """Which model each role has actually called on this task, from the record.

        The ledger is the only place that knows what a task *did* run, as opposed
        to what it was configured to run.  That makes it the way to detect the
        one case a frozen configuration cannot cover: a task created before
        snapshots existed, whose models would otherwise change without anyone
        being told.  It is corroboration, not configuration -- it cannot say
        which search providers were enabled, and says nothing about roles that
        never ran.
        """

        rows = await self._connection.execute_fetchall(
            "SELECT DISTINCT role, execution FROM operations WHERE task_id = ?",
            (task_id,),
        )
        used: dict[str, list[str]] = {}
        for role, execution in rows:
            try:
                model_id = str(json.loads(str(execution)).get("model_id", ""))
            except (json.JSONDecodeError, TypeError, AttributeError):
                continue
            seen = used.setdefault(str(role), [])
            if model_id and model_id not in seen:
                seen.append(model_id)
        return {role: tuple(sorted(models)) for role, models in used.items()}

    async def outcome(self, operation_id: str) -> str:
        """Replay the stored outcome of a completed operation."""

        record = await self._require(operation_id)
        if record.status != "completed" or record.outcome_ref is None:
            raise OperationError(
                f"operation {operation_id} has no completed outcome to replay"
            )
        return await self._content_store.get(record.outcome_ref)

    async def _require(self, operation_id: str) -> OperationRecord:
        record = await self.get(operation_id)
        if record is None:
            raise OperationError(f"operation {operation_id} is unknown")
        return record

    async def _update(self, operation_id: str, **columns: object) -> None:
        assignments = ", ".join(f"{name} = ?" for name in columns)
        await self._connection.execute(
            f"UPDATE operations SET {assignments} WHERE operation_id = ?",
            (*columns.values(), operation_id),
        )
        await self._connection.commit()


def _record_from_row(row: Iterable[object]) -> OperationRecord:
    (
        operation_id,
        fingerprint,
        task_id,
        kind,
        role,
        execution,
        input_refs,
        parent_refs,
        status,
        attempts,
        max_attempts,
        idempotency_key,
        outcome_hash,
        outcome_chars,
        failure,
        detail,
    ) = row
    identity = json.loads(str(execution))
    return OperationRecord(
        operation_id=str(operation_id),
        fingerprint=str(fingerprint),
        task_id=str(task_id),
        kind=str(kind),
        role=str(role),
        execution=ExecutionIdentity(
            provider=str(identity["provider"]),
            endpoint=str(identity.get("endpoint", "")),
            model_id=str(identity.get("model_id", "")),
            limits={
                str(key): str(value)
                for key, value in dict(identity.get("limits", {})).items()
            },
        ),
        input_refs=tuple(json.loads(str(input_refs))),
        parent_refs=tuple(json.loads(str(parent_refs))),
        status=str(status),  # type: ignore[arg-type]
        attempts=int(attempts),
        max_attempts=int(max_attempts),
        idempotency_key=str(idempotency_key or ""),
        outcome_ref=(
            BodyRef(content_hash=str(outcome_hash), char_count=int(outcome_chars))
            if outcome_hash is not None
            else None
        ),
        failure=str(failure or ""),
        detail=str(detail or ""),
    )


async def run_once(
    ledger: SqliteOperationLedger,
    request: OperationRequest,
    send: Callable[[], Awaitable[str]],
    *,
    not_executed: tuple[type[BaseException], ...] = (),
    usage_of: Callable[[str], Mapping[str, int] | None] | None = None,
) -> str:
    """Perform one external call at most once, across crashes and restarts.

    Callers should reach for this rather than driving the ledger by hand: it is
    the only place that gets the commit-before-send ordering right, and it turns
    every unknown outcome into a pause instead of a second charge.

    ``send`` must raise on failure.  Any exception raised out of ``send`` is
    treated as *possibly executed* -- the honest default for a network call --
    and freezes the operation for reconciliation.  ``not_executed`` names the
    exception types the caller can prove never reached execution (a provider
    rejecting a malformed request, say); those record a retryable failure
    instead, because freezing an operation nobody was billed for turns a typo
    into a dead task.
    """

    record = await ledger.reserve(request)

    if record.status == "completed":
        return await ledger.outcome(record.operation_id)
    if record.status == "needs_reconciliation":
        raise OperationReconciliationRequired(record.operation_id, record.detail)
    if record.status == "cancelled":
        raise OperationError(f"operation {record.operation_id} was cancelled")
    if record.status == "in_flight":
        # A previous process committed "sending" and never recorded an outcome.
        # Whether the provider ran is unknowable from here.
        await ledger.flag_reconciliation(
            record.operation_id,
            "process restarted while the provider outcome was unknown",
        )
        raise OperationReconciliationRequired(
            record.operation_id,
            "process restarted while the provider outcome was unknown",
        )
    if record.status == "failed" and not record.may_retry:
        raise OperationBudgetExhausted(
            f"operation {record.operation_id} exhausted its retry budget "
            f"({record.attempts}/{record.max_attempts})"
        )

    await ledger.mark_sent(record.operation_id)
    try:
        outcome = await send()
    except not_executed as error:
        await ledger.fail(
            record.operation_id,
            category="not_executed",
            detail=f"{type(error).__name__}: {error}"[:300],
        )
        raise
    except BaseException as error:
        await ledger.flag_reconciliation(
            record.operation_id, f"{type(error).__name__} during provider call"
        )
        raise
    # Spend is read off the outcome the caller just produced, so the ledger
    # stays generic: it records token counts without knowing what a model is.
    completed = await ledger.complete(
        record.operation_id,
        outcome,
        usage=usage_of(outcome) if usage_of is not None else None,
    )
    return await ledger.outcome(completed.operation_id)


__all__ = [
    "ExecutionIdentity",
    "FailureCategory",
    "OperationBudgetExhausted",
    "OperationError",
    "OperationLedger",
    "OperationReconciliationRequired",
    "OperationRecord",
    "OperationRequest",
    "OperationStatus",
    "SqliteOperationLedger",
    "require_operation_id",
    "run_once",
]
