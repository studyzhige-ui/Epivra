"""Small opt-in real research runs; hidden criteria never enter model context."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from deep_research_agent.adapters import DEFAULT_MODEL, credentials
from deep_research_agent.application import online_service
from deep_research_agent.domain import identity
from deep_research_agent.storage import Store


def export(store, study, folder, errors, running=False):
    """Export reviewable domain facts, excluding provider-private step bodies."""
    kinds = (
        "plan",
        "work",
        "work_result",
        "work_wait",
        "source",
        "evidence_anchor",
        "note",
        "memory",
        "report",
        "review",
        "publication",
        "observation",
    )
    trace = [
        {"seq": a.seq, "ref": a.ref, "kind": kind, "parents": a.parents, "body": a.body}
        for kind in kinds
        for a in store.list(study, kind)
    ]
    trace.sort(key=lambda a: a["seq"])
    (folder / "trace.json").write_text(
        json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    c = store.control(study)
    publications = [
        a for a in store.list(study, "publication") if c.direction in a.parents
    ]
    if publications:
        report = store.get(study, publications[-1].body["report"])
        (folder / "report.md").write_text(report.body["text"], encoding="utf-8")
    usage = sum(
        json.loads(r[0]).get("data", {}).get("usage", {}).get("total_tokens", 0)
        for r in store.db.execute(
            "SELECT result FROM operations WHERE status='succeeded'"
        )
    )
    result = {
        "running": running,
        "published": bool(publications),
        "unknown": len(store.unsettled(study)),
        "steps": len(store.list(study, "step")),
        "tokens": usage,
        "errors": errors,
        "semantic_acceptance": "pending_primary_review",
    }
    (folder / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return result


async def run(root, case_id, run_id, assess_only=False):
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", run_id):
        raise ValueError("invalid run ID")
    cases = json.loads(
        (root / "evals/closed_loop_cases.json").read_text(encoding="utf-8")
    )
    case = next(c for c in cases if c["id"] == case_id)
    folder = root / ".deep-research-agent" / f"closed-{case_id}-{run_id}"
    if assess_only and not (folder / "research.db").exists():
        raise ValueError("no existing run")
    corpus = folder / "corpus"
    implementation = identity(
        [
            [p.name, p.read_text(encoding="utf-8")]
            for p in sorted((root / "src/deep_research_agent").glob("*.py"))
        ]
    )
    binding = identity(case, DEFAULT_MODEL, implementation)
    manifest = folder / "fixture.json"
    if not assess_only and (
        manifest.exists()
        and json.loads(manifest.read_text(encoding="utf-8"))["binding"] != binding
    ):
        raise ValueError("fixture or model changed; use a new run ID")
    if not assess_only:
        corpus.mkdir(parents=True, exist_ok=True)
        manifest.write_text(
            json.dumps(
                {
                    "binding": binding,
                    "case": case_id,
                    "model": DEFAULT_MODEL,
                    "implementation": implementation,
                }
            ),
            encoding="utf-8",
        )
        for i, source in enumerate(case["sources"]):
            (corpus / f"material-{i}.txt").write_text(source, encoding="utf-8")
    store = Store(folder / "research.db")
    service, clients = None, []
    prior = folder / "result.json"
    errors = (
        json.loads(prior.read_text(encoding="utf-8")).get("errors", {})
        if prior.exists()
        else {}
    )
    try:
        if not store.list(case_id, "direction"):
            store.create(
                case_id,
                case["task"],
                {
                    "model": DEFAULT_MODEL,
                    "stream_model": True,
                    "network": False,
                    "local_roots": [str(corpus)],
                },
            )
        if not assess_only:
            service, clients = online_service(
                store, case_id, credentials(root / ".env")
            )
            for _ in range(2):
                task = asyncio.create_task(service.run(case_id))
                while not task.done():
                    await asyncio.wait({task}, timeout=20)
                    export(
                        store, case_id, folder, service.errors, running=not task.done()
                    )
                    print(
                        json.dumps(
                            {
                                "case": case_id,
                                "steps": len(store.list(case_id, "step")),
                                "running": not task.done(),
                            }
                        ),
                        flush=True,
                    )
                await task
                control = store.control(case_id)
                if control.approved or service.errors:
                    break
                plans = store.list(case_id, "plan")
                if not plans:
                    break
                store.command(
                    case_id,
                    "fixture-approval",
                    control.ref,
                    "approve",
                    {"plan": plans[-1].ref},
                )
            errors = {**service.errors, **service.work_errors}
    finally:
        print(json.dumps(export(store, case_id, folder, errors)), flush=True)
        if service:
            await service.close()
        for client in clients:
            await client.close()
        store.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--case",
        choices=["decision", "archive", "measurement", "training"],
        required=True,
    )
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--assess-only", action="store_true")
    args = parser.parse_args()
    asyncio.run(
        run(
            Path(__file__).resolve().parents[1],
            args.case,
            args.run_id,
            args.assess_only,
        )
    )
