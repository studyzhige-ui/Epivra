"""Final input ablations. No production prompt or role permission is changed.

All arms use the same official adapter/model settings and a single completion.
This isolates input effects, NOT the latency of complete autonomous research.
"""
from __future__ import annotations

import argparse
import asyncio
import copy
import hashlib
import json
import os
import re
import sys
import time
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from epivra.domain import encode
from epivra.models import create_model, freeze_model_settings
from epivra.prompts import ROLES
from tools.run_live_eval import save

ARCHIVE_SHA = "d4c547b7fa318a970906285c18565a4e8d0bc12d61fde6885c6d31d2882ffed9"
BASELINE = "afa3fc3fc1f62b5c326fa8c6f392ae101c96ad04"
REQUEST = {"version": 1, "request_id": "final-causal-audit-20260920-01"}
TRANSPORT = "\n本次给出的材料可直接阅读，没有可用工具。请直接输出本项成果，不输出工具调用或操作计划。"
MINIMAL = "依据用户原问题和所给材料完成研究，给出有依据、有适用边界的答案。"
SHORT = {
    "cost_estimate": {
        "request": "依据预算资料说明哪些月度成本与盈亏平衡条件可以确定。保留每月三场安排，不新增活动或价格策略。",
        "source": "活动计划每月三场。下期月度总成本预计为40000元，这只是估计值，不是合同承诺的最低成本；表中未单列维护费，不能据此确定维护费是否已计入。另一个附加测算明确假设总成本恰好40000元，在该假设下，月收入40000元时盈亏平衡。",
        "claim": "若维护费未包含在40000元预算内，实际总成本就一定高于40000元，因此实际盈亏平衡收入也一定更高。",
    },
    "cost_exact": {
        "request": "依据预算资料说明哪些月度成本与盈亏平衡条件可以确定。保留每月三场安排，不新增活动或价格策略。",
        "source": "活动计划每月三场。本次已核实的当月全部其他实际成本为40000元，另有已核实的维护费2000元，前一数额明确不包含这2000元，没有其他成本。这里讨论收入减全部成本等于零时的盈亏平衡，不讨论税项、机会成本或现金流。",
        "claim": "当月全部成本为42000元，在材料规定的计算口径下，月收入42000元时盈亏平衡。",
    },
    "mode_active": {
        "request": "依据同步规约说明在读取活动未结束时，模式A和B各能保证什么；区分完成同步与重置日志，不讨论产品之外的方案。",
        "source": "模式A等待写入结束，并等待所有读取者都使用最新快照，然后同步全部记录并完成；此时读取活动不必结束。模式B先完成A，再等到所有读取者都不使用日志，保证下一写入者能从日志开头重启。概览说读取活动可能使同步无法完成或日志无法重置；这描述潜在阻碍，不是对任意读取活动的充分判断。",
        "claim": "只要有任何读取活动尚未结束，模式A就不可能完成同步。",
    },
    "mode_finished": {
        "request": "依据同步规约说明在读取活动未结束时，模式A和B各能保证什么；区分完成同步与重置日志，不讨论产品之外的方案。",
        "source": "本产品的模式A明确等待写入者结束、所有读取活动全部结束，才开始完整同步并返回成功。模式B先完成A，再把日志文件长度截为零。规约未提供允许读取活动继续存在时A成功完成的其他路径。这里只讨论这份规约定义的A和B，不类比其他产品。",
        "claim": "按本产品规约，只要仍有读取活动未结束，模式A就不能成功完成；B在完成A后还需把日志截为零。",
    },
}


def load_archive(path):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != ARCHIVE_SHA:
        raise ValueError("historical evidence archive changed")
    with zipfile.ZipFile(path) as archive:
        manifest = json.loads(archive.read("artifact-manifest.json"))
        for name, digest in manifest.items():
            if hashlib.sha256(archive.read(name)).hexdigest() != digest:
                raise ValueError("historical evidence member changed")
        records = json.loads(archive.read("public-artifacts.json"))
        fixture = json.loads(archive.read("fixture.json"))
    return records, fixture


def real_inputs(records, fixture):
    by_seq = {r["seq"]: r for r in records}
    sources = [{"ref": r["ref"], **r["body"]} for r in records if r["kind"] == "source"]
    upstream = [copy.deepcopy(by_seq[n]) for n in (901, 983)]
    if any(r["kind"] != "work_result" for r in upstream):
        raise ValueError("expected original investigator results")
    assignment = by_seq[1055]["body"]["task"]
    base = {"original_request": fixture["task"], "task": assignment,
            "sources": sources, "upstream": upstream}
    neutral = "围绕用户原问题整合已有依据，解决会影响答案的实质分歧，直接给出有根据的研究成果。"
    corrected = copy.deepcopy(base)
    finding = corrected["upstream"][0]["body"]["findings"][2]
    old = '因此长读事务只能经"checkpoint 无法完成/重置"的间接路径影响提交延迟。'
    new = '这些资料给出长读事务经"checkpoint 无法完成/重置"间接影响提交延迟的一条可能路径，但未建立路径的穷尽性。'
    if finding["statement"].count(old) != 1:
        raise ValueError("audited unsupported claim changed")
    finding["statement"] = finding["statement"].replace(old, new)
    # A changed input is a new projection, never falsely given the old immutable ref.
    corrected["upstream"][0]["ref"] = hashlib.sha256(encode(corrected["upstream"][0]["body"]).encode()).hexdigest()
    return {
        "original": (ROLES["synthesizer"], base),
        "neutral_task": (ROLES["synthesizer"], {**base, "task": neutral}),
        "corrected_upstream": (ROLES["synthesizer"], corrected),
        "direct_sources": (MINIMAL, {"original_request": fixture["task"], "task": neutral, "sources": sources}),
    }


