"""MCP transports and explicit installation grants. No Agent loop or storage."""

import asyncio
import json
import os
import re
from contextlib import asynccontextmanager
from copy import deepcopy
from urllib.parse import urlsplit

from .domain import identity
from .local_security import protect_if_present


def servers(root):
    path = root / "mcp-servers.json"
    result = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if not isinstance(result, dict):
        raise ValueError("mcp-servers.json must contain an object")
    return result


def validate(name, config):
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,24}", name):
        raise ValueError("MCP connection name must be 1-24 letters, digits, _ or -")
    allowed = {
        "transport",
        "command",
        "args",
        "cwd",
        "url",
        "token_env",
        "env",
        "tools",
        "resources",
        "timeout",
    }
    if not isinstance(config, dict) or set(config) - allowed:
        raise ValueError("unknown MCP connection fields")
    transport = config.get("transport")
    if not isinstance(config.get("env", {}), dict) or not isinstance(
        config.get("tools", {}), dict
    ):
        raise ValueError("MCP env and tools must be objects")
    if transport == "stdio":
        if not isinstance(config.get("command"), str) or not config["command"]:
            raise ValueError("MCP stdio command required")
        if not isinstance(config.get("args", []), list) or not all(
            isinstance(x, str) for x in config.get("args", [])
        ):
            raise ValueError("MCP args must be a list of strings")
    elif transport == "http":
        url = urlsplit(config.get("url", ""))
        if (
            url.username
            or url.password
            or url.query
            or url.fragment
            or not url.hostname
        ):
            raise ValueError("MCP URL must not contain credentials, query or fragment")
        if url.scheme != "https" and not (
            url.scheme == "http" and url.hostname in {"localhost", "127.0.0.1", "::1"}
        ):
            raise ValueError("remote MCP requires HTTPS")
    else:
        raise ValueError("MCP transport must be stdio or http")
    names = [
        *config.get("env", {}).values(),
        *([config["token_env"]] if config.get("token_env") else []),
    ]
    if not all(
        isinstance(n, str) and re.fullmatch(r"[A-Z_][A-Z0-9_]*", n) for n in names
    ):
        raise ValueError("MCP credentials must reference environment variable names")
    timeout = config.get("timeout", 120)
    if type(timeout) not in {int, float} or not 0 < timeout < float("inf"):
        raise ValueError("MCP timeout must be finite and positive")
    for grant in config.get("tools", {}).values():
        if isinstance(grant, dict) and grant.get("result_contract") not in (
            None,
            "knowledge-v1",
        ):
            raise ValueError("unsupported MCP result contract")
        if not isinstance(grant, dict) or type(grant.get("write")) is not bool:
            raise ValueError("each MCP tool needs an explicit write true/false grant")
        if (
            not isinstance(grant.get("roles"), list)
            or not grant.get("roles")
            or set(grant["roles"])
            - {
                "investigator",
                "synthesizer",
                "writer",
                "reviewer",
            }
        ):
            raise ValueError("MCP tool roles must be explicitly assigned")
    if not isinstance(config.get("resources", []), list) or not all(
        isinstance(uri, str) for uri in config.get("resources", [])
    ):
        raise ValueError("MCP resources must be exact URI strings")
    return config


def secret(root, name):
    if name in os.environ:
        return os.environ[name]
    path = root / ".env"
    for line in (
        path.read_text(encoding="utf-8") if protect_if_present(path) else ""
    ).splitlines():
        if not line.lstrip().startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            if key.strip() == name:
                return value.strip().strip("\"'")
    raise ValueError("MCP credential variable is not configured: " + name)


