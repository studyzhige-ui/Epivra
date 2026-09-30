"""MCP preparation/serialization precedes quota and durable send admission."""

import asyncio
import json
import tempfile
import unittest
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from mcp import Client
from mcp.server import MCPServer

from epivra.domain import Call, Conflict, NotAllowed, UnknownOutcome
from epivra.harness import Harness
from epivra.host import Host
from epivra.mcp_client import MCPConnection
from epivra.mcp_tools import connect_tools
from epivra.scheduling import Scheduler
from epivra.storage import Store


async def until(predicate):
    async with asyncio.timeout(3):
        while not predicate():
            await asyncio.sleep(0.001)


class Model:
    identity = "offline"
    context_tokens = 100000
    max_tokens = 1000


class MCPAdmissionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.root_path = Path(self.folder.name)
        self.store = Store(self.root_path / ".epivra/research.db")
        self.connections = []
        self.tasks = []
        self.now = 100.0
        self.scheduler = Scheduler(clock=lambda: self.now)

    async def asyncTearDown(self):
        for task in self.tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        for connection in self.connections:
            await connection.close()
        self.store.close()
        self.folder.cleanup()

    def setup_tool(self, *, write=True, definition=None):
        self.definition = definition or {
            "name": "fixture", "inputSchema": {"type": "object", "properties": {
                "value": {"type": "string"}}, "required": ["value"]}}
        config = {"transport": "http", "url": "https://fixture.example/mcp", "timeout": 2,
                  "tools": {self.definition["name"]: {"roles": ["investigator"], "write": write}}, "resources": []}
        policy = {"mcp": {"fixture": {"connection": config, "definitions": [self.definition]}}}
        control = self.store.create("study", "Offline MCP admission", policy)
        plan = self.store.put("study", "plan", {}, (control.direction,))
        self.control = self.store.command("study", "approve", control.ref, "approve", {"plan": plan.ref})
        root = self.store.work("study", self.control.ref, "lead", "root")
        self.works = [self.store.work("study", self.control.ref, "investigator", str(i), owner=root.ref) for i in range(3)]
        self.steps = [self.store.put("study", "step", {"request": {}}, (work.ref,)) for work in self.works]
        tools, self.connections = connect_tools(self.store, "study", policy)
        self.tool_name = next(iter(tools))
        self.harness = Harness(self.store, Model(), tools, scheduler=self.scheduler)
        return config

    def start(self, index):
        task = asyncio.create_task(self.harness._acquired(
            "study", self.works[index].ref, self.control.epoch,
            self.steps[index].ref, 0, Call(self.tool_name, {"value": str(index)})))
        self.tasks.append(task)
        return task

    async def fixture(self, phase, *, write=True, command="pause", cancel_waiter=False):
        self.setup_tool(write=write)
        entered, release = asyncio.Event(), asyncio.Event()
        sent = []
        outer = self

        class Session:
            async def send_request(self, request, *args):
                sent.append((request.params.arguments["value"], outer.store.control("study").paused))
                if phase == "queue" and len(sent) == 1:
                    entered.set()
                    await release.wait()
                return {"content": [{"type": "text", "text": "fixture result"}], "isError": False}

        async def list_tools(**kwargs):
            if phase == "pagination" and kwargs.get("cursor") is None:
                return SimpleNamespace(tools=[], next_cursor="next")
            if phase in {"discovery", "pagination"} and not release.is_set():
                entered.set()
                await release.wait()
            return SimpleNamespace(tools=[SimpleNamespace(name=self.definition["name"],
                model_dump=lambda **kwargs: self.definition,
                model_dump_json=lambda: json.dumps(self.definition))], next_cursor=None)

        @asynccontextmanager
        async def connection(config, root):
            if phase == "setup":
                entered.set()
                await release.wait()
            yield SimpleNamespace(session=Session(), list_tools=list_tools)

        with patch("epivra.mcp_client.connection", connection):
            first = self.start(0)
            await asyncio.wait_for(entered.wait(), 3)
            waiting = first
            if phase == "queue":
                waiting = self.start(1)
                await until(lambda: self.scheduler.waiting.get("mcp:fixture") == 1)
            expected_sends = 1 if phase == "queue" else 0
            self.assertEqual(len(self.store.admissions()), expected_sends)
            self.assertEqual(len(self.scheduler.history.get("mcp:fixture", [])), expected_sends)
            if cancel_waiter:
                waiting.cancel()
            else:
                self.store.command("study", command, self.control.ref, command)
            # Waiting work must withdraw without the unrelated active call/setup completing.
            result = (await asyncio.wait_for(asyncio.gather(waiting, return_exceptions=True), 2))[0]
            self.assertIsInstance(result, asyncio.CancelledError if cancel_waiter else (Conflict, NotAllowed))
            self.assertEqual(len(self.store.admissions()), expected_sends)
            self.assertEqual(len(sent), expected_sends)
            release.set()
            await asyncio.gather(first, return_exceptions=True)
            if cancel_waiter:
                # A withdrawing caller must not cancel shared session readiness.
                await asyncio.wait_for(self.start(2), 3)
                self.assertEqual(len(sent), expected_sends + 1)
            else:
                self.assertTrue(all(not paused for _, paused in sent))
                self.assertEqual(self.store.unsettled("study"), [])
            self.assertFalse(self.connections[0].lock.locked())
            self.assertEqual(self.connections[0].prepared, {})
            self.assertEqual(self.scheduler.active.get("mcp:fixture", 0), 0)
            self.assertEqual(self.scheduler.waiting.get("mcp:fixture", 0), 0)

    async def test_pause_withdraws_queued_write(self):
        await self.fixture("queue")

    async def test_pause_withdraws_queued_read(self):
        await self.fixture("queue", write=False)

    async def test_cancel_withdraws_queued_write(self):
        await self.fixture("queue", command="cancel")

    async def test_cancel_withdraws_queued_read(self):
        await self.fixture("queue", write=False, command="cancel")

    async def test_pause_during_session_setup(self):
        await self.fixture("setup")

    async def test_pause_during_definition_refresh(self):
        await self.fixture("discovery")

    async def test_pause_during_discovery_pagination(self):
        await self.fixture("pagination")

    async def test_cancel_during_session_setup(self):
        await self.fixture("setup", command="cancel")

    async def test_cancel_during_definition_refresh(self):
        await self.fixture("discovery", command="cancel")

    async def test_task_cancellation_preserves_shared_setup(self):
        await self.fixture("setup", cancel_waiter=True)

    async def test_task_cancellation_withdraws_queued_call(self):
        await self.fixture("queue", cancel_waiter=True)

    async def test_task_cancellation_during_definition_refresh(self):
        await self.fixture("discovery", cancel_waiter=True)

    async def test_quota_recheck_releases_prepared_turn_and_records_actual_send(self):
        self.setup_tool()
        self.scheduler.limits = {"mcp:fixture": {"rpm": 1}}
        entered, release = asyncio.Event(), asyncio.Event()
        sent = []

        async def list_tools(**kwargs):
            entered.set()
            await release.wait()
            return SimpleNamespace(tools=[SimpleNamespace(name=self.definition["name"],
                model_dump=lambda **kwargs: self.definition,
                model_dump_json=lambda: json.dumps(self.definition))], next_cursor=None)

        async def send_request(*args):
            sent.append(self.now)
            return {"content": [], "isError": False}

        @asynccontextmanager
        async def connection(config, root):
            yield SimpleNamespace(session=SimpleNamespace(send_request=send_request), list_tools=list_tools)

        with patch("epivra.mcp_client.connection", connection):
            task = self.start(0)
            await entered.wait()
            self.now = 150.0
            async with self.scheduler.slot("mcp:fixture", lambda: None):
                pass
            release.set()
            await until(lambda: not self.connections[0].lock.locked())
            self.assertFalse(task.done())
            self.assertEqual(self.store.admissions(), [])
            self.assertEqual(self.connections[0].prepared, {})
            self.now = 211.0
            await asyncio.wait_for(task, 3)
            self.assertEqual(sent, [211.0])
            admission = self.store.admissions()[0]
            self.assertEqual(admission["at"], 211.0)
            self.assertEqual(admission["timing"]["invoked_at"], 211.0)

    async def test_definition_rejection_has_no_admission_and_releases_turn(self):
        self.setup_tool()
        current = {**self.definition, "description": "changed"}

        async def list_tools(**kwargs):
            return SimpleNamespace(tools=[SimpleNamespace(name=current["name"],
                model_dump=lambda **kwargs: current,
                model_dump_json=lambda: json.dumps(current))], next_cursor=None)

        async def send_request(*args):
            return {"content": [], "isError": False}

        @asynccontextmanager
        async def connection(config, root):
            yield SimpleNamespace(session=SimpleNamespace(send_request=send_request), list_tools=list_tools)

        with patch("epivra.mcp_client.connection", connection):
            with self.assertRaisesRegex(ValueError, "definition changed"):
                await self.start(0)
            self.assertEqual(self.store.admissions(), [])
            self.assertFalse(self.connections[0].lock.locked())
            current = self.definition
            await self.start(0)
            self.assertEqual(len(self.store.admissions()), 1)

    async def test_owner_close_after_actual_dispatch_preserves_unknown(self):
        server = MCPServer("offline-owner-close")
        entered = asyncio.Event()

        @server.tool()
        async def fixture(value: str) -> dict[str, str]:
            entered.set()
            await asyncio.Event().wait()
            return {"value": value}

        definition = (await server.list_tools())[0].model_dump(mode="json", by_alias=True, exclude_none=True)
        self.setup_tool(definition=definition)

        @asynccontextmanager
        async def connection(config, root):
            async with Client(server) as client:
                yield client

        with patch("epivra.mcp_client.connection", connection):
            task = self.start(0)
            await asyncio.wait_for(entered.wait(), 3)
            await asyncio.wait_for(self.connections[0].close(), 3)
            outcome = (await asyncio.wait_for(asyncio.gather(task, return_exceptions=True), 3))[0]
            self.assertIsInstance(outcome, (RuntimeError, asyncio.CancelledError))
            self.assertEqual(len(self.store.unsettled("study")), 1)
            with self.assertRaises(UnknownOutcome):
                await self.start(0)
            self.assertFalse(self.connections[0].lock.locked())

    async def test_connection_setup_failure_is_provably_not_admitted(self):
        self.setup_tool()

        @asynccontextmanager
        async def unavailable(config, root):
            raise ConnectionError("offline fixture unavailable")
            yield

        with patch("epivra.mcp_client.connection", unavailable):
            with self.assertRaisesRegex(ValueError, "session unavailable"):
                await self.start(0)
        self.assertEqual(self.store.admissions(), [])
        self.assertEqual(self.scheduler.history.get("mcp:fixture", []), [])
        self.assertFalse(self.connections[0].lock.locked())

    async def test_host_reload_resumes_with_a_fresh_mcp_session(self):
        self.store.close()
        host = Host(self.root_path)
        self.store = host.store
        self.setup_tool()
        host.clients["study"] = self.connections
        sessions, sent = [], []

        async def list_tools(**kwargs):
            return SimpleNamespace(tools=[SimpleNamespace(name=self.definition["name"],
                model_dump=lambda **kwargs: self.definition,
                model_dump_json=lambda: json.dumps(self.definition))], next_cursor=None)

        @asynccontextmanager
        async def connection(config, root):
            generation = len(sessions) + 1
            sessions.append(generation)

            async def send_request(*args):
                sent.append(generation)
                return {"content": [], "isError": False}

            yield SimpleNamespace(session=SimpleNamespace(send_request=send_request), list_tools=list_tools)

        with patch("epivra.mcp_client.connection", connection):
            await self.start(0)
            paused = self.store.command("study", "pause", self.control.ref, "pause")
            result = await host.dispatch({"token": host.token, "action": "reload", "study": "study"})
            self.assertEqual(result, {"reloaded": True})
            with patch.object(host, "start_study"):
                await host.dispatch({"token": host.token, "action": "control", "study": "study",
                    "command": "resume", "command_id": "resume", "expected": paused.ref})
            self.control = self.store.control("study")
            await self.start(1)
        self.assertEqual(sent, [1, 2])
        self.assertFalse(self.connections[0].closed)


class SDKTurnTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_sdk_session_owner_and_borrowed_send_task(self):
        server = MCPServer("offline-borrower")

        @server.tool()
        async def fixture(value: str) -> dict[str, str]:
            return {"value": value}

        definition = (await server.list_tools())[0].model_dump(mode="json", by_alias=True, exclude_none=True)
        config = {"timeout": 2}

        @asynccontextmanager
        async def connection(config, root):
            async with Client(server) as client:
                yield client

        client = MCPConnection(Path("."), config)
        receipts = []
        with patch("epivra.mcp_client.connection", connection):
            try:
                async with client.turn(definition, {"value": "safe"}, check=lambda: None):
                    self.assertIsNot(client.task, asyncio.current_task())
                    value = await client.invoke(definition, {"value": "safe"}, receive=receipts.append)
                self.assertEqual(value["structuredContent"], {"value": "safe"})
                self.assertEqual(receipts, [value])
                self.assertFalse(client.lock.locked())
            finally:
                await client.close()
        self.assertTrue(client.task.done())
