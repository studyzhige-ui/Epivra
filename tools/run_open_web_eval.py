"""One explicitly selected small online task through the unchanged product service."""

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

from epivra.adapters import credentials
from epivra.application import online_service
from epivra.diagnostics import environment
from epivra.local_security import private_directory
from epivra.models import freeze_model_settings
from epivra.storage import Store
from tools.run_live_eval import collect, save, scrub


def selection(root: Path, request: object) -> tuple[dict, dict]:
    """No arbitrary task/batch injection; assessment material is never supplied."""
    if not isinstance(request, dict) or set(request) != {"version", "request_id", "case"}:
        raise ValueError("unexpected request fields")
    if type(request["version"]) is not int or request["version"] != 1:
        raise ValueError("invalid request version")
    if not isinstance(request["request_id"], str) or not re.fullmatch(
        r"[A-Za-z0-9_-]{1,64}", request["request_id"]
    ):
        raise ValueError("invalid request identity")
    cases = json.loads((root / "evals/open_web_cases.json").read_text(encoding="utf-8"))
    if not isinstance(request["case"], str) or request["case"] not in cases:
        raise ValueError("one registered small online task required")
    case = cases[request["case"]]
    if set(case) != {"task", "as_of_date"} or not all(isinstance(v, str) and v for v in case.values()):
        raise ValueError("invalid case definition")
    return request, case


def execution_gate(summary: dict, records: list[dict]) -> bool:
    """Completion is not semantic acceptance; require successful search AND reading."""
    used = {r.get("tool") for r in records if r.get("status") == "succeeded" and r.get("http_status") == 200}
    return bool(
        summary.get("published") and not summary.get("error_type")
        and not summary.get("errors") and not summary.get("work_errors")
        and summary.get("unknown_operations") == 0
        and {"web_search", "fetch_web"} <= used
    )


def evaluation_active_seconds() -> int:
    """Diagnostic-job guard only; it is not a product research time budget."""
    raw = os.environ.get("EPIVRA_EVAL_ACTIVE_SECONDS", "1500")
    try:
        seconds = int(raw)
    except ValueError as exc:
        raise ValueError("EPIVRA_EVAL_ACTIVE_SECONDS must be an integer") from exc
    if not 300 <= seconds <= 1800:
        raise ValueError("evaluation active window must be between 300 and 1800 seconds")
    return seconds


async def drive(service, store, study, output, summary, secrets, *, stop_at=None):
    task = asyncio.create_task(service.run(study))
    pause_requested = False
    try:
        while not task.done():
            wait = 30.0
            if stop_at is not None and not pause_requested:
                wait = max(0.0, min(wait, stop_at - time.monotonic()))
            await asyncio.wait({task}, timeout=wait)
            if (
                not task.done()
                and stop_at is not None
                and not pause_requested
                and time.monotonic() >= stop_at
            ):
                control = store.control(study)
                if not control.paused and not control.cancelled:
                    store.command(
                        study,
                        f"evaluation-deadline-{summary['run_id']}",
                        control.ref,
                        "pause",
                    )
                pause_requested = True
                summary["evaluation_deadline_reached"] = True
                summary["stage"] = "evaluation_deadline_paused"
            summary["last_heartbeat"] = time.time()
            summary["artifact_counts"] = dict(store.db.execute(
                "SELECT kind,COUNT(*) FROM artifacts WHERE study=? GROUP BY kind", (study,)
            ).fetchall())
            save(output / "summary.json", summary, secrets)
            # No source text, prompts, credentials or private model protocol in logs.
            print(json.dumps({"stage": summary["stage"], "counts": summary["artifact_counts"]}), flush=True)
        await task
    finally:
        if not task.done():
            task.cancel()
        await asyncio.gather(task, return_exceptions=True)


