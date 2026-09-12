"""MCP facade over the existing authenticated local host, never a new runtime."""

import argparse
import asyncio
import json
import os
import secrets
from pathlib import Path

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from .host import send


def build(root, allow_approval=False, sender=send):
    server = MCPServer(
        "Deep Research",
        instructions="Research runs in a persistent local host. Read the exact strategy before approval; disconnection does not cancel research.",
    )

    async def call(action, **fields):
        result = await sender(root, {"action": action, **fields})
        if result.get("error") and action != "status":
            raise ToolError("Research host rejected request: " + result["error"])
        return result

    @server.tool(
        structured_output=True, annotations=ToolAnnotations(read_only_hint=True)
    )
    async def list_research() -> dict[str, object]:
        """List persistent research tasks and their current public state."""
        return await call("overview")

    @server.tool(structured_output=True)
    async def create_research(
        request: str,
        provider: str = "deepseek",
        model: str | None = None,
        web: bool = False,
        analysis: bool = False,
        mcp_servers: list[str] | None = None,
    ) -> dict[str, object]:
        """Create a paused draft. Upload material, then resume to prepare a strategy. No research approval is implied."""
        return await call(
            "create",
            request=request,
            provider=provider,
            model=model,
            web=web,
            analysis=analysis,
            mcp_servers=mcp_servers or [],
            draft=True,
        )

    @server.tool(
        structured_output=True, annotations=ToolAnnotations(read_only_hint=True)
    )
    async def research_status(study: str) -> dict[str, object]:
        """Read status, current strategy including its binding brief, and control version."""
        return await call("status", study=study)

    @server.tool(structured_output=True)
    async def control_research(
        study: str,
        expected: str,
        command_id: str,
        command: str,
        request: str | None = None,
        plan: str | None = None,
    ) -> dict[str, object]:
        """Pause/resume/steer/cancel using the observed control version and unique command ID. Approval requires installation permission and an exact plan reference."""
        if command not in {"pause", "resume", "steer", "cancel", "approve"}:
            raise ToolError("unsupported research control")
        if command == "approve" and not allow_approval:
            raise ToolError(
                "Approve in the local CLI; MCP approval delegation is not enabled"
            )
        return await call(
            "control",
            study=study,
            expected=expected,
            command_id=command_id,
            command=command,
            payload={
                k: v
                for k, v in {"request": request, "plan": plan}.items()
                if v is not None
            },
        )

    @server.tool(structured_output=True)
    async def upload_material(
        study: str, expected: str, name: str, data_base64: str
    ) -> dict[str, object]:
        """Upload explicitly supplied file bytes to a draft/paused task. Limit approximately 3 MiB. Never grant a host directory."""
        if len(data_base64) > 4 * 1024 * 1024 - 8192:
            raise ToolError("upload exceeds IPC limit")
        return await call(
            "upload", study=study, expected=expected, name=name, data=data_base64
        )

    @server.tool(
        structured_output=True, annotations=ToolAnnotations(read_only_hint=True)
    )
    async def read_report(study: str) -> dict[str, object]:
        """Read the published report of the current research direction and its source references."""
        return await call("report", study=study)

    @server.tool(
        structured_output=True, annotations=ToolAnnotations(read_only_hint=True)
    )
    async def list_materials(study: str) -> dict[str, object]:
        """List original and computed material references available for download."""
        return await call("sources", study=study)

    @server.tool(
        structured_output=True, annotations=ToolAnnotations(read_only_hint=True)
    )
    async def download_material(
        study: str, source: str, offset: int = 0, length: int = 65536
    ) -> dict[str, object]:
        """Read original file bytes in base64 chunks (maximum 256 KiB). No host filesystem destination is accepted."""
        return await call(
            "download", study=study, source=source, offset=offset, length=length
        )

    @server.tool(
        structured_output=True, annotations=ToolAnnotations(read_only_hint=True)
    )
    async def research_usage(study: str) -> dict[str, object]:
        """Read actual recorded model/search usage; missing provider counters remain unknown."""
        return await call("usage", study=study)

    @server.resource("research://{study}/report")
    async def report_resource(study: str) -> str:
        """Published research report; requests do not start or resume research."""
        return json.dumps(await call("report", study=study), ensure_ascii=False)

    return server


class Bearer:
    def __init__(self, app, token):
        self.app, self.token = app, token

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            supplied = dict(scope.get("headers", [])).get(b"authorization", b"")
            if not secrets.compare_digest(supplied, ("Bearer " + self.token).encode()):
                await send(
                    {
                        "type": "http.response.start",
                        "status": 401,
                        "headers": [(b"www-authenticate", b"Bearer")],
                    }
                )
                await send({"type": "http.response.body", "body": b"Unauthorized"})
                return
        await self.app(scope, receive, send)


def main():
    parser = argparse.ArgumentParser(
        description="Expose local research through MCP; credentials are never printed"
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument(
        "--allow-approval",
        action="store_true",
        help="Explicitly delegate exact strategy approvals to the connected client",
    )
    parser.add_argument("--token-env", default="DR_MCP_TOKEN")
    args = parser.parse_args()
    root = args.root.resolve()
    token = os.environ.get(args.token_env, "")
    if args.transport == "http" and not token:
        parser.error("HTTP requires an independent Bearer token in --token-env")
    try:
        asyncio.run(send(root, {"action": "list"}))
    except (OSError, ValueError, TimeoutError):
        parser.error(
            "Start the independent research host first: deep-research --root <root> start"
        )
    server = build(root, args.allow_approval)
    if args.transport == "stdio":
        server.run()
    else:
        import uvicorn

        app = server.streamable_http_app(stateless_http=True, host="127.0.0.1")
        uvicorn.run(
            Bearer(app, token), host="127.0.0.1", port=args.port, access_log=False
        )


if __name__ == "__main__":
    main()
