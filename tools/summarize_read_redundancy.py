"""Summarize exact repeated public read results without judging necessity."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

READ_TOOLS = {"read_source", "read_artifact", "read_artifact_range", "read_report"}


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def summarize(artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    works = {
        row["ref"]: row.get("body", {})
        for row in artifacts
        if row.get("kind") == "work"
    }
    groups: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    totals = Counter()
    for row in artifacts:
        if row.get("kind") != "observation":
            continue
        body = row.get("body", {})
        tool = body.get("tool")
        result = body.get("result")
        if tool not in READ_TOOLS or body.get("failure") or not isinstance(result, dict):
            continue
        work = next((p for p in row.get("parents", []) if p in works), None)
        role = str(works.get(work, {}).get("role") or "unknown")
        digest = hashlib.sha256(canonical(result).encode()).hexdigest()
        groups[(role, str(tool), digest)].append(int(row.get("seq", 0)))
        totals[(role, str(tool))] += 1

    repeated = []
    repeated_count = 0
    for (role, tool, digest), seqs in sorted(groups.items()):
        if len(seqs) < 2:
            continue
        repeated_count += len(seqs) - 1
        repeated.append(
            {
                "role": role,
                "tool": tool,
                "result_sha256": digest,
                "occurrences": len(seqs),
                "additional_identical_reads": len(seqs) - 1,
                "sequences": seqs,
            }
        )

    total_reads = sum(totals.values())
    return {
        "successful_public_reads": total_reads,
        "additional_identical_read_results": repeated_count,
        "exact_repeat_fraction": repeated_count / total_reads if total_reads else 0.0,
        "by_role_tool": [
            {"role": role, "tool": tool, "reads": count}
            for (role, tool), count in sorted(totals.items())
        ],
        "repeated_groups": repeated,
        "interpretation": (
            "Exact repeated public results are a diagnostic signal only. "
            "A repeat may be deliberate re-verification or recovery after context "
            "compaction; this summary does not label it waste or change runtime behavior."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifacts", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rows = json.loads(args.artifacts.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise SystemExit("public-artifacts must be a JSON list")
    result = summarize(rows)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        if args.output.exists():
            raise SystemExit("refuse to overwrite prior diagnostic evidence")
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
