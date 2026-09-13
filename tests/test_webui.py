"""Local Web contract tests, with a real Host and no model/search calls."""

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlencode

import httpx

from epivra import cli_settings
from epivra.host import Host, send
from epivra.webui import App, Server


class WebTests(unittest.IsolatedAsyncioTestCase):
    async def test_error_language_is_per_request(self):
        en, zh = await asyncio.gather(
            self.http.post(
                "/api/command",
                json={"action": "not-real"},
                headers={"X-Epivra-Language": "en"},
            ),
            self.http.post(
                "/api/command",
                json={"action": "not-real"},
                headers={"X-Epivra-Language": "zh-CN"},
            ),
        )
        self.assertEqual(en.status_code, 400)
        self.assertEqual(zh.status_code, 400)
        self.assertEqual(en.json()["error"], "Unsupported operation or parameters.")
        self.assertEqual(zh.json()["error"], "不支持的操作或参数。")

    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.host = Host(self.root)
        self.host.start_study = lambda study: None
        self.requests = []
        loop = asyncio.get_running_loop()

        async def dispatch(request):
            self.requests.append(request)
            try:
                return await self.host.dispatch({**request, "token": self.host.token})
            except Exception as exc:
                return {"error": type(exc).__name__}

        async def sender(root, request):
            return await asyncio.wrap_future(
                asyncio.run_coroutine_threadsafe(dispatch(request), loop)
            )

        self.app = App(self.root, sender)
        self.server = Server(self.app, max_upload=4 * 1024 * 1024)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.http = httpx.AsyncClient(
            base_url=self.server.origin,
            headers={
                "X-Research-Token": self.server.token,
                "Origin": self.server.origin,
            },
            trust_env=False,
        )

    async def asyncTearDown(self):
        await self.http.aclose()
        await asyncio.to_thread(self.server.shutdown)
        self.server.server_close()
        await asyncio.to_thread(self.thread.join, 2)
        self.host.store.close()
        self.temp.cleanup()

    async def test_listening_port_is_exclusive(self):
        with self.assertRaises(OSError):
            Server(self.app, port=self.server.server_port)
        self.assertEqual(200, (await self.http.get("/")).status_code)

    async def call(self, action, **fields):
        return await self.http.post("/api/command", json={"action": action, **fields})

    async def draft(self):
        reply = await self.call("create", request="比较本地资料", provider="deepseek")
        self.assertEqual(200, reply.status_code, reply.text)
        study = reply.json()["study"]
        return study, self.host.store.control(study)

    async def test_model_discovery_route_is_authenticated_and_ephemeral(self):
        result = {"models": [{"id": "example"}], "source": "account"}
        with patch("epivra.webui.discover", return_value=result) as discover:
            reply = await self.http.post(
                "/api/models", json={"provider": "deepseek", "key": "temporary-key"}
            )
            self.assertEqual(200, reply.status_code)
            self.assertEqual(result, reply.json())
            self.assertEqual("temporary-key", discover.call_args.args[2])
            self.assertFalse((self.root / ".env").exists())
            reply = await self.http.post(
                "/api/models",
                json={
                    "provider": "deepseek",
                    "url": "https://invalid.example",
                    "key": "temporary-key",
                },
            )
            self.assertEqual(400, reply.status_code)
            reply = await self.http.post(
                "/api/models",
                json={"provider": "deepseek"},
                headers={"X-Research-Token": "wrong"},
            )
            self.assertEqual(401, reply.status_code)
            self.assertEqual(1, discover.call_count)

    async def test_loopback_guard_csrf_and_assets(self):
        reply = await self.http.get("/")
        self.assertEqual(200, reply.status_code)
        self.assertIn("Epivra · 自主研究工作台", reply.text)
        self.assertNotIn(self.server.token, reply.text)
        self.assertIn(
            "frame-ancestors 'none'", reply.headers["Content-Security-Policy"]
        )
        for headers in (
            {"Host": "evil.example"},
            {"Origin": "https://evil.example"},
            {"X-Research-Token": "wrong"},
        ):
            reply = await self.http.post(
                "/api/command", json={"action": "overview"}, headers=headers
            )
            self.assertIn(reply.status_code, (401, 403))
            self.assertNotIn("access-control-allow-origin", reply.headers)
        self.assertEqual([], self.requests)
        self.assertEqual(404, (await self.http.get("/../.env")).status_code)
        self.assertEqual(501, (await self.http.options("/api/command")).status_code)
        script = await self.http.get("/markdown-it.min.js")
        self.assertEqual(200, script.status_code)
        self.assertGreater(len(script.content), 10000)

    async def test_allowlist_no_shutdown_export_or_approval_bypass(self):
        for action, fields in (
            ("shutdown", {}),
            ("export", {"destination": "unrequested"}),
            ("create", {"request": "x", "draft": False}),
            ("control", {"command": "reconcile"}),
            ("overview", {"token": "injected"}),
        ):
            reply = await self.call(action, **fields)
            self.assertEqual(400, reply.status_code)
        self.assertEqual([], self.requests)

    async def test_draft_import_and_exact_approval_conflict(self):
        study, c = await self.draft()
        self.assertTrue(c.paused)
        path = self.root / "中文资料.txt"
        path.write_text("本地原始材料", encoding="utf-8")
        result = await self.call(
            "import_file", study=study, expected=c.ref, path=str(path)
        )
        self.assertEqual(200, result.status_code, result.text)
        self.assertEqual(
            [], self.host.store.get(study, c.direction).body["policy"]["local_roots"]
        )
        plan = self.host.store.put(
            study,
            "plan",
            {"text": "原策略", "brief": {"subject": "材料范围"}},
            (c.direction,),
        )
        shown = (await self.call("status", study=study)).json()
        self.assertEqual("材料范围", shown["plans"][0]["body"]["brief"]["subject"])
        self.host.store.command(
            study, "changed", c.ref, "steer", {"request": "新的范围"}
        )
        reply = await self.call(
            "control",
            study=study,
            expected=shown["control"],
            command_id="approval",
            command="approve",
            payload={"plan": plan.ref},
        )
        self.assertEqual(409, reply.status_code)
        self.assertFalse(self.host.store.control(study).approved)
        self.assertEqual(
            1, sum(r.get("command_id") == "approval" for r in self.requests)
        )
        self.assertEqual([], self.host.store.list(study, "operation"))

    async def test_browser_upload_over_ipc_limit_and_chunk_download(self):
        study, c = await self.draft()
        raw = ("完整材料\n" * 270000).encode()
        self.assertGreater(len(raw), 3 * 1024 * 1024)
        params = urlencode({"study": study, "expected": c.ref, "name": "中文资料.txt"})
        reply = await self.http.post("/api/upload?" + params, content=raw)
        self.assertEqual(200, reply.status_code, reply.text)
        source = reply.json()["source"]
        self.assertEqual([], list((self.root / ".epivra").glob("web-upload-*")))
        self.assertTrue(self.host.store.control(study).paused)
        downloaded = await self.http.post(
            "/api/file", json={"study": study, "source": source}
        )
        self.assertEqual(200, downloaded.status_code)
        self.assertEqual(raw, downloaded.content)
        self.assertEqual(1, sum(r["action"] == "export" for r in self.requests))
        self.assertEqual([], list((self.root / ".epivra").glob("web-download-*")))

    async def test_failed_import_keeps_draft_and_cleans_staging(self):
        study, c = await self.draft()
        params = urlencode({"study": study, "expected": "old", "name": "资料.txt"})
        reply = await self.http.post("/api/upload?" + params, content="材料".encode())
        self.assertEqual(400, reply.status_code)
        self.assertTrue(self.host.store.control(study).paused)
        self.assertEqual([], self.host.store.list(study, "source"))
        self.assertEqual([], list((self.root / ".epivra").glob("web-upload-*")))
        for name in ("../escape.txt", "..\\escape.txt", "x:y.txt"):
            params = urlencode({"study": study, "expected": c.ref, "name": name})
            reply = await self.http.post("/api/upload?" + params, content=b"x")
            self.assertEqual(400, reply.status_code)
        self.assertEqual([], self.host.store.list(study, "source"))

    async def test_credentials_never_return_and_settings_share_cli_file(self):
        sentinel = "fixture-do-not-return-secret"
        reply = await self.http.post(
            "/api/key", json={"name": "DEEPSEEK_API_KEY", "value": sentinel}
        )
        self.assertEqual(200, reply.status_code)
        settings = await self.http.get("/api/settings")
        self.assertNotIn(sentinel, settings.text)
        self.assertTrue(
            next(p for p in settings.json()["providers"] if p["id"] == "deepseek")[
                "configured"
            ]
        )
        values = {
            "provider": "deepseek",
            "model": "deepseek-flash",
            "parser": "light",
            "analysis": False,
        }
        reply = await self.http.post("/api/settings", json=values)
        self.assertEqual(200, reply.status_code, reply.text)
        self.assertEqual(values, cli_settings.load(self.root))
        invalid = {**values, "model": "unknown-model"}
        self.assertEqual(
            400, (await self.http.post("/api/settings", json=invalid)).status_code
        )
        self.assertEqual(values, cli_settings.load(self.root))
        self.assertEqual(
            400,
            (
                await self.http.post("/api/key", json={"name": "PATH", "value": "bad"})
            ).status_code,
        )

    async def test_status_blocker_is_visible_and_old_report_not_returned(self):
        study, c = await self.draft()
        self.host.failures[study] = "CredentialRequired"
        reply = await self.call("status", study=study)
        self.assertEqual(200, reply.status_code)
        self.assertEqual("CredentialRequired", reply.json()["error"])
        report = self.host.store.put(
            study, "report", {"text": "old report", "evidence": []}
        )
        self.host.store._put(
            study, "publication", {"report": report.ref}, (c.direction,)
        )
        self.assertEqual(
            "old report", (await self.call("report", study=study)).json()["text"]
        )
        self.host.store.command(study, "steer", c.ref, "steer", {"request": "new"})
        self.assertNotIn("text", (await self.call("report", study=study)).json())

    async def test_native_picker_cancel_and_no_arbitrary_command(self):
        class Result:
            returncode = 0
            stdout = json.dumps({"path": None})

        with patch("epivra.webui.subprocess.run", return_value=Result()) as run:
            result = await self.http.post("/api/pick", json={"kind": "folder"})
            self.assertEqual({"path": None}, result.json())
            self.assertEqual(["folder", "zh-CN"], run.call_args.args[0][-2:])
            result = await self.http.post(
                "/api/pick",
                json={"kind": "folder"},
                headers={"X-Epivra-Language": "en"},
            )
            self.assertEqual({"path": None}, result.json())
            self.assertEqual(["folder", "en"], run.call_args.args[0][-2:])
            self.assertEqual(
                400,
                (await self.http.post("/api/pick", json={"kind": "shell"})).status_code,
            )
            self.assertEqual(2, run.call_count)
        self.assertEqual([], self.requests)

    async def test_web_shutdown_leaves_host_state_unchanged(self):
        study, c = await self.draft()
        await asyncio.to_thread(self.server.shutdown)
        self.server.server_close()
        self.assertEqual(c.ref, self.host.store.control(study).ref)
        self.assertFalse(self.host.stopping.is_set())
        self.assertFalse(any(r["action"] == "shutdown" for r in self.requests))


class WebProcessTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_web_exit_preserves_newly_started_host(self):
        temp = tempfile.TemporaryDirectory(prefix="web-process-test-")
        root = Path(temp.name)
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-X",
            "utf8",
            "-m",
            "epivra.webui",
            "--root",
            str(root),
            "--port",
            "0",
            "--no-browser",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        try:
            line = await asyncio.wait_for(process.stdout.readline(), 15)
            self.assertIn("本地研究工作台：http://127.0.0.1:", line.decode("utf-8"))
            self.assertEqual({"studies": []}, await send(root, {"action": "list"}))
            process.terminate()
            await asyncio.wait_for(process.wait(), 5)
            self.assertEqual({"studies": []}, await send(root, {"action": "list"}))
        finally:
            if process.returncode is None:
                process.terminate()
                await process.wait()
            if (root / ".epivra/host.json").exists():
                await send(root, {"action": "shutdown"})
            # Pointer removal precedes the child's final log-handle close on Windows.
            for _ in range(100):
                try:
                    temp.cleanup()
                    break
                except PermissionError:
                    await asyncio.sleep(0.02)
            else:
                temp.cleanup()