@asynccontextmanager
async def connection(config, root):
    from mcp import Client, StdioServerParameters

    if config["transport"] == "stdio":
        # SDK also merges a minimal OS environment, never the whole parent env.
        env = {
            target: secret(root, source)
            for target, source in config.get("env", {}).items()
        }
        transport = StdioServerParameters(
            command=config["command"],
            args=config.get("args", []),
            env=env,
            cwd=config.get("cwd") or str(root),
        )
        async with Client(
            transport, read_timeout_seconds=config.get("timeout", 120)
        ) as client:
            yield client
    else:
        import httpx2
        from mcp.client.streamable_http import streamable_http_client

        headers = (
            {"Authorization": "Bearer " + secret(root, config["token_env"])}
            if config.get("token_env")
            else {}
        )
        async with httpx2.AsyncClient(
            headers=headers, follow_redirects=False, timeout=config.get("timeout", 120),
            trust_env=urlsplit(config["url"]).hostname not in {"localhost", "127.0.0.1", "::1"},
        ) as http:
            async with Client(
                streamable_http_client(config["url"], http_client=http),
                read_timeout_seconds=config.get("timeout", 120),
            ) as client:
                yield client


async def pages(method, field):
    values, cursor, seen = [], None, set()
    size = 0
    while True:
        page = await method(cursor=cursor)
        for value in getattr(page, field):
            size += len(value.model_dump_json().encode("utf-8"))
            if size > 16 * 1024 * 1024 or len(values) >= 10000:
                raise ValueError("MCP catalog exceeds single-discovery capacity")
            values.append(value)
        cursor = page.next_cursor
        if not cursor:
            return values
        if cursor in seen:
            raise ValueError("MCP pagination cursor repeated")
        seen.add(cursor)
        if len(seen) >= 1000:
            raise ValueError("MCP catalog exceeds pagination capacity")


async def catalog(config, root):
    async with asyncio.timeout(config.get("timeout", 120)):
        async with connection(config, root) as client:
            tools = (
                await pages(client.list_tools, "tools")
                if client.server_capabilities.tools
                else []
            )
            resources = (
                await pages(client.list_resources, "resources")
                if client.server_capabilities.resources
                else []
            )
            return {
                "tools": [
                    t.model_dump(mode="json", by_alias=True, exclude_none=True)
                    for t in tools
                ],
                "resources": [
                    r.model_dump(mode="json", by_alias=True, exclude_none=True)
                    for r in resources
                ],
                "protocol": client.protocol_version,
            }


async def freeze(root, names):
    configured = servers(root)
    if not isinstance(names, list) or len(set(names)) != len(names):
        raise ValueError("MCP connections must be distinct names")
    frozen = {}
    for name in names:
        if name not in configured:
            raise ValueError("unknown MCP connection")
        config = validate(name, configured[name])
        found = await catalog(config, root)
        selected = [t for t in found["tools"] if t["name"] in config.get("tools", {})]
        if len(selected) != len(config.get("tools", {})):
            raise ValueError("an authorized MCP tool is missing")
        frozen[name] = {"connection": config, "definitions": selected}
    return frozen


def alias(server, tool):
    return "mcp_" + server + "_" + identity(tool)[:16]


@asynccontextmanager
async def borrowed(client):
    yield client


async def prepare(config, definition, args, resource, client):
    """Validate discovery before a caller reserves quota or admits a send."""
    from mcp import types

    if resource:
        if args["uri"] not in config.get("resources", []):
            raise ValueError("resource URI not authorized")
        return types.ReadResourceRequest(
            params=types.ReadResourceRequestParams(uri=args["uri"])
        )
    tools = await pages(client.list_tools, "tools")
    current = next(
        (tool.model_dump(mode="json", by_alias=True, exclude_none=True)
         for tool in tools if tool.name == definition["name"]), None
    )
    if current != definition:
        raise ValueError(
            "MCP tool definition changed; create a newly authorized research configuration"
        )
    return types.CallToolRequest(
        params=types.CallToolRequestParams(name=definition["name"], arguments=args)
    )


