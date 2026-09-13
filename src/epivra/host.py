"""Local single-owner research host and authenticated command-line client."""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import secrets
import sys
import uuid
from pathlib import Path

from .adapters import credentials
from .analysis import settings as analysis_settings
from .analysis_runtime import AnalysisRuntime
from .application import online_service
from .model_catalog import OFFICIAL_PROVIDERS
from .models import freeze_model_settings
from .scheduling import Scheduler
from .storage import Store
from .usage import summarize
from .web_providers import CONNECTIONS, READERS, SEARCH
from .workspace import Workspace


class Host:
    def __init__(self, root: Path, factory=None):
        self.root = root.resolve()
        self.state = self.root / ".epivra"
        self.store = Store(self.state / "research.db")
        try:
            limits_path = self.root / "provider-limits.json"
            limits = (
                json.loads(limits_path.read_text(encoding="utf-8"))
                if limits_path.exists()
                else {}
            )
            self.scheduler = Scheduler(limits=limits, history=self.store.admissions())
            for row in self.store.db.execute(
                "SELECT DISTINCT study FROM artifacts WHERE kind IN ('retry', 'cooldown')"
            ):
                for artifact in self.store.list(row[0], "retry") + self.store.list(
                    row[0], "cooldown"
                ):
                    retry = artifact.body
                    if "resource" in retry:
                        self.scheduler.defer(retry["resource"], retry["not_before"])
        except BaseException:
            self.store.close()
            raise
        self.factory = factory
        self.services = {}
        self.failures = {}
        self.clients = {}
        self.token = secrets.token_urlsafe(32)
        self.stopping = asyncio.Event()
        self.analysis_errors = {}

    async def maintain_analyses(self):
        while not self.stopping.is_set():
            for row in self.store.db.execute(
                "SELECT DISTINCT study FROM artifacts WHERE kind='analysis_job'"
            ).fetchall():
                study = row[0]
                service = self.services.get(study)
                task = service.tasks.get(study) if service else None
                if task and not task.done():
                    continue
                try:
                    await AnalysisRuntime(self.store).reconcile(study)
                    self.analysis_errors.pop(study, None)
                except (ValueError, OSError, TimeoutError) as exc:
                    self.analysis_errors[study] = str(exc)
            try:
                await asyncio.wait_for(self.stopping.wait(), 5)
            except TimeoutError:
                pass

    def service(self, study):
        if study not in self.services:
            self.store.control(study)
            if self.factory:
                service, clients = self.factory(self.store, study)
            else:
                service, clients = online_service(
                    self.store,
                    study,
                    credentials(self.root / ".env"),
                    scheduler=self.scheduler,
                )
            self.services[study] = service
            self.clients[study] = clients
            self.failures.pop(study, None)
        return self.services[study]

    def start_study(self, study):
        try:
            self.service(study).start(study)
        except Exception as exc:
            self.failures[study] = type(exc).__name__

    async def dispatch(self, request):
        if not secrets.compare_digest(str(request.get("token", "")), self.token):
            return {"error": "unauthorized"}
        action = request.get("action")
        if action in {"mcp_connections", "mcp_discover"}:
            from .mcp_client import catalog, servers, validate

            configured = servers(self.root)
            if action == "mcp_connections":
                return {"servers": list(configured)}
            name = request["name"]
            return await catalog(validate(name, configured[name]), self.root)
        if action == "shutdown":
            self.stopping.set()
            return {"stopping": True}
        if action == "list":
            studies = self.store.db.execute(
                "SELECT DISTINCT study FROM artifacts WHERE kind='control' ORDER BY study"
            ).fetchall()
            return {"studies": [r[0] for r in studies]}
        if action == "overview":
            studies = self.store.db.execute(
                "SELECT study, MAX(rowid) AS recent FROM artifacts "
                "WHERE kind='control' GROUP BY study ORDER BY recent DESC"
            ).fetchall()
            return {"studies": [self.describe(row[0]) for row in studies]}
        if action == "create":
            text = request.get("request")
            if not isinstance(text, str) or not text.strip():
                raise ValueError("request required")
            roots = request.get("local_roots", [])
            if not isinstance(roots, list) or not all(
                isinstance(r, str) for r in roots
            ):
                raise ValueError("local_roots must be a list of paths")
            resolved = []
            for root in roots:
                directory = Path(root).resolve(strict=True)
                if not directory.is_dir():
                    raise ValueError("local root is not a directory")
                resolved.append(str(directory))
            study = uuid.uuid4().hex
            policy = {
                "network": request.get("web") is True,
                "local_roots": resolved,
                "provider": request.get("provider", "deepseek"),
                **{
                    name: request[name]
                    for name in ("model", "region", "context_tokens", "max_tokens")
                    if request.get(name) is not None
                },
            }
            policy = freeze_model_settings(policy)
            if request.get("mcp_servers"):
                from .mcp_client import freeze

                policy["mcp"] = await freeze(self.root, request["mcp_servers"])
            if request.get("analysis"):
                path = self.root / "analysis-settings.json"
                overrides = (
                    json.loads(path.read_text(encoding="utf-8"))
                    if path.exists()
                    else {}
                )
                policy["analysis"] = await analysis_settings(overrides)
            if policy["network"]:
                keys = credentials(self.root / ".env")
                available = [
                    n
                    for n in SEARCH
                    if n == "duckduckgo" or keys.get(CONNECTIONS[n][1])
                ]
                readable = [
                    n for n in READERS if n == "jina" or keys.get(CONNECTIONS[n][1])
                ]
                primary = request.get("search_provider") or (
                    "tavily" if "tavily" in available else "duckduckgo"
                )
                reader = request.get("reader_provider") or "jina"
                if primary not in available or reader not in readable:
                    raise ValueError(
                        "selected search/reader provider requires its credential"
                    )
                policy.update(
                    search_providers=[primary, *[n for n in available if n != primary]],
                    reader_providers=[reader, *[n for n in readable if n != reader]],
                )
            else:
                policy.update(search_providers=[], reader_providers=[])
            policy["parsing"] = {
                "parser": request.get("parser", "auto"),
                "artifacts_path": request.get("docling_models")
                or (
                    "models/docling"
                    if (self.root / "models/docling").is_dir()
                    else None
                ),
                "timeout": request.get("parse_timeout", 300),
            }
            if policy["parsing"]["parser"] not in {"auto", "light", "docling"}:
                raise ValueError("unknown parser mode")
            if policy["parsing"]["artifacts_path"] is not None:
                models = Path(policy["parsing"]["artifacts_path"])
                models = (self.root / models).resolve()
                if not models.is_dir():
                    raise ValueError("Docling model directory does not exist")
                policy["parsing"]["artifacts_path"] = str(models)
            if type(policy["parsing"]["timeout"]) not in (int, float) or not 0 < policy[
                "parsing"
            ]["timeout"] < float("inf"):
                raise ValueError("positive finite parse timeout required")
            created = self.store.create(
                study,
                text,
                policy,
            )
            if request.get("draft"):
                self.store.command(study, "draft", created.ref, "pause")
            else:
                self.start_study(study)
            return {"study": study}
        study = request["study"]
        if not isinstance(study, str):
            raise ValueError("study must be text")
        if action == "usage":
            self.store.control(study)
            return {"calls": self.store.usage_records(study)}
        if action == "sources":
            self.store.control(study)
            return {
                "sources": [
                    {
                        "ref": s.ref,
                        "origin": s.body.get("origin"),
                        "coverage": s.body.get("coverage"),
                    }
                    for s in self.store.list(study, "source")
                ]
            }
        if action == "download":
            offset, length = request.get("offset", 0), request.get("length", 65536)
            if (
                type(offset) is not int
                or offset < 0
                or type(length) is not int
                or not 0 < length <= 262144
            ):
                raise ValueError("invalid download range")
            raw = Workspace(self.store).original(study, request["source"])
            return {
                "data": base64.b64encode(raw[offset : offset + length]).decode("ascii"),
                "offset": offset,
                "total": len(raw),
                "next_offset": min(offset + length, len(raw)),
            }
        if action == "export":
            raw = Workspace(self.store).original(study, request["source"])
            target = Path(request["destination"]).expanduser().resolve()
            with target.open("xb") as stream:
                stream.write(raw)
            return {"path": str(target), "bytes": len(raw)}
        if action in {"upload", "import_file"}:
            control = self.store.control(study)
            service = self.services.get(study)
            task = service.tasks.get(study) if service else None
            if control.cancelled or (
                control.approved and (not control.paused or (task and not task.done()))
            ):
                raise ValueError("pause approved research and wait before uploading")
            if action == "import_file":
                path = Path(request["path"]).expanduser().resolve(strict=True)
                if not path.is_file():
                    raise ValueError("selected path is not a file")
                name, raw = path.name, await asyncio.to_thread(path.read_bytes)
            else:
                name = request["name"]
                raw = base64.b64decode(request["data"], validate=True)
            source = await Workspace(self.store).upload_async(
                study,
                request["expected"],
                name,
                raw,
            )
            return {
                "source": source.ref,
                "coverage": source.body["coverage"],
                "issues": source.body["issues"],
                "characters": len(source.body["text"]),
            }
        if action in {"reload", "reconcile"}:
            control = self.store.control(study)
            service = self.services.get(study)
            task = service.tasks.get(study) if service else None
            if not control.paused or (task and not task.done()):
                raise ValueError("pause research and wait for in-flight work to finish")
            if action == "reconcile":
                receipt = self.store.reconcile(
                    study,
                    request["expected"],
                    request["operation"],
                    request["receipt_id"],
                    request["result"],
                    request["evidence"],
                )
                return {"receipt": receipt.ref, "paused": True}
            keys = credentials(self.root / ".env")
            policy = self.store.get(study, control.direction).body["policy"]
            updates = [
                (client, keys.get(client.credential_env, ""))
                for client in self.clients.get(study, [])
                if client.credential_env
                and (client.credential_env != "TAVILY_API_KEY" or policy.get("network"))
                and (
                    client.credential_env != "JINA_API_KEY" or keys.get("JINA_API_KEY")
                )
            ]
            if any(not key.strip() for _, key in updates):
                raise ValueError("credential required")
            for client, key in updates:
                client.replace_key(key)
            from .mcp_client import MCPConnection

            for client in self.clients.get(study, []):
                if isinstance(client, MCPConnection):
                    await client.close()
            return {"reloaded": True}
        if action == "control":
            result = self.store.command(
                study,
                request["command_id"],
                request["expected"],
                request["command"],
                request.get("payload"),
            )
            if not result.paused and not result.cancelled:
                self.start_study(study)
            return {
                "control": result.ref,
                "epoch": result.epoch,
                "paused": result.paused,
                "approved": result.approved,
            }
        if action == "status":
            service = self.services.get(study)
            return {
                **(service.status(study) if service else {}),
                **self.describe(study),
                "unsettled_operations": self.store.unsettled(study),
                "usage": summarize(self.store.usage_records(study)),
                "analyses": [a.body for a in self.store.list(study, "analysis_result")],
                "analysis_cleanup_error": self.analysis_errors.get(study),
            }
        if action == "report":
            direction = self.store.control(study).direction
            pubs = [
                p
                for p in self.store.list(study, "publication")
                if direction in p.parents
            ]
            if not pubs:
                return {"report": None}
            report = self.store.get(study, pubs[-1].body["report"])
            sources = [self.store.get(study, ref) for ref in report.body["evidence"]]
            return {
                "ref": report.ref,
                "text": report.body["text"],
                "sources": [
                    {"ref": s.ref, "origin": s.body.get("origin")} for s in sources
                ],
            }
        raise ValueError("unknown host command")

    def describe(self, study):
        c = self.store.control(study)
        direction = self.store.get(study, c.direction)
        service = self.services.get(study)
        task = service.tasks.get(study) if service else None
        plans = [a for a in self.store.list(study, "plan") if c.direction in a.parents]
        published = any(
            c.direction in a.parents for a in self.store.list(study, "publication")
        )
        return {
            "study": study,
            "request": direction.body["request"],
            "control": c.ref,
            "approved": c.approved,
            "paused": c.paused,
            "cancelled": c.cancelled,
            "running": bool(task and not task.done()),
            "published": published,
            "error": self.failures.get(study)
            or (service.errors.get(study) if service else None),
            "plans": [{"ref": a.ref, "body": a.body} for a in plans],
            "policy": direction.body["policy"],
            "source_count": len(self.store.list(study, "source")),
            "work": [
                {"role": a.body["role"], "task": a.body["task"]}
                for a in self.store.list(study, "work")
                if a.body["direction"] == c.direction
            ],
        }

    async def connection(self, reader, writer):
        try:
            line = await asyncio.wait_for(reader.readline(), 10)
            request = json.loads(line)
            if not isinstance(request, dict):
                raise ValueError("expected object")
            result = await self.dispatch(request)
        except Exception as exc:
            result = {"error": type(exc).__name__}
        try:
            writer.write((json.dumps(result, ensure_ascii=False) + "\n").encode())
            await writer.drain()
        except (ConnectionError, OSError):
            pass
        finally:
            writer.close()
            await writer.wait_closed()

    async def serve(self):
        pointer = self.state / "host.json"
        server = None
        maintenance = None
        temporary = pointer.with_suffix(".tmp")
        try:
            server = await asyncio.start_server(
                self.connection, "127.0.0.1", 0, limit=4 * 1024 * 1024
            )
            port = server.sockets[0].getsockname()[1]
            temporary.write_text(
                json.dumps({"port": port, "token": self.token}), encoding="utf-8"
            )
            temporary.replace(pointer)
            maintenance = asyncio.create_task(self.maintain_analyses())
            for row in self.store.db.execute(
                "SELECT DISTINCT study FROM artifacts WHERE kind='control'"
            ):
                study = row[0]
                c = self.store.control(study)
                if not c.paused and not c.cancelled:
                    self.start_study(study)
            async with server:
                await self.stopping.wait()
        finally:
            if maintenance:
                maintenance.cancel()
                await asyncio.gather(maintenance, return_exceptions=True)
            if server:
                server.close()
                await server.wait_closed()
            for service in self.services.values():
                await service.close()
            for clients in self.clients.values():
                for client in clients:
                    await client.close()
            self.store.close()
            pointer.unlink(missing_ok=True)
            temporary.unlink(missing_ok=True)


