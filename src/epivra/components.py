"""Optional local components, installed only after an explicit user action."""

import asyncio
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import uuid
import zipfile
from pathlib import Path, PurePosixPath

from .analysis import DEFAULTS
from .local_security import exclusive_lock, private_directory, protect
from .native_analysis import NativeSandbox, component, component_base, regular
from .platform_paths import (
    component_environment,
    python_executable,
)

DOCUMENT_REQUIREMENTS = ["docling==2.129.0", "onnxruntime==1.30.0"]
DOCUMENT_ID = f"documents-v1-py{sys.version_info.major}{sys.version_info.minor}"


def documents(root):
    path = Path(root) / ".epivra-components" / DOCUMENT_ID
    if (path / "ready.json").is_file() and (path / "packages/docling").is_dir() and (path / "models").is_dir():
        return path
    return None


def python_with_packages(packages, code, *args):
    bootstrap = "import sys; sys.path.insert(0,sys.argv.pop(1)); " + code
    return [python_executable(), "-I", "-c", bootstrap, str(packages), *map(str, args)]


def analysis_ready(root):
    try:
        installed = component(root)
        ready = installed / "ready.json"
        if hashlib.sha256(ready.read_bytes()).hexdigest() != installed.name:
            return False
        manifest = json.loads(ready.read_text(encoding="utf-8"))
        files = runtime_manifest(installed)["files"]
        for name in ("python.exe", "DLLs/_overlapped.pyd"):
            with (installed / "runtime" / name).open("rb") as stream:
                if hashlib.file_digest(stream, "sha256").hexdigest() != files.get(name):
                    return False
        return (isinstance(manifest, dict) and manifest.get("verified") is True and manifest.get("platform") == "win32"
                and (installed / "runtime/python.exe").is_file()
                and (installed / "runtime/DLLs/_overlapped.pyd").is_file())
    except (OSError, ValueError, KeyError):
        return False


