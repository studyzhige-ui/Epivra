import asyncio
import base64
import json
import os
import socket
import sys
import tempfile
import unittest
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import AsyncMock, patch

try:
    from mcp import Client, StdioServerParameters
    from mcp.server import MCPServer
except ImportError:
    raise unittest.SkipTest(
        "install optional .[mcp] dependencies for MCP integration tests"
    )

from epivra.domain import Call, Reply
from epivra.harness import Harness
from epivra.host import Host, send, start
from epivra.mcp_client import (
    MCPConnection,
    alias,
    catalog,
    execute,
    freeze,
    validate,
)
from epivra.mcp_server import Bearer, build
from epivra.mcp_tools import connect_tools
from epivra.storage import Store
from epivra.workspace import Workspace


class MCPTests(unittest.IsolatedAsyncioTestCase):
    async def test_cancelled_consumer_keeps_received_response_in_ledger(self):
        from epivra.domain import identity
        from epivra.harness import Tool

        store = Store(self.root / "cancelled.db")
        c = store.create("cancel", "Inspect", {})
        p = store.put("cancel", "plan", {"text": "Inspect"}, (c.direction,))
        c = store.command("cancel", "approve", c.ref, "approve", {"plan": p.ref})
        lead = store.work("cancel", c.ref, "lead", "Coordinate")
        work = store.work("cancel", c.ref, "investigator", "Inspect", (), lead.ref)
        connection = MCPConnection(self.root, self.config)
        raw = {"content": [{"type": "text", "text": "paid original"}]}

        @asynccontextmanager
        async def session(*args):
            yield object()

        count = 0

        async def execute_and_cancel(*args):
            nonlocal count
            count += 1
            consumer.cancel()
            return raw

        async def invoke(args):
            return await connection.invoke({}, args)

        async def received(args, receive):
            return await connection.invoke({}, args, receive=receive)

        class Model:
            context_tokens = 49024
            max_tokens = 1024
            identity = "cancel-fixture"

            async def complete(self, request):
                return Reply("", (Call("lookup", {}),)).to_json()

        tool = Tool(
            "lookup",
            {"type": "object", "properties": {}, "required": []},
            invoke,
            invoke_received=received,
            roles=("investigator",),
        )
        try:
            with (
                patch("epivra.mcp_client.connection", session),
                patch("epivra.mcp_client.execute", execute_and_cancel),
            ):
                harness = Harness(store, Model(), {"lookup": tool})
                consumer = asyncio.create_task(harness.step("cancel", work.ref))
                with self.assertRaises(asyncio.CancelledError):
                    await consumer
                step = store.related("cancel", "step", work.ref)[-1]
                operation = identity("tool", step.ref, 0)
                self.assertEqual(
                    "succeeded",
                    store.db.execute(
                        "SELECT status FROM operations WHERE id=?", (operation,)
                    ).fetchone()[0],
                )
                await connection.close()
                store.close()
                store = Store(self.root / "cancelled.db")
                await Harness(store, Model(), {"lookup": tool}).step("cancel", work.ref)
                self.assertEqual(1, count)
                self.assertFalse(store.unsettled("cancel"))
        finally:
            await connection.close()
            store.close()

    async def test_full_schema_reaches_harness_and_invalid_arguments_do_not_send(self):
        from mcp import types

        shapes = [
            ({"type": "number"}, 1.5, "bad"),
            ({"type": ["string", "null"]}, None, 7),
            ({"$ref": "#/$defs/value"}, 1.5, "bad"),
            (
                {"type": "object", "additionalProperties": {"type": "number"}},
                {"extra": 1.5},
                {"extra": "bad"},
            ),
            ({"enum": ["yes", 7]}, 7, "no"),
        ]
        for index, (shape, good, bad) in enumerate(shapes):
            with self.subTest(shape=shape):
                schema = {
                    "type": "object",
                    "properties": {"value": shape},
                    "required": ["value"],
                    "additionalProperties": False,
                    "$defs": {"value": {"type": "number"}},
                }
                definition = {"name": "lookup", "inputSchema": schema}
                client = AsyncMock()
                client.list_tools.return_value = types.ListToolsResult(
                    tools=[types.Tool.model_validate(definition)]
                )
                client.session.send_request.return_value = {
                    "content": [{"type": "text", "text": "original evidence"}]
                }

                @asynccontextmanager
                async def connection(config, root):
                    yield client

                store = Store(self.root / f"schema-{index}.db")
                connections = []
                try:
                    frozen = {
                        "test": {"connection": self.config, "definitions": [definition]}
                    }
                    c = store.create("s", "Check schema", {"mcp": frozen})
                    plan = store.put("s", "plan", {"text": "plan"}, (c.direction,))
                    c = store.command(
                        "s", "approve", c.ref, "approve", {"plan": plan.ref}
                    )
                    lead = store.work("s", c.ref, "lead", "coordinate")
                    work = store.work(
                        "s", c.ref, "investigator", "lookup", (), lead.ref
                    )
                    name = alias("test", "tool:lookup")

                    class Model:
                        context_tokens = 49024
                        max_tokens = 1024
                        identity = "schema-fixture"
                        value = good

                        async def complete(inner, request):
                            self.assertEqual(
                                schema, request["tools"][name]["parameters"]
                            )
                            return Reply(
                                "", (Call(name, {"value": inner.value}),)
                            ).to_json()

                    model = Model()
                    tools, connections = connect_tools(store, "s", {"mcp": frozen})
                    with patch("epivra.mcp_client.connection", connection):
                        harness = Harness(store, model, tools)
                        await harness.step("s", work.ref)
                        self.assertEqual(1, client.session.send_request.await_count)
                        self.assertEqual(1, store.count("s", "source"))
                        model.value = bad
                        await harness.step("s", work.ref)
                        self.assertEqual(1, client.session.send_request.await_count)
                        self.assertIn(
                            "error", store.list("s", "observation")[-1].body["result"]
                        )
                finally:
                    for item in connections:
                        await item.close()
                    store.close()

    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.server = MCPServer("fixture")
        self.calls = 0

        @self.server.tool(structured_output=True)
        def lookup(query: str) -> dict[str, object]:
            """Return a source record."""
            self.calls += 1
            return {"text": "原始证据", "query": query}

        @self.server.resource("fixture://material")
        def resource() -> str:
            return "original material"

        @asynccontextmanager
        async def connection(config, root):
            async with Client(self.server) as client:
                yield client

        self.patch = patch("epivra.mcp_client.connection", connection)
        self.patch.start()
        self.config = {
            "transport": "stdio",
            "command": "fixture",
            "tools": {"lookup": {"write": False, "roles": ["investigator"]}},
            "resources": ["fixture://material"],
        }
        (self.root / "mcp-servers.json").write_text(
            json.dumps({"test": self.config}), encoding="utf-8"
        )

    async def asyncTearDown(self):
        self.patch.stop()
        # Host pointer removal precedes final process exit and Windows log-handle close.
        for attempt in range(50):
            try:
                self.temp.cleanup()
                break
            except PermissionError:
                if attempt == 49:
                    raise
                await asyncio.sleep(0.02)

    async def test_discovery_tool_resource_and_definition_drift(self):
        found = await freeze(self.root, ["test"])
        definition = found["test"]["definitions"][0]
        raw = await execute(self.root, self.config, definition, {"query": "topic"})
        self.assertFalse(raw.get("isError", False))
        self.assertEqual("原始证据", raw["structuredContent"]["text"])
        resource = await execute(
            self.root, self.config, {}, {"uri": "fixture://material"}, True
        )
        self.assertEqual("original material", resource["contents"][0]["text"])
        bad = await execute(
            self.root,
            self.config,
            {**definition, "description": "changed"},
            {"query": "x"},
        )
        self.assertTrue(bad["isError"])
        self.assertEqual(1, self.calls)
        denied = await execute(
            self.root, self.config, {}, {"uri": "file:///private"}, True
        )
        self.assertTrue(denied["isError"])

    async def test_production_harness_uses_ledger_sources_and_role_grants(self):
        frozen = await freeze(self.root, ["test"])
        store = Store(self.root / ".epivra/state.db")
        try:
            c = store.create("s", "Research fixture", {"mcp": frozen})
            plan = store.put("s", "plan", {"text": "approved"}, (c.direction,))
            c = store.command("s", "approve", c.ref, "approve", {"plan": plan.ref})
            lead = store.work("s", c.ref, "lead", "coordinate")
            work = store.work(
                "s", c.ref, "investigator", "lookup evidence", (), lead.ref
            )
            name = alias("test", "tool:lookup")

            class Model:
                context_tokens = 49024
                max_tokens = 1024
                identity = "fixture"

                async def complete(self, request):
                    return Reply("", (Call(name, {"query": "topic"}),)).to_json()

            tools, connections = connect_tools(store, "s", {"mcp": frozen})
            harness = Harness(store, Model(), tools)
            await harness.step("s", work.ref)
            self.assertEqual(1, self.calls)
            source = store.list("s", "source")[0]
            self.assertIn("原始证据", source.body["text"])
            self.assertIn("operation", source.body["acquisition"])
            self.assertNotIn(name, harness._schema("lead", {"_approved": True}))
            self.assertNotIn(name, harness._schema("reviewer", {"_approved": True}))
            step = store.list("s", "step")[-1]
            await harness._external(
                "s", work.ref, c.epoch, step.ref, 0, Call(name, {"query": "topic"})
            )
            self.assertEqual(1, self.calls)
        finally:
            for connection in connections:
                await connection.close()
            store.close()

    async def test_facade_real_protocol_shared_host_and_approval_permission(self):
        host = Host(self.root)
        host.start_study = lambda study: None

        async def sender(root, request):
            return await host.dispatch({**request, "token": host.token})

        try:
            server = build(self.root, sender=sender)
            async with Client(server) as client:
                result = await client.call_tool(
                    "create_research", {"request": "question"}
                )
                study = result.structured_content["study"]
                c = host.store.control(study)
                self.assertTrue(c.paused)
                plan = host.store.put(study, "plan", {"text": "plan"}, (c.direction,))
                args = {
                    "study": study,
                    "expected": c.ref,
                    "command_id": "approve",
                    "command": "approve",
                    "plan": plan.ref,
                }
                denied = await client.call_tool("control_research", args)
                self.assertTrue(denied.is_error)
                uploaded = await client.call_tool(
                    "upload_material",
                    {
                        "study": study,
                        "expected": c.ref,
                        "name": "a.txt",
                        "data_base64": base64.b64encode(b"exact bytes").decode(),
                    },
                )
                source = uploaded.structured_content["source"]
                data = await client.call_tool(
                    "download_material", {"study": study, "source": source, "length": 5}
                )
                self.assertEqual(
                    b"exact", base64.b64decode(data.structured_content["data"])
                )
            async with Client(build(self.root, True, sender)) as client:
                approved = await client.call_tool("control_research", args)
                self.assertFalse(approved.is_error)
                self.assertTrue(host.store.control(study).approved)
            self.assertTrue(host.store.control(study).approved)
        finally:
            host.store.close()

    async def test_http_bearer_guard(self):
        app, send = AsyncMock(), AsyncMock()
        guard = Bearer(app, "test-secret")
        await guard({"type": "http", "headers": []}, AsyncMock(), send)
        self.assertEqual(401, send.call_args_list[0].args[0]["status"])
        app.assert_not_called()
        await guard(
            {"type": "http", "headers": [(b"authorization", b"Bearer test-secret")]},
            AsyncMock(),
            send,
        )
        app.assert_awaited_once()

    async def test_real_streamable_http_with_bearer(self):
        import uvicorn

        self.patch.stop()
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        app = Bearer(
            self.server.streamable_http_app(stateless_http=True), "fixture-token"
        )
        server = uvicorn.Server(
            uvicorn.Config(app, log_level="error", access_log=False)
        )
        task = asyncio.create_task(server.serve(sockets=[sock]))
        try:
            for _ in range(200):
                if server.started:
                    break
                if task.done():
                    await task
                await asyncio.sleep(0.01)
            self.assertTrue(server.started)
            config = {
                **self.config,
                "transport": "http",
                "url": f"http://127.0.0.1:{port}/mcp",
                "token_env": "FIXTURE_MCP_TOKEN",
            }
            with patch.dict(os.environ, {"FIXTURE_MCP_TOKEN": "fixture-token"}):
                found = await catalog(config, self.root)
                value = await execute(
                    self.root, config, found["tools"][0], {"query": "http"}
                )
                self.assertEqual("原始证据", value["structuredContent"]["text"])
            with patch.dict(os.environ, {"FIXTURE_MCP_TOKEN": "wrong"}):
                denied = await execute(
                    self.root, config, found["tools"][0], {"query": "no"}
                )
                self.assertTrue(denied["isError"])
            self.assertEqual(1, self.calls)
        finally:
            server.should_exit = True
            await asyncio.wait_for(task, 5)
            sock.close()

    async def test_schema_cannot_fetch_and_structured_result_stays_readable(self):
        frozen = await freeze(self.root, ["test"])
        frozen["test"]["definitions"][0]["inputSchema"] = {
            "$ref": "https://invalid.example/private.json"
        }
        store = Store(self.root / ".epivra/state.db")
        try:
            store.create("s", "fixture", {})
            tools, connections = connect_tools(store, "s", {"mcp": frozen})
            tool = tools[alias("test", "tool:lookup")]
            with patch("urllib.request.urlopen") as fetch:
                with self.assertRaises(ValueError):
                    tool.validate_arguments({"query": "x"})
                fetch.assert_not_called()
            result = Workspace(store).mcp_snapshot(
                "s",
                "test",
                {
                    "content": [{"type": "text", "text": "summary"}],
                    "structuredContent": {"important": 23},
                },
                {"operation": "fixture-operation"},
            )
            self.assertEqual(2, len(result["sources"]))
            self.assertIn(
                '"important": 23',
                store.get("s", result["sources"][1]["ref"]).body["text"],
            )
        finally:
            store.close()

    async def test_received_invalid_output_is_not_lost_by_sdk_validation(self):
        definition = (await catalog(self.config, self.root))["tools"][0]
        client = AsyncMock()
        from mcp import types

        client.list_tools.return_value = types.ListToolsResult(
            tools=[types.Tool.model_validate(definition)]
        )
        raw = {
            "content": [{"type": "text", "text": "actual result"}],
            "structuredContent": {"unexpected": True},
        }
        client.session.send_request.return_value = raw

        @asynccontextmanager
        async def connection(config, root):
            yield client

        with patch("epivra.mcp_client.connection", connection):
            self.assertEqual(
                raw, await execute(self.root, self.config, definition, {"query": "x"})
            )
        client.call_tool.assert_not_called()

    async def test_real_stdio_sdk_process_lifecycle(self):
        self.patch.stop()
        config = {
            **self.config,
            "command": sys.executable,
            "args": [str(Path(__file__).with_name("mcp_fixture.py"))],
        }
        found = await catalog(config, self.root)
        self.assertEqual(["lookup"], [t["name"] for t in found["tools"]])
        value = await execute(self.root, config, found["tools"][0], {"query": "stdio"})
        self.assertEqual(7, value["structuredContent"]["value"])
        connection = MCPConnection(self.root, config)
        try:
            first = await connection.invoke(found["tools"][0], {"query": "first"})
            second = await connection.invoke(found["tools"][0], {"query": "second"})
            self.assertEqual(1, first["structuredContent"]["calls"])
            self.assertEqual(2, second["structuredContent"]["calls"])
        finally:
            await connection.close()

    async def test_real_stdio_facade_does_not_own_host_lifetime(self):
        await start(self.root)
        transport = StdioServerParameters(
            command=sys.executable,
            args=["-m", "epivra.mcp_server", "--root", str(self.root)],
        )
        try:
            async with Client(transport) as client:
                result = await client.call_tool("list_research")
                self.assertEqual([], result.structured_content["studies"])
            # Bridge exited; the single host remains available.
            self.assertEqual([], (await send(self.root, {"action": "list"}))["studies"])
        finally:
            pointer = self.root / ".epivra/host.json"
            if pointer.exists():
                await send(self.root, {"action": "shutdown"})
                for _ in range(100):
                    if not pointer.exists():
                        break
                    await asyncio.sleep(0.02)

    async def test_timeout_is_unknown_not_a_completed_error(self):
        from mcp import types
        from mcp.shared.exceptions import MCPError

        definition = (await catalog(self.config, self.root))["tools"][0]
        client = AsyncMock()
        client.list_tools.return_value = types.ListToolsResult(
            tools=[types.Tool.model_validate(definition)]
        )
        client.session.send_request.side_effect = MCPError(
            types.REQUEST_TIMEOUT, "timeout"
        )

        @asynccontextmanager
        async def connection(config, root):
            yield client

        with patch("epivra.mcp_client.connection", connection):
            with self.assertRaisesRegex(RuntimeError, "outcome unknown"):
                await execute(self.root, self.config, definition, {"query": "x"})
        self.assertEqual(1, client.session.send_request.await_count)

    def test_permissions_and_secretless_configuration(self):
        with self.assertRaises(ValueError):
            validate(
                "x", {**self.config, "tools": {"lookup": {"roles": ["investigator"]}}}
            )
        with self.assertRaises(ValueError):
            validate(
                "x", {"transport": "http", "url": "https://key:secret@example.com/mcp"}
            )
        with self.assertRaises(ValueError):
            validate("x", {"transport": "http", "url": "http://example.com/mcp"})
