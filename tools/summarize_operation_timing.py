"""Summarize persisted operation timing without replaying any operation."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any


def intervals_union_seconds(intervals: list[tuple[float, float]]) -> float:
    valid = sorted((start, end) for start, end in intervals if end >= start)
    if not valid:
        return 0.0
    total = 0.0
    start, end = valid[0]
    for next_start, next_end in valid[1:]:
        if next_start <= end:
            end = max(end, next_end)
        else:
            total += end - start
            start, end = next_start, next_end
    return total + end - start


def _interval(row: dict[str, Any], start_key: str, end_key: str):
    start, end = row.get(start_key), row.get(end_key)
    if (
        type(start) not in (int, float)
        or type(end) not in (int, float)
        or end < start
    ):
        return None
    return float(start), float(end)


def summarize(calls: list[dict[str, Any]], summary: dict[str, Any] | None = None):
    external, queue, tracked = [], [], []
    per_resource: dict[str, list[float]] = defaultdict(list)
    timed, unknown = 0, 0
    admission_to_invoke = []
    for row in calls:
        if row.get("status") == "unknown":
            unknown += 1
        ext = _interval(row, "invoked_at", "settled_at")
        que = _interval(row, "queued_at", "admitted_at")
        if ext is not None:
            external.append(ext)
            tracked.append(ext)
            per_resource[str(row.get("resource") or "unknown")].append(ext[1] - ext[0])
            timed += 1
        if que is not None:
            queue.append(que)
            tracked.append(que)
        local = row.get("admission_to_invoke_seconds")
        if type(local) in (int, float) and local >= 0:
            admission_to_invoke.append(float(local))

    result = {
        "operations": len(calls),
        "timed_external_operations": timed,
        "operations_without_complete_external_span": len(calls) - timed,
        "unknown_operations": unknown,
        "external_sum_seconds": sum(end - start for start, end in external),
        "external_union_seconds": intervals_union_seconds(external),
        "queue_sum_seconds": sum(end - start for start, end in queue),
        "queue_union_seconds": intervals_union_seconds(queue),
        "tracked_wait_union_seconds": intervals_union_seconds(tracked),
        "admission_to_invoke_sum_seconds": sum(admission_to_invoke),
        "by_resource": {
            resource: {
                "operations": len(values),
                "sum_seconds": sum(values),
                "median_seconds": statistics.median(values),
                "max_seconds": max(values),
            }
            for resource, values in sorted(per_resource.items())
        },
    }
    if summary is not None:
        start, end = summary.get("started_at"), summary.get("finished_at")
        if type(start) in (int, float) and type(end) in (int, float) and end >= start:
            elapsed = float(end - start)
            result["run_elapsed_seconds"] = elapsed
            result["untracked_or_local_wall_seconds"] = max(
                0.0, elapsed - result["tracked_wait_union_seconds"]
            )
            result["note"] = (
                "Residual wall time includes local work and any uninstrumented waits; "
                "it is not a CPU-time measurement. Interval unions preserve overlap."
            )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("calls", type=Path)
    parser.add_argument("--summary", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    calls = json.loads(args.calls.read_text(encoding="utf-8"))
    if not isinstance(calls, list):
        raise SystemExit("calls must be a JSON list")
    summary = (
        json.loads(args.summary.read_text(encoding="utf-8"))
        if args.summary is not None
        else None
    )
    result = summarize(calls, summary)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        if args.output.exists():
            raise SystemExit("refuse to overwrite existing timing summary")
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
