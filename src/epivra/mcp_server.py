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
from .locale import LANGUAGES, configure, tr


def build(root, allow_approval=False, sender=send, language="zh-CN"):
    def text(message):
        return tr(message, language=language)

    server = MCPServer(
        "Epivra",
        instructions=text(
            "研究在持久本地宿主中运行。审批前阅读精确策略；断开连接不会取消研究。"
        ),
    )

    async def call(action, **fields):
        result = await sender(root, {"action": action, **fields})
        if result.get("error") and action != "status":
            raise ToolError(text("研究宿主拒绝请求：") + result["error"])
        return result

    @server.tool(
        structured_output=True,
        annotations=ToolAnnotations(read_only_hint=True),
        description=text("列出持久保存的研究任务及其当前公开状态。"),
    )
    async def list_research() -> dict[str, object]:
        """List persistent research tasks and their current public state."""
        return await call("overview")

    @server.tool(
        structured_output=True,
        description=text(
            "创建暂停草稿。上传资料后恢复，以准备研究策略；创建不表示批准研究。"
        ),
    )
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
        structured_output=True,
        annotations=ToolAnnotations(read_only_hint=True),
        description=text("读取研究状态、含范围约定的当前策略和控制版本。"),
    )
    async def research_status(study: str) -> dict[str, object]:
        """Read status, current strategy including its binding brief, and control version."""
        return await call("status", study=study)

    @server.tool(
        structured_output=True,
        description=text(
            "使用已读取的控制版本和唯一命令ID暂停、恢复、改向或取消。审批需要安装级授权和精确策略引用。"
        ),
    )
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
            raise ToolError(text("不支持的研究控制"))
        if command == "approve" and not allow_approval:
            raise ToolError(text("请在本地工作台审批；未启用MCP代为审批。"))
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

    @server.tool(
        structured_output=True,
        description=text(
            "向草稿或暂停的研究上传用户明确提供的文件字节，约3 MiB上限；不会授权宿主目录。"
        ),
    )
    async def upload_material(
        study: str, expected: str, name: str, data_base64: str
    ) -> dict[str, object]:
        """Upload explicitly supplied file bytes to a draft/paused task. Limit approximately 3 MiB. Never grant a host directory."""
        if len(data_base64) > 4 * 1024 * 1024 - 8192:
            raise ToolError(text("上传超过IPC容量限制"))
        return await call(
            "upload", study=study, expected=expected, name=name, data=data_base64
        )

    @server.tool(
        structured_output=True,
        annotations=ToolAnnotations(read_only_hint=True),
        description=text("读取当前研究方向已发布的报告及来源引用。"),
    )
    async def read_report(study: str) -> dict[str, object]:
        """Read the published report of the current research direction and its source references."""
        return await call("report", study=study)

    @server.tool(
        structured_output=True,
        annotations=ToolAnnotations(read_only_hint=True),
        description=text("列出可下载的原始资料和计算产物引用。"),
    )
    async def list_materials(study: str) -> dict[str, object]:
        """List original and computed material references available for download."""
        return await call("sources", study=study)

    @server.tool(
        structured_output=True,
        annotations=ToolAnnotations(read_only_hint=True),
        description=text(
            "分块读取原始文件的base64字节，每块最多256 KiB；不接受宿主文件系统保存路径。"
        ),
    )
    async def download_material(
        study: str, source: str, offset: int = 0, length: int = 65536
    ) -> dict[str, object]:
        """Read original file bytes in base64 chunks (maximum 256 KiB). No host filesystem destination is accepted."""
        return await call(
            "download", study=study, source=source, offset=offset, length=length
        )

    @server.tool(
        structured_output=True,
        annotations=ToolAnnotations(read_only_hint=True),
        description=text("读取实际记录的模型和搜索用量；供应商未提供的计数保持未知。"),
    )
    async def research_usage(study: str) -> dict[str, object]:
        """Read actual recorded model/search usage; missing provider counters remain unknown."""
        return await call("usage", study=study)

    @server.resource(
        "research://{study}/report",
        description=text("已发布研究报告；读取不会启动或恢复研究。"),
    )
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
    language = configure()
    parser = argparse.ArgumentParser(description=tr("通过MCP提供本地研究；不输出凭据"))
    parser.add_argument("--lang", choices=LANGUAGES, help="简体中文 / English")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument(
        "--allow-approval",
        action="store_true",
        help=tr("明确授权连接的客户端审批精确研究策略"),
    )
    parser.add_argument("--token-env", default="EPIVRA_MCP_TOKEN")
    args = parser.parse_args()
    root = args.root.resolve()
    token = os.environ.get(args.token_env, "")
    if args.transport == "http" and not token:
        parser.error(tr("HTTP需要通过--token-env指定独立Bearer令牌"))
    try:
        asyncio.run(send(root, {"action": "list"}))
    except (OSError, ValueError, TimeoutError):
        parser.error(tr("请先独立启动研究宿主：epivra --root <root> start"))
    server = build(root, args.allow_approval, language=language)
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
