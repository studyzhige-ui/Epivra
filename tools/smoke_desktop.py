"""Exercise relocated native bundles without keys, providers or system Python."""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path


def smoke(package):
    windows = sys.platform == "win32"
    with tempfile.TemporaryDirectory(prefix="Epivra relocation ") as folder:
        base = Path(folder)
        moved = base / "space and 中文" / package.name
        shutil.copytree(package, moved, symlinks=True)
        resources = moved if windows else moved / "Contents/Resources"
        python = resources / "runtime" / ("python.exe" if windows else "bin/python3")
        launcher = moved / "Epivra.exe" if windows else moved / "Contents/MacOS/Epivra"
        root = base / "user data"
        root.mkdir()
        sentinel = root / "keep.txt"
        sentinel.write_text("preserve upgrades", encoding="utf-8")
        allowed = {"SYSTEMROOT", "WINDIR", "TEMP", "TMP", "TMPDIR", "HOME", "USERPROFILE",
                   "HOMEDRIVE", "HOMEPATH", "LOCALAPPDATA", "APPDATA", "LANG"}
        env = {k: v for k, v in os.environ.items() if k.upper() in allowed}
        env["PATH"] = os.path.join(env.get("SYSTEMROOT", "C:/Windows"), "System32") if windows else "/usr/bin:/bin"
        env["PYTHONNOUSERSITE"] = "1"
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        pointer = root / ".epivra/desktop.json"

        def request(record, path, data=None, token=True):
            origin = f"http://127.0.0.1:{record['port']}"
            headers = {"Origin": origin, "Content-Type": "application/json"}
            if token:
                headers["X-Research-Token"] = record["token"]
            req = urllib.request.Request(origin + path, data=None if data is None else json.dumps(data).encode(),
                                         headers=headers)
            return opener.open(req, timeout=10)

        def wait_ready(process):
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    break
                try:
                    record = json.loads(pointer.read_text(encoding="utf-8"))
                    with request(record, "/api/settings") as response:
                        settings = json.load(response)
                    assert settings["root"] == str(root.resolve())
                    assert not any(p["configured"] for p in settings["providers"])
                    return record
                except (OSError, ValueError):
                    time.sleep(0.2)
            log = root / ".epivra/desktop.log"
            raise AssertionError(log.read_text(encoding="utf-8") if log.exists() else "Desktop never became ready")

        def launch():
            return subprocess.Popen([str(launcher), "--root", str(root), "--headless", "--no-browser"],
                                    cwd=base, env=env)

        process = launch()
        try:
            record = wait_ready(process)
            for path in ("/", "/app.js", "/messages.json", "/api/components"):
                with request(record, path) as response:
                    assert response.status == 200 and response.read()
            try:
                request(record, "/api/settings", token=False)
                raise AssertionError("unauthenticated settings were accepted")
            except urllib.error.HTTPError as exc:
                assert exc.code == 401
            duplicate = launch()
            assert duplicate.wait(timeout=20) == 0
            assert json.loads(pointer.read_text())["token"] == record["token"]
            # This exercises an actual second parser process, not just an import.
            subprocess.run([str(python), "-I", "-c",
                            "import asyncio; from epivra.materials import parse_isolated; "
                            "r=asyncio.run(parse_isolated('sample.txt',b'hello desktop')); "
                            "assert 'hello desktop' in r['text']; print('parser OK')"],
                           cwd=base, env=env, check=True, timeout=30)
            subprocess.run([str(python), "-I", "-c",
                            "import tkinter; r=tkinter.Tk(); r.withdraw(); r.update(); r.destroy(); print('Tk OK')"],
                           cwd=base, env=env, check=True, timeout=30)
            with request(record, "/api/desktop/quit", {}) as response:
                assert json.load(response)["stopping"]
            assert process.wait(timeout=40) == 0
            assert not pointer.exists()
            assert not (root / ".epivra/host.json").exists()
            assert sentinel.read_text() == "preserve upgrades"
            process = launch()
            record = wait_ready(process)
            subprocess.run([str(launcher), "--root", str(root), "--shutdown"],
                           cwd=base, env=env, check=True, timeout=15)
            assert process.wait(timeout=40) == 0
        finally:
            if process.poll() is None:
                try:
                    with request(json.loads(pointer.read_text()), "/api/desktop/quit", {}):
                        pass
                    process.wait(timeout=40)
                except Exception:
                    process.kill()
                    process.wait()
        assert not list(moved.rglob(".env"))
        assert not list(moved.rglob("state.db"))
        print("Desktop smoke passed: native launch, relocation, assets, auth, duplicate, parser, Tk, exit and restart")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("package", type=Path)
    smoke(parser.parse_args().package.resolve())
