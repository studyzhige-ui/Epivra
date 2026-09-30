"""Offline component integrity, private filesystem and MCP protocol boundaries."""

import asyncio
import hashlib
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from mcp import Client
from mcp.server import MCPServer

from epivra import components, mcp_client, mcp_server, native_analysis
from epivra.analysis import DEFAULTS, DockerSandbox, filename
from epivra.local_security import exclusive_lock, private_directory, protect
from epivra.platform_paths import component_environment


class Files(unittest.TestCase):
    def test_portable_names(self):
        for value in [
            "../x",
            "/x",
            "a//b",
            "a/./b",
            "a/../b",
            "a\\b",
            "x:stream",
            "CON.txt",
            "x/LPT9",
            "a.",
            "a ",
            "a\x00b",
            "a" * 221,
            "",
        ]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                filename(value)
        for value in ["数据/报告.csv", "a-b.txt", "safe_dir/result.json"]:
            self.assertEqual(filename(value), value)

    def test_docker_command_boundary(self):
        cmd = DockerSandbox().command("n", "j", "/tmp/safe, quoted folder", DEFAULTS)
        for arg in [
            "--read-only",
            "ALL",
            "no-new-privileges",
            "none",
            "65534:65534",
            "--pids-limit",
        ]:
            self.assertIn(arg, cmd)
        self.assertIn("readonly", cmd[cmd.index("--mount") + 1])
        self.assertIn("safe, quoted folder", cmd[cmd.index("--mount") + 1])

    def test_native_paths_and_links(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            s = native_analysis.NativeSandbox(p)
            for job in ["../escape", "g" * 64, "a" * 63]:
                with self.assertRaises(ValueError):
                    s.folder(job)
            f = p / "normal"
            f.write_text("x")
            self.assertEqual(native_analysis.measured(p, 1), 1)
            with self.assertRaises(ValueError):
                native_analysis.measured(p, 0)
            h = p / "link"
            os.link(f, h)
            with self.assertRaises(ValueError):
                native_analysis.regular(h)
            if os.name != "nt":
                h.unlink()
                h.symlink_to(f)
                with self.assertRaises(ValueError):
                    native_analysis.regular(h)

    def test_manifest_mutation_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "runtime").mkdir()
            f = p / "runtime/python.exe"
            f.write_bytes(b"fake")
            manifest = {"files": {"python.exe": hashlib.sha256(b"fake").hexdigest()}}
            (p / "manifest.json").write_text(json.dumps(manifest))
            self.assertEqual(components.verify_runtime(p), manifest)
            f.write_bytes(b"changed")
            with self.assertRaises(ValueError):
                components.verify_runtime(p)
            f.write_bytes(b"fake")
            (p / "runtime/extra").write_text("x")
            with self.assertRaises(ValueError):
                components.verify_runtime(p)

    def test_component_pointer_cannot_traverse(self):
        with tempfile.TemporaryDirectory() as d:
            base = native_analysis.component_base(d)
            base.mkdir(parents=True)
            for identity in ["../x", "x" * 64, 3, None]:
                (base / "current.json").write_text(json.dumps({"identity": identity}))
                with self.assertRaises(ValueError):
                    native_analysis.component(d)

    @unittest.skipIf(os.name == "nt", "POSIX ownership/permission probe")
    def test_private_permissions_and_exclusive_lock(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "private"
            private_directory(root)
            self.assertEqual(stat.S_IMODE(root.stat().st_mode), 0o700)
            with exclusive_lock(root / "lock"):
                with self.assertRaises(OSError):
                    exclusive_lock(root / "lock")
            with exclusive_lock(root / "lock"):
                pass
            target = Path(d) / "original"
            target.write_text("safe")
            (root / "link").symlink_to(target)
            with self.assertRaises(ValueError):
                protect(root / "link")
            self.assertEqual(target.read_text(), "safe")

    def test_component_environment(self):
        with patch.dict(
            os.environ,
            {
                "EPIVRA_TEST_SECRET": "private",
                "OPENAI_API_KEY": "fake",
                "PYTHONPATH": "bad",
            },
        ):
            env = component_environment()
        self.assertNotIn("EPIVRA_TEST_SECRET", env)
        self.assertNotIn("OPENAI_API_KEY", env)
        self.assertNotIn("PYTHONPATH", env)

    def test_manifest_locks_agree(self):
        root = Path(__file__).resolve().parents[1]
        entries = json.loads((root / "packaging/analysis/wheels.json").read_text())
        lock = (root / "packaging/analysis/requirements.lock").read_text().splitlines()
        self.assertEqual(len(entries), len(lock))
        for e in entries:
            self.assertIn(
                f"{e['name']}=={e['version']} --hash=sha256:{e['sha256']}", lock
            )


class Async(unittest.IsolatedAsyncioTestCase):
    async def test_repeated_cancel_settles_owner(self):
        release = asyncio.Event()
        done = asyncio.Event()

        async def child():
            await release.wait()
            done.set()
            return 42

        work = asyncio.create_task(child())
        wrapper = asyncio.create_task(native_analysis.settle_thread(work))
        await asyncio.sleep(0)
        wrapper.cancel()
        await asyncio.sleep(0)
        wrapper.cancel()
        await asyncio.sleep(0)
        self.assertFalse(work.done())
        release.set()
        self.assertEqual(await wrapper, (42, True))
        self.assertTrue(done.is_set())

    async def test_mcp_grants_reject_insecure_configuration(self):
        base = {
            "transport": "http",
            "url": "https://example.com/mcp",
            "tools": {"echo": {"write": False, "roles": ["investigator"]}},
        }
        mcp_client.validate("valid", base)
        for url in [
            "http://remote.example/mcp",
            "https://user:pass@example.com/mcp",
            "https://example.com/mcp?token=secret",
            "https://example.com/mcp#x",
        ]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                mcp_client.validate("valid", {**base, "url": url})
        for t in [float("nan"), float("inf"), 0, -1, True]:
            with self.assertRaises(ValueError):
                mcp_client.validate("valid", {**base, "timeout": t})
        with self.assertRaises(ValueError):
            mcp_client.validate(
                "valid", {**base, "tools": {"echo": {"roles": ["investigator"]}}}
            )

    async def test_mcp_facade_installation_grants(self):
        calls = []

        async def sender(root, payload):
            calls.append(payload)
            return {"accepted": payload}

        server = mcp_server.build(Path("/tmp/fake-root"), sender=sender, language="en")
        async with Client(server) as client:
            tools = await client.list_tools()
            self.assertEqual(len(tools.tools), 10)
            denied = await client.call_tool(
                "control_research",
                {
                    "study": "s",
                    "expected": "e",
                    "command_id": "c",
                    "command": "approve",
                },
            )
            self.assertTrue(denied.is_error)
            self.assertEqual(calls, [])
            denied = await client.call_tool(
                "delete_research", {"study": "s", "expected": "e"}
            )
            self.assertTrue(denied.is_error)
            self.assertEqual(calls, [])
            await client.call_tool("create_research", {"request": "offline test"})
            self.assertTrue(calls[-1]["draft"])
            self.assertEqual(calls[-1]["action"], "create")
            denied = await client.call_tool(
                "upload_material",
                {
                    "study": "s",
                    "expected": "e",
                    "name": "x",
                    "data_base64": "A" * (4 * 1024 * 1024),
                },
            )
            self.assertTrue(denied.is_error)
            self.assertEqual(len(calls), 1)
            await client.call_tool(
                "control_research",
                {"study": "s", "expected": "e", "command_id": "c", "command": "pause"},
            )
            self.assertEqual(calls[-1]["action"], "control")

    async def test_bearer_boundary(self):
        calls = []
        responses = []

        async def app(*args):
            calls.append(args)

        async def receive():
            return {}

        async def send(v):
            responses.append(v)

        app = mcp_server.Bearer(app, "fake-secret")
        for auth in [b"", b"Bearer wrong"]:
            await app(
                {"type": "http", "headers": [(b"authorization", auth)]}, receive, send
            )
            self.assertEqual(responses[-2]["status"], 401)
        self.assertEqual(calls, [])
        await app(
            {"type": "http", "headers": [(b"authorization", b"Bearer fake-secret")]},
            receive,
            send,
        )
        self.assertEqual(len(calls), 1)

    async def test_mcp_frozen_definition_and_known_result(self):
        server = MCPServer("audit")
        sent = []

        @server.tool()
        async def echo(value: str) -> dict[str, str]:
            sent.append(value)
            return {"value": value}

        async with Client(server) as client:
            definition = (
                (await client.list_tools())
                .tools[0]
                .model_dump(mode="json", by_alias=True, exclude_none=True)
            )
            config = {"timeout": 2, "resources": ["test://approved"]}
            result = await mcp_client.execute(
                Path("/tmp"), config, definition, {"value": "ok"}, client=client
            )
            self.assertEqual(result["structuredContent"], {"value": "ok"})
            self.assertEqual(sent, ["ok"])
            changed = {**definition, "description": "changed"}
            result = await mcp_client.execute(
                Path("/tmp"), config, changed, {"value": "not sent"}, client=client
            )
            self.assertTrue(result["isError"])
            self.assertEqual(sent, ["ok"])
            result = await mcp_client.execute(
                Path("/tmp"),
                config,
                {},
                {"uri": "test://denied"},
                resource=True,
                client=client,
            )
            self.assertTrue(result["isError"])
            self.assertEqual(sent, ["ok"])

    async def test_mcp_unknown_outcome_not_retried(self):
        calls = []

        class Session:
            async def send_request(self, *args):
                calls.append(args)
                raise TimeoutError("after send")

        client = SimpleNamespace(session=Session())
        with self.assertRaisesRegex(RuntimeError, "outcome unknown"):
            await mcp_client.execute(
                Path("/tmp"),
                {"resources": ["test://ok"], "timeout": 1},
                {},
                {"uri": "test://ok"},
                True,
                client,
            )
        self.assertEqual(len(calls), 1)

    async def test_pagination_cycle_rejected(self):
        async def page(**kwargs):
            return SimpleNamespace(tools=[], next_cursor="same")

        with self.assertRaisesRegex(ValueError, "cursor repeated"):
            await mcp_client.pages(page, "tools")
