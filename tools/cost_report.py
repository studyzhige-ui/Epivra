"""Render the resource-utilisation report for finished runs.

Reads databases only -- no provider is ever called, so this costs nothing to
produce and can be run as often as wanted.

The cross-run table is the point.  Every 1e fixture passed on its own terms
while Material yield per search varied a hundredfold between them, so the axis
only becomes visible side by side (`docs/ARCHITECTURE.md` §10.6).

Usage::

    python tools/cost_report.py .deep-research-agent/*.sqlite3
    python tools/cost_report.py --glob '.deep-research-agent/1e-*.sqlite3'
"""

from __future__ import annotations

import argparse
import glob as globbing
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "eval_resources", ROOT / "evals" / "resources.py"
)
assert _spec is not None and _spec.loader is not None
resources = importlib.util.module_from_spec(_spec)
sys.modules["eval_resources"] = resources
_spec.loader.exec_module(resources)


def _tokens(value: int | None) -> str:
    if value is None:
        return "未记录"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}k"
    return str(value)


def _ratio(value: float | None) -> str:
    return "—" if value is None else f"{value:.2f}"


def _duration(seconds: float | None) -> str:
    if seconds is None:
        return "未记录"
    if seconds < 90:
        return f"{seconds:.0f}s"
    minutes = seconds / 60
    if minutes < 90:
        return f"{minutes:.0f}m"
    return f"{minutes / 60:.1f}h"


def render(cohort) -> str:  # noqa: ANN001 - duck-typed across the import shim
    lines: list[str] = []
    header = (
        f"{'run':<40}{'时长':>8}{'LLM':>6}{'检索':>6}{'抓取':>6}"
        f"{'素材':>6}{'输入tok':>10}{'输出tok':>10}{'素材/检索':>10}{'素材/快照':>10}"
    )
    lines.append(header)
    lines.append("-" * len(header))
    for run in sorted(cohort.runs, key=lambda item: item.label):
        lines.append(
            f"{run.label[:39]:<40}"
            f"{_duration(run.wall_clock_seconds):>8}"
            f"{run.model_calls:>6}{run.searches:>6}"
            f"{run.fetches_ok:>6}{run.materials:>6}"
            f"{_tokens(run.input_tokens):>10}{_tokens(run.output_tokens):>10}"
            f"{_ratio(run.materials_per_search):>10}"
            f"{_ratio(run.materials_per_snapshot):>10}"
        )

    lines.append("")
    lines.append(
        f"合计：{len(cohort.runs)} 次运行，{cohort.searches} 次检索，"
        f"{cohort.materials} 份素材，tokens {_tokens(cohort.total_tokens)}"
    )

    unmeasured = cohort.unmeasured_runs
    if unmeasured:
        # Stated rather than silently omitted: a total that quietly excludes runs
        # reads as complete when it is not.
        lines.append(
            f"其中 {len(unmeasured)} 次运行早于用量记账，token 未计入："
            + "、".join(unmeasured[:6])
            + ("…" if len(unmeasured) > 6 else "")
        )

    spread = cohort.yield_spread()
    if spread is not None:
        best, worst = spread
        lines.append("")
        lines.append("素材/检索的两端（资源缺陷首先在这里显形）：")
        lines.append(
            f"  最好 {best.label}：{_ratio(best.materials_per_search)}"
            f"（抓取失败率 {_ratio(best.fetch_failure_rate)}）"
        )
        lines.append(
            f"  最差 {worst.label}：{_ratio(worst.materials_per_search)}"
            f"（抓取失败率 {_ratio(worst.fetch_failure_rate)}）"
        )

    frozen = [run for run in cohort.runs if run.frozen_operations]
    if frozen:
        lines.append("")
        lines.append("冻结待对账的操作（每一条都是无法自动继续的付费不确定性）：")
        for run in frozen:
            lines.append(f"  {run.label}: {run.frozen_operations}")
    return "\n".join(lines)


def render_run_detail(run) -> str:  # noqa: ANN001 - duck-typed
    lines = [f"=== {run.label} ({run.database}) ==="]
    lines.append(f"时长 {_duration(run.wall_clock_seconds)}")
    if run.by_role:
        lines.append("按角色：")
        for item in run.by_role:
            lines.append(
                f"  {item.provider:<14}{item.calls:>5} 次"
                f"  输入 {_tokens(item.input_tokens):>9}"
                f"  输出 {_tokens(item.output_tokens):>9}"
            )
    if run.by_provider:
        lines.append("按模型：")
        for item in run.by_provider:
            lines.append(
                f"  {item.provider:<26}{item.calls:>5} 次"
                f"  输入 {_tokens(item.input_tokens):>9}"
                f"  输出 {_tokens(item.output_tokens):>9}"
            )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("databases", nargs="*", type=Path)
    parser.add_argument("--glob", default="", help="按模式匹配数据库")
    parser.add_argument("--detail", action="store_true", help="逐次运行按角色/模型展开")
    args = parser.parse_args(argv)

    paths = list(args.databases)
    if args.glob:
        paths.extend(Path(item) for item in sorted(globbing.glob(args.glob)))
    if not paths:
        parser.error("给出至少一个数据库路径，或用 --glob")

    cohort = resources.read_cohort(paths)
    if not cohort.runs:
        print("这些数据库里没有带操作记录的任务。")
        return 1
    print(render(cohort))
    if args.detail:
        for run in sorted(cohort.runs, key=lambda item: item.task_id):
            print()
            print(render_run_detail(run))
    return 0


if __name__ == "__main__":
    sys.exit(main())
