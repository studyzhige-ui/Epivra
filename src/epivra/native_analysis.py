"""Restricted Python analysis on the host OS; no shell or unrestricted fallback."""
import asyncio
import base64
import hashlib
import json
import os
import shutil
import stat
import sys
import time
from pathlib import Path

from .analysis import DEFAULTS, filename
from .local_security import private_directory

COMPONENT = "analysis-native-v1"
BOOTSTRAP = (
    "import pathlib,runpy,sys; sys.dont_write_bytecode=True; "
    "sys.path.insert(0,sys.argv[4]); "
    "runpy.run_path(sys.argv[1],run_name='__main__',init_globals={"
    "'INPUT_DIR':pathlib.Path(sys.argv[2]),'OUTPUT_DIR':pathlib.Path(sys.argv[3])})"
)


def component_base(root):
    path = Path(root).resolve() / ".epivra-components" / COMPONENT
    # Scientific wheels contain deep paths. Use Win32 extended paths without
    # requiring users to change the system-wide LongPathsEnabled registry value.
    value = str(path)
    if os.name == "nt" and not value.startswith("\\\\?\\"):
        value = "\\\\?\\UNC\\" + value[2:] if value.startswith("\\\\") else "\\\\?\\" + value
        return Path(value)
    return path


def component(root):
    base = component_base(root)
    pointer = base / "current.json"
    if not pointer.is_file():
        return base / "unprepared"
    record = json.loads(pointer.read_text(encoding="utf-8"))
    if not isinstance(record, dict):
        raise ValueError("Invalid analysis component pointer")
    identity = record.get("identity")
    if not isinstance(identity, str) or len(identity) != 64 or any(c not in "0123456789abcdef" for c in identity):
        raise ValueError("Invalid analysis component identity")
    return base / identity


def settings(root, overrides):
    allowed = (set(DEFAULTS) - {"image", "pids"}) | {"backend"}
    if set(overrides) - allowed or overrides.get("backend") != "native":
        raise ValueError("Unknown native analysis settings")
    config = {k: v for k, v in DEFAULTS.items() if k not in {"image", "pids"}}
    config.update({k: v for k, v in overrides.items() if k != "backend"})
    if any(type(v) is not int or v < 1 for v in config.values()):
        raise ValueError("Analysis limits must be positive integers")
    ready = component(root) / "ready.json"
    if not ready.is_file():
        raise ValueError("Prepare the native Python analysis component in Settings first")
    identity = hashlib.sha256(ready.read_bytes()).hexdigest()
    if ready.parent.name != identity or not (ready.parent / "runtime/python.exe").is_file():
        raise ValueError("Analysis component needs repair in Settings")
    manifest = json.loads(ready.read_text(encoding="utf-8"))
    if (not isinstance(manifest, dict) or manifest.get("platform") != sys.platform
            or manifest.get("verified") is not True):
        raise ValueError("Analysis component is not verified for this platform")
    return {**config, "backend": "native", "image": "native:" + hashlib.sha256(ready.read_bytes()).hexdigest()}


def regular(path):
    info = path.lstat()
    if (stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400
            or (not stat.S_ISDIR(info.st_mode) and (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1))):
        raise ValueError("Analysis output contains a link or non-regular file")
    return info


def measured(folder, maximum):
    total, count = 0, 0
    regular(folder)
    for base, directories, files in os.walk(folder, followlinks=False):
        for name in directories + files:
            info = regular(Path(base) / name)
            count += 1
            total += info.st_size if stat.S_ISREG(info.st_mode) else 0
            if count > 1000 or total > maximum:
                raise ValueError("Analysis scratch/output limit exceeded")
    return total


async def settle_thread(task):
    """Repeated cancellation cannot abandon a thread that owns process handles."""
    if not isinstance(task, asyncio.Task):
        task = asyncio.create_task(task)
    cancelled = False
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            cancelled = True
    return task.result(), cancelled


