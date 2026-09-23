"""Distribution boundaries: persistent paths, process ownership and optional setup."""

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from epivra.components import Components, documents, python_with_packages
from epivra.desktop import contact
from epivra.local_security import exclusive_lock, private_directory
from epivra.platform_paths import (
    component_environment,
    desktop_root,
    kill_child,
    python_executable,
)


class DesktopTests(unittest.TestCase):
    def test_data_path_is_not_derived_from_working_directory(self):
        with patch("epivra.platform_paths.sys.platform", "win32"), patch.dict(
            os.environ, {"LOCALAPPDATA": "C:/Users/test/AppData/Local"}
        ):
            self.assertEqual(desktop_root(), Path("C:/Users/test/AppData/Local/Epivra"))
        with patch("epivra.platform_paths.sys.platform", "darwin"), patch(
            "epivra.platform_paths.Path.home", return_value=Path("/Users/test")
        ):
            self.assertEqual(desktop_root(), Path("/Users/test/Library/Application Support/Epivra"))

    def test_gui_python_is_not_used_for_parser_or_host(self):
        with patch("epivra.platform_paths.sys.executable", "C:/App/runtime/pythonw.exe"):
            self.assertEqual(Path(python_executable()), Path("C:/App/runtime/python.exe"))

    def test_component_subprocesses_never_inherit_provider_credentials(self):
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "fake-secret", "HF_TOKEN": "fake",
                                    "PYTHONPATH": "/untrusted", "PIP_INDEX_URL": "https://secret.invalid"}):
            env = component_environment()
            for name in ("DEEPSEEK_API_KEY", "HF_TOKEN", "PYTHONPATH", "PIP_INDEX_URL"):
                self.assertNotIn(name, env)

    def test_component_entrypoint_arguments_are_not_executable_code(self):
        path = Path("folder with spaces")
        command = python_with_packages(path, "print('ok')", "models", "download")
        self.assertEqual(command[-3:], [str(path), "models", "download"])
        self.assertIn("-I", command)

    def test_failed_component_is_not_advertised_as_installed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            private_directory(root / ".epivra")
            installer = Components(root)
            with patch.object(installer, "_documents", side_effect=RuntimeError("test failure")):
                installer.busy = True
                installer.job["component"] = "documents"
                installer._install("documents")
            self.assertIsNone(documents(root))
            self.assertEqual(installer.status()["job"]["state"], "failed")
            self.assertFalse(installer.busy)

    def test_lock_released_after_process_crash(self):
        with tempfile.TemporaryDirectory() as folder:
            lock = Path(folder) / "lock"
            process = subprocess.Popen([sys.executable, "-c",
                "import sys,time; from pathlib import Path; "
                "from epivra.local_security import exclusive_lock; "
                "f=exclusive_lock(Path(sys.argv[1])); print('locked',flush=True); time.sleep(30)",
                str(lock)], stdout=subprocess.PIPE, text=True)
            try:
                self.assertEqual(process.stdout.readline().strip(), "locked")
                with self.assertRaises(OSError):
                    exclusive_lock(lock)
            finally:
                kill_child(process)
                process.wait()
                process.stdout.close()
            exclusive_lock(lock).close()

    def test_desktop_reopens_same_session_then_stops_host_and_restarts(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            def launch():
                return subprocess.Popen([sys.executable, "-m", "epivra.desktop",
                    "--root", str(root), "--headless", "--no-browser"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            process = launch()
            try:
                deadline = time.monotonic() + 20
                while True:
                    try:
                        record, origin = contact(root)
                        break
                    except (OSError, ValueError, KeyError):
                        if process.poll() is not None or time.monotonic() > deadline:
                            self.fail(process.stderr.read().decode(errors="replace") if process.poll() is not None else "startup timed out")
                        time.sleep(0.1)
                duplicate = launch()
                self.assertEqual(duplicate.wait(timeout=15), 0)
                duplicate.stderr.close()
                again, _ = contact(root)
                self.assertEqual(record, again)
                contact(root, stop=True)
                self.assertEqual(process.wait(timeout=40), 0)
                self.assertFalse((root / ".epivra/host.json").exists())
                self.assertFalse((root / ".epivra/desktop.json").exists())
            finally:
                if process.poll() is None:
                    try:
                        contact(root, stop=True)
                        process.wait(timeout=40)
                    except Exception:
                        kill_child(process)
                        process.wait()
                        try:
                            from epivra.host import send
                            asyncio.run(send(root, {"action": "shutdown"}))
                        except OSError:
                            pass
                process.stderr.close()

    def test_shutdown_and_component_install_share_one_gate(self):
        with tempfile.TemporaryDirectory() as folder:
            installer = Components(Path(folder))
            installer.close()
            with self.assertRaises(ValueError):
                installer.start("documents")
            active = Components(Path(folder))
            active.busy = True
            with self.assertRaises(ValueError):
                active.close()
            self.assertFalse(active.closing)

    def test_starting_host_is_reaped_on_desktop_cancel(self):
        import threading

        from epivra import host

        with tempfile.TemporaryDirectory() as folder:
            cancel = threading.Event()
            cancel.set()
            child = MagicMock()
            child.poll.return_value = None
            with patch("epivra.host.send", new=AsyncMock(side_effect=FileNotFoundError)), patch(
                "subprocess.Popen", return_value=child
            ), patch("epivra.host.kill_child") as kill:
                with self.assertRaises(asyncio.CancelledError):
                    asyncio.run(host.start(Path(folder), wait=None, cancel=cancel))
            kill.assert_called_once_with(child)
            self.assertTrue(child.wait.called)

    def test_endpoint_rejects_non_loopback_port_data(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / ".epivra").mkdir()
            (root / ".epivra/desktop.json").write_text(json.dumps({"port": "evil", "token": "fake"}))
            with self.assertRaises(ValueError):
                contact(root)
