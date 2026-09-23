"""Application paths and executables, independent of the working directory."""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def desktop_root():
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "Epivra"
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/Epivra"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "Epivra"


def python_executable():
    path = Path(sys.executable)
    return str(path.with_name("python.exe") if path.name.lower() == "pythonw.exe" else path)


def docker_executable():
    found = shutil.which("docker")
    if found:
        return found
    if sys.platform == "darwin":
        paths = [Path.home() / ".docker/bin/docker",
                 Path("/Applications/Docker.app/Contents/Resources/bin/docker")]
    else:
        paths = [Path(os.environ.get("ProgramFiles", "C:/Program Files"))
                 / "Docker/Docker/resources/bin/docker.exe"]
    return next((str(p) for p in paths if p.is_file()), "docker")


def sandbox_resources():
    bundled = Path(sys.prefix) / "epivra-resources/sandbox"
    if bundled.is_dir():
        return bundled
    return Path(__file__).resolve().parents[2] / "sandbox"


def component_environment():
    allowed = {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "TMPDIR",
               "LANG", "LC_ALL", "HOME", "USERPROFILE", "HOMEDRIVE", "HOMEPATH",
               "LOCALAPPDATA", "APPDATA"}
    return {k: v for k, v in os.environ.items() if k.upper() in allowed}


def kill_child(process):
    """Stop a child, including the Windows venv interpreter redirector."""
    if os.name == "nt":
        # A venv python.exe can launch the base interpreter as another process.
        # Terminate the whole owned tree before waiting for pipe/lock release.
        result = subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=15,
        )
        if result.returncode == 0:
            return
    try:
        process.kill()
    except ProcessLookupError:
        pass
