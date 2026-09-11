"""Opt-in paid, paired semantic review tests through the production Harness."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from deep_research_agent.adapters import DeepSeek, JsonAPI, credentials
from deep_research_agent.harness import Harness
from deep_research_agent.storage import Store
from evals.review_cases import CASES


async def run(
    root: Path,
    run_id: str,
    report_db: Path | None = None,
    mechanisms=False,
    only=None,
    expect_accept=False,
):
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", run_id):
        raise ValueError("invalid run ID")
    folder = root / ".deep-research-agent" / f"review-{run_id}"
    database = folder / "research.db"
    if report_db and not database.exists():
        folder.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(
            f"{report_db.resolve().as_uri()}?mode=ro", uri=True
        ) as source:
            with sqlite3.connect(database) as destination:
                source.backup(destination)
    store = Store(database)
    cases = CASES
    if mechanisms:
        if report_db:
            raise ValueError(
                "mechanism pairs cannot be combined with a report database"
            )
        from evals.mechanism_cases import CASES as mechanism_cases

        cases = [
            {
                "id": c["id"] + "-" + variant,
                "task": c["task"],
                "sources": c["sources"],
                "report": c[variant]["report"],
                "accept": variant == "positive",
            }
            for c in mechanism_cases
            for variant in ("positive", "negative")
        ]
    target_report = None
    if report_db:
        row = store.db.execute(
            "SELECT study,body FROM artifacts WHERE kind='publication' ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        if row is None:
            store.close()
            raise ValueError("source run has no publication")
        target_report = store.get(row[0], json.loads(row[1])["report"])
        cases = [{"id": row[0], "accept": expect_accept}]

    if only:
        cases = [c for c in cases if c["id"] in only]
        if {c["id"] for c in cases} != set(only):
            store.close()
            raise ValueError("unknown case selection")
    api = JsonAPI(
        "https://api.deepseek.com", credentials(root / ".env")["DEEPSEEK_API_KEY"]
    )
    harness = Harness(store, DeepSeek(api, stream=True))
    results = []
    try:
        for case in cases:
            study = case["id"]
            try:
                c = store.control(study)
            except ValueError:
                c = store.create(
                    study,
                    case.get("task", "仅根据提供材料核查报告是否可交付。"),
                    {"network": False},
                )
                plan = store.put(
                    study, "plan", {"text": "评测夹具：独立核查"}, (c.direction,)
                )
                c = store.command(
                    study, "fixture-approval", c.ref, "approve", {"plan": plan.ref}
                )
            owner = store.work(study, c.ref, "lead", "评测报告")
            if target_report:
                report = target_report
                sources = [store.get(study, ref) for ref in report.body["evidence"]]
            else:
                sources = [
                    store.put(study, "source", {"origin": f"source-{i}", "text": text})
                    for i, text in enumerate(case["sources"])
                ]
                report = store.put(
                    study,
                    "report",
                    {"text": case["report"], "evidence": [s.ref for s in sources]},
                    (owner.ref, c.direction),
                )
            work = store.work(
                study,
                c.ref,
                "reviewer",
                "独立核查指定报告及来源，判断是否可直接交付。自行核对来源，不采用已有审查结论。",
                (report.ref, *(s.ref for s in sources)),
                owner.ref,
            )
            error = None
            try:
                while not harness.finished(study, work.ref):
                    await harness.step(study, work.ref)
                    print(
                        json.dumps(
                            {"case": study, "steps": len(store.list(study, "step"))}
                        ),
                        flush=True,
                    )
            except Exception as exc:
                error = type(exc).__name__
            reviews = [
                r for r in store.list(study, "review") if r.body.get("work") == work.ref
            ]
            accepted = reviews[-1].body["accepted"] if reviews else None
            results.append(
                {
                    "case": study,
                    "expected_accept": case["accept"],
                    "accepted": accepted,
                    "decision_matches": accepted is case["accept"],
                    "error": error,
                    "review": reviews[-1].body if reviews else None,
                    "manual_reason_check": "required",
                }
            )
            (folder / "result.json").write_text(
                json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        print(
            json.dumps(
                {
                    "matched": sum(r["decision_matches"] for r in results),
                    "cases": len(results),
                }
            ),
            flush=True,
        )
    finally:
        await api.close()
        store.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--expect-accept",
        action="store_true",
        help="Expected label for a copied positive report; never sent to the model",
    )
    parser.add_argument(
        "--only",
        nargs="+",
        help="Exact case IDs to repeat without rerunning the full suite",
    )
    parser.add_argument(
        "--mechanisms",
        action="store_true",
        help="36 primary-reviewed report calibration examples; not a behavior acceptance test",
    )
    parser.add_argument(
        "--report-db",
        type=Path,
        help="Copy and re-review a known failing report; original remains unchanged",
    )
    args = parser.parse_args()
    asyncio.run(
        run(
            Path(__file__).resolve().parents[1],
            args.run_id,
            args.report_db,
            args.mechanisms,
            args.only,
            args.expect_accept,
        )
    )
