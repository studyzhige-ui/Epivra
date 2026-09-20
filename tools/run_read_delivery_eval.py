"""One complete fixed-source research task, identical across rollback and repair.

Uses the actual ResearchService, not a prescribed role or tool sequence. Fixture
extraction is offline and hash-bound. No answer labels enter model input.
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
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import epivra
from epivra.application import online_service
from epivra.models import freeze_model_settings
from epivra.storage import Store
from tools.run_live_eval import collect, save, scrub
from tools.run_open_web_eval import drive

BASELINE = "9492635771460b7d312cb06541748b13379e9471"
SOURCE_REFS = (
    "8cb0a0ffc86328a3a5486eeb64226e4c401bf4854c3e2c5d446ead892146c407",
    "ca97f8e119e9fec8dd4f09746f9bf394adbbd032a197c58da17a16ffc16f960c",
    "918724573e113c3e6170e6585cfb7138d0856fc7be53766c34faf8eb37e38671",
)
TASK = "依据提供的 SQLite 官方页面快照，为本机读多写少的应用解释：启用 WAL 后，为什么仍可能出现较慢的提交？请区分自动 checkpoint、长读事务以及主动调用 checkpoint 的关系，给出有依据的处理建议与适用限制。只讨论这一问题；不得把快照之外的内容当作已核实事实，关键判断附可回查引用。"


def fixture(archive: Path) -> dict:
    with zipfile.ZipFile(archive) as zipped:
        records = json.loads(zipped.read("public-artifacts.json"))
    by_ref = {a["ref"]: a for a in records}
    sources = []
    for ref in SOURCE_REFS:
        item = by_ref[ref]
        if item["kind"] != "source" or not isinstance(item["body"].get("text"), str):
            raise ValueError("invalid original snapshot")
        body = item["body"]
        sources.append({"text": body["text"], "origin": body["origin"],
                        "coverage": body.get("coverage"), "issues": body.get("issues", []),
                        "snapshot_ref": ref})
    return {"task": TASK, "as_of_date": "2026-09-20", "sources": sources,
            "provenance": {"source_run": 35460940529, "artifact_id": 10588969892,
                           "public_artifacts_sha256": hashlib.sha256(zipped_bytes(archive)).hexdigest()}}


def zipped_bytes(archive):
    with zipfile.ZipFile(archive) as zipped:
        return zipped.read("public-artifacts.json")


def validate_request(value):
    if (not isinstance(value, dict) or set(value) != {"version", "request_id", "case"}
            or type(value["version"]) is not int or value["version"] != 1
            or value["case"] != "wal-checkpoint-snapshot"
            or not isinstance(value["request_id"], str)
            or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", value["request_id"])):
        raise ValueError("one fixed small complete task required")
    return value


def execution_gate(summary):
    return bool(summary.get("published") and summary.get("unknown_operations") == 0
                and not any(summary.get(k) for k in ("error_type", "errors", "work_errors",
                                                    "cleanup_error_type", "export_error_type")))


async def run(root, arm, run_id, archive):
    request = validate_request(json.loads((root / "evals/read-delivery-request.json").read_text()))
    if arm not in {"baseline", "candidate"} or not re.fullmatch(r"[A-Za-z0-9_-]{1,90}", run_id):
        raise ValueError("invalid run identity")
    if os.environ.get("GITHUB_RUN_ATTEMPT", "1") != "1":
        raise ValueError("inspect original paid attempt; do not blindly resend")
    source_root = Path(epivra.__file__).resolve().parent
    if source_root != (root / (".baseline/src/epivra" if arm == "baseline" else "src/epivra")).resolve():
        raise ValueError("wrong implementation loaded")
    case = fixture(archive)
    encoded = json.dumps(case, ensure_ascii=False, separators=(",", ":")).encode()
    if hashlib.sha256(encoded).hexdigest() != "2be384a07731ca4ff51f9b9b962f0d4f36f9c19ab246aa96617bfe8def2ce1e4":
        raise ValueError("fixture changed")
    state = root / ".epivra" / f"delivery-{run_id}-{arm}"
    output = root / "artifacts" / f"delivery-{arm}"
    if state.exists() or output.exists():
        raise ValueError("fresh identity required")
    secret = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not secret:
        raise ValueError("missing model credential")
    state.mkdir(parents=True); output.mkdir(parents=True)
    secrets = (secret,)
    policy = freeze_model_settings({"provider": "deepseek", "model": "deepseek-flash",
        "stream_model": True, "network": False, "local_roots": [], "as_of_date": case["as_of_date"]})
    summary = {"run_id": run_id, "arm": arm, "request": request,
        "code": BASELINE if arm == "baseline" else os.environ.get("GITHUB_SHA"),
        "started_at": time.time(), "stage": "planning", "published": False,
        "semantic_acceptance": "pending_independent_source_review",
        "scope": "complete ResearchService on frozen official snapshots, not fresh web research"}
    save(output / "fixture.json", case)
    save(output / "policy.json", policy)
    save(output / "code-manifest.json", {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in source_root.glob("*.py")})
    save(output / "eval-manifest.json", {"runner": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "fixture": hashlib.sha256(encoded).hexdigest()})
    store = Store(state / "research.db")
    service, clients = None, []
    try:
        store.create("study", case["task"], policy)
        for source in case["sources"]:
            store.put("study", "source", source)
        service, clients = online_service(store, "study", {"DEEPSEEK_API_KEY": secret})
        stop_at = time.monotonic() + 900  # This evaluation's graceful-stop margin only.
        await drive(service, store, "study", output, summary, secrets, stop_at=stop_at)
        control = store.control("study")
        plans = store.list("study", "plan")
        if not summary.get("evaluation_deadline_reached") and not control.approved and plans and not service.errors:
            store.command("study", "fixture-plan-approval", control.ref, "approve", {"plan": plans[-1].ref})
            summary.update(stage="research", approved_at=time.time())
            await drive(service, store, "study", output, summary, secrets, stop_at=stop_at)
        control = store.control("study")
        published = [p for p in store.list("study", "publication") if control.direction in p.parents]
        summary.update(published=bool(published), paused=control.paused,
                       errors=service.errors, work_errors=service.work_errors)
        if published:
            report = store.get("study", published[-1].body["report"])
            summary["report_ref"] = report.ref
            (output / "report.md").write_text(str(scrub(report.body["text"], secrets)), encoding="utf-8")
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
        store.close()
        try:
            projection = collect(state / "research.db")
            for field, name in (("artifacts", "public-artifacts.json"), ("calls", "calls.json"), ("windows", "window-manifest.json")):
                save(output / name, projection[field], secrets)
            summary.update(usage=projection["usage"], unknown_operations=projection["unknown_operations"])
        except Exception as exc:
            summary["export_error_type"] = type(exc).__name__
        summary.update(finished_at=time.time(), elapsed_seconds=time.time()-summary["started_at"])
        summary["execution_pass"] = execution_gate(summary)
        save(output / "summary.json", summary, secrets)
        save(output / "artifact-manifest.json", {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir() if p.name != "artifact-manifest.json"})
    print(json.dumps(scrub(summary, secrets), ensure_ascii=False))
    return 0 if summary["execution_pass"] else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", choices=("baseline", "candidate"), required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--archive", type=Path, required=True)
    args = parser.parse_args()
    try:
        status = asyncio.run(run(Path(__file__).resolve().parents[1], args.arm, args.run_id, args.archive))
    except Exception as exc:
        print(json.dumps({"error_type": type(exc).__name__}));status = 1
    raise SystemExit(status)