class NativeSandbox:
    def __init__(self, root, runtime=None, component_root=None):
        self.root = Path(root).resolve()
        self.component_root = Path(component_root or root).resolve()
        self.runtime = Path(runtime).resolve() if runtime else None
        self.active = {}

    def folder(self, job):
        if len(job) != 64 or any(x not in "0123456789abcdef" for x in job):
            raise ValueError("invalid native job identity")
        path = self.root / "native-analysis" / job
        if path.resolve() != path or path.parent.resolve() != self.root / "native-analysis":
            raise ValueError("native staging must not redirect")
        return path

    async def run(self, job, folder, config, fresh, guard):
        if sys.platform != "win32":
            raise ValueError("Native analysis requires Windows x64")
        if not fresh:
            return {"status": "interrupted", "log": "Native execution was interrupted; no automatic rerun.", "files": []}
        runtime = self.runtime
        if config.get("backend") == "native":
            identity = config["image"].removeprefix("native:")
            if len(identity) != 64 or any(c not in "0123456789abcdef" for c in identity):
                raise ValueError("Invalid pinned native component")
            runtime = runtime or component_base(self.component_root) / identity / "runtime"
            ready = runtime.parent / "ready.json"
            if not ready.is_file() or "native:" + hashlib.sha256(ready.read_bytes()).hexdigest() != config["image"]:
                raise ValueError("Native component differs from the approved research runtime")
        if runtime is None:
            raise ValueError("Native analysis requires a pinned runtime")
        target = self.folder(job)
        if target.exists():
            raise ValueError("Native job staging already exists; reconciliation required")
        private_directory(target)
        inputs, outputs, scratch = (target / name for name in ("inputs", "outputs", "scratch"))
        shutil.copytree(folder, inputs)
        (inputs / "data").mkdir(exist_ok=True)
        outputs.mkdir()
        scratch.mkdir()
        python = runtime / "python.exe"
        if not python.is_file():
            raise ValueError("Native Python runtime is missing")
        moniker = "Epivra.Analysis." + hashlib.sha256((str(self.root) + job).encode()).hexdigest()[:40]
        manifest = target / "supervisor.json"
        specification = {**config, "runtime": str(runtime), "readonly": [str(runtime), str(inputs)],
                         "writable": [str(outputs), str(scratch)], "inputs": str(inputs / "data"),
                         "outputs": str(outputs), "script": str(inputs / "analysis.py"), "moniker": moniker}
        manifest.write_text(json.dumps(specification), encoding="utf-8")
        env = {k: v for k, v in os.environ.items() if k.upper() in {
            "SYSTEMROOT", "WINDIR", "SYSTEMDRIVE", "USERPROFILE", "APPDATA", "LOCALAPPDATA"}}
        env.update(TEMP=str(scratch), TMP=str(scratch), TMPDIR=str(scratch), HOME=str(scratch),
                   MPLCONFIGDIR=str(scratch / "matplotlib"), MPLBACKEND="Agg",
                   OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1",
                   PYTHONNOUSERSITE="1", PYTHONDONTWRITEBYTECODE="1")
        guard()
        def launch():
            from .sandbox_windows import WindowsProcess
            return WindowsProcess(
                [str(python), "-I", "-S", "-X", "utf8", "-c", BOOTSTRAP, str(inputs / "analysis.py"),
                 str(inputs / "data"), str(outputs), str(runtime / "Lib/site-packages")],
                [runtime, inputs], [outputs, scratch], outputs, env, config, moniker)
        process, cancelled = await settle_thread(asyncio.to_thread(launch))
        if cancelled:
            await settle_thread(asyncio.to_thread(process.close))
            process.output.close()
            raise asyncio.CancelledError()
        self.active[job] = process
        log = bytearray()
        exceeded = False
        def drain():
            nonlocal exceeded
            while chunk := process.output.read(65536):
                if len(log) + len(chunk) > 256 * 1024:
                    exceeded = True
                    process.kill()
                    return
                log.extend(chunk)
        reader = asyncio.create_task(asyncio.to_thread(drain))
        status = "failed"
        exit_code = None
        try:
            guard()
            process.start()
            deadline = time.monotonic() + config["timeout"]
            while process.poll() is None:
                guard()
                measured(outputs, config["output_mb"] * 1024 * 1024)
                measured(scratch, config["output_mb"] * 1024 * 1024)
                if time.monotonic() >= deadline:
                    status = "timeout"
                    process.kill()
                    break
                await asyncio.sleep(0.05)
            else:
                exit_code = process.poll()
                status = "succeeded" if exit_code == 0 else "failed"
        finally:
            # Reap before reading artifacts. Cancellation cannot strand a worker.
            _, cancelled = await settle_thread(asyncio.to_thread(process.close))
            _, read_cancelled = await settle_thread(reader)
            process.output.close()
            self.active.pop(job, None)
            (target / "reaped").write_text("reaped", encoding="utf-8")
            if cancelled or read_cancelled:
                raise asyncio.CancelledError()
        if exceeded:
            status = "resource_limit"
        files = []
        if status == "succeeded":
            measured(outputs, config["output_mb"] * 1024 * 1024)
            for path in sorted(outputs.rglob("*")):
                info = regular(path)
                if not stat.S_ISREG(info.st_mode):
                    continue
                if len(files) >= 100:
                    raise ValueError("Too many analysis outputs")
                with path.open("rb") as handle:
                    opened = os.fstat(handle.fileno())
                    if (opened.st_ino, opened.st_dev, opened.st_nlink) != (info.st_ino, info.st_dev, 1):
                        raise ValueError("Analysis output identity changed")
                    raw = handle.read(config["output_mb"] * 1024 * 1024 + 1)
                files.append({"name": filename(path.relative_to(outputs).as_posix()), "data": base64.b64encode(raw).decode()})
        return {"status": status, "log": log.decode("utf-8", errors="replace"), "files": files, "issues": [], "exit_code": exit_code}

    async def cleanup(self, job):
        process = self.active.pop(job, None)
        if process:
            _, cancelled = await settle_thread(asyncio.to_thread(process.close))
            process.output.close()
            if cancelled:
                raise asyncio.CancelledError()
        target = self.folder(job)
        if target.exists():
            # Windows crash recovery must revoke the old per-job SID first.
            if os.name == "nt" and not (target / "reaped").exists() and (target / "supervisor.json").is_file():
                from .sandbox_windows import cleanup_profile
                manifest = json.loads((target / "supervisor.json").read_text(encoding="utf-8"))
                runtime = Path(manifest["runtime"]).resolve()
                if self.runtime is not None:
                    if runtime != self.runtime:
                        raise ValueError("Unexpected native recovery runtime")
                elif not runtime.is_relative_to(component_base(self.component_root)):
                    raise ValueError("Unexpected native recovery runtime")
                await asyncio.to_thread(cleanup_profile, manifest["moniker"],
                                        [runtime, target / "inputs"])
            shutil.rmtree(target)
