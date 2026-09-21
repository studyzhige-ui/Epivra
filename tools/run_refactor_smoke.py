"""One complete autonomous research task on fixed supplied records.

The model gets no expected answer, tool sequence or prescribed helper roles.
A job-only deadline preserves evidence; it is not a product research time limit.
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

from epivra.application import online_service
from epivra.local_security import private_directory
from epivra.models import freeze_model_settings
from epivra.storage import Store
from tools.run_live_eval import collect, save, scrub
from tools.run_open_web_eval import drive

REQUEST = {"version": 1, "request_id": "continuous-workspace-20260921-01"}
CASE = {
    "task": "请依据提供的三份资料，为本机房维护团队整理一份可执行的说明：2025年9月以后，AX-7设备应采用怎样的巡检安排；两份规程对间隔的不同说法是否构成实际冲突；验证记录能支持哪些运行可靠性判断，哪些不能。建议要对应资料及适用条件，关键判断提供可回查引用，不扩展为其他设备或未提供的标准。",
    "sources": [
        {"origin": "AX7-procedure-v1.txt", "text": "AX-7维护规程V1。发布日期2024-06-01。对按照V1部署的AX-7设备，每7天一次人工检查，检查密封件和报警日志；发现密封破损时停止运行并维修。规程适用干燥室内机房。本文未规定后续版本的适用时间。", "coverage": "complete"},
        {"origin": "AX7-procedure-v2.txt", "text": "AX-7维护规程V2。发布日期2025-08-15，自2025-09-01起替代V1，适用于全部已部署AX-7，不限于新设备。正常状态下每14天人工检查密封件与报警日志；发生进水报警后，应立即停用，并在维修、检查合格后恢复。适用环境仍为干燥室内机房。V2没有提供延长巡检间隔的试验推导或费用数据。", "coverage": "complete"},
        {"origin": "AX7-validation-record.txt", "text": "AX-7验证记录，2025-08-01。10台设备在干燥室内、20至25摄氏度、有人值守条件下，各运行8小时，均未触发故障报警。未测试室外环境、进水情形、连续24小时运行或无人值守情形；没有计算故障率置信区间，也没有比较7天与14天巡检策略。", "coverage": "complete"},
    ],
}


def admit(value, run_id, state, output):
    if not isinstance(value, dict) or value != REQUEST or type(value.get("version")) is not int:
        raise ValueError("only the frozen small complete-task request is allowed")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,90}", run_id):
        raise ValueError("invalid run identity")
    if os.environ.get("GITHUB_RUN_ATTEMPT", "1") != "1":
        raise ValueError("inspect original attempt; do not blindly replay paid calls")
    if state.exists() or output.exists():
        raise ValueError("fresh state and evidence directory required")


def execution_gate(summary):
    return bool(summary.get("published") and summary.get("unknown_operations") == 0
                and not any(summary.get(k) for k in ("error_type", "errors", "work_errors", "cleanup_error_type", "export_error_type")))


async def run(root, run_id):
    state = root / ".epivra" / ("workspace-smoke-" + run_id)
    output = root / "artifacts/workspace-smoke"
    value = json.loads((root / "evals/refactor-smoke-request.json").read_text(encoding="utf-8"))
    admit(value, run_id, state, output)
    key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not key:
        raise ValueError("model credential missing")
    policy = freeze_model_settings({"provider": "deepseek", "model": "deepseek-flash", "stream_model": True,
                                    "network": False, "local_roots": [], "as_of_date": "2026-09-21"})
    private_directory(state)
    output.mkdir(parents=True)
    summary = {"run_id": run_id, "commit": os.environ.get("GITHUB_SHA"), "started_at": time.time(),
               "request": value, "stage": "planning", "published": False,
               "semantic_acceptance": "pending_independent_review", "approval_count": 0,
               "scope": "complete ResearchService with synthetic supplied records; not web/Benchmark-10 acceptance"}
    save(output / "input.json", {"case": CASE, "policy": policy})
    save(output / "code-manifest.json", {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                                         for p in sorted((root / "src/epivra").glob("*.py"))})
    store = Store(state / "research.db")
    service, clients = None, []
    try:
        store.create("study", CASE["task"], policy)
        for source in CASE["sources"]:
            store.put("study", "source", source)
        service, clients = online_service(store, "study", {"DEEPSEEK_API_KEY": key})
        deadline = time.monotonic() + 600
        await drive(service, store, "study", output, summary, (key,), stop_at=deadline)
        control = store.control("study")
        plans = store.list("study", "plan")
        if not summary.get("evaluation_deadline_reached") and not control.approved and plans and not service.errors:
            store.command("study", "initial-route-approval", control.ref, "approve", {"plan": plans[-1].ref})
            summary.update(approval_count=1, plan=plans[-1].ref, stage="research", approved_at=time.time())
            save(output / "approved-route.json", plans[-1].body)
            await drive(service, store, "study", output, summary, (key,), stop_at=deadline)
        control = store.control("study")
        published = [a for a in store.list("study", "publication") if control.direction in a.parents]
        summary.update(published=bool(published), errors=service.errors, work_errors=service.work_errors, paused=control.paused)
        if published:
            report = store.get("study", published[-1].body["report"])
            summary["report_ref"] = report.ref
            (output / "report.md").write_text(str(scrub(report.body["text"], (key,))), encoding="utf-8")
    except BaseException as exc:
        summary["error_type"] = type(exc).__name__
        if isinstance(exc, (KeyboardInterrupt, SystemExit, asyncio.CancelledError)):
            raise
    finally:
        try:
            if service:
                await service.close()
            await asyncio.gather(*(c.close() for c in clients))
        except Exception as exc:
            summary["cleanup_error_type"] = type(exc).__name__
        finally:
            store.close()
        try:
            projection = collect(state / "research.db")
            for field, name in (("artifacts", "public-artifacts.json"), ("windows", "window-manifest.json"), ("calls", "calls.json")):
                save(output / name, projection[field], (key,))
            summary.update(usage=projection["usage"], unknown_operations=projection["unknown_operations"])
        except Exception as exc:
            summary["export_error_type"] = type(exc).__name__
        summary.update(finished_at=time.time(), elapsed_seconds=time.time() - summary["started_at"])
        summary["execution_pass"] = execution_gate(summary)
        save(output / "summary.json", summary, (key,))
        save(output / "artifact-manifest.json", {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir()
                                                  if p.name != "artifact-manifest.json"})
    print(json.dumps({"published": summary["published"], "execution_pass": summary["execution_pass"]}))
    return 0 if summary["execution_pass"] else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    try:
        status = asyncio.run(run(Path(__file__).resolve().parents[1], args.run_id))
    except Exception as exc:
        print(json.dumps({"error_type": type(exc).__name__}))
        status = 1
    raise SystemExit(status)
