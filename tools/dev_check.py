"""Resumable evidence for development checks, never a research execution driver."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import platform
import re
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WATCHED = ("src", "tests", "tools", ".github")
MODULES = ("httpx", "pypdf", "openpyxl", "questionary", "rich", "markdown_it", "docx", "mcp", "ruff", "mypy", "build")
FULL = (
    ("requirements", ("-m", "pip", "check")),
    ("compile", ("-m", "compileall", "-q", "src", "tests", "tools")),
    ("tests", ("-m", "unittest", "discover", "-s", "tests")),
    ("architecture", ("tools/check_architecture.py",)),
    ("lint", ("-m", "ruff", "check", "src", "tests", "tools")),
    ("types", ("-m", "mypy")),
    ("wheel", ("-m", "build", "--wheel")),
)
SMOKE = (("execution_tests", ("-m", "unittest", "discover", "-s", "tests", "-p", "test_dev_check.py", "-v")),)


def write_json(path: Path, value: dict) -> None:
    """Replace one checkpoint atomically, including on a same-volume Windows path."""
    fd, name = tempfile.mkstemp(prefix=".checkpoint-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def fingerprint(root: Path) -> str:
    """Hash code/config content, not mtimes, caches, installed packages or logs."""
    digest = hashlib.sha256()
    files = [root / "pyproject.toml"]
    for folder in WATCHED:
        files.extend(p for p in (root / folder).rglob("*") if p.is_file() and not any(x == "__pycache__" or x.endswith(".egg-info") for x in p.parts))
    for path in sorted(files):
        if path.is_symlink():
            raise ValueError("symlink in validation input")
        if path.is_file():
            digest.update(path.relative_to(root).as_posix().encode() + b"\0")
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def preflight(profile: str) -> dict:
    required = MODULES if profile == "full" else ()
    missing = [name for name in required if importlib.util.find_spec(name) is None]
    return {"python": sys.version.split()[0], "platform": platform.system(), "missing_modules": missing,
            "ready": not missing, "installs_attempted": False, "profile": profile}


def check_environment() -> dict[str, str]:
    """Do not pass provider or connector credentials into offline test commands."""
    return {k: v for k, v in os.environ.items()
            if not re.search(r"(?:^|_)(?:KEYS?|TOKENS?|SECRETS?|PASSWORDS?)(?:_\d+)?$", k, re.I)}


def stop_process_tree(process: subprocess.Popen) -> None:
    if os.name == "nt":
        result = subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15, check=False)
        if result.returncode and process.poll() is None:
            process.kill()  # Terminate the owned child even if tree enumeration is denied.
            process.wait(timeout=15)
            raise RuntimeError("validation process-tree termination failed; descendants unverified")
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    process.wait(timeout=15)


def execute(command: list[str], cwd: Path, log: Path, timeout: float) -> int:
    options = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
    with log.open("wb") as output:
        process = subprocess.Popen(command, cwd=cwd, env=check_environment(), stdin=subprocess.DEVNULL,
                                   stdout=output, stderr=subprocess.STDOUT, **options)
        try:
            return process.wait(timeout=timeout)
        except BaseException:
            stop_process_tree(process)
            raise


def run_checks(root: Path, output: Path, profile: str, timeout: float = 480) -> int:
    """No implicit resume: an interrupted gate is unknown until explicitly rerun."""
    output = output.resolve()
    root = root.resolve()
    if any(output.is_relative_to(root / name) for name in WATCHED):
        raise ValueError("validation output must not change a watched input directory")
    output.mkdir(parents=True, exist_ok=False)
    check = preflight(profile)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True, timeout=10).strip()
    before = fingerprint(root)
    state = {"version": 1, "state": "running" if check["ready"] else "blocked_environment",
             "head": head, "input_sha256": before, "profile": profile, "environment": check,
             "started_at": time.time(), "steps": [], "scope": "offline development only; no paid evaluation"}
    def save():
        write_json(output / "summary.json", state)
    save()
    if not check["ready"]:
        return 2
    for name, args in FULL if profile == "full" else SMOKE:
        log = output / (name + ".log")
        row = {"name": name, "state": "running", "argv": [sys.executable, *args], "started_at": time.time(), "log": log.name}
        state["steps"].append(row)
        save()  # A hard process/session death leaves a non-successful durable receipt.
        try:
            code = execute(row["argv"], root, log, timeout)
            row.update(returncode=code, state="passed" if code == 0 else "failed")
        except subprocess.TimeoutExpired:
            row.update(state="timeout", returncode=None)
        except BaseException as exc:
            row.update(state="interrupted", error_type=type(exc).__name__, returncode=None)
            state["state"] = "interrupted"
            save()
            raise
        row.update(finished_at=time.time(), log_sha256=hashlib.sha256(log.read_bytes()).hexdigest())
        if row["state"] != "passed":
            state["state"] = row["state"]
        save()
        print(json.dumps({"step": name, "state": row["state"]}), flush=True)
        if row["state"] != "passed":
            return 1
    state.update(state="passed" if before == fingerprint(root) else "stale_inputs", finished_at=time.time())
    save()
    return 0 if state["state"] == "passed" else 1


def inspect_result(root: Path, output: Path) -> dict:
    state = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    logs_valid = True
    for row in state["steps"]:
        path = output / row["log"]
        if path.name != row["log"]:
            raise ValueError("invalid log path")
        logs_valid &= path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == row.get("log_sha256")
    matched = state["input_sha256"] == fingerprint(root)
    plan = FULL if state["profile"] == "full" else SMOKE
    steps_valid = ([x["name"] for x in state["steps"]] == [name for name, _ in plan]
                   and all(x["state"] == "passed" and x.get("returncode") == 0 for x in state["steps"]))
    return {"state": state["state"], "profile": state["profile"], "head": state["head"],
            "inputs_match": matched, "logs_valid": bool(logs_valid),
            "verified_success": bool(state["state"] == "passed" and steps_valid and matched and logs_valid),
            "steps": [{"name": x["name"], "state": x["state"]} for x in state["steps"]]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("preflight", "run", "inspect"))
    parser.add_argument("--profile", choices=("smoke", "full"), default="full")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--timeout-seconds", type=float, default=480, help="development command timeout; not a product research limit")
    args = parser.parse_args()
    if args.timeout_seconds <= 0:
        parser.error("positive timeout required")
    if args.action == "preflight":
        result = preflight(args.profile)
        print(json.dumps(result))
        return 0 if result["ready"] else 2
    if args.output is None:
        parser.error("--output is required for run/inspect")
    if args.action == "run":
        return run_checks(ROOT, args.output, args.profile, args.timeout_seconds)
    result = inspect_result(ROOT, args.output)
    print(json.dumps(result))
    return 0 if result["verified_success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