async def send(root: Path, request: dict):
    pointer = json.loads((root / ".epivra/host.json").read_text(encoding="utf-8"))
    reader, writer = await asyncio.open_connection(
        "127.0.0.1", pointer["port"], limit=4 * 1024 * 1024
    )
    try:
        writer.write(
            (json.dumps({**request, "token": pointer["token"]}) + "\n").encode()
        )
        await writer.drain()
        # Parsing has its own configured timeout. Losing a client must not imply failure.
        timeout = 600 if request.get("action") in {"upload", "import_file"} else 30
        return json.loads(await asyncio.wait_for(reader.readline(), timeout))
    finally:
        writer.close()
        await writer.wait_closed()


async def start(root: Path):
    import os
    import subprocess
    import threading

    async def available():
        try:
            reply = await asyncio.wait_for(send(root, {"action": "list"}), 1)
            return "studies" in reply
        except (OSError, ValueError, KeyError, TimeoutError):
            return False

    if await available():
        return {"already_running": True}
    state = root / ".epivra"
    state.mkdir(parents=True, exist_ok=True)
    with (state / "host.log").open("ab") as log:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "epivra.host",
                "--root",
                str(root),
                "serve",
            ],
            cwd=root,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=log,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            start_new_session=os.name != "nt",
        )
    # Reap our child while this client lives, without tying host lifetime to it.
    threading.Thread(target=process.wait, daemon=True).start()
    for _ in range(100):
        if await available():
            return {"ready": True, "started_pid": process.pid}
        if process.poll() is not None:
            raise RuntimeError("host exited before becoming ready")
        await asyncio.sleep(0.05)
    return {"ready": False, "starting_pid": process.pid}