async def execute(root, config, definition, args, resource=False, client=None, prepared=None):
    from mcp import types
    from mcp.shared.exceptions import MCPError
    from pydantic import TypeAdapter

    sent = False
    completed = None
    try:
        async with asyncio.timeout(config.get("timeout", 120)):
            async with (
                borrowed(client) if client is not None else connection(config, root)
            ) as client:
                request = prepared if prepared is not None else await prepare(
                    config, definition, args, resource, client
                )
                sent = True
                # The SDK's convenience call validates outputSchema before returning.
                # Receive the protocol result unchanged so the ledger saves it first.
                try:
                    completed = await client.session.send_request(
                        request, TypeAdapter(dict)
                    )
                except MCPError as exc:
                    if exc.code in {types.CONNECTION_CLOSED, types.REQUEST_TIMEOUT}:
                        raise
                    completed = {
                        "isError": True,
                        "protocol_error": exc.error.model_dump(
                            mode="json", by_alias=True
                        ),
                        "content": [],
                    }
        return completed
    except Exception as exc:
        if completed is not None:
            return completed
        if sent:
            # May have executed a remote write. The existing ledger retains unknown.
            raise RuntimeError(
                "MCP outcome unknown; do not automatically resend"
            ) from None
        return {
            "isError": True,
            "content": [
                {"type": "text", "text": "MCP request not sent: " + type(exc).__name__}
            ],
        }


class MCPConnection:
    """Own session lifetime; lend a prepared exclusive turn before admission.

    SDK context entry/exit stays in one owner task. Calls execute in the task
    holding the turn, without a second queue between admission and dispatch.
    """

    credential_env = None

    def __init__(self, root, config):
        self.root, self.config = root, config
        self.lock = asyncio.Lock()
        self.task = None
        self.ready = None
        self.closed = False
        self.resetting = False
        self.generation = 0
        self.prepared = {}

    async def _owner(self, ready):
        try:
            async with connection(self.config, self.root) as client:
                ready.set_result(client)
                await asyncio.Future()  # The owner is closed explicitly.
        except Exception:
            pass  # No operation has been admitted during connection setup.
        finally:
            if not ready.done():
                ready.set_result(None)

    def _session(self):
        if self.task is None or self.task.done():
            self.ready = asyncio.get_running_loop().create_future()
            self.task = asyncio.create_task(self._owner(self.ready))
        return self.ready

    @staticmethod
    async def _checked(future, check):
        while not future.done():
            check()
            await asyncio.wait({future}, timeout=0.25)
        check()
        return future.result()

    @asynccontextmanager
    async def turn(self, definition, args, resource=False, *, check):
        """Wait/discover cooperatively, with no quota or durable operation yet."""
        owner = asyncio.current_task()
        generation = self.generation
        if owner in self.prepared:
            raise RuntimeError("MCP turn is already held by this task")

        def allowed():
            check()
            if self.closed or self.resetting or generation != self.generation:
                raise ValueError("MCP connection is closed; request not sent")

        acquiring = asyncio.create_task(self.lock.acquire())
        preparation = None
        try:
            await self._checked(acquiring, allowed)
            async with asyncio.timeout(self.config.get("timeout", 120)):
                client = await self._checked(self._session(), allowed)
                if client is None:
                    raise ValueError("MCP session unavailable; request not sent")
                preparation = asyncio.create_task(
                    prepare(self.config, definition, args, resource, client)
                )
                request = await self._checked(preparation, allowed)
            self.prepared[owner] = (client, request, deepcopy((definition, args, resource)))
            yield
        finally:
            self.prepared.pop(owner, None)
            cleanup = []
            if preparation is not None and not preparation.done():
                preparation.cancel()
                cleanup.append(preparation)
            if not acquiring.done():
                acquiring.cancel()
                cleanup.append(acquiring)
            if not acquiring.cancelled() and acquiring.done() and acquiring.result():
                self.lock.release()
            if cleanup:
                await asyncio.gather(*cleanup, return_exceptions=True)

    async def invoke(self, definition, args, resource=False, *, receive=None):
        held = self.prepared.get(asyncio.current_task())
        if held is None or held[2] != (definition, args, resource):
            raise ValueError("MCP invocation requires its exact prepared turn")
        client, request, _ = held
        value = await execute(
            self.root, self.config, definition, args, resource, client, prepared=request
        )
        if receive is not None:
            receive(value)
        return value

    async def _stop(self):
        if self.task:
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)

    async def reset(self):
        """Reload credentials in a fresh session; invalidate older waiters."""
        if self.closed:
            raise ValueError("MCP connection is closed")
        self.generation += 1
        self.resetting = True
        try:
            await self._stop()
        finally:
            self.resetting = False

    async def close(self):
        self.closed = True
        self.generation += 1
        await self._stop()
