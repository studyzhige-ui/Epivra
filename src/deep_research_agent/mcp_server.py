"""Local STDIO MCP adapter over :class:`ResearchService`.

MCP is a product entry, not another research runtime.  This module translates
tool calls into the same service methods the interactive workspace uses and
translates the service's projections back into plain JSON values.  It never
writes artifacts or interprets task state itself.
"""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import aiosqlite
from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp.types import ToolAnnotations

from . import __version__
from .application import load_environment
from .cli.paths import config_file, default_database, settings_file
from .cli.settings import load as load_settings
from .cli.settings import runtime_environment
from .contract import SourceAccess
from .service import Event, Listener, ResearchService, Task

JsonObject = dict[str, Any]

SERVER_INSTRUCTIONS = (
    "Deep Research is an Agent-first research system. create_research proposes a "
    "direction but does not start retrieval. Show the returned direction and "
    "plan_id to the user; call start_research only after the user explicitly "
    "accepts that exact direction. Use adjust_research_direction for changes and "
    "answer_research_clarification for an open question. Read task state from the "
    "tools, never infer or invent it. Research calls can take a long time."
)


def _task_payload(task: Task) -> JsonObject:
    """Serialize the service projection without deriving another state view."""

    plan: JsonObject | None = None
    if task.plan_id:
        plan = {"plan_id": task.plan_id, "version": task.plan_version}

    clarification: JsonObject | None = None
    if task.clarification_id:
        clarification = {
            "clarification_id": task.clarification_id,
            "question": task.clarification_question,
            "why_it_changes_the_plan": task.clarification_why,
        }

    return {
        "task_id": task.task_id,
        "request": task.request,
        "language": task.language,
        "source_access": list(task.source_access),
        "state": task.state,
        "materials": task.materials,
        "sources": task.sources,
        "plan": plan,
        "clarification": clarification,
        "allowed_actions": list(task.allowed_actions),
    }


def _progress_message(event: Event) -> str:
    """Keep a progress notification useful without copying a large artifact."""

    first_line = next(
        (line.strip() for line in event.message.splitlines() if line.strip()), ""
    )
    summary = first_line or event.kind.replace("_", " ")
    if len(summary) > 240:
        summary = summary[:237].rstrip() + "..."
    return f"{event.kind}: {summary}"


@asynccontextmanager
async def _progress_listener(ctx: Context):  # noqa: ANN202
    """Bridge synchronous service events to non-durable MCP notifications."""

    pending: list[asyncio.Task[None]] = []

    def listen(event: Event) -> None:
        pending.append(
            asyncio.create_task(
                ctx.report_progress(
                    progress=float(len(pending) + 1),
                    message=_progress_message(event),
                )
            )
        )

    try:
        yield listen
    finally:
        if pending:
            # Progress is presentation only.  A client that does not accept a
            # notification must not invalidate research facts already committed.
            await asyncio.gather(*pending, return_exceptions=True)


@dataclass(frozen=True, slots=True)
class McpAdapter:
    """Open the shared service for one MCP call, with no adapter-owned state."""

    database: Path

    @asynccontextmanager
    async def _service(self):  # noqa: ANN202
        settings = load_settings(settings_file())
        environment = runtime_environment(
            settings.defaults, dict(load_environment(config_file()))
        )
        self.database.parent.mkdir(parents=True, exist_ok=True)
        connection = await aiosqlite.connect(self.database)
        try:
            service = ResearchService(
                connection=connection,
                environ=environment,
                corpus_root=(
                    Path(settings.defaults.corpus_root)
                    if settings.defaults.corpus_root
                    else None
                ),
            )
            await service.setup()
            yield service
        finally:
            await connection.close()

    async def _detail(self, service: ResearchService, task: Task) -> JsonObject:
        payload = _task_payload(task)
        if task.plan_id:
            payload["direction"] = await service.approval_card(task.task_id)
        payload["execution"] = await service.execution_summary(task.task_id)
        return payload

    async def create(
        self,
        request: str,
        *,
        language: str,
        source_access: Sequence[SourceAccess],
        constraints: Sequence[str],
        listen: Listener,
    ) -> JsonObject:
        async with self._service() as service:
            task = await service.open_task(
                request,
                language=language,
                source_access=source_access,
                constraints=constraints,
                created_at=datetime.now(UTC).isoformat(),
                listen=listen,
            )
            return await self._detail(service, task)

    async def get(self, task_id: str) -> JsonObject:
        async with self._service() as service:
            return await self._detail(service, await service.task(task_id))

    async def list(self) -> list[JsonObject]:
        async with self._service() as service:
            return [_task_payload(task) for task in await service.tasks()]

    async def answer(
        self,
        task_id: str,
        clarification_id: str,
        answer: str,
        *,
        listen: Listener,
    ) -> JsonObject:
        async with self._service() as service:
            task = await service.answer_clarification(
                task_id, clarification_id, answer, listen=listen
            )
            return await self._detail(service, task)

    async def retry_planning(
        self, task_id: str, *, listen: Listener
    ) -> JsonObject:
        async with self._service() as service:
            task = await service.replan(task_id, listen=listen)
            return await self._detail(service, task)

    async def adjust(
        self,
        task_id: str,
        plan_id: str,
        instruction: str,
        *,
        listen: Listener,
    ) -> JsonObject:
        async with self._service() as service:
            task = await service.request_revision(
                task_id, plan_id, instruction, listen=listen
            )
            return await self._detail(service, task)

    async def start(
        self, task_id: str, plan_id: str, *, listen: Listener
    ) -> JsonObject:
        async with self._service() as service:
            await service.approve(task_id, plan_id)
            await service.advance(task_id, listen=listen)
            return await self._detail(service, await service.task(task_id))

    async def continue_research(
        self, task_id: str, *, listen: Listener
    ) -> JsonObject:
        async with self._service() as service:
            await service.advance(task_id, listen=listen)
            return await self._detail(service, await service.task(task_id))

    async def report(self, task_id: str) -> JsonObject:
        async with self._service() as service:
            report = await service.report(task_id)
            if report is None:
                raise ValueError("这项研究还没有已发布的报告。")
            return {
                "task": _task_payload(await service.task(task_id)),
                "report": report,
            }

    async def delete(self, task_id: str) -> JsonObject:
        async with self._service() as service:
            return {
                "task_id": task_id,
                "deleted": await service.delete_research(task_id),
            }


