"""Judge published reports against the rubric, and report resources beside it.

The two are printed together and never merged.  A report can be honest and
expensive, or cheap and overconfident, and a single combined number would hide
whichever half the reader cares about (`docs/ARCHITECTURE.md` §10.6).

Judging is ledger-guarded, so re-running this on an unchanged report replays the
stored verdict instead of paying again.  Editing the judge's prompt counts as
different work and correctly re-runs.

Usage::

    python tools/run_judge.py --database .deep-research-agent/1e-genre-shift.sqlite3
    python tools/run_judge.py --glob '.deep-research-agent/1e-*.sqlite3'
"""

from __future__ import annotations

import argparse
import asyncio
import glob as globbing
import importlib.util
import sys
from pathlib import Path

import aiosqlite

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


def _load(name: str, filename: str):  # noqa: ANN202
    spec = importlib.util.spec_from_file_location(name, ROOT / "evals" / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


resources = _load("eval_resources", "resources.py")
judge = _load("eval_judge", "judge.py")

from deep_research_agent.application import (  # noqa: E402
    build_runtimes,
    load_environment,
)
from deep_research_agent.artifact_store import SqliteArtifactStore  # noqa: E402
from deep_research_agent.config import load_config  # noqa: E402
from deep_research_agent.content_store import SqliteContentStore  # noqa: E402
from deep_research_agent.operations import SqliteOperationLedger  # noqa: E402
from deep_research_agent.sources import ArtifactValidationError  # noqa: E402


async def judge_one(database: Path, task_id: str, environ: dict[str, str]) -> bool:
    """Judge one task; returns whether a verdict was produced."""

    # The judge reads long reports and the whole evidence set, so it uses the
    # reasoning tier -- the same reason the Curator is never downgraded.
    runtime = build_runtimes(environ, roles=("reviewer",))["reviewer"]

    connection = await aiosqlite.connect(database)
    try:
        content = SqliteContentStore(connection)
        await content.setup()
        store = SqliteArtifactStore(connection, content, task_id=task_id)
        await store.setup()
        ledger = SqliteOperationLedger(connection, content)
        await ledger.setup()

        try:
            judgement = await judge.judge_report(
                store, ledger, model=runtime.model, execution=runtime.execution
            )
        except ArtifactValidationError as error:
            print(f"  跳过：{error}")
            return False

        print(judgement.render())
        run = resources.read_run(database, task_id)
        print(
            f"\n  资源（独立报告，不并入判定）："
            f"{run.model_calls} 次调用 / {run.searches} 次检索 / "
            f"{run.materials} 份素材"
            + (
                f" / 输入 {run.input_tokens:,} tok / 输出 {run.output_tokens:,} tok"
                if run.measured
                else " / token 未记录（该运行早于用量记账）"
            )
        )
        return True
    finally:
        await connection.close()


async def run(args: argparse.Namespace) -> int:
    environ = load_environment(ROOT / ".env")
    chosen = load_config(environ).model_for("reviewer")
    print(f"judge 模型：{chosen.provider.name}/{chosen.model_id}（{chosen.tier} 档）")

    paths = list(args.databases)
    if args.glob:
        paths.extend(Path(item) for item in sorted(globbing.glob(args.glob)))
    if not paths:
        print("给出至少一个数据库路径，或用 --glob")
        return 2

    judged = 0
    for database in paths:
        if not database.is_file():
            continue
        for task_id in resources.task_ids(database):
            print(f"\n=== {task_id} @ {database.stem} ===")
            if await judge_one(database, task_id, environ):
                judged += 1
    print(f"\n共判定 {judged} 份报告。")
    return 0 if judged else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", dest="databases", nargs="*", default=[], type=Path)
    parser.add_argument("--glob", default="")
    return asyncio.run(run(parser.parse_args(argv)))


if __name__ == "__main__":
    sys.exit(main())
