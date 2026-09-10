"""Local single-owner research host and authenticated command-line client."""

from __future__ import annotations

import argparse
import asyncio
import json
import secrets
import sys
import uuid
from pathlib import Path

from .adapters import credentials
from .application import online_service
from .storage import Store


class Host:
    def __init__(self, root: Path, factory=None):
        self.root = root.resolve()
        self.state = self.root / ".deep-research-agent"
        self.store = Store(self.state / "research.db")
        self.factory = factory
        self.services = {}
        self.clients = []
        self.token = secrets.token_urlsafe(32)
        self.stopping = asyncio.Event()

    def service(self, study):
        if study not in self.services:
            self.store.control(study)
            if self.factory:
                service, clients = self.factory(self.store, study)
            else:
                service, clients = online_service(
                    self.store, study, credentials(self.root / ".env")
                )
            self.services[study] = service
            self.clients.extend(clients)
        return self.services[study]

    async def dispatch(self, request):
        if not secrets.compare_digest(str(request.get("token", "")), self.token):
            return {"error": "unauthorized"}
        action = request.get("action")
        if action == "shutdown":
            self.stopping.set()
            return {"stopping": True}
        if action == "list":
            studies = self.store.db.execute(
                "SELECT DISTINCT study FROM artifacts WHERE kind='control' ORDER BY study"
            ).fetchall()
            return {"studies": [r[0] for r in studies]}
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
            self.store.create(
                study,
                text,
                {
                    "network": request.get("web") is True,
                    "local_roots": resolved,
                    "stream_model": True,
                },
            )
            self.service(study).start(study)
            return {"study": study}
        study = request["study"]
        if not isinstance(study, str):
            raise ValueError("study must be text")
        if action == "control":
            result = self.store.command(
                study,
                request["command_id"],
                request["expected"],
                request["command"],
                request.get("payload"),
            )
            if not result.paused and not result.cancelled:
                self.service(study).start(study)
            return {
                "control": result.ref,
                "epoch": result.epoch,
                "paused": result.paused,
                "approved": result.approved,
            }
        if action == "status":
            return self.service(study).status(study)
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
        temporary = pointer.with_suffix(".tmp")
        try:
            server = await asyncio.start_server(
                self.connection, "127.0.0.1", 0, limit=65536
            )
            port = server.sockets[0].getsockname()[1]
            temporary.write_text(
                json.dumps({"port": port, "token": self.token}), encoding="utf-8"
            )
            temporary.replace(pointer)
            for row in self.store.db.execute(
                "SELECT DISTINCT study FROM artifacts WHERE kind='control'"
            ):
                study = row[0]
                c = self.store.control(study)
                if not c.paused and not c.cancelled:
                    self.service(study).start(study)
            async with server:
                await self.stopping.wait()
        finally:
            if server:
                server.close()
                await server.wait_closed()
            for service in self.services.values():
                await service.close()
            for client in self.clients:
                await client.close()
            self.store.close()
            pointer.unlink(missing_ok=True)
            temporary.unlink(missing_ok=True)


async def send(root: Path, request: dict):
    pointer = json.loads(
        (root / ".deep-research-agent/host.json").read_text(encoding="utf-8")
    )
    reader, writer = await asyncio.open_connection(
        "127.0.0.1", pointer["port"], limit=4 * 1024 * 1024
    )
    try:
        writer.write(
            (json.dumps({**request, "token": pointer["token"]}) + "\n").encode()
        )
        await writer.drain()
        return json.loads(await asyncio.wait_for(reader.readline(), 30))
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
    state = root / ".deep-research-agent"
    state.mkdir(parents=True, exist_ok=True)
    with (state / "host.log").open("ab") as log:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "deep_research_agent.host",
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
    create = sub.add_parser("create")
    create.add_argument("request")
    create.add_argument("--web", action="store_true")
    create.add_argument("--local-root", action="append", default=[])
    for action in ("status", "report"):
        sub.add_parser(action).add_argument("study")
    control = sub.add_parser("control")
    control.add_argument("study")
    control.add_argument(
        "command", choices=["approve", "pause", "resume", "steer", "cancel"]
    )
    control.add_argument("--expected", required=True)
    control.add_argument("--plan")
    control.add_argument("--request")
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        if args.action == "serve":
            asyncio.run(Host(root).serve())
            return
        if args.action == "start":
            print(json.dumps(asyncio.run(start(root))))
            return
        request = {"action": args.action}
        if args.action == "create":
            request.update(
                request=args.request, web=args.web, local_roots=args.local_root
            )
        elif args.action in ("status", "report", "control"):
            request["study"] = args.study
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
