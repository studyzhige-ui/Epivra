"""Opt-in paid Flash research evaluation; fixed runs resume and replay."""

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
from deep_research_agent.storage import Store
from evals.research_case import QUESTION, assess, corpus


async def run(root: Path, size: int, run_id: str, assess_only: bool = False):
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", run_id):
        raise ValueError("invalid run ID")
    folder = root / ".deep-research-agent" / f"eval-{size}-{run_id}"
    if assess_only and not (folder / "research.db").exists():
        raise ValueError("assessment requires an existing run")
    prior = (
        json.loads((folder / "result.json").read_text(encoding="utf-8"))
        if (folder / "result.json").exists()
        else {}
    )
    gold = corpus(folder / "corpus", size)
    store = Store(folder / "research.db")
    study = "lumina"
    service = None
    clients = []
    try:
        try:
            store.control(study)
        except ValueError:
            store.create(
                study,
                QUESTION,
                {
                    "network": False,
                    "model": DEFAULT_MODEL,
                    "stream_model": True,
                    "local_roots": [str(folder / "corpus")],
                },
            )
        if not assess_only:
            service, clients = online_service(store, study, credentials(root / ".env"))
            for _ in range(2):
                task = asyncio.create_task(service.run(study))
                while not task.done():
                    await asyncio.wait({task}, timeout=20)
                    print(
                        json.dumps(
                            {
                                "steps": len(store.list(study, "step")),
                                "sources": len(store.list(study, "source")),
                                "running": not task.done(),
                            }
                        ),
                        flush=True,
                    )
                await task
                control = store.control(study)
                if control.approved or service.errors:
                    break
                plans = store.list(study, "plan")
                if not plans:
                    break
                # Explicit fixture approval; production approval remains user-owned.
                store.command(
                    study,
                    "eval-approval",
                    control.ref,
                    "approve",
                    {"plan": plans[-1].ref},
                )
        result = {
            **assess(store, study, gold),
            "errors": service.errors if service else prior.get("errors", {}),
            "work_errors": service.work_errors
            if service
            else prior.get("work_errors", {}),
            "model": DEFAULT_MODEL,
            "corpus_size": size,
        }
        usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        for row in store.db.execute(
            "SELECT result FROM operations WHERE status='succeeded'"
        ):
            raw = json.loads(row[0])
            counts = raw.get("data", {}).get("usage", {})
            for field in usage:
                usage[field] += counts.get(field, 0)
        result["usage"] = usage
        if result["published"]:
            report = store.get(study, result["report_ref"])
            (folder / "report.md").write_text(report.body["text"], encoding="utf-8")
        (folder / "result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps(result, ensure_ascii=False), flush=True)
    finally:
        if service:
            await service.close()
        for client in clients:
            await client.close()
        store.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=int, choices=[30, 100], default=30)
    parser.add_argument("--run-id", default="baseline")
    parser.add_argument("--assess-only", action="store_true")
    args = parser.parse_args()
    asyncio.run(
        run(
            Path(__file__).resolve().parents[1],
            args.sources,
            args.run_id,
            args.assess_only,
        )
    )
