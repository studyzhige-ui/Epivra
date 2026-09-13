"""Opt-in single-call baseline, using the same model and frozen task/corpus.

This measures the model without role handoffs, not the product research loop.
Requests/results use the operation ledger; an unknown call is never reissued.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
from pathlib import Path

from epivra.adapters import DeepSeek, JsonAPI, credentials
from epivra.domain import identity
from epivra.storage import Store


async def run(root: Path, case_id: str, run_id: str):
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", run_id):
        raise ValueError("invalid run ID")
    case = next(
        c
        for c in json.loads(
            (root / "evals/closed_loop_cases.json").read_text(encoding="utf-8")
        )
        if c["id"] == case_id
    )
    folder = root / ".epivra" / f"baseline-{case_id}-{run_id}"
    store = Store(folder / "research.db")
    api = JsonAPI(
        "https://api.deepseek.com", credentials(root / ".env")["DEEPSEEK_API_KEY"]
    )
    model = DeepSeek(api, stream=True)
    try:
        if not store.list(case_id, "direction"):
            c = store.create(case_id, case["task"], {"network": False})
            plan = store.put(
                case_id,
                "plan",
                {"text": "Single-call evaluation fixture"},
                (c.direction,),
            )
            store.command(case_id, "fixture", c.ref, "approve", {"plan": plan.ref})
        c = store.control(case_id)
        owner = store.work(case_id, c.ref, "lead", "Baseline fixture")
        work = store.work(case_id, c.ref, "investigator", case["task"], (), owner.ref)
        request = {
            "wire": model.prepare(
                {
                    "system": "你是一位严谨的研究者。根据用户提供的任务和资料给出可直接使用的答案，引用材料编号。",
                    "task": case["task"],
                    "sources": [
                        {"id": f"material-{i}", "text": s}
                        for i, s in enumerate(case["sources"])
                    ],
                    "tools": {},
                },
                None,
            )
        }
        # A fixed logical operation makes changed inputs conflict, never silently rerun.
        operation = identity("baseline", case_id, run_id)
        raw = store.admit(case_id, work.ref, c.epoch, operation, request)
        if raw is None:
            raw = await model.complete(request)
            store.settle(operation, raw)
        choice = raw.get("data", {}).get("choices", [{}])[0]
        if raw.get("http_status") != 200 or choice.get("finish_reason") != "stop":
            raise ValueError("baseline did not return a complete answer")
        (folder / "report.md").write_text(
            choice["message"]["content"], encoding="utf-8"
        )
        result = {
            "model": model.identity,
            "usage": raw["data"].get("usage", {}),
            "semantic_acceptance": "pending_primary_review",
        }
        (folder / "result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps(result), flush=True)
    finally:
        store.close()
        await api.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--case",
        required=True,
        choices=("decision", "archive", "measurement", "training"),
    )
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    asyncio.run(run(Path(__file__).resolve().parents[1], args.case, args.run_id))