def trials(records, fixture):
    result = []
    for i, (case, data) in enumerate(SHORT.items()):
        arms = ["direct", "writer_prompt"] if i % 2 == 0 else ["writer_prompt", "direct"]
        for arm in arms:
            result.append({"id": f"short-{case}-{arm}", "group": "short_generation", "case": case, "arm": arm,
                           "system": MINIMAL if arm == "direct" else ROLES["writer"],
                           "input": {"original_request": data["request"], "source": data["source"]}})
    inputs = real_inputs(records, fixture)
    for repeat in range(2):
        order = list(inputs) if repeat == 0 else list(reversed(inputs))
        for arm in order:
            system, payload = inputs[arm]
            result.append({"id": f"real-{repeat}-{arm}", "group": "historical_input_ablation", "case": "sqlite", "arm": arm,
                           "repeat": repeat, "system": system, "input": payload})
    for i, (case, data) in enumerate(SHORT.items()):
        arms = ["minimal", "reviewer_prompt"] if i % 2 == 0 else ["reviewer_prompt", "minimal"]
        for arm in arms:
            result.append({"id": f"review-{case}-{arm}", "group": "focused_review", "case": case, "arm": arm,
                           "system": "核对给出的报告陈述是否由材料支持，区分错误与有依据的限定结论。" if arm == "minimal" else ROLES["reviewer"],
                           "input": {"original_request": data["request"], "source": data["source"], "report": data["claim"],
                                     "task": "判断这段报告的结论是否由材料支持。直接返回JSON对象：accepted为布尔值，reason给出依据；存在实质错误时accepted=false，不要替报告补写未给出的前提。"}})
    return result


def admit(request, run_id, output):
    if request != REQUEST or type(request.get("version")) is not int:
        raise ValueError("only the frozen final diagnosis request is admitted")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,90}", run_id) or os.environ.get("GITHUB_RUN_ATTEMPT", "1") != "1":
        raise ValueError("inspect original attempt; no blind resend")
    if output.exists():
        raise ValueError("fresh evidence directory required")


async def run(root, run_id, archive):
    output = root / "artifacts/final-root"
    request = json.loads((root / "evals/final-root-request.json").read_text(encoding="utf-8"))
    admit(request, run_id, output)
    records, fixture = load_archive(archive)
    selected = trials(records, fixture)
    if len(selected) != 24 or len({t["id"] for t in selected}) != 24:
        raise ValueError("trial schedule changed")
    key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not key:
        raise ValueError("model credential required")
    policy = freeze_model_settings({"provider": "deepseek", "model": "deepseek-flash", "network": False,
                                    "stream_model": True, "as_of_date": "2026-09-20"})
    output.mkdir(parents=True)
    save(output / "experiment.json", {"request": request, "baseline": BASELINE, "code": os.environ.get("GITHUB_SHA"),
                                       "source_archive_sha256": ARCHIVE_SHA, "policy": policy, "trials": selected,
                                       "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    summary = {"run_id": run_id, "started_at": time.time(), "calls": [], "unknown_operations": 0,
               "semantic_acceptance": "pending independent review", "scope": "one-completion input ablations, not an autonomous full-product benchmark"}
    stop_at = time.monotonic() + 1200
    model, api = create_model(policy, {"DEEPSEEK_API_KEY": key})
    try:
        for trial in selected:
            if time.monotonic() >= stop_at:
                summary["diagnostic_window_reached"] = True
                break
            context = {"provider": model.identity, "system": trial["system"] + TRANSPORT,
                       "tools": {}, "tool_versions": {}, **trial["input"]}
            wire = model.prepare(context, None)
            row = {"id": trial["id"], "invoked_at": time.time(),
                   "public_input_sha256": hashlib.sha256(encode(context).encode()).hexdigest()}
            try:
                raw = await model.complete({"wire": wire})
                row["http_status"] = raw.get("http_status")
                row["usage"] = (raw.get("data") or {}).get("usage")
                decoded = model.decode(raw)
                row["complete"] = bool(decoded["complete"] and not decoded["calls"] and decoded["text"].strip())
                (output / (trial["id"] + ".txt")).write_text(decoded["text"].replace(key, "[REDACTED]"), encoding="utf-8")
                row["status"] = "succeeded" if row["complete"] else "incomplete"
            except Exception as exc:
                row["error_type"] = type(exc).__name__
                row["status"] = "failed" if row.get("http_status") else "unknown"
                if row["status"] == "unknown":
                    summary["unknown_operations"] += 1
            row["settled_at"] = time.time()
            row["elapsed_seconds"] = row["settled_at"] - row["invoked_at"]
            summary["calls"].append(row)
            save(output / "summary.json", summary, (key,))
            print(json.dumps({"trial": trial["id"], "status": row["status"], "seconds": round(row["elapsed_seconds"], 2)}), flush=True)
            if row["status"] in {"unknown", "incomplete"}:
                break
    finally:
        await api.close()
        summary["finished_at"] = time.time()
        summary["elapsed_seconds"] = summary["finished_at"] - summary["started_at"]
        summary["execution_pass"] = len(summary["calls"]) == len(selected) and all(c["status"] == "succeeded" for c in summary["calls"])
        save(output / "summary.json", summary, (key,))
        save(output / "artifact-manifest.json", {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir() if p.name != "artifact-manifest.json"})
    return 0 if summary["execution_pass"] else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--archive", type=Path, required=True)
    args = parser.parse_args()
    try:
        status = asyncio.run(run(Path(__file__).resolve().parents[1], args.run_id, args.archive))
    except Exception as exc:
        print(json.dumps({"error_type": type(exc).__name__}))
        status = 1
    raise SystemExit(status)