def _annotations(
    *,
    read_only: bool,
    destructive: bool = False,
    idempotent: bool | None = None,
    open_world: bool,
) -> ToolAnnotations:
    return ToolAnnotations(
        read_only_hint=read_only,
        destructive_hint=destructive if not read_only else None,
        idempotent_hint=idempotent if not read_only else None,
        open_world_hint=open_world,
    )


def build_server(adapter: McpAdapter) -> MCPServer:
    """Build the protocol surface around one stateless application adapter."""

    server = MCPServer(
        name="deep-research",
        title="Deep Research",
        description="Plan and run evidence-backed research with an Agent.",
        instructions=SERVER_INSTRUCTIONS,
        version=__version__,
    )

    @server.tool(
        title="Create a research direction",
        annotations=_annotations(read_only=False, open_world=True),
    )
    async def create_research(
        request: str,
        ctx: Context,
        language: str = "zh",
        source_access: tuple[SourceAccess, ...] = ("public_web",),
        constraints: tuple[str, ...] = (),
    ) -> JsonObject:
        """Create a study and propose its direction; do not start retrieval.

        Return the exact direction and plan_id that must be shown to the user.
        If clarification is present, ask that question instead.
        """

        async with _progress_listener(ctx) as listen:
            return await adapter.create(
                request,
                language=language,
                source_access=source_access,
                constraints=constraints,
                listen=listen,
            )

    @server.tool(
        title="Get a research study",
        annotations=_annotations(read_only=True, open_world=False),
    )
    async def get_research(task_id: str) -> JsonObject:
        """Get the current fact-derived study view and exact research direction."""

        return await adapter.get(task_id)

    @server.tool(
        title="List research studies",
        annotations=_annotations(read_only=True, open_world=False),
    )
    async def list_research() -> list[JsonObject]:
        """List all studies, newest first, using service-projected task views."""

        return await adapter.list()

    @server.tool(
        title="Answer a research clarification",
        annotations=_annotations(read_only=False, open_world=True),
    )
    async def answer_research_clarification(
        task_id: str,
        clarification_id: str,
        answer: str,
        ctx: Context,
    ) -> JsonObject:
        """Answer the exact open question and let the Agent propose a direction."""

        async with _progress_listener(ctx) as listen:
            return await adapter.answer(
                task_id,
                clarification_id,
                answer,
                listen=listen,
            )

    @server.tool(
        title="Retry research planning",
        annotations=_annotations(read_only=False, idempotent=True, open_world=True),
    )
    async def retry_research_planning(task_id: str, ctx: Context) -> JsonObject:
        """Retry planning after an interrupted planning call; never start research."""

        async with _progress_listener(ctx) as listen:
            return await adapter.retry_planning(task_id, listen=listen)

    @server.tool(
        title="Adjust a research direction",
        annotations=_annotations(read_only=False, open_world=True),
    )
    async def adjust_research_direction(
        task_id: str,
        plan_id: str,
        instruction: str,
        ctx: Context,
    ) -> JsonObject:
        """Replace the exact proposed direction using the user's instruction."""

        async with _progress_listener(ctx) as listen:
            return await adapter.adjust(
                task_id, plan_id, instruction, listen=listen
            )

    @server.tool(
        title="Start accepted research",
        annotations=_annotations(read_only=False, open_world=True),
    )
    async def start_research(
        task_id: str, plan_id: str, ctx: Context
    ) -> JsonObject:
        """Start the exact direction the user has explicitly accepted.

        This can make paid model and search calls and may run for a long time.
        Never call it merely because a direction was generated.
        """

        async with _progress_listener(ctx) as listen:
            return await adapter.start(task_id, plan_id, listen=listen)

    @server.tool(
        title="Continue a research study",
        annotations=_annotations(read_only=False, open_world=True),
    )
    async def continue_research(task_id: str, ctx: Context) -> JsonObject:
        """Continue an already accepted study from its committed facts.

        This can make paid model and search calls and may run for a long time.
        """

        async with _progress_listener(ctx) as listen:
            return await adapter.continue_research(task_id, listen=listen)

    @server.tool(
        title="Get a published research report",
        annotations=_annotations(read_only=True, open_world=False),
    )
    async def get_research_report(task_id: str) -> JsonObject:
        """Return the published report; fail clearly if it is not published yet."""

        return await adapter.report(task_id)

    @server.tool(
        title="Delete a research study",
        annotations=_annotations(
            read_only=False,
            destructive=True,
            idempotent=True,
            open_world=False,
        ),
    )
    async def delete_research(task_id: str) -> JsonObject:
        """Irreversibly delete one study and all of its task-owned facts."""

        return await adapter.delete(task_id)

    return server


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="deep-research-mcp",
        description="Run the local Deep Research STDIO MCP server.",
    )
    parser.add_argument(
        "--database",
        default=str(default_database()),
        help="SQLite task database (default: %(default)s)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the local STDIO server.  Protocol output is owned by the MCP SDK."""

    args = _parser().parse_args(argv)
    build_server(McpAdapter(Path(args.database))).run(transport="stdio")
    return 0


__all__ = ["McpAdapter", "build_server", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