def main():
    parser = argparse.ArgumentParser(description="Local research host and client")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("serve")
    sub.add_parser("start")
    sub.add_parser("shutdown")
    sub.add_parser("list")
    sub.add_parser("providers")
    sub.add_parser("mcp-connections")
    sub.add_parser("mcp-discover").add_argument("name")
    create = sub.add_parser("create")
    create.add_argument("request")
    create.add_argument("--web", action="store_true")
    create.add_argument("--local-root", action="append", default=[])
    create.add_argument(
        "--provider", choices=sorted(OFFICIAL_PROVIDERS), default="deepseek"
    )
    create.add_argument("--model")
    create.add_argument("--region")
    create.add_argument("--context-tokens", type=int)
    create.add_argument("--max-tokens", type=int)
    create.add_argument("--search-provider", choices=SEARCH)
    create.add_argument("--reader-provider", choices=READERS)
    create.add_argument(
        "--parser", choices=("auto", "light", "docling"), default="auto"
    )
    create.add_argument("--docling-models")
    create.add_argument("--parse-timeout", type=float, default=300)
    create.add_argument("--analysis", action="store_true")
    create.add_argument("--mcp-server", action="append", default=[])
    export = sub.add_parser("export")
    export.add_argument("study")
    export.add_argument("source")
    export.add_argument("destination", type=Path)
    for action in ("status", "report", "reload", "usage"):
        sub.add_parser(action).add_argument("study")
    control = sub.add_parser("control")
    control.add_argument("study")
    control.add_argument(
        "command", choices=["approve", "pause", "resume", "steer", "cancel"]
    )
    control.add_argument("--expected", required=True)
    control.add_argument("--plan")
    control.add_argument("--request")
    reconcile = sub.add_parser("reconcile")
    reconcile.add_argument("study")
    reconcile.add_argument("operation")
    reconcile.add_argument("--expected", required=True)
    reconcile.add_argument("--receipt-id", required=True)
    reconcile.add_argument("--response-file", type=Path, required=True)
    reconcile.add_argument("--evidence", required=True)
    upload = sub.add_parser("upload")
    upload.add_argument("study")
    upload.add_argument("file", type=Path)
    upload.add_argument("--expected", required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        if args.action == "providers":
            print(
                json.dumps(
                    [
                        {
                            "provider": spec.id,
                            "credential_env": spec.credential_env,
                            "model": spec.default_model.id,
                            "protocol": spec.protocol,
                            "regions": dict(spec.endpoints),
                            "default_region": spec.default_region,
                            "notes": spec.notes,
                        }
                        for spec in OFFICIAL_PROVIDERS.values()
                    ],
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return
        if args.action == "serve":
            asyncio.run(Host(root).serve())
            return
        if args.action == "start":
            print(json.dumps(asyncio.run(start(root))))
            return
        request = {"action": args.action}
        if args.action in {"mcp-connections", "mcp-discover"}:
            request["action"] = args.action.replace("-", "_")
            if args.action == "mcp-discover":
                request["name"] = args.name
        if args.action == "create":
            request.update(
                request=args.request, web=args.web, local_roots=args.local_root
            )
            request["mcp_servers"] = args.mcp_server
            request.update(
                {
                    name: getattr(args, name)
                    for name in (
                        "provider",
                        "model",
                        "region",
                        "context_tokens",
                        "max_tokens",
                        "search_provider",
                        "reader_provider",
                        "parser",
                        "docling_models",
                        "parse_timeout",
                        "analysis",
                    )
                    if getattr(args, name) is not None
                }
            )
        elif args.action in (
            "status",
            "report",
            "control",
            "reload",
            "usage",
            "reconcile",
            "upload",
            "export",
        ):
            request["study"] = args.study
        if args.action == "export":
            request.update(
                source=args.source, destination=str(args.destination.resolve())
            )
        if args.action == "upload":
            raw = args.file.read_bytes()
            if len(raw) > 3 * 1024 * 1024 - 8192:
                raise ValueError(
                    "file exceeds upload IPC limit; authorize its directory instead"
                )
            request.update(
                expected=args.expected,
                name=args.file.name,
                data=base64.b64encode(raw).decode("ascii"),
            )
        if args.action == "reconcile":
            request.update(
                operation=args.operation,
                expected=args.expected,
                receipt_id=args.receipt_id,
                evidence=args.evidence,
                result=json.loads(args.response_file.read_text(encoding="utf-8")),
            )
        if args.action == "control":
            payload = {}
            if args.plan:
                payload["plan"] = args.plan
            if args.request:
                payload["request"] = args.request
            request.update(
                command=args.command,
                expected=args.expected,
                payload=payload,
                command_id=uuid.uuid4().hex,
            )
        print(
            json.dumps(asyncio.run(send(root, request)), ensure_ascii=False, indent=2)
        )
    except Exception as exc:
        print(json.dumps({"error": type(exc).__name__}))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
