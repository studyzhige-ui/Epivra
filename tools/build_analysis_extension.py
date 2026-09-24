"""Build the pinned Windows CPython extension for restricted analysis."""
import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECIPE = ROOT / "packaging/analysis"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_digest(root):
    entries = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("Build inputs must not contain symbolic links")
        if path.is_file():
            entries[path.relative_to(root).as_posix()] = digest(path)
    return hashlib.sha256(json.dumps(entries, sort_keys=True).encode()).hexdigest()


def build(runtime, compiler, output, source_cache=None):
    """Never modify the input runtime; emit a separately reviewable artifact."""
    runtime, compiler, output = (p.resolve() for p in (runtime, compiler, output))
    if output.exists():
        raise FileExistsError("Use a fresh extension output directory")
    version = subprocess.check_output([str(compiler), "version"], text=True).strip()
    if version != "0.13.0":
        raise ValueError("This build recipe requires Zig 0.13.0")
    identity = subprocess.check_output(
        [str(runtime / "python.exe"), "-I", "-c",
         "import sys,struct,platform; print(sys.version.split()[0],"
         "struct.calcsize('P'),sys.implementation.name,platform.machine().lower(),"
         "hasattr(sys,'gettotalrefcount'))"],
        text=True).strip()
    if identity != "3.12.13 8 cpython amd64 False":
        raise ValueError("This build recipe requires CPython 3.12.13 x64")
    sources = json.loads((RECIPE / "cpython-sources.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="epivra-extension-") as folder:
        stage = Path(folder)
        for name, checksum in sources.items():
            destination = stage / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            if source_cache:
                shutil.copy2(source_cache / name, destination)
            else:
                url = "https://raw.githubusercontent.com/python/cpython/v3.12.13/" + name
                with urllib.request.urlopen(url, timeout=60) as response:
                    destination.write_bytes(response.read())
            if digest(destination) != checksum:
                raise ValueError("CPython source checksum mismatch: " + name)
        change = RECIPE / "cpython-overlapped.diff"
        subprocess.run(["git", "apply", "--check", str(change)], cwd=stage, check=True)
        subprocess.run(["git", "apply", str(change)], cwd=stage, check=True)
        extension = stage / "_overlapped.pyd"
        arguments = ["cc", "-target", "x86_64-windows-gnu", "-shared", "-O2",
                     "-I", str(runtime / "include"), str(stage / "Modules/overlapped.c"),
                     str(runtime / "python312.dll"), "-lws2_32", "-lmswsock",
                     "-o", str(extension)]
        subprocess.run([str(compiler), *arguments], cwd=stage, check=True)
        output.mkdir(parents=True)
        shutil.copy2(extension, output / extension.name)
        shutil.copy2(RECIPE / "PYTHON-LICENSE.txt", output / "PYTHON-LICENSE.txt")
        manifest = {
            "python": "3.12.13", "architecture": "x64", "compiler": "zig " + version,
            "target": "x86_64-windows-gnu", "optimization": "-O2",
            "source_sha256": sources, "change_sha256": digest(change),
            "extension_sha256": digest(extension),
            "python_dll_sha256": digest(runtime / "python312.dll"),
            "headers_tree_sha256": tree_digest(runtime / "include"),
            "compiler_tree_sha256": tree_digest(compiler.parent),
            "runtime_identity": identity,
            "verified": False,
        }
        (output / "build.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--zig", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-cache", type=Path)
    args = parser.parse_args()
    print(build(args.runtime, args.zig, args.output, args.source_cache))
