"""Build the Windows x64 desktop download with built-in restricted analysis."""

import argparse
import hashlib
import io
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = "3.12.13"
RUNTIMES = {
    "windows": ("x86_64-pc-windows-msvc", "de3e362376859b060fa8b856c434efa81fcf6d4ede3d6e177c7e2169670cac50"),
}


def run(*args, **kwargs):
    subprocess.run(list(map(str, args)), check=True, **kwargs)


def build(output, runtime_archive=None, analysis_bundle=None, wheelhouse=None):
    machine = platform.machine().lower()
    if sys.platform != "win32" or machine not in {"amd64", "x86_64"}:
        raise RuntimeError("Build on Windows x64.")
    analysis_bundle = analysis_bundle or ROOT / "dist/analysis"
    if not (analysis_bundle / "bundle.json").is_file():
        raise RuntimeError("Build the verified analysis component with tools/build_analysis_bundle.py first.")
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    name = f"Epivra-{version}-windows-x64"
    output.mkdir(parents=True, exist_ok=True)
    package = output / name
    if package.exists():
        raise FileExistsError(f"Use a new output directory: {package}")
    resources = package
    resources.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix="epivra-build-") as work:
        work = Path(work)
        target, checksum = RUNTIMES["windows"]
        archive = runtime_archive or work / "runtime.tar.gz"
        if runtime_archive is None:
            url = ("https://github.com/astral-sh/python-build-standalone/releases/download/"
                   f"20260623/cpython-{PYTHON}%2B20260623-{target}-install_only_stripped.tar.gz")
            with urllib.request.urlopen(url, timeout=90) as response, archive.open("wb") as handle:
                shutil.copyfileobj(response, handle)
        if hashlib.sha256(archive.read_bytes()).hexdigest() != checksum:
            raise RuntimeError("CPython runtime checksum mismatch.")
        with tarfile.open(archive) as bundle:
            bundle.extractall(work / "extracted", filter="data")
        runtime = resources / "runtime"
        shutil.copytree(work / "extracted/python", runtime, symlinks=True)
        python = runtime / "python.exe"
        wheels = work / "wheels"
        run(sys.executable, "-m", "build", "--wheel", "--outdir", wheels, ROOT)
        wheel = next(wheels.glob("epivra-*.whl"))
        run(python, "-I", "-m", "ensurepip", "--upgrade")
        install = [python, "-I", "-m", "pip", "--isolated", "--disable-pip-version-check",
                   "install", "--only-binary=:all:", "--require-hashes", "--no-cache-dir",
                   "-r", ROOT / "packaging/windows/requirements.lock"]
        if wheelhouse:
            install.extend(["--no-index", "--find-links", wheelhouse])
        run(*install)
        run(python, "-I", "-m", "pip", "--isolated", "--disable-pip-version-check",
            "install", "--no-deps", str(wheel) + "[mcp]")
        run(python, "-I", "-m", "pip", "check")
        shutil.copytree(analysis_bundle, runtime / "epivra-resources/analysis")
        for pattern in ("LICENSE*", "COPYING*", "NOTICE*"):
            for source in ROOT.glob(pattern):
                if source.is_file():
                    shutil.copy2(source, resources / source.name)
        # Retain upstream distribution metadata and license files in site-packages.
        manifest = subprocess.check_output(
            [str(python), "-I", "-m", "pip", "list", "--format=json"], text=True)
        (resources / "THIRD-PARTY-PACKAGES.json").write_text(manifest, encoding="utf-8")
        shutil.copy2(ROOT / "packaging/START-HERE.txt", resources / "START-HERE.txt")
        (resources / "BUILD.json").write_text(json.dumps({
            "version": version, "platform": sys.platform, "architecture": machine,
            "python": PYTHON,
            "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()),
            "signed": False,
            "source_wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
            "analysis_bundle": json.loads((analysis_bundle / "bundle.json").read_text(encoding="utf-8")),
        }, indent=2), encoding="utf-8")

        import resvg_py
        from PIL import Image

        image = Image.open(io.BytesIO(resvg_py.svg_to_bytes(
            svg_path=str(ROOT / "src/epivra/web/favicon.svg"), width=1024, height=1024)))
        icon = work / "epivra.ico"
        image.save(icon, sizes=[(n, n) for n in (16, 32, 48, 64, 128, 256)])
        csc = Path(os.environ["WINDIR"]) / "Microsoft.NET/Framework64/v4.0.30319/csc.exe"
        run(csc, "/nologo", "/target:winexe", "/platform:x64",
            "/reference:System.Windows.Forms.dll", f"/win32icon:{icon}",
            f"/out:{package / 'Epivra.exe'}", ROOT / "packaging/windows/Launcher.cs")

    return finalize(package)


def finalize(package):
    """Validate the complete existing bundle before writing its release archive."""
    package = package.resolve()
    run(sys.executable, ROOT / "tools/smoke_desktop.py", package)
    artifact = Path(shutil.make_archive(str(package), "zip", package.parent, package.name))
    with artifact.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    (package.parent / (artifact.name + ".sha256")).write_text(
        f"{digest}  {artifact.name}" + chr(10), encoding="utf-8")
    print(artifact)
    return artifact


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "dist/desktop")
    parser.add_argument("--runtime-archive", type=Path)
    parser.add_argument("--analysis-bundle", type=Path)
    parser.add_argument("--wheelhouse", type=Path)
    args = parser.parse_args()
    build(args.output.resolve(), args.runtime_archive, args.analysis_bundle, args.wheelhouse)
