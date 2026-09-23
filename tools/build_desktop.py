"""Build native desktop downloads. Run on Windows x64 or macOS arm64."""

import argparse
import hashlib
import io
import json
import os
import platform
import plistlib
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
    "macos": ("aarch64-apple-darwin", "41df7d3ae4757e84b97874f76d634268456aaa271740d33f968d826374998fb7"),
}


def run(*args, **kwargs):
    subprocess.run(list(map(str, args)), check=True, **kwargs)


def build(output, runtime_archive=None):
    windows = sys.platform == "win32"
    machine = platform.machine().lower()
    if not ((windows and machine in {"amd64", "x86_64"}) or
            (sys.platform == "darwin" and machine == "arm64")):
        raise RuntimeError("Build on Windows x64 or macOS Apple Silicon.")
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    name = f"Epivra-{version}-{'windows-x64' if windows else 'macos-arm64'}"
    output.mkdir(parents=True, exist_ok=True)
    package = output / (name if windows else "Epivra.app")
    if package.exists():
        raise FileExistsError(f"Use a new output directory: {package}")
    resources = package if windows else package / "Contents/Resources"
    resources.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix="epivra-build-") as work:
        work = Path(work)
        target, checksum = RUNTIMES["windows" if windows else "macos"]
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
        python = runtime / ("python.exe" if windows else "bin/python3")
        wheels = work / "wheels"
        run(sys.executable, "-m", "build", "--wheel", "--outdir", wheels, ROOT)
        wheel = next(wheels.glob("epivra-*.whl"))
        run(python, "-I", "-m", "ensurepip", "--upgrade")
        run(python, "-I", "-m", "pip", "--isolated", "--disable-pip-version-check",
            "install", "--only-binary=:all:", "--no-cache-dir", str(wheel) + "[mcp]")
        run(python, "-I", "-m", "pip", "check")
        shutil.copytree(ROOT / "sandbox", runtime / "epivra-resources/sandbox",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
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
        }, indent=2), encoding="utf-8")

        import resvg_py
        from PIL import Image

        image = Image.open(io.BytesIO(resvg_py.svg_to_bytes(
            svg_path=str(ROOT / "src/epivra/web/favicon.svg"), width=1024, height=1024)))
        if windows:
            icon = work / "epivra.ico"
            image.save(icon, sizes=[(n, n) for n in (16, 32, 48, 64, 128, 256)])
            csc = Path(os.environ["WINDIR"]) / "Microsoft.NET/Framework64/v4.0.30319/csc.exe"
            run(csc, "/nologo", "/target:winexe", "/platform:x64",
                "/reference:System.Windows.Forms.dll", f"/win32icon:{icon}",
                f"/out:{package / 'Epivra.exe'}", ROOT / "packaging/windows/Launcher.cs")
        else:
            image.save(resources / "Epivra.icns")
            executable = package / "Contents/MacOS/Epivra"
            executable.parent.mkdir()
            run("clang", "-arch", "arm64", "-mmacosx-version-min=14.0",
                ROOT / "packaging/macos/launcher.c", "-o", executable)
            with (package / "Contents/Info.plist").open("wb") as handle:
                plistlib.dump({
                    "CFBundleExecutable": "Epivra", "CFBundleName": "Epivra",
                    "CFBundleIdentifier": "app.epivra.desktop",
                    "CFBundleVersion": version, "CFBundleShortVersionString": version,
                    "CFBundlePackageType": "APPL", "CFBundleIconFile": "Epivra.icns",
                    "LSMinimumSystemVersion": "14.0", "NSHighResolutionCapable": True,
                }, handle)
            # Ad-hoc signatures preserve arm64 integrity; they do NOT confer
            # Developer ID trust or replace Apple notarization.
            mach = {b"\xfe\xed\xfa\xcf", b"\xcf\xfa\xed\xfe",
                    b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca"}
            for path in runtime.rglob("*"):
                if path.is_file() and not path.is_symlink():
                    with path.open("rb") as stream:
                        header = stream.read(4)
                    if header in mach:
                        run("codesign", "--force", "--sign", "-", path)
            run("codesign", "--force", "--sign", "-", package)
            run("codesign", "--verify", "--deep", "--strict", package)

    # Relocate and launch from outside the bundle, without system Python on PATH.
    run(sys.executable, ROOT / "tools/smoke_desktop.py", package)
    if windows:
        artifact = Path(shutil.make_archive(str(output / name), "zip", output, package.name))
    else:
        with tempfile.TemporaryDirectory(prefix="epivra-dmg-") as folder:
            stage = Path(folder)
            run("ditto", package, stage / "Epivra.app")
            (stage / "Applications").symlink_to("/Applications")
            artifact = output / (name + ".dmg")
            run("hdiutil", "create", "-volname", "Epivra", "-srcfolder", stage,
                "-format", "UDZO", "-ov", artifact)
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    (output / (artifact.name + ".sha256")).write_text(
        f"{digest}  {artifact.name}\n", encoding="utf-8")
    print(artifact)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "dist/desktop")
    parser.add_argument("--runtime-archive", type=Path)
    args = parser.parse_args()
    build(args.output.resolve(), args.runtime_archive)
