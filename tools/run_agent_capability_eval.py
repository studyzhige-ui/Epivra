"""Paired real-model capability probes; Agent chooses its own sequence of tools.

Six completed decisions per probe is a diagnostic scope, not a product limit.
No web calls, predetermined tool script, answer labels, or report length limits.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import epivra
from epivra.citations import render
from epivra.domain import identity
from epivra.harness import Harness
from epivra.models import create_model, freeze_model_settings
from epivra.storage import Store
from evals.agent_capability_cases import CASES, request_cases
from tools.run_live_eval import collect, save

BASELINE = "6bcd5a2588cab7c4952525902e438ab78df5f7c0"


def seed(store, case_id):
    case = CASES[case_id]
    policy = freeze_model_settings(
        {
            "provider": "deepseek",
            "model": "deepseek-flash",
            "stream_model": True,
            "network": False,
            "as_of_date": "2026-09-20",
        }
    )
    c = store.create(case_id, case["task"], policy)
    p = store.put(
        case_id,
        "plan",
        {
            "text": "Use the supplied original records; pursue the evidence required to answer accurately."
        },
        (c.direction,),
    )
    c = store.command(case_id, "approved-probe", c.ref, "approve", {"plan": p.ref})
    owner = store.work(case_id, c.ref, "lead", "Coordinate")
    sources = [
        store.put(case_id, "source", {**s, "coverage": "complete"})
        for s in case["sources"]
    ]
    if case_id.startswith("source-"):
        return store.work(
            case_id,
            c.ref,
            "investigator",
            case["task"],
            tuple(s.ref for s in sources),
            owner.ref,
        ), policy
    producer = store.work(
        case_id,
        c.ref,
        "investigator",
        "Verify the original register",
        tuple(s.ref for s in sources),
        owner.ref,
    )
    finding = store.put(
        case_id,
        "work_result",
        {
            "text": sources[0].body["text"],
            "producer": producer.ref,
            "refs": [sources[0].ref],
        },
        (producer.ref, sources[0].ref),
    )
    old_writer = store.work(
        case_id, c.ref, "writer", "Previous version", (finding.ref,), owner.ref
    )
    cite = "[[cite:" + sources[0].ref + "]]"
    text = (
        "# 活动报告\n\n## 摘要\n活动成效提升20%"
        + cite
        + "。\n\n## 统计\n本月120人，上月100人，登记增加20%"
        + cite
        + "。\n\n|指标|判断|\n|---|---|\n|活动成效|提高20%"
        + cite
        + "|\n\n## 执行资料\n"
    )
    text += "\n\n".join(
        f"记录{i:02d}：实施前核对场地、签到表和设备，按既定流程保留凭证。"
        for i in range(1, 61)
    )
    text += (
        "\n\n## 后续安排\n由于效果已改善，应沿用本次活动机制。下月安排三场，每场预算3000元，总预算9000元"
        + cite
        + "。"
    )
    report = store.put(
        case_id,
        "report",
        {
            **render(text, [sources[0].ref], lambda ref: store.get(case_id, ref)),
            "evidence": [sources[0].ref],
            "producer": old_writer.ref,
        },
        (old_writer.ref, c.direction, finding.ref, sources[0].ref),
    )
    store.put(
        case_id,
        "work_result",
        {"ref": report.ref, "producer": old_writer.ref},
        (old_writer.ref, report.ref),
    )
    return store.work(
        case_id, c.ref, "writer", case["task"], (finding.ref, report.ref), owner.ref
    ), policy


async def run(root, arm, run_id):
    if os.environ.get("GITHUB_RUN_ATTEMPT", "1") != "1" or not re.fullmatch(
        r"[A-Za-z0-9_-]{1,90}", run_id
    ):
        raise ValueError("no blind rerun or ambiguous identity")
    request = json.loads(
        (root / "evals/agent-capability-request.json").read_text(encoding="utf-8")
    )
    cases = request_cases(request)
    source_root = Path(epivra.__file__).resolve().parent
    expected = root / (".baseline/src/epivra" if arm == "baseline" else "src/epivra")
    if source_root != expected.resolve():
        raise ValueError("wrong implementation loaded")
    folder = root / ".epivra" / f"capabilities-{run_id}-{arm}"
    output = root / "artifacts" / f"capabilities-{arm}"
    if folder.exists() or output.exists():
        raise ValueError("fresh probe required")
    key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not key:
        raise ValueError("missing model credential")
    folder.mkdir(parents=True)
    output.mkdir(parents=True)
    store = Store(folder / "research.db")
    clients = []
    summary = {
        "arm": arm,
        "request": request,
        "code": BASELINE if arm == "baseline" else os.environ.get("GITHUB_SHA"),
        "started_at": time.time(),
        "cases": [],
        "scope": "closed-material role tasks; not an end-to-end quality benchmark",
        "semantic_acceptance": "pending_independent_review",
    }
    save(
        output / "manifest.json",
        {
            "source": {
                p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in source_root.glob("*.py")
            },
            "cases": identity(CASES),
            "runner": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        },
    )
    try:
        for case_id in cases:
            work, policy = seed(store, case_id)
            model, api = create_model(policy, {"DEEPSEEK_API_KEY": key})
            clients.append(api)
            h = Harness(store, model)
            started = time.perf_counter()
            calls = 0
            error = None
            try:
                while calls < 6 and not h.finished(case_id, work.ref):
                    if h.waiting(case_id, work.ref):
                        break
                    await h.step(case_id, work.ref)
                    calls += 1
            except Exception as exc:
                error = type(exc).__name__
            results = h._steps(case_id, "work_result", work.ref)
            summary["cases"].append(
                {
                    "id": case_id,
                    "steps": calls,
                    "complete": h.finished(case_id, work.ref),
                    "elapsed_seconds": time.perf_counter() - started,
                    "error_type": error,
                    "result_refs": [r.ref for r in results],
                }
            )
            save(output / "summary.json", summary, (key,))
            if store.unsettled(case_id):
                break  # Do not replay or obscure uncertainty.
    finally:
        await asyncio.gather(*(c.close() for c in clients), return_exceptions=True)
        store.close()
        projection = collect(folder / "research.db")
        for field, name in [
            ("artifacts", "public-artifacts.json"),
            ("calls", "calls.json"),
            ("windows", "window-manifest.json"),
        ]:
            save(output / name, projection[field], (key,))
        summary.update(
            finished_at=time.time(),
            usage=projection["usage"],
            unknown_operations=projection["unknown_operations"],
        )
        summary["execution_pass"] = (
            len(summary["cases"]) == len(cases)
            and all(c["complete"] and not c["error_type"] for c in summary["cases"])
            and not summary["unknown_operations"]
        )
        save(output / "summary.json", summary, (key,))
        save(
            output / "artifact-manifest.json",
            {
                p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in output.iterdir()
                if p.name != "artifact-manifest.json"
            },
        )
    print(
        json.dumps(
            {
                "arm": arm,
                "complete": summary["execution_pass"],
                "cases": len(summary["cases"]),
            }
        )
    )
    return 0 if summary["execution_pass"] else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", choices=("baseline", "candidate"), required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    try:
        status = asyncio.run(
            run(Path(__file__).resolve().parents[1], args.arm, args.run_id)
        )
    except Exception as exc:
        print(json.dumps({"error_type": type(exc).__name__}))
        status = 1
    raise SystemExit(status)
