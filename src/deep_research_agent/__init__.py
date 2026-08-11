"""Agent-first deep research with deterministic trust boundaries."""

from .api import (
    DEFAULT_WORKFLOW_RECURSION_LIMIT,
    ResearchAgent,
    RunResult,
    TaskAlreadyExistsError,
    create_memory_agent,
    inspect_sqlite_task,
    open_sqlite_agent,
)
from .citations import CitationRenderer
from .roles import RoleExecutors
from .runtime import AgentRuntime, build_environment_runtime, build_role_executors
from .workflow import build_research_graph

__version__ = "0.1.0"

__all__ = [
    "AgentRuntime",
    "CitationRenderer",
    "DEFAULT_WORKFLOW_RECURSION_LIMIT",
    "ResearchAgent",
    "RoleExecutors",
    "RunResult",
    "TaskAlreadyExistsError",
    "__version__",
    "build_research_graph",
    "build_environment_runtime",
    "build_role_executors",
    "create_memory_agent",
    "inspect_sqlite_task",
    "open_sqlite_agent",
]
