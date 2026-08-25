"""Agent-led deep research with deterministic trust boundaries.

Artifacts and the operation ledger hold durable facts; the research service
projects those facts into user-visible state and Agent behaviour.
"""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _version

from .service import Event, ResearchService, Task, TaskAction, TaskState

try:
    __version__ = _version("deep-research-agent")
except PackageNotFoundError:  # a source tree that was never installed
    __version__ = "0+unknown"

__all__ = [
    "__version__",
    "Event",
    "ResearchService",
    "Task",
    "TaskAction",
    "TaskState",
]
