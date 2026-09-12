"""Container supervisor: no network or credentials; emit bounded JSON once."""

import base64
import json
import os
import signal
import stat
import subprocess
import sys
from pathlib import Path


def main():
    timeout = float(sys.argv[1])
    limit = int(sys.argv[2])
    status = "failed"
    with open("/tmp/analysis.log", "wb") as log:
        child = subprocess.Popen(
            [sys.executable, "-I", "/inputs/analysis.py"],
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            code = child.wait(timeout=timeout)
            status = "succeeded" if code == 0 else "failed"
        except subprocess.TimeoutExpired:
            status, code = "timeout", None
        finally:
            # Reap descendants even if the direct Python process has exited.
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            child.wait()
    files, total, issues = [], 0, []
    for path in Path("/outputs").rglob("*"):
        mode = path.lstat().st_mode
        if stat.S_ISDIR(mode):
            continue
        if not stat.S_ISREG(mode) or path.is_symlink():
            issues.append("Rejected non-regular output: " + path.name)
            continue
        size = path.stat().st_size
        if len(files) >= 100 or total + size > limit:
            issues.append("Output limit exceeded")
            break
        raw = path.read_bytes()
        total += len(raw)
        files.append(
            {
                "name": path.relative_to("/outputs").as_posix(),
                "data": base64.b64encode(raw).decode("ascii"),
            }
        )
    log_path = Path("/tmp/analysis.log")
    with log_path.open("rb") as stream:
        log = stream.read(256 * 1024)
    if log_path.stat().st_size > len(log):
        issues.append("Log truncated at 256 KiB")
    print(
        json.dumps(
            {
                "status": status,
                "exit_code": code,
                "log": log.decode("utf-8", errors="replace"),
                "files": files,
                "issues": issues,
            },
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
