"""Optional local components, installed only after an explicit user action."""

import json
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from .local_security import exclusive_lock, private_directory
from .platform_paths import (
    component_environment,
    docker_executable,
    python_executable,
    sandbox_resources,
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
            "analysis": (self.root / ".epivra-components/analysis-ready.json").is_file(),
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
        docker = docker_executable()
        self.phase("checking_docker")
        self._command([docker, "info", "--format", "{{.OSType}}"], log, timeout=30)
        recipe = sandbox_resources()
        if not (recipe / "Dockerfile").is_file():
            raise RuntimeError("This installation is missing the analysis image recipe.")
        self.phase("building_image")
        self._command([docker, "build", "-t", "epivra-analysis:1", str(recipe)], log)
        self.phase("validating")
        self._command([docker, "run", "--rm", "--network", "none",
                       "--entrypoint", "python", "epivra-analysis:1",
                       "-c", "import numpy,pandas,matplotlib; print('analysis-ready')"], log, timeout=120)
        (base / "analysis-ready.json").write_text('{"image":"epivra-analysis:1"}', encoding="utf-8")

    def _install(self, component):
        base = self.root / ".epivra-components"
        handle = None
        try:
            private_directory(base)
            handle = exclusive_lock(base / "setup.lock")
            with (base / "setup.log").open("wb") as log:
                if component == "documents":
                    self._documents(base, log)
                else:
                    self._analysis(base, log)
            with self.lock:
                self.job.update(state="ready", phase="complete")
        except Exception as exc:
            with self.lock:
                self.job.update(state="failed", error=(
                    "Docker Desktop is unavailable. Install and start it, then try again."
                    if isinstance(exc, FileNotFoundError) and component == "analysis"
                    else str(exc)))
        finally:
            if handle:
                handle.close()
            with self.lock:
                self.busy = False
