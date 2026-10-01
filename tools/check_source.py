"""Check distributed source locally, on PRs and at release; tests stay local."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel-dir", type=Path, help="also build the distributable wheel")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    python = sys.executable
    commands = [
        [python, "tools/check_architecture.py"],
        [python, "-m", "ruff", "check", "src", "tools"],
        [python, "-m", "mypy"],
        *[["node", "--check", str(path.relative_to(root))]
          for path in sorted((root / "src/epivra/web").glob("*.js"))],
    ]
    if args.wheel_dir:
        commands.append([python, "-m", "build", "--wheel", "--outdir", str(args.wheel_dir.resolve())])
    print("Public source checks; private regression tests are run separately.", flush=True)
    for command in commands:
        print("+ " + " ".join(command), flush=True)
        subprocess.run(command, cwd=root, check=True)


if __name__ == "__main__":
    main()
