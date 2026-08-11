"""Stable Python API for starting and resuming durable research threads."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from langgraph.errors import GraphRecursionError
from langgraph.types import Command

from .checkpoint import (
    memory_checkpointer,
    readonly_sqlite_checkpointer,
    sqlite_checkpointer,
    sqlite_writer_lock,
)
from .citations import CitationRenderer
from .roles import RoleExecutors
from .workflow import GuideContextProvider, build_research_graph, empty_guide_context


RunStatus = Literal[
    "awaiting_approval",
    "awaiting_user",
    "retryable_failure",
    "recoverable_pause",
    "completed",
    "cancelled",
    "paused",
]

DEFAULT_WORKFLOW_RECURSION_LIMIT = 512


class TaskAlreadyExistsError(ValueError):
    """A new task attempted to reuse a durable thread identifier."""


@dataclass(frozen=True, slots=True)
class RunResult:
    task_id: str
    status: RunStatus
    approval_card: str = ""
    user_prompt: str = ""
    final_report: str = ""
    error_summary: str = ""


def _interrupt_payload(state: dict[str, Any]) -> dict[str, Any] | None:
    values = state.get("__interrupt__", ())
    if not values:
        return None
    first = values[0]
    value = getattr(first, "value", first)
    return dict(value) if isinstance(value, dict) else {"value": value}


def _run_result(task_id: str, state: dict[str, Any]) -> RunResult:
    stage = str(state.get("stage", ""))
    if stage == "finished" and state.get("final_report"):
        return RunResult(task_id, "completed", final_report=state["final_report"])
    if stage == "cancelled":
        return RunResult(task_id, "cancelled")
    if stage == "awaiting_approval":
        return RunResult(
            task_id,
            "awaiting_approval",
            approval_card=str(state.get("approval_card", "")),
        )
    if stage in {"awaiting_user", "planner_clarification"}:
        return RunResult(
            task_id,
            "awaiting_user",
            user_prompt=str(state.get("stage_note", "")),
        )
    payload = _interrupt_payload(state)
    if payload and payload.get("type") == "research_plan_approval":
        return RunResult(
            task_id,
            "awaiting_approval",
            approval_card=str(payload.get("approval_card", "")),
        )
    if payload:
        return RunResult(
            task_id,
            "awaiting_user",
            user_prompt=str(payload.get("question", payload.get("value", ""))),
        )
    return RunResult(task_id, "paused")


def _has_failed_task(snapshot: Any) -> bool:
    return any(getattr(task, "error", None) for task in snapshot.tasks)


def _retryable_result(task_id: str) -> RunResult:
    return RunResult(
        task_id,
        "retryable_failure",
        error_summary="一个已保存的运行步骤失败；状态仍保留，可显式重试。",
    )


def _recoverable_pause_result(task_id: str) -> RunResult:
    return RunResult(
        task_id,
        "recoverable_pause",
        error_summary=(
            "运行在一个已保存的步骤边界暂停；尚有工作待执行，可显式继续。"
        ),
    )


def _has_pending_work(snapshot: Any) -> bool:
    return bool(getattr(snapshot, "next", ()))


def _snapshot_result(task_id: str, snapshot: Any) -> RunResult:
    if _has_failed_task(snapshot):
        return _retryable_result(task_id)
    state = dict(snapshot.values)
    if snapshot.interrupts:
        state["__interrupt__"] = snapshot.interrupts
        return _run_result(task_id, state)
    if _has_pending_work(snapshot):
        return _recoverable_pause_result(task_id)
    return _run_result(task_id, state)


class ResearchAgent:
    """A thin task API over one compiled, checkpointer-backed graph."""

    def __init__(
        self,
        graph: Any,
        *,
        recursion_limit: int = DEFAULT_WORKFLOW_RECURSION_LIMIT,
    ) -> None:
        if (
            not isinstance(recursion_limit, int)
            or isinstance(recursion_limit, bool)
            or recursion_limit < 1
        ):
            raise ValueError("recursion_limit must be a positive integer")
        self._graph = graph
        self._recursion_limit = recursion_limit
        # Every mutation for one thread is serialized.  This prevents duplicate
        # approval consumption and resume/retry races within this process.
        self._mutation_locks: dict[str, asyncio.Lock] = {}

    @staticmethod
    def _config(task_id: str) -> dict[str, dict[str, str]]:
        if not isinstance(task_id, str) or not task_id.strip():
            raise ValueError("task_id must be a non-empty string")
        return {"configurable": {"thread_id": task_id.strip()}}

    def _mutation_config(self, task_id: str) -> dict[str, Any]:
        config: dict[str, Any] = self._config(task_id)
        config["recursion_limit"] = self._recursion_limit
        return config

    async def start(self, question: str, *, task_id: str | None = None) -> RunResult:
        if not isinstance(question, str) or not question.strip():
            raise ValueError("question must be a non-empty string")
        if task_id is not None and (
            not isinstance(task_id, str) or not task_id.strip()
        ):
            raise ValueError("task_id must be a non-empty string")
        resolved_id = task_id.strip() if task_id is not None else uuid4().hex
        lock = self._mutation_locks.setdefault(resolved_id, asyncio.Lock())
        async with lock:
            existing = await self._graph.aget_state(self._config(resolved_id))
            if existing.values:
                raise TaskAlreadyExistsError(
                    f"task_id {resolved_id!r} already exists; use resume instead"
                )
            try:
                state = await self._graph.ainvoke(
                    {
                        "task_id": resolved_id,
                        "question": question.strip(),
                        "stage": "planning",
                    },
                    self._mutation_config(resolved_id),
                )
            except GraphRecursionError:
                snapshot = await self._graph.aget_state(self._config(resolved_id))
                if _has_pending_work(snapshot):
                    return _snapshot_result(resolved_id, snapshot)
                raise
            except Exception:
                snapshot = await self._graph.aget_state(self._config(resolved_id))
                if _has_failed_task(snapshot):
                    return _snapshot_result(resolved_id, snapshot)
                raise
        return _run_result(resolved_id, state)

    async def resume(self, task_id: str, response: Any) -> RunResult:
        config = self._config(task_id)
        lock = self._mutation_locks.setdefault(task_id.strip(), asyncio.Lock())
        async with lock:
            snapshot = await self._graph.aget_state(config)
            if not snapshot.values:
                raise KeyError(f"unknown task_id {task_id!r}")
            if _has_failed_task(snapshot):
                raise ValueError(
                    f"task_id {task_id!r} has a failed step; use retry instead of resume"
                )
            if not snapshot.interrupts:
                raise ValueError(f"task_id {task_id!r} is not awaiting user input")
            try:
                state = await self._graph.ainvoke(
                    Command(resume=response),
                    self._mutation_config(task_id),
                )
            except GraphRecursionError:
                snapshot = await self._graph.aget_state(config)
                if _has_pending_work(snapshot):
                    return _snapshot_result(task_id, snapshot)
                raise
            except Exception:
                snapshot = await self._graph.aget_state(config)
                if _has_failed_task(snapshot):
                    return _snapshot_result(task_id, snapshot)
                raise
        return _run_result(task_id, state)

    async def retry(self, task_id: str) -> RunResult:
        """Retry only the failed checkpointed graph step for one task."""

        config = self._config(task_id)
        lock = self._mutation_locks.setdefault(task_id.strip(), asyncio.Lock())
        async with lock:
            snapshot = await self._graph.aget_state(config)
            if not snapshot.values:
                raise KeyError(f"unknown task_id {task_id!r}")
            if not _has_failed_task(snapshot):
                raise ValueError(f"task_id {task_id!r} has no retryable failure")
            try:
                state = await self._graph.ainvoke(
                    None, self._mutation_config(task_id)
                )
            except GraphRecursionError:
                pending = await self._graph.aget_state(config)
                if _has_pending_work(pending):
                    return _snapshot_result(task_id, pending)
                raise
            except Exception:
                failed = await self._graph.aget_state(config)
                if _has_failed_task(failed):
                    return _snapshot_result(task_id, failed)
                raise
        return _run_result(task_id, state)

    async def continue_task(self, task_id: str) -> RunResult:
        """Continue a checkpoint with pending work but no error or interrupt."""

        config = self._config(task_id)
        lock = self._mutation_locks.setdefault(task_id.strip(), asyncio.Lock())
        async with lock:
            snapshot = await self._graph.aget_state(config)
            if not snapshot.values:
                raise KeyError(f"unknown task_id {task_id!r}")
            if _has_failed_task(snapshot):
                raise ValueError(
                    f"task_id {task_id!r} has a failed step; use retry instead"
                )
            if snapshot.interrupts:
                raise ValueError(
                    f"task_id {task_id!r} is awaiting user input; use resume instead"
                )
            if not _has_pending_work(snapshot):
                raise ValueError(f"task_id {task_id!r} has no pending work to continue")
            try:
                state = await self._graph.ainvoke(
                    None, self._mutation_config(task_id)
                )
            except GraphRecursionError:
                pending = await self._graph.aget_state(config)
                if _has_pending_work(pending):
                    return _snapshot_result(task_id, pending)
                raise
            except Exception:
                failed = await self._graph.aget_state(config)
                if _has_failed_task(failed):
                    return _snapshot_result(task_id, failed)
                raise
        return _run_result(task_id, state)

    async def status(self, task_id: str) -> RunResult:
        snapshot = await self._graph.aget_state(self._config(task_id))
        if not snapshot.values:
            raise KeyError(f"unknown task_id {task_id!r}")
        return _snapshot_result(task_id, snapshot)


async def inspect_sqlite_task(
    database_path: str | Path, task_id: str
) -> RunResult:
    """Read user-visible status without importing or constructing role code."""

    config = ResearchAgent._config(task_id)
    path = Path(database_path).expanduser().resolve()
    if not path.is_file():
        raise KeyError(f"unknown task_id {task_id!r}")
    async with readonly_sqlite_checkpointer(path) as saver:
        checkpoint_tuple = await saver.aget_tuple(config)
        if checkpoint_tuple is None:
            raise KeyError(f"unknown task_id {task_id!r}")
        if any(
            len(write) >= 2 and write[1] == "__error__"
            for write in checkpoint_tuple.pending_writes
        ):
            return _retryable_result(task_id)
        graph = build_research_graph(
            _inspection_roles(),
            checkpointer=saver,
        )
        snapshot = await graph.aget_state(config)
    return _snapshot_result(task_id, snapshot)


async def _inspection_role(_context: Any) -> Any:
    raise RuntimeError("read-only checkpoint inspection cannot execute roles")


def _inspection_roles() -> RoleExecutors:
    """Build only the graph topology required to reconstruct ``snapshot.next``."""

    return RoleExecutors(
        planner=_inspection_role,
        supervisor=_inspection_role,
        researcher=_inspection_role,
        curator=_inspection_role,
        synthesizer=_inspection_role,
        writer=_inspection_role,
        validator_factory=lambda: _inspection_role,
        editor=_inspection_role,
    )

def create_memory_agent(
    roles: RoleExecutors,
    *,
    guide_context: GuideContextProvider = empty_guide_context,
    guide_catalog: Sequence[str] = (),
    presearch: Sequence[str] = (),
    provider_catalog: Sequence[str] = (),
    citation_renderer: CitationRenderer | None = None,
    recursion_limit: int = DEFAULT_WORKFLOW_RECURSION_LIMIT,
) -> ResearchAgent:
    """Create a non-durable agent for tests and embedded experimentation."""

    graph = build_research_graph(
        roles,
        checkpointer=memory_checkpointer(),
        guide_context=guide_context,
        guide_catalog=guide_catalog,
        presearch=presearch,
        provider_catalog=provider_catalog,
        citation_renderer=citation_renderer,
    )
    return ResearchAgent(graph, recursion_limit=recursion_limit)


@asynccontextmanager
async def open_sqlite_agent(
    roles: RoleExecutors,
    database_path: str | Path,
    *,
    guide_context: GuideContextProvider = empty_guide_context,
    guide_catalog: Sequence[str] = (),
    presearch: Sequence[str] = (),
    provider_catalog: Sequence[str] = (),
    citation_renderer: CitationRenderer | None = None,
    recursion_limit: int = DEFAULT_WORKFLOW_RECURSION_LIMIT,
) -> AsyncIterator[ResearchAgent]:
    """Open the production-local API with durable SQLite checkpoints."""

    with sqlite_writer_lock(database_path):
        async with sqlite_checkpointer(database_path) as saver:
            graph = build_research_graph(
                roles,
                checkpointer=saver,
                guide_context=guide_context,
                guide_catalog=guide_catalog,
                presearch=presearch,
                provider_catalog=provider_catalog,
                citation_renderer=citation_renderer,
            )
            yield ResearchAgent(graph, recursion_limit=recursion_limit)


__all__ = [
    "DEFAULT_WORKFLOW_RECURSION_LIMIT",
    "ResearchAgent",
    "RunResult",
    "RunStatus",
    "TaskAlreadyExistsError",
    "create_memory_agent",
    "inspect_sqlite_task",
    "open_sqlite_agent",
]
