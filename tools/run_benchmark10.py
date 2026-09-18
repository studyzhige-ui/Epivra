"""User-authorized ten-case batch. Normal research, isolated diagnostic exports."""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import os
import re
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from epivra.adapters import JsonAPI, credentials
from epivra.application import online_service
from epivra.cli_settings import write
from epivra.diagnostics import environment, windows
from epivra.host import send, start
from epivra.models import freeze_model_settings
from epivra.scheduling import Scheduler
from epivra.storage import Store
from epivra.usage import summarize


def save(path, value):
    write(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def append(path, value):
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(value, ensure_ascii=False) + "\n")


def run_status(folder):
    """A persisted heartbeat is not proof of a live runner; inspect its OS lock."""
    import msvcrt

    result = json.loads((folder / "status.json").read_text(encoding="utf-8"))
    with (folder / "runner.lock").open("r+b") as lock:
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            result["alive"] = True
        else:
            result["alive"] = False
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
    if not result["alive"] and not result.get("complete"):
        for case in result.get("cases", []):
            if case.get("status") == "running":
                case["status"] = "interrupted"
    return result


def instrument(api, path, study, index):
    # Wrap full calls, including stream consumption; never log auth or bodies.
    for name in ("request", "chat_stream"):
        original = getattr(api, name, None)
        if original is None:
            continue

        async def measured(*args, _call=original, _name=name, **kwargs):
            started = time.time()
            event = {
                "study": study,
                "client": index,
                "method": _name,
                "started_at": started,
                "event": "started",
            }
            append(path, event)
            try:
                raw = await _call(*args, **kwargs)
                event.update(
                    {
                        k: raw[k]
                        for k in ("http_status", "credential_slot", "credential_retry")
                        if k in raw
                    }
                )
                return raw
            except BaseException as exc:
                event["error_type"] = type(exc).__name__
                raise
            finally:
                append(
                    path,
                    {
                        **event,
                        "event": "finished",
                        "elapsed_seconds": time.time() - started,
                    },
                )

        setattr(api, name, measured)


def snapshot(store, study, folder, state):
    save(folder / "window-manifest.json", list(windows(store, study)))
    selected = {
        "direction",
        "plan",
        "work",
        "work_result",
        "note",
        "source",
        "review",
        "report",
        "publication",
        "clarification",
        "clarification_answer",
        "retry",
        "cooldown",
        "analysis_result",
    }
    counts = dict(
        store.db.execute(
            "SELECT kind, COUNT(*) FROM artifacts WHERE study=? GROUP BY kind", (study,)
        ).fetchall()
    )
    artifacts = [a for kind in selected for a in store.list(study, kind)]
    artifacts.sort(key=lambda a: a.seq)
    works = {a.ref: a.body["role"] for a in artifacts if a.kind == "work"}
    records = store.usage_records(study)
    sources = [a for a in artifacts if a.kind == "source"]
    publications = [a for a in artifacts if a.kind == "publication"]
    reports = [a for a in artifacts if a.kind == "report"]
    result = {
        **state,
        "updated_at": time.time(),
        "artifact_counts": dict(counts),
        "roles": dict(Counter(works.values())),
        "usage": summarize(records),
        "usage_by_role": {
            role: summarize([r for r in records if works.get(r["work"]) == role])
            for role in set(works.values())
        },
        "operations": len(records),
        "unknown_operations": len(store.unsettled(study)),
        "source_count": len(sources),
        "unique_source_origins": len({a.body.get("origin") for a in sources}),
        "published": bool(publications),
        "elapsed_seconds": state.get("finished_at", time.time()) - state["started_at"],
        "research_seconds": (
            state.get("finished_at", time.time()) - state["approved_at"]
        )
        if state.get("approved_at")
        else None,
    }
    text = ""
    if publications:
        report = store.get(study, publications[-1].body["report"])
        text = report.body["text"]
        write(folder / "report.md", text)
        result["report_ref"] = report.ref
        result["evidence_source_count"] = len(report.body.get("evidence", []))
        result["citation_entries"] = len(report.body.get("citations", []))
    elif reports:
        write(folder / "draft.md", reports[-1].body["text"])
    result["report_metrics"] = {
        "unicode_characters": len(text),
        "non_whitespace_characters": len(re.sub(r"\s", "", text)),
        "heading_lines": len(re.findall(r"^#{1,6} ", text, re.M)),
        "table_lines": len(re.findall(r"^\|", text, re.M)),
    }
    save(folder / "metrics.json", result)
    save(folder / "calls.json", records)
    # Original role deliverables and review reasons, not extra LLM summaries.
    save(
        folder / "artifacts.json",
        [
            {"ref": a.ref, "kind": a.kind, "parents": a.parents, "body": a.body}
            for a in artifacts
            if a.kind
            in {
                "direction",
                "plan",
                "work",
                "work_result",
                "note",
                "review",
                "report",
                "publication",
                "clarification",
                "clarification_answer",
                "retry",
                "cooldown",
                "analysis_result",
            }
        ],
    )
    save(folder / "sources.json", [{"ref": a.ref, "body": a.body} for a in sources])
    return result