async def run(root: Path, request: object, run_id: str) -> int:
    request, case = selection(root, request)
    if os.environ.get("GITHUB_RUN_ATTEMPT", "1") != "1":
        raise ValueError("inspect prior attempt; authorize a fresh request instead of blind rerun")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", run_id):
        raise ValueError("invalid run ID")
    state = root / ".epivra" / f"open-web-{run_id}"
    output = root / "artifacts/open-web"
    if state.exists() or output.exists():
        raise ValueError("fresh run required")
    keys = credentials(root / ".env")
    if not all(keys.get(k, "").strip() for k in ("DEEPSEEK_API_KEY", "TAVILY_API_KEY")):
        raise ValueError("provider credentials missing")
    secrets = tuple(v for raw in keys.values() for v in (raw, *raw.split(",")) if v)
    policy = freeze_model_settings({
        "provider": "deepseek", "model": "deepseek-flash", "stream_model": True,
        "network": True, "public_sources": False,
        "search_providers": ["tavily"], "reader_providers": ["tavily"],
        "local_roots": [], "as_of_date": case["as_of_date"],
    })
    private_directory(state)
    output.mkdir(parents=True)
    summary = {
        "version": 1, "run_id": run_id, "request": request, "commit": os.environ.get("GITHUB_SHA"),
        "started_at": time.time(), "stage": "planning", "published": False,
        "execution_pass": False, "semantic_acceptance": "pending_independent_source_review",
        "approval": "owner_authorized_small_task_generated_plan_unchanged",
    }
    save(output / "summary.json", summary, secrets)
    save(output / "environment.json", environment(), secrets)
    save(output / "task.json", {"request": request, **case, "policy": policy})
    save(output / "code-manifest.json", {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for pattern in ("src/epivra/*.py", "tools/*eval*.py", "evals/open_web_cases.json")
        for p in sorted(root.glob(pattern))
    })
    database, study = state / "research.db", request["case"]
    store, service, clients = None, None, []
    stop_at = time.monotonic() + evaluation_active_seconds()
    try:
        store = Store(database)
        store.create(study, case["task"], policy)
        service, clients = online_service(store, study, keys)
        await drive(service, store, study, output, summary, secrets, stop_at=stop_at)
        control = store.control(study)
        plans = store.list(study, "plan")
        if (
            not summary.get("evaluation_deadline_reached")
            and not control.approved
            and plans
            and not service.errors
        ):
            store.command(study, "small-task-approval", control.ref, "approve", {"plan": plans[-1].ref})
            summary.update(stage="research", approved_at=time.time(), plan=plans[-1].ref)
            await drive(service, store, study, output, summary, secrets, stop_at=stop_at)
        control = store.control(study)
        publications = [a for a in store.list(study, "publication") if control.direction in a.parents]
        summary.update(published=bool(publications), errors=service.errors, work_errors=service.work_errors,
                       paused=control.paused, cancelled=control.cancelled)
        if publications:
            report = store.get(study, publications[-1].body["report"])
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
            if clients:
                await asyncio.gather(*(c.close() for c in clients))
        except Exception as exc:
            summary["cleanup_error_type"] = type(exc).__name__
        finally:
            if store:
                store.close()
        try:
            if database.is_file():
                projection = collect(database)
                for field, name in (("artifacts", "public-artifacts.json"), ("windows", "window-manifest.json"), ("calls", "calls.json")):
                    save(output / name, projection[field], secrets)
                summary.update(usage=projection["usage"], unknown_operations=projection["unknown_operations"])
                summary["execution_pass"] = execution_gate(summary, projection["calls"]) and not summary.get("cleanup_error_type")
        except Exception as exc:
            summary.update(export_error_type=type(exc).__name__, execution_pass=False)
        summary.update(stage="finished", finished_at=time.time())
        summary["elapsed_seconds"] = summary["finished_at"] - summary["started_at"]
        save(output / "summary.json", summary, secrets)
        save(output / "artifact-manifest.json", {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir())
            if p.is_file() and p.name != "artifact-manifest.json"
        })
    print(json.dumps(scrub(summary, secrets), ensure_ascii=False), flush=True)
    return 0 if summary["execution_pass"] else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        request = json.loads((root / "evals/open-web-request.json").read_text(encoding="utf-8"))
        code = asyncio.run(run(root, request, args.run_id))
    except Exception as exc:
        print(json.dumps({"execution_pass": False, "error_type": type(exc).__name__}))
        code = 1
    raise SystemExit(code)
