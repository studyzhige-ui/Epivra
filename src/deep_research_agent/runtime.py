"""Small composition root for the built-in agentic runtime.

Constructing a runtime reads configuration but performs no model, search, or
network request.  The eight semantic executors remain separate; only Planner
and Researcher receive their explicitly allowed external tools.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, distribution
from pathlib import Path

from .guides import GuideCatalog, guide_context_provider
from .llm_roles import (
    DEFAULT_MAX_PAYLOAD_CHARS,
    CuratorExecutor,
    EditorExecutor,
    SupervisorExecutor,
    SynthesizerExecutor,
    ValidatorExecutor,
    WriterExecutor,
)
from .model import ChatModel, DeepSeekChatClient
from .planner import AgenticPlanner
from .providers import PublicHttpReader, configured_search_providers
from .researcher import ControlledResearcher
from .roles import RoleExecutors
from .tools import SourceReader, TransparentSearchBroker


DEFAULT_PLANNER_TURN_LIMIT: int | None = None
DEFAULT_RESEARCHER_TURN_LIMIT: int | None = None


@dataclass(frozen=True, slots=True)
class AgentRuntime:
    """The minimal dependencies needed to compile a task graph."""

    roles: RoleExecutors
    guides: GuideCatalog

    @property
    def guide_catalog(self) -> tuple[str, ...]:
        return tuple(
            f"{item.guide_id}@{item.version} [{item.kind}] - "
            f"{item.title}: {item.summary}"
            for item in self.guides.summaries()
        )

    @property
    def guide_context(self):
        return guide_context_provider(self.guides)


def build_role_executors(
    model: ChatModel,
    broker: TransparentSearchBroker,
    reader: SourceReader,
    *,
    guide_catalog: GuideCatalog | None = None,
    validator_model_factory: Callable[[], ChatModel] | None = None,
    planner_turn_limit: int | None = DEFAULT_PLANNER_TURN_LIMIT,
    researcher_turn_limit: int | None = DEFAULT_RESEARCHER_TURN_LIMIT,
    role_max_payload_chars: int = DEFAULT_MAX_PAYLOAD_CHARS,
) -> RoleExecutors:
    """Compose eight narrow roles without giving tools to producer/reviewer roles."""

    def validator_factory() -> ValidatorExecutor:
        validator_model = (
            validator_model_factory() if validator_model_factory else model
        )
        return ValidatorExecutor(
            validator_model, max_payload_chars=role_max_payload_chars
        )

    return RoleExecutors(
        planner=AgenticPlanner(
            model,
            broker,
            reader,
            guide_catalog=guide_catalog,
            runtime_turn_limit=planner_turn_limit,
            max_payload_chars=role_max_payload_chars,
        ),
        supervisor=SupervisorExecutor(
            model, max_payload_chars=role_max_payload_chars
        ),
        researcher=ControlledResearcher(
            model,
            broker,
            reader,
            runtime_turn_limit=researcher_turn_limit,
            max_payload_chars=role_max_payload_chars,
        ),
        curator=CuratorExecutor(model, max_payload_chars=role_max_payload_chars),
        synthesizer=SynthesizerExecutor(
            model, max_payload_chars=role_max_payload_chars
        ),
        writer=WriterExecutor(model, max_payload_chars=role_max_payload_chars),
        validator_factory=validator_factory,
        editor=EditorExecutor(model, max_payload_chars=role_max_payload_chars),
    )


def build_environment_runtime(
    *,
    guide_root: str | Path | None = None,
    model: ChatModel | None = None,
    reader: SourceReader | None = None,
    planner_turn_limit: int | None = DEFAULT_PLANNER_TURN_LIMIT,
    researcher_turn_limit: int | None = DEFAULT_RESEARCHER_TURN_LIMIT,
    role_max_payload_chars: int = DEFAULT_MAX_PAYLOAD_CHARS,
) -> AgentRuntime:
    """Build the first-party DeepSeek + configured-search runtime.

    This reads local environment/configuration but performs no model, search, or
    network request.  At least one fixed-origin provider must be configured.
    Tavily and Exa can return extracted text; Brave and Bocha provide independent
    discovery results that the Researcher can pass to the public reader.
    """

    root = Path(guide_root) if guide_root is not None else builtin_guide_root()
    guides = GuideCatalog.discover(root) if root.exists() else GuideCatalog()
    resolved_model = model or DeepSeekChatClient.from_environment()
    providers = configured_search_providers()
    if not providers:
        raise ValueError(
            "No search provider is configured; set TAVILY_API_KEY, EXA_API_KEY, "
            "BRAVE_SEARCH_API_KEY, or BOCHA_API_KEY"
        )
    broker = TransparentSearchBroker(providers)
    resolved_reader = reader or PublicHttpReader()
    return AgentRuntime(
        roles=build_role_executors(
            resolved_model,
            broker,
            resolved_reader,
            guide_catalog=guides,
            planner_turn_limit=planner_turn_limit,
            researcher_turn_limit=researcher_turn_limit,
            role_max_payload_chars=role_max_payload_chars,
        ),
        guides=guides,
    )


def builtin_guide_root() -> Path:
    """Locate repository Guides in development and installed data otherwise."""

    source_root = Path(__file__).resolve().parents[2] / "guides"
    if source_root.is_dir():
        return source_root
    try:
        installed = distribution("deep-research-agent").locate_file(
            "share/deep-research-agent/guides"
        )
    except PackageNotFoundError:
        return source_root
    return Path(installed)


__all__ = [
    "AgentRuntime",
    "DEFAULT_PLANNER_TURN_LIMIT",
    "DEFAULT_RESEARCHER_TURN_LIMIT",
    "build_environment_runtime",
    "build_role_executors",
    "builtin_guide_root",
]