def runtime_manifest(stage):
    manifest = json.loads((stage / "manifest.json").read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or not isinstance(manifest.get("files"), dict):
        raise ValueError("Invalid analysis file manifest")
    if any(not isinstance(value, str) or len(value) != 64
           or any(c not in "0123456789abcdef" for c in value)
           for value in manifest["files"].values()):
        raise ValueError("Invalid analysis file digest")
    return manifest


def verify_runtime(stage):
    manifest = runtime_manifest(stage)
    runtime = stage / "runtime"
    actual = {p.relative_to(runtime).as_posix(): p for p in runtime.rglob("*") if p.is_file()}
    if actual.keys() != manifest["files"].keys():
        raise ValueError("Analysis runtime file list differs from the manifest.")
    for name, path in actual.items():
        regular(path)
        with path.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != manifest["files"][name]:
                raise ValueError("Analysis runtime file integrity check failed.")
    return manifest


class Components:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.lock = threading.Lock()
        self.job = {"state": "idle", "component": None, "phase": "", "error": None}
        self.busy = False
        self.closing = False

    def status(self):
        with self.lock:
            job = dict(self.job)
        return {
            "documents": bool(documents(self.root)),
            "analysis": analysis_ready(self.root),
            "job": job,
        }

    def close(self):
        with self.lock:
            if self.busy:
                raise ValueError("Component setup is running. Wait for it to finish before quitting.")
            self.closing = True

    def start(self, component):
        if component not in {"documents", "analysis"}:
            raise ValueError("unknown optional component")
        with self.lock:
            if self.closing:
                raise ValueError("Epivra is shutting down.")
            if self.busy:
                raise ValueError("Component setup is already running.")
            self.busy = True
            self.job = {"state": "running", "component": component, "phase": "preparing", "error": None}
        threading.Thread(target=self._install, args=(component,), daemon=True).start()
        return self.status()

    def phase(self, name):
        with self.lock:
            self.job["phase"] = name

    def _command(self, args, log, timeout=3600):
        env = component_environment()
        env.update(HF_HUB_DISABLE_TELEMETRY="1", HF_HUB_DISABLE_PROGRESS_BARS="1",
                   PIP_NO_INPUT="1", PYTHONNOUSERSITE="1")
        result = subprocess.run(
            args, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
            env=env, timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        if result.returncode:
            raise RuntimeError("Setup command failed. See .epivra-components/setup.log in the data folder.")

    def _documents(self, base, log):
        if documents(self.root):
            return
        target = base / DOCUMENT_ID
        if target.exists():
            raise RuntimeError("An incomplete component directory exists; see the data folder before retrying.")
        with tempfile.TemporaryDirectory(prefix="documents-install-", dir=base) as folder:
            stage = Path(folder)
            private_directory(stage)
            packages = stage / "packages"
            self.phase("downloading_packages")
            self._command([python_executable(), "-I", "-m", "pip", "--isolated",
                           "--disable-pip-version-check", "install", "--progress-bar", "off",
                           "--only-binary=:all:", "--target", str(packages),
                           *DOCUMENT_REQUIREMENTS], log)
            self.phase("downloading_models")
            self._command(python_with_packages(
                packages,
                "from importlib.metadata import distribution; "
                "entry=next(e for e in distribution('docling').entry_points if e.name=='docling-tools'); "
                "entry.load()()",
                "models", "download", "layout", "tableformer", "rapidocr",
                "--rapidocr-backend-lang", "onnxruntime:chinese", "--output-dir", stage / "models",
            ), log)
            self.phase("validating")
            self._command(python_with_packages(
                packages, "from docling.document_converter import DocumentConverter; import onnxruntime"
            ), log, timeout=120)
            if not any((stage / "models").rglob("*.onnx")):
                raise RuntimeError("OCR model download did not produce ONNX weights.")
            (stage / "ready.json").write_text(
                json.dumps({"requirements": DOCUMENT_REQUIREMENTS}), encoding="utf-8")
            stage.rename(target)

    def _analysis(self, base, log):
        if sys.platform != "win32":
            raise ValueError("Built-in analysis requires Windows x64.")
        generations = component_base(self.root)
        generations.mkdir(parents=True, exist_ok=True)
        protect(generations)
        bundled = Path(sys.prefix) / "epivra-resources/analysis"
        recipe = bundled if bundled.is_dir() else Path(__file__).resolve().parents[2] / "dist/analysis"
        if not (recipe / "bundle.json").is_file():
            raise RuntimeError(
                "The built-in analysis archive is missing. Use the complete Windows download. "
                "Source developers: run python tools/build_analysis_bundle.py first.")
        catalog = json.loads((recipe / "bundle.json").read_text(encoding="utf-8"))
        if not isinstance(catalog, dict):
            raise ValueError("Invalid analysis archive catalog")
        archive = recipe / "runtime.zip"
        self.phase("verifying_archive")
        with archive.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if (catalog.get("component") != generations.name or catalog.get("platform") != "win32"
                or digest != catalog.get("sha256")):
            raise ValueError("Analysis archive integrity check failed. Download the complete application again.")
        if analysis_ready(self.root):
            installed = component(self.root)
            ready = json.loads((installed / "ready.json").read_text(encoding="utf-8"))
            if ready.get("bundle_sha256") == digest:
                self.phase("validating")
                try:
                    verify_runtime(installed)
                except (OSError, ValueError, KeyError):
                    pass  # Repair creates a new generation; never overwrite pinned research.
                else:
                    return
        with tempfile.TemporaryDirectory(prefix="analysis-install-", dir=base) as folder:
            stage = Path(folder)
            private_directory(stage)
            self.phase("extracting_runtime")
            with zipfile.ZipFile(archive) as bundle:
                entries = bundle.infolist()
                if len(entries) > 50000 or sum(e.file_size for e in entries) > 2 * 1024**3:
                    raise ValueError("Analysis archive exceeds its installation limit.")
                for entry in entries:
                    path = PurePosixPath(entry.filename)
                    if (path.is_absolute() or ".." in path.parts
                            or any(part.endswith((".", " ")) for part in path.parts)
                            or ":" in entry.filename or "\\" in entry.filename
                            or (entry.external_attr >> 16) & 0o170000 == 0o120000):
                        raise ValueError("Unsafe analysis archive entry.")
                bundle.extractall(stage)
            manifest = verify_runtime(stage)
            if (manifest.get("component") != generations.name or manifest.get("platform") != "win32"
                    or manifest.get("architecture") != "x64"):
                raise ValueError("Unsupported analysis runtime manifest.")
            runtime = stage / "runtime"
            self.phase("validating")
            async def verify():
                source = stage / "probe"
                source.mkdir()
                (source / "analysis.py").write_text(
                    "import numpy,pandas,statsmodels.api; from sklearn.linear_model import LinearRegression; "
                    "assert numpy.isclose(LinearRegression().fit([[0],[1]],[1,3]).predict([[2]])[0],5); "
                    "print('analysis-ready')", encoding="utf-8")
                sandbox = NativeSandbox(stage / "verification", runtime)
                job = hashlib.sha256(b"component-verification").hexdigest()
                try:
                    result = await sandbox.run(job, source, DEFAULTS, True, lambda: None)
                    log.write(result["log"].encode("utf-8"))
                    if result["status"] != "succeeded":
                        raise RuntimeError("Restricted analysis verification failed. See setup.log.")
                finally:
                    await sandbox.cleanup(job)
            asyncio.run(verify())
            # Only runtime and provenance are installed; test staging is not part of the component.
            shutil.rmtree(stage / "probe")
            shutil.rmtree(stage / "verification")
            (stage / "ready.json").write_text(json.dumps({
                "platform": "win32", "verified": True, "bundle_sha256": digest,
                "component": generations.name, "python": manifest["python"],
                "generation": uuid.uuid4().hex,
            }), encoding="utf-8")
            identity = hashlib.sha256((stage / "ready.json").read_bytes()).hexdigest()
            stage.rename(generations / identity)
            pointer = generations / ".current.tmp"
            pointer.write_text(json.dumps({"identity": identity}), encoding="utf-8")
            os.replace(pointer, generations / "current.json")

    def _install(self, component):
        base = self.root / ".epivra-components"
        handle = None
        try:
            base.mkdir(parents=True, exist_ok=True)
            protect(base)
            handle = exclusive_lock(base / "setup.lock")
            for stage in base.glob("analysis-install-*"):
                regular(stage)
                if stage.resolve() != stage:
                    raise ValueError("Unexpected component recovery directory")
                sandbox = NativeSandbox(stage / "verification", stage / "runtime")
                asyncio.run(sandbox.cleanup(hashlib.sha256(b"component-verification").hexdigest()))
                shutil.rmtree(stage)
            with (base / "setup.log").open("wb") as log:
                if component == "documents":
                    self._documents(base, log)
                else:
                    self._analysis(base, log)
            with self.lock:
                self.job.update(state="ready", phase="complete")
        except Exception as exc:
            with self.lock:
                self.job.update(state="failed", error=str(exc))
        finally:
            if handle:
                handle.close()
            with self.lock:
                self.busy = False
