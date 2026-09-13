"""Opt-in paid, paired semantic review tests through the production Harness."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from epivra.adapters import DEFAULT_MODEL, DeepSeek, JsonAPI, credentials
from epivra.domain import identity
from epivra.harness import Harness
from epivra.storage import Store
from evals.review_cases import CASES


def source_snapshot(database: Path) -> dict:
    """Fingerprint immutable records without exporting private execution bodies."""
    with closing(
        sqlite3.connect(f"{database.resolve().as_uri()}?mode=ro", uri=True)
    ) as db:
        db.execute("BEGIN")
        publication = db.execute(
            "SELECT study,body FROM artifacts WHERE kind='publication' ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        if publication is None:
            raise ValueError("source run has no publication")
        return {
            "study": publication[0],
            "report": json.loads(publication[1])["report"],
            "records": identity(
                [r[0] for r in db.execute("SELECT ref FROM artifacts ORDER BY seq")]
            ),
        }


def bind_run(root: Path, folder: Path, cases: list, effort: str, source=None) -> dict:
    """Reject config drift before opening providers or mutating a prior run."""
    if effort not in {"low", "high", "max"}:
        raise ValueError("invalid reasoning effort")
    implementation = identity(
        [
            [str(p.relative_to(root)), p.read_text(encoding="utf-8")]
            for p in sorted((root / "src/epivra").glob("*.py"))
        ],
        Path(__file__).read_text(encoding="utf-8"),
    )
    config = {
        "model": DEFAULT_MODEL,
        "effort": effort,
        "implementation": implementation,
        "cases": cases,
        "source": source,
    }
    manifest = {"binding": identity(config), **config}
    path = folder / "fixture.json"
    if path.exists():
        if json.loads(path.read_text(encoding="utf-8")) != manifest:
            raise ValueError("review inputs or configuration changed; use a new run ID")
    elif folder.exists() and any(folder.iterdir()):
        raise ValueError("unbound review run is audit-only; use a new run ID")
    else:
        folder.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return manifest


async def run(
    root: Path,
    run_id: str,
    report_db: Path | None = None,
    mechanisms=False,
    only=None,
    expect_accept=False,
    effort="high",
):
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", run_id):
        raise ValueError("invalid run ID")
    folder = root / ".epivra" / f"review-{run_id}"
    database = folder / "research.db"
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
    snapshot = None
    if report_db:
        snapshot = {"path": str(report_db.resolve()), **source_snapshot(report_db)}
        cases = [{"id": snapshot["study"], "accept": expect_accept}]

    if only:
        cases = [c for c in cases if c["id"] in only]
        if {c["id"] for c in cases} != set(only):
            raise ValueError("unknown case selection")
    manifest = bind_run(root, folder, cases, effort, snapshot)
    if report_db and not database.exists():
        try:
            with closing(
                sqlite3.connect(f"{report_db.resolve().as_uri()}?mode=ro", uri=True)
            ) as source:
                with closing(sqlite3.connect(database)) as destination:
                    source.backup(destination)
            if source_snapshot(database) != {
                k: v for k, v in snapshot.items() if k != "path"
            }:
                raise ValueError("source changed while copying; use a new run ID")
        except BaseException:
            # A partial/unverified seed must never be resumed as the bound input.
            (folder / "fixture.json").unlink()
            raise
    store = Store(database)
    api = None
    results = []
    try:
        if snapshot:
            target_report = store.get(snapshot["study"], snapshot["report"])
        api = JsonAPI(
            "https://api.deepseek.com", credentials(root / ".env")["DEEPSEEK_API_KEY"]
        )
        harness = Harness(store, DeepSeek(api, stream=True, reasoning_effort=effort))
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
                    "run_binding": manifest["binding"],
                    "model": manifest["model"],
                    "effort": manifest["effort"],
                    "implementation": manifest["implementation"],
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
        if api is not None:
            await api.close()
        store.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--effort", choices=("low", "high", "max"), default="high")
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
            args.effort,
        )
    )