async def run(root, run_id, case_ids=None, *, queries):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", run_id):
        raise ValueError("invalid run ID")
    folder = root / ".epivra" / run_id
    folder.mkdir(parents=True, exist_ok=True)
    # OS-owned lock: crash releases it; a second launcher cannot duplicate work.
    import msvcrt

    with (folder / "runner.lock").open("a+b") as lock:
        lock.seek(0)
        if not lock.read(1):
            lock.write(b"0")
            lock.flush()
        lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        store = Store(folder / "research.db")
        try:
            cases = [
                json.loads(s)
                for s in Path(queries).read_text(encoding="utf-8").splitlines()
                if s.strip()
            ]
            if case_ids is not None:
                if not set(case_ids) <= {c["id"] for c in cases}:
                    raise ValueError("unknown benchmark case")
                cases = [c for c in cases if c["id"] in case_ids]
            keys = credentials(root / ".env")
            policy = freeze_model_settings(
                {
                    "provider": "deepseek",
                    "model": "deepseek-flash",
                    "network": True,
                    "public_sources": True,
                    "stream_model": True,
                    "search_providers": ["tavily", "duckduckgo"],
                    "reader_providers": ["jina", "tavily"],
                }
            )
            fingerprint = {
                str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted((root / "src/epivra").rglob("*.py"))
            }
            fingerprint["tools/run_benchmark10.py"] = hashlib.sha256(
                Path(__file__).read_bytes()
            ).hexdigest()
            manifest = {
                "cases": cases,
                "policy": policy,
                "code_sha256": fingerprint,
                "case_concurrency": 1,
                "shared_provider_capacity": Scheduler().capacity,
                "approval": "user_authorized_unchanged_plans",
                "quality_assessment": "deferred",
                "environment": environment(),
            }
            manifest_path = folder / "manifest.json"
            prior = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
            manifest["as_of_date"] = prior.get("as_of_date", datetime.now(timezone.utc).date().isoformat())
            policy["as_of_date"] = manifest["as_of_date"]
            if (
                manifest_path.exists()
                and json.loads(manifest_path.read_text(encoding="utf-8")) != manifest
            ):
                raise ValueError(
                    "frozen run changed; do not silently resume different inputs/code"
                )
            save(manifest_path, manifest)
            scheduler = Scheduler(history=store.admissions())
            states = {}

            async def case_run(case):
                study = f"{run_id}-case-{case['id']:02d}"
                target = folder / study
                target.mkdir(exist_ok=True)
                prior = (
                    json.loads((target / "metrics.json").read_text(encoding="utf-8"))
                    if (target / "metrics.json").exists()
                    else {}
                )
                state = states[study] = {
                    "study": study,
                    "id": case["id"],
                    "started_at": prior.get("started_at", time.time()),
                    "status": "running",
                    "approved_at": prior.get("approved_at"),
                }
                service, clients = None, []
                try:
                    if not store.list(study, "direction"):
                        store.create(study, case["prompt"], policy)
                    if store.list(study, "publication"):
                        state["status"] = "published"
                        if prior.get("finished_at"):
                            state["finished_at"] = prior["finished_at"]
                        return
                    service, clients = online_service(
                        store, study, keys, scheduler=scheduler
                    )
                    for i, api in enumerate(clients):
                        instrument(api, folder / "http-timing.jsonl", study, i)
                    await service.run(study)
                    c = store.control(study)
                    plans = store.list(study, "plan")
                    if not c.approved and plans and not service.errors:
                        store.command(
                            study,
                            "benchmark-auto-approve",
                            c.ref,
                            "approve",
                            {"plan": plans[-1].ref},
                        )
                        state["approved_at"] = time.time()
                        snapshot(store, study, target, state)
                        await service.run(study)
                    state.update(
                        status="published"
                        if store.list(study, "publication")
                        else "blocked",
                        errors=service.errors,
                        work_errors=service.work_errors,
                    )
                except asyncio.CancelledError:
                    state.update(status="interrupted", error_type="CancelledError")
                    raise
                except Exception as exc:
                    state.update(status="blocked", error_type=type(exc).__name__)
                finally:
                    state.setdefault("finished_at", time.time())
                    state["elapsed_seconds"] = (
                        state["finished_at"] - state["started_at"]
                    )
                    state["research_seconds"] = (
                        state["finished_at"] - state["approved_at"]
                        if state.get("approved_at")
                        else None
                    )
                    try:
                        snapshot(store, study, target, state)
                        if state["status"] == "published":
                            try:
                                await start(root)
                                imported = await send(
                                    root,
                                    {
                                        "action": "import_study",
                                        "study": study,
                                        "database": str(store.path),
                                    },
                                )
                                if "error" in imported:
                                    raise ValueError("product import rejected")
                                state["product_imported"] = True
                            except Exception as exc:
                                state["product_import_error"] = type(exc).__name__
                    finally:
                        if service:
                            await service.close()
                        await asyncio.gather(*(api.close() for api in clients))

            async def sequence():
                for case in cases:
                    try:
                        await case_run(case)
                    except Exception as exc:
                        study = f"{run_id}-case-{case['id']:02d}"
                        states.setdefault(
                            study,
                            {
                                "study": study,
                                "id": case["id"],
                                "started_at": time.time(),
                            },
                        ).update(status="blocked", runner_error=type(exc).__name__)

            task = asyncio.create_task(sequence())
            try:
                while True:
                    await asyncio.wait({task}, timeout=30)
                    rows = [
                        snapshot(store, study, folder / study, state)
                        for study, state in states.items()
                    ]
                    save(
                        folder / "status.json",
                        {
                            "pid": os.getpid(),
                            "updated_at": time.time(),
                            "complete": task.done(),
                            "cases": rows,
                            "queued_case_ids": [
                                c["id"]
                                for c in cases
                                if f"{run_id}-case-{c['id']:02d}" not in states
                            ],
                            "provider_queue": scheduler.snapshot(),
                        },
                    )
                    with (folder / "summary.csv").open(
                        "w", encoding="utf-8-sig", newline=""
                    ) as f:
                        columns = [
                            "id",
                            "status",
                            "elapsed_seconds",
                            "research_seconds",
                            "source_count",
                            "unique_source_origins",
                            "operations",
                            "unknown_operations",
                            "published",
                        ]
                        writer = csv.DictWriter(f, columns, extrasaction="ignore")
                        writer.writeheader()
                        writer.writerows(rows)
                    try:
                        import psutil

                        process = psutil.Process()
                        append(
                            folder / "resources.jsonl",
                            {
                                "at": time.time(),
                                "rss_bytes": process.memory_info().rss,
                                "cpu_seconds": sum(process.cpu_times()[:2]),
                                "threads": process.num_threads(),
                            },
                        )
                    except ImportError:
                        pass
                    if task.done():
                        await task
                        usage = []
                        for i, key in enumerate(keys["TAVILY_API_KEY"].split(","), 1):
                            api = JsonAPI("https://api.tavily.com", key)
                            try:
                                usage.append(
                                    {"slot": i, **await api.request("GET", "/usage")}
                                )
                            except Exception as exc:
                                usage.append(
                                    {"slot": i, "error_type": type(exc).__name__}
                                )
                            finally:
                                await api.close()
                        save(folder / "usage-after.json", usage)
                        break
            finally:
                if not task.done():
                    task.cancel()
                await asyncio.gather(task, return_exceptions=True)
                save(
                    folder / "status.json",
                    {
                        "pid": os.getpid(),
                        "updated_at": time.time(),
                        "complete": all(
                            f"{run_id}-case-{c['id']:02d}" in states
                            and states[f"{run_id}-case-{c['id']:02d}"]["status"]
                            != "interrupted"
                            for c in cases
                        ),
                        "cases": list(states.values()),
                        "queued_case_ids": [
                            c["id"]
                            for c in cases
                            if f"{run_id}-case-{c['id']:02d}" not in states
                        ],
                    },
                )
        finally:
            store.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--cases", type=int, nargs="+")
    parser.add_argument(
        "--queries", type=Path, help="JSONL cases with integer id and prompt"
    )
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.run_id):
        parser.error("invalid run ID")
    if args.status:
        print(
            json.dumps(
                run_status(root / ".epivra" / args.run_id), ensure_ascii=False, indent=2
            )
        )
    else:
        if args.queries is None:
            parser.error("--queries is required when starting a run")
        asyncio.run(run(root, args.run_id, args.cases, queries=args.queries))
