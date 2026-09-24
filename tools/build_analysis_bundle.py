"""Build a self-contained, verified Windows x64 analysis component."""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from build_analysis_extension import build as build_extension
from build_desktop import PYTHON, RUNTIMES

ROOT = Path(__file__).resolve().parents[1]
COMPILER_SHA256 = "b64b2aa936ebbfeecfbb2611df331a5474edebe1246b98c2f56d6ae4d58b71fc"


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def build(output, runtime_archive=None, compiler_wheel=None, wheelhouse=None, source_cache=None):
    if sys.platform != "win32":
        raise RuntimeError("Build and verify this component on Windows x64")
    output = output.resolve()
    if output.exists():
        raise FileExistsError("Use a fresh analysis output directory")
    with tempfile.TemporaryDirectory(prefix="epivra-analysis-build-") as folder:
        work = Path(folder)
        target, checksum = RUNTIMES["windows"]
        archive = runtime_archive or work / "python.tar.gz"
        if runtime_archive is None:
            url = ("https://github.com/astral-sh/python-build-standalone/releases/download/"
                   f"20260623/cpython-{PYTHON}%2B20260623-{target}-install_only_stripped.tar.gz")
            with urllib.request.urlopen(url, timeout=90) as response, archive.open("wb") as out:
                shutil.copyfileobj(response, out)
        if sha256(archive) != checksum:
            raise ValueError("CPython archive checksum mismatch")
        with tarfile.open(archive) as bundle:
            bundle.extractall(work / "extracted", filter="data")
        runtime = work / "extracted/python"
        command = [sys.executable, "-m", "pip", "--isolated", "install",
                   "--only-binary=:all:", "--require-hashes", "--no-deps",
                   "--python-version", "3.12", "--platform", "win_amd64", "--abi", "cp312",
                   "--implementation", "cp", "--target", str(runtime / "Lib/site-packages"),
                   "-r", str(ROOT / "packaging/analysis/requirements.lock")]
        if wheelhouse:
            command.extend(["--no-index", "--find-links", str(wheelhouse)])
        subprocess.run(command, check=True)
        if compiler_wheel is None:
            downloads = work / "compiler-download"
            subprocess.run([sys.executable, "-m", "pip", "--isolated", "download",
                            "--only-binary=:all:", "--no-deps", "--dest", str(downloads),
                            "ziglang==0.13.0"], check=True)
            compiler_wheel = next(downloads.glob("ziglang-*-win_amd64.whl"))
        if sha256(compiler_wheel) != COMPILER_SHA256:
            raise ValueError("Compiler distribution checksum mismatch")
        compiler_dir = work / "compiler"
        with zipfile.ZipFile(compiler_wheel) as bundle:
            bundle.extractall(compiler_dir)
        extension = build_extension(runtime, compiler_dir / "ziglang/zig.exe",
                                    work / "extension", source_cache)
        shutil.copy2(extension / "_overlapped.pyd", runtime / "DLLs/_overlapped.pyd")
        subprocess.run([sys.executable, str(ROOT / "tools/smoke_analysis_extension.py"),
                        "--runtime", str(runtime)], check=True, timeout=60)
        receipt = subprocess.check_output(
            [sys.executable, str(ROOT / "tools/smoke_native_analysis.py"),
             "--runtime", str(runtime), "--scientific"], text=True, encoding="utf-8", timeout=900)
        evidence = json.loads(receipt)
        files = {p.relative_to(runtime).as_posix(): sha256(p)
                 for p in sorted(runtime.rglob("*")) if p.is_file()
                 and "__pycache__" not in p.parts and p.suffix != ".pyc"}
        manifest = {"component": "analysis-native-v1", "platform": "win32",
                    "architecture": "x64", "python": PYTHON, "runtime_archive_sha256": checksum,
                    "compiler_archive_sha256": COMPILER_SHA256,
                    "requirements_sha256": sha256(ROOT / "packaging/analysis/requirements.lock"),
                    "extension": json.loads((extension / "build.json").read_text()),
                    "verification": evidence, "files": files}
        output.mkdir(parents=True)
        try:
            destination = output / "runtime.zip"
            with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as bundle:
                for name in files:
                    bundle.write(runtime / name, "runtime/" + name)
                bundle.writestr("manifest.json", json.dumps(manifest, sort_keys=True))
                bundle.write(ROOT / "packaging/analysis/PYTHON-LICENSE.txt", "PYTHON-LICENSE.txt")
                bundle.write(ROOT / "packaging/analysis/cpython-overlapped.diff", "cpython-overlapped.diff")
            (output / "bundle.json").write_text(json.dumps({
                "component": "analysis-native-v1", "sha256": sha256(destination),
                "bytes": destination.stat().st_size, "platform": "win32",
            }, indent=2), encoding="utf-8")
        except BaseException:
            # Leave incomplete build output for inspection; no catalog means not installable.
            (output / "bundle.json").unlink(missing_ok=True)
            raise
        print(json.dumps({"output": str(output), "bytes": destination.stat().st_size,
                          "verification": evidence}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist/analysis")
    parser.add_argument("--runtime-archive", type=Path)
    parser.add_argument("--compiler-wheel", type=Path)
    parser.add_argument("--wheelhouse", type=Path)
    parser.add_argument("--source-cache", type=Path)
    args = parser.parse_args()
    build(args.output, args.runtime_archive, args.compiler_wheel, args.wheelhouse, args.source_cache)
