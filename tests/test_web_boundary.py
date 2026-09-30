"""Loopback HTTP acceptance over the real Web App, Host and Store."""

import asyncio
import json
import tempfile
import threading
import unittest
from pathlib import Path

import httpx

from epivra.host import Host
from epivra.webui import App, Server


class WebBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_loopback_host_interface(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            h = Host(root)
            loop = asyncio.get_running_loop()

            async def send(root, data):
                f = asyncio.run_coroutine_threadsafe(
                    h.dispatch({**data, "token": h.token}), loop
                )
                try:
                    return await asyncio.wrap_future(f)
                except Exception as e:
                    return {"error": type(e).__name__}

            app = App(root, sender=send)
            server = Server(app, port=0, max_upload=1024)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                async with httpx.AsyncClient(
                    base_url=server.origin, trust_env=False
                ) as c:
                    r = await c.get("/")
                    assert (
                        r.status_code == 200
                        and "frame-ancestors 'none'"
                        in r.headers["content-security-policy"]
                    )
                    assert (await c.get("/api/settings")).status_code == 401
                    headers = {
                        "X-Research-Token": server.token,
                        "Origin": server.origin,
                    }
                    assert (
                        await c.get(
                            "/api/settings",
                            headers={**headers, "Origin": "https://evil.example"},
                        )
                    ).status_code == 403
                    assert (
                        await c.get("/", headers={"Host": "evil.example"})
                    ).status_code == 403
                    r = await c.get("/api/settings", headers=headers)
                    assert (
                        r.status_code == 200
                        and r.json()["max_upload"] == 1024
                        and all("key" not in x for x in r.json()["providers"])
                    )
                    assert (
                        await c.post(
                            "/api/command", headers=headers, json={"action": "shutdown"}
                        )
                    ).status_code == 400
                    assert (
                        await c.post(
                            "/api/command",
                            headers=headers,
                            json={"action": "create", "request": "x", "draft": False},
                        )
                    ).status_code == 400
                    r = await c.post(
                        "/api/command",
                        headers=headers,
                        json={
                            "action": "create",
                            "request": "Local offline boundary test",
                            "web": False,
                        },
                    )
                    assert r.status_code == 200, r.text
                    study = r.json()["study"]
                    state = h.store.control(study)
                    assert state.paused and not h.services
                    params = {
                        "study": study,
                        "expected": state.ref,
                        "name": "source.txt",
                    }
                    r = await c.post(
                        "/api/upload",
                        params=params,
                        headers=headers,
                        content="本地 source".encode(),
                    )
                    assert r.status_code == 200, r.text
                    ref = r.json()["source"]
                    r = await c.post(
                        "/api/file",
                        headers=headers,
                        json={"study": study, "source": ref},
                    )
                    assert r.content == "本地 source".encode()
                    assert (
                        await c.post(
                            "/api/upload",
                            params={**params, "name": "../bad.txt"},
                            headers=headers,
                            content=b"x",
                        )
                    ).status_code == 400
                    assert (
                        await c.post(
                            "/api/upload",
                            params=params,
                            headers=headers,
                            content=b"x" * 1025,
                        )
                    ).status_code == 413
                    assert (
                        await c.post(
                            "/api/report-export",
                            headers=headers,
                            json={"study": study, "expected": "wrong"},
                        )
                    ).status_code == 409
                    assert (
                        await c.post(
                            "/api/command",
                            headers=headers,
                            json={
                                "action": "delete",
                                "study": study,
                                "expected": state.ref,
                                "confirmed": False,
                            },
                        )
                    ).status_code == 400
                    r = await c.post(
                        "/api/command",
                        headers=headers,
                        json={
                            "action": "delete",
                            "study": study,
                            "expected": state.ref,
                            "confirmed": True,
                        },
                    )
                    assert r.status_code == 200 and r.json()["deleted"]
                    print(
                        json.dumps(
                            {
                                "surface": "real loopback HTTP Server + real App + real Host/Store",
                                "checks": [
                                    "CSP",
                                    "token",
                                    "Host",
                                    "Origin",
                                    "allowlisted commands",
                                    "forced paused draft",
                                    "Unicode upload/download",
                                    "filename traversal",
                                    "upload byte cap",
                                    "stale export binding",
                                    "explicit deletion confirmation",
                                ],
                                "result": "PASS",
                                "provider_calls": 0,
                            }
                        )
                    )
            finally:
                await asyncio.to_thread(server.shutdown)
                server.server_close()
                thread.join()
                h.store.close()
