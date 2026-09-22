"""Loopback browser UI: installation settings and an allowlisted Host facade."""

import argparse
import asyncio
import json
import os
import secrets
import socket
import subprocess
import sys
import tempfile
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from . import cli_settings, host
from .locale import LANGUAGES, configure, current_language, set_language, tr
from .model_catalog import OFFICIAL_PROVIDERS
from .model_discovery import DiscoveryError, discover
from .models import freeze_model_settings
from .report_export import word_report
from .web_providers import CONNECTIONS, READERS, SEARCH

DEFAULT_FIELDS = {
    "provider",
    "model",
    "role_models",
    "region",
    "context_tokens",
    "max_tokens",
    "search_provider",
    "reader_provider",
    "parser",
    "docling_models",
    "parse_timeout",
    "text_encoding",
    "analysis",
    "mcp_servers",
}
COMMANDS = {
    "delete": {"study", "expected", "confirmed"},
    "overview": set(),
    "status": {"study"},
    "report": {"study", "expected"},
    "progress": {"study"},
    "work_detail": {"study", "work"},
    "source_text": {"study", "source", "offset"},
    "sources": {"study"},
    "usage": {"study"},
    "reload": {"study"},
    "create": DEFAULT_FIELDS | {"request", "web", "local_roots"},
    "control": {"study", "expected", "command_id", "command", "payload"},
    "import_file": {"study", "expected", "path"},
    "mcp_connections": set(),
    "mcp_discover": {"name"},
}
ASSETS = {
    "/reader.js": ("reader.js", "text/javascript; charset=utf-8"),
    "/katex.min.js": ("katex.min.js", "text/javascript; charset=utf-8"),
    "/messages.json": ("messages.json", "application/json; charset=utf-8"),
    "/i18n.js": ("i18n.js", "text/javascript; charset=utf-8"),
    "/epivra-icon.svg": ("epivra-icon.svg", "image/svg+xml"),
    "/favicon.svg": ("favicon.svg", "image/svg+xml"),
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
    "/markdown-it.min.js": ("markdown-it.min.js", "text/javascript; charset=utf-8"),
}


class WebError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


