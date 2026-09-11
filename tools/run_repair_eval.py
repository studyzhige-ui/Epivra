"""Opt-in paid revision regression using copied evidence and a rejected review."""

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
from deep_research_agent.application import ResearchService
from deep_research_agent.harness import Harness
from deep_research_agent.storage import Store


async def run(root: Path, source_db: Path, run_id: str):
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", run_id):
        raise ValueError("invalid run ID")
    folder = root / ".deep-research-agent" / f"repair-{run_id}"
    database = folder / "research.db"
    if not database.exists():
        folder.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(
            f"{source_db.resolve().as_uri()}?mode=ro", uri=True
        ) as source:
            with sqlite3.connect(database) as destination:
                source.backup(destination)
    store = Store(database)
    api = JsonAPI(
        "https://api.deepseek.com", credentials(root / ".env")["DEEPSEEK_API_KEY"]
    )
    service = ResearchService(store, Harness(store, DeepSeek(api, stream=True)))
    try:
        row = store.db.execute(
            "SELECT study,ref FROM artifacts WHERE kind='review' AND json_extract(body,'$.accepted')=0 ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        if row is None:
            raise ValueError("revision requires a rejected review")
        study = row[0]
        markers = store.list(study, "eval_repair")
        if markers:
            marker = markers[0]
        else:
            review = store.get(study, row[1])
            report = next(
                store.get(study, ref)
                for ref in review.parents
                if store.get(study, ref).kind == "report"
            )
            c = store.control(study)
            request = store.get(study, c.direction).body["request"]
            marker = store.put(
                study,
                "eval_repair",
                {
                    "control": c.ref,
                    "request": request
                    + f"\n依据已有来源与独立核查 {review.ref} 修订报告 {report.ref}。保留正确内容，核对并处理全部修订要求，再经过独立核查后交付。不要重新收集已保存的资料。",
                    "last_operation": store.db.execute(
                        "SELECT coalesce(max(rowid),0) FROM operations"
                    ).fetchone()[0],
                    "steps": len(store.list(study, "step")),
                },
            )
        store.command(
            study,
            "repair-eval",
            marker.body["control"],
            "steer",
            {"request": marker.body["request"]},
        )
        task = asyncio.create_task(service.run(study))
        while not task.done():
            await asyncio.wait({task}, timeout=20)
            print(
                json.dumps(
                    {
                        "new_steps": len(store.list(study, "step"))
                        - marker.body["steps"],
                        "running": not task.done(),
                    }
                ),
                flush=True,
            )
        await task
        publications = [
            p
            for p in store.list(study, "publication")
            if store.control(study).direction in p.parents
        ]
        usage = sum(
            json.loads(r[0]).get("data", {}).get("usage", {}).get("total_tokens", 0)
            for r in store.db.execute(
                "SELECT result FROM operations WHERE rowid>? AND status='succeeded'",
                (marker.body["last_operation"],),
            )
        )
        result = {
            "published": bool(publications),
            "new_tokens": usage,
            "new_steps": len(store.list(study, "step")) - marker.body["steps"],
            "errors": service.errors,
            "manual_review": "required",
        }
        if publications:
            report = store.get(study, publications[-1].body["report"])
            result["report_ref"] = report.ref
            (folder / "report.md").write_text(report.body["text"], encoding="utf-8")
        (folder / "result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps(result), flush=True)
    finally:
        await service.close()
        await api.close()
        store.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-db", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    asyncio.run(run(Path(__file__).resolve().parents[1], args.source_db, args.run_id))