class App:
    def __init__(self, root, sender=None):
        self.root = Path(root).resolve()
        self.sender = sender or host.send
        self.settings_lock = threading.Lock()
        self.picker_lock = threading.Lock()

    def call(self, data):
        action = data.get("action")
        if action not in COMMANDS or data.keys() - COMMANDS[action] - {"action"}:
            raise WebError(tr("不支持的操作或参数。"))
        if action == "control" and data.get("command") not in {
            "approve",
            "pause",
            "resume",
            "steer",
            "cancel",
        }:
            raise WebError(tr("不支持的研究控制。"))
        if action == "create":
            data = {**data, "draft": True}
        return self.send(data)

    def send(self, data):
        action = data["action"]
        result = asyncio.run(self.sender(self.root, data))
        if action == "delete" and result.get("deleted") is False:
            raise WebError(
                tr(
                    "研究已停止，但资源清理尚未完成。请检查本地工具或Docker状态后重试删除；记录暂时保留。"
                ),
                503,
            )
        # A status error is a research blocker, not a failed read.
        if result.get("error") and not (action == "status" and "control" in result):
            messages = {
                "Conflict": tr("研究状态已变化，请刷新并重新阅读策略后确认。"),
                "NotAllowed": tr("当前状态不允许操作，请先暂停并等待在途工作结束。"),
                "ValueError": tr("操作未完成，请检查路径、连接配置和研究状态。"),
                "KeyError": tr("未找到所选研究、资料或连接，请刷新。"),
                "FileNotFoundError": tr("找不到所选文件，请检查路径或重新选择。"),
                "PermissionError": tr("无法读取所选文件，请检查本地访问权限。"),
            }
            raise WebError(
                messages.get(result["error"], tr("宿主操作失败：") + result["error"]),
                409 if result["error"] == "Conflict" else 400,
            )
        return result

    def settings(self):
        with self.settings_lock:
            keys = cli_settings.configured(self.root)
            defaults = cli_settings.load(self.root)
        return {
            "root": str(self.root),
            "defaults": {k: v for k, v in defaults.items() if k in DEFAULT_FIELDS},
            "providers": [
                {
                    "id": s.id,
                    "model": s.default_model.id,
                    "region": s.default_region,
                    "regions": [r for r, _ in s.endpoints],
                    "credential": s.credential_env,
                    "configured": s.credential_env in keys,
                }
                for s in OFFICIAL_PROVIDERS.values()
            ],
            "connections": [
                {
                    "id": name,
                    "credential": value[1],
                    "configured": bool(value[1] and value[1] in keys),
                }
                for name, value in CONNECTIONS.items()
            ],
            "search": list(SEARCH),
            "readers": list(READERS),
        }

    def discover_models(self, data):
        if data.keys() - {"provider", "region", "key"}:
            raise WebError(tr("未知模型列表参数。"))
        provider = data["provider"]
        with self.settings_lock:
            try:
                key = cli_settings.model_key(self.root, provider, data.get("key", ""))
            except ValueError as exc:
                raise WebError(tr(str(exc))) from None
        try:
            result = discover(provider, data.get("region"), key)
            result["message"] = tr(result.get("message", ""))
            return result
        except DiscoveryError as exc:
            raise WebError(tr(str(exc))) from None

    def save_settings(self, data):
        if data.keys() - DEFAULT_FIELDS:
            raise WebError(tr("未知默认设置。"))
        # Validate model capacity/region with the same provider contract, without I/O.
        freeze_model_settings(data)
        if data.get("parser", "auto") not in {"auto", "light", "docling"}:
            raise WebError(tr("未知解析器。"))
        for key, choices in (("search_provider", SEARCH), ("reader_provider", READERS)):
            if key in data and data[key] not in choices:
                raise WebError(tr("未知搜索或网页读取连接。"))
        if "analysis" in data and type(data["analysis"]) is not bool:
            raise WebError(tr("分析设置应为开关。"))
        names = data.get("mcp_servers", [])
        if not isinstance(names, list) or not all(isinstance(n, str) for n in names):
            raise WebError(tr("MCP 连接应为名称列表。"))
        if names and set(names) - set(
            self.call({"action": "mcp_connections"})["servers"]
        ):
            raise WebError(tr("MCP 连接未配置。"))
        if "parse_timeout" in data and (
            type(data["parse_timeout"]) not in (int, float)
            or not 0 < data["parse_timeout"] < float("inf")
        ):
            raise WebError(tr("解析超时须为正数。"))
        if (
            data.get("docling_models")
            and not (self.root / data["docling_models"]).is_dir()
        ):
            raise WebError(tr("Docling 模型文件夹不存在。"))
        with self.settings_lock:
            cli_settings.save(self.root, data)
        return {"saved": True}

    def pick(self, data):
        if data.get("kind") not in {"file", "folder"}:
            raise WebError(tr("请选择文件或文件夹。"))
        if not self.picker_lock.acquire(blocking=False):
            raise WebError(tr("系统选择窗口已打开，请先完成选择。"), 409)
        try:
            # Tk owns the main thread of this short-lived process, not an HTTP worker.
            result = subprocess.run(
                [
                    sys.executable,
                    "-X",
                    "utf8",
                    "-c",
                    "from epivra.terminal import native_path; "
                    "from epivra.locale import set_language; "
                    "import json,sys; "
                    "set_language(sys.argv[2]); "
                    "p=native_path(directory=sys.argv[1]=='folder'); "
                    "print(json.dumps({'path':str(p) if p else None}))",
                    data["kind"],
                    current_language(),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=180,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            if result.returncode:
                raise WebError(tr("系统选择窗口不可用，请粘贴本地路径或上传文件。"))
            return json.loads(result.stdout)
        finally:
            self.picker_lock.release()


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def server_bind(self):
        # Windows address reuse can route requests to another instance/token.
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()

    def __init__(self, app, port=0, max_upload=256 * 1024 * 1024, max_workers=16):
        self.workers = threading.BoundedSemaphore(max_workers)
        self.app, self.token, self.max_upload = (
            app,
            secrets.token_urlsafe(32),
            max_upload,
        )
        super().__init__(("127.0.0.1", port), Handler)
        self.authority = f"127.0.0.1:{self.server_port}"
        self.origin = f"http://{self.authority}"

    def process_request(self, request, client_address):
        if not self.workers.acquire(blocking=False):
            try:
                request.settimeout(0.2)
                request.sendall(b'HTTP/1.0 503 Service Unavailable\r\nContent-Type: application/json\r\nContent-Length: 23\r\nRetry-After: 1\r\nConnection: close\r\n\r\n{"error":"server_busy"}')
            except OSError:
                pass
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self.workers.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.workers.release()

    @property
    def url(self):
        return f"{self.origin}/#token={self.token}"


class Handler(BaseHTTPRequestHandler):
    server_version = "Epivra"

    def setup(self):
        super().setup()
        self.connection.settimeout(600)

    def log_message(self, *args):
        pass  # No URL, uploaded names or credentials in access logs.

    def reply(self, data, status=200, content_type="application/json; charset=utf-8"):
        # Drain small rejected bodies before closing: Windows otherwise resets the
        # socket with unread bytes and browsers lose the actionable error response.
        unread = getattr(self, "unread", 0)
        if 0 < unread <= 1024 * 1024:
            self.connection.settimeout(1)
            try:
                self.rfile.read(unread)
            except OSError:
                pass
            self.unread = 0
        raw = (
            data
            if isinstance(data, bytes)
            else json.dumps(data, ensure_ascii=False).encode()
        )
        try:
            self.send_headers(len(raw), content_type, status)
            self.wfile.write(raw)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            self.close_connection = True

    def send_headers(self, size, content_type, status=200):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(size))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; "
            "style-src 'self'; img-src 'self' blob: data:; connect-src 'self'; "
            "object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
        )
        self.end_headers()

    def guard(self, api=False):
        language = self.headers.get("X-Epivra-Language", "zh-CN")
        set_language(language if language in LANGUAGES else "zh-CN")
        if self.headers.get("Host") != self.server.authority:
            raise WebError(tr("无效的本地访问地址。"), 403)
        origin = self.headers.get("Origin")
        if origin is not None and origin != self.server.origin:
            raise WebError(tr("仅允许当前本地页面访问。"), 403)
        if api and not secrets.compare_digest(
            self.headers.get("X-Research-Token", ""), self.server.token
        ):
            raise WebError(tr("访问链接已失效，请使用终端中的启动链接重新打开。"), 401)

    def do_GET(self):
        self.handle_request(False)

    def do_POST(self):
        self.handle_request(True)

    def length(self, maximum):
        if self.headers.get("Transfer-Encoding"):
            raise WebError(tr("不支持分块请求编码。"))
        try:
            size = int(self.headers.get("Content-Length", "-1"))
        except ValueError:
            raise WebError(tr("请求长度无效。")) from None
        if size < 0 or size > maximum:
            raise WebError(tr("文件或请求超过上传上限，请使用本地文件路径导入。"), 413)
        return size

    def handle_request(self, post):
        self.unread = 0
        try:
            self.unread = max(0, int(self.headers.get("Content-Length", "0")))
            path = urlsplit(self.path).path
            self.guard(api=path.startswith("/api/"))
            if not post and path in ASSETS:
                name, mime = ASSETS[path]
                self.reply(
                    (Path(__file__).with_name("web") / name).read_bytes(),
                    content_type=mime,
                )
                return
            if not post and path == "/api/settings":
                self.reply(
                    {**self.server.app.settings(), "max_upload": self.server.max_upload}
                )
                return
            if post and path == "/api/upload":
                self.upload()
                return
            if not post or path not in {
                "/api/command",
                "/api/settings",
                "/api/models",
                "/api/key",
                "/api/pick",
                "/api/file",
                "/api/report-export",
            }:
                raise WebError(tr("未找到此入口。"), 404)
            if self.headers.get_content_type() != "application/json":
                raise WebError(tr("请求应为 JSON。"), 415)
            raw = self.rfile.read(self.length(1024 * 1024))
            self.unread = 0
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise WebError(tr("请求应为对象。"))
            app = self.server.app
            if path == "/api/report-export":
                if set(data) != {"study", "expected"} or not data["expected"]:
                    raise WebError(tr("导出需要当前报告版本。"))
                report = app.call({"action": "report", **data})
                self.reply(
                    word_report(report),
                    content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
                return
            if path == "/api/file":
                self.download(data)
                return
            if path == "/api/command":
                result = app.call(data)
            elif path == "/api/models":
                result = app.discover_models(data)
            elif path == "/api/settings":
                result = app.save_settings(data)
            elif path == "/api/pick":
                result = app.pick(data)
            else:
                with app.settings_lock:
                    overridden = cli_settings.save_key(
                        app.root, data["name"], data["value"]
                    )
                result = {"saved": True, "environment_override": overridden}
            self.reply(result)
        except WebError as exc:
            self.reply({"error": str(exc)}, exc.status)
        except (TimeoutError, subprocess.TimeoutExpired):
            self.reply(
                {
                    "error": tr(
                        "等待超时，操作可能仍在后台执行。请刷新状态，不要重复创建或提交。"
                    )
                },
                504,
            )
        except (ValueError, KeyError, TypeError):
            self.reply({"error": tr("参数或配置无效，请检查后重试。")}, 400)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            self.close_connection = True
        except OSError:
            self.reply(
                {"error": tr("无法访问文件或研究宿主，请检查本地路径与宿主状态。")}, 503
            )

    def download(self, data):
        if set(data) != {"study", "source"}:
            raise WebError(tr("下载需要研究与资料引用。"))
        state = self.server.app.root / ".epivra"
        state.mkdir(parents=True, exist_ok=True)
        # One Host export per transfer; never decode the entire SQLite original
        # again for each HTTP chunk. This temporary copy has no persistent identity.
        with tempfile.TemporaryDirectory(
            prefix="web-download-", dir=state
        ) as directory:
            target = Path(directory) / "original.bin"
            self.server.app.send(
                {"action": "export", **data, "destination": str(target)}
            )
            with target.open("rb") as source:
                self.send_headers(target.stat().st_size, "application/octet-stream")
                while chunk := source.read(1024 * 1024):
                    self.wfile.write(chunk)

    def upload(self):
        from urllib.parse import parse_qs

        from .analysis import filename

        query = parse_qs(urlsplit(self.path).query, strict_parsing=True)
        name, study, expected = (query[k][0] for k in ("name", "study", "expected"))
        try:
            filename(name)
            if "/" in name:
                raise ValueError("upload requires one filename")
        except ValueError:
            raise WebError(tr("文件名无效。")) from None
        size = self.length(self.server.max_upload)
        state = self.server.app.root / ".epivra"
        state.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="web-upload-", dir=state) as directory:
            path = Path(directory) / name
            with path.open("xb") as output:
                remaining = size
                while remaining:
                    chunk = self.rfile.read(min(remaining, 1024 * 1024))
                    if not chunk:
                        raise WebError(tr("上传中断，资料未提交。"))
                    output.write(chunk)
                    remaining -= len(chunk)
                    self.unread = remaining
            result = self.server.app.call(
                {
                    "action": "import_file",
                    "study": study,
                    "expected": expected,
                    "path": str(path),
                }
            )
        self.reply(result)


def main(argv=None):
    language = configure(argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=tr("Epivra · 本地自主研究工作台"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--lang", choices=LANGUAGES, help="简体中文 / English")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--max-upload-mb", type=int, default=256)
    args = parser.parse_args(argv)
    if not 0 <= args.port <= 65535 or args.max_upload_mb <= 0:
        parser.error(tr("端口须为 0–65535，上传容量须为正数。"))
    try:
        server = Server(App(args.root), args.port, args.max_upload_mb * 1024 * 1024)
    except OSError:
        parser.error(
            tr("无法绑定本地端口，可能已有工作台运行；可用 --port 0 自动选择。")
        )
    try:
        ready = asyncio.run(host.start(args.root.resolve()))
        if ready.get("ready") is False:
            raise RuntimeError(tr("研究宿主仍在启动，请稍后重试。"))
        url = server.url + "&lang=" + language
        print(
            tr("Epivra 本地研究工作台：{0}\n关闭页面或此服务后，后台研究继续。", url),
            flush=True,
        )
        if not args.no_browser:
            webbrowser.open(url)
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        print(tr("\nWeb 工作台已关闭，研究宿主继续运行。"))
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
