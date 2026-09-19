"""Small, explicit paid checks; never dispatch Benchmark-10 or change research policy."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import sys
import time
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from epivra.adapters import DEFAULT_MODEL, DeepSeek, JsonAPI, credentials
from epivra.diagnostics import environment, windows
from epivra.local_security import private_directory
from epivra.storage import Store
from epivra.usage import counters, summarize
from epivra.web_providers import connect
from evals.mechanism_cases import CASES
from tools.run_closed_loop_eval import run as closed_run
from tools.run_review_eval import run as review_run

CLOSED_CASES = {"archive", "decision", "measurement", "training"}
PRIVATE_FIELDS = {
    "reasoning_content", "reasoning_details", "encrypted_content", "signature",
    "authorization", "api_key", "request_headers", "response_headers",
}
PUBLIC_KINDS = {
    "direction", "plan", "work", "work_result", "work_wait", "clarification",
    "clarification_answer", "source", "evidence_anchor", "note", "memory",
    "report", "review", "publication", "observation", "retry", "cooldown",
}


def validate_request(value: object) -> dict:
    """Evaluation selection limits are not production research budget limits."""
    required = {"version", "request_id", "mode", "cases", "probe_providers"}
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError("unexpected live request fields")
    if type(value["version"]) is not int or value["version"] != 1:
        raise ValueError("unsupported live request version")
    if not isinstance(value["request_id"], str) or not re.fullmatch(
        r"[A-Za-z0-9_-]{1,64}", value["request_id"]
    ):
        raise ValueError("invalid request ID")
    if type(value["probe_providers"]) is not bool:
        raise ValueError("probe_providers must be boolean")
    cases = value["cases"]
    if not isinstance(cases, list) or any(not isinstance(c, str) for c in cases):
        raise ValueError("case IDs must be a list of strings")
    if len(set(cases)) != len(cases):
        raise ValueError("duplicate cases")
    mode = value["mode"]
    if mode == "review":
        known = {c["id"] + "-" + v for c in CASES for v in ("positive", "negative")}
        if not 1 <= len(cases) <= 4 or not set(cases) <= known:
            raise ValueError("select 1-4 existing review calibration cases")
    elif mode == "closed":
        if len(cases) != 1 or cases[0] not in CLOSED_CASES:
            raise ValueError("select one small existing closed-corpus case")
    elif mode == "providers":
        if cases or not value["probe_providers"]:
            raise ValueError("provider mode requires probes and no research cases")
    else:
        raise ValueError("large/benchmark batches need separate owner approval and workflow")
    return value


def scrub(value: object, secrets: tuple[str, ...]) -> object:
    """Defense in depth after allowlist projection; never export native protocol."""
    if isinstance(value, dict):
        if isinstance(value.get("type"), str) and value["type"] in {
            "thinking", "redacted_thinking", "reasoning"
        }:
            return {"type": "omitted_private_block"}
        return {
            str(scrub(k, secrets)): scrub(v, secrets)
            for k, v in value.items() if str(k).lower() not in PRIVATE_FIELDS
        }
    if isinstance(value, (tuple, list)):
        return [scrub(v, secrets) for v in value]
    if isinstance(value, str):
        for secret in sorted(secrets, key=len, reverse=True):
            if secret:
                value = value.replace(secret, "[REDACTED]")
    return value


def save(path: Path, value: object, secrets: tuple[str, ...] = ()) -> None:
    text = json.dumps(scrub(value, secrets), ensure_ascii=False, indent=2, allow_nan=False)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text + "\n", encoding="utf-8")
    temporary.replace(path)


def collect(database: Path) -> dict:
    """Project evidence, calls and actual-input receipts without step/response bodies."""
    if not database.is_file():
        raise ValueError("missing evaluation database")
    store = Store(database)
    try:
        studies = [r[0] for r in store.db.execute(
            "SELECT DISTINCT study FROM artifacts ORDER BY study"
        )]
        artifacts, window_records, calls = [], [], []
        unknown = 0
        for study in studies:
            for kind in sorted(PUBLIC_KINDS):
                artifacts.extend({
                    "study": study, "seq": a.seq, "ref": a.ref, "kind": a.kind,
                    "parents": a.parents, "body": a.body,
                } for a in store.iter_artifacts(study, kind))
            window_records.extend({"study": study, **row} for row in windows(store, study))
            calls.extend({"study": study, **r} for r in store.usage_records(study))
            unknown += len(store.unsettled(study))
        artifacts.sort(key=lambda a: a["seq"])
        return {
            "artifacts": artifacts, "windows": window_records, "calls": calls,
            "usage": summarize(calls), "unknown_operations": unknown,
        }
    finally:
        store.close()


def review_checks(rows: object, selected: list[str]) -> dict:
    if not isinstance(rows, list) or len(rows) != len(selected):
        raise ValueError("review output missing cases")
    if {r.get("case") for r in rows} != set(selected):
        raise ValueError("review output case identities differ")
    completed = all(
        r.get("error") is None and type(r.get("accepted")) is bool
        and isinstance(r.get("review"), dict) for r in rows
    )
    matches = sum(r.get("accepted") is r.get("expected_accept") for r in rows)
    return {
        "execution_complete": completed,
        "decision_matches": matches,
        "case_count": len(rows),
        "decision_gate": completed and matches == len(rows),
        "semantic_acceptance": "pending_independent_reason_review",
    }


async def provider_probe(keys: dict, record) -> bool:
    """One tiny completion, then one real search per configured Tavily slot; no retries."""
    api = JsonAPI("https://api.deepseek.com", keys["DEEPSEEK_API_KEY"], deadline=120)
    try:
        model = DeepSeek(api, thinking=False, max_tokens=32)
        raw = await api.post("/chat/completions", model._payload(
            [{"role": "user", "content": "Reply with exactly OK."}], []
        ))
        decoded = model.decode(raw)
        ok = decoded["complete"] and decoded["text"].strip() == "OK" and not decoded["calls"]
        record({"provider": "deepseek", "ok": ok, "http_status": raw.get("http_status"),
                "usage": counters(raw, "deepseek")})
        if not ok:
            return False
    finally:
        await api.close()
    slots = list(dict.fromkeys(k.strip() for k in keys["TAVILY_API_KEY"].split(",") if k.strip()))
    if not 1 <= len(slots) <= 4:
        raise ValueError("this small probe supports one to four Tavily slots")
    provider = connect("tavily", keys)
    try:
        all_ok = True
        for slot in range(1, len(slots) + 1):
            raw = await provider.search({"query": "site:docs.python.org asyncio TaskGroup"})
            # A rejection is recorded, not retried with another account for this request.
            status = raw.get("http_status")
            decoded = provider.decode_search(raw) if status == 200 else {"results": []}
            ok = status == 200 and bool(decoded["results"]) and raw.get("credential_slot") == slot
            record({"provider": "tavily", "slot": slot, "ok": ok,
                    "http_status": status, "results": len(decoded["results"]),
                    "usage": counters(raw, "tavily")})
            all_ok = all_ok and ok
        return all_ok
    finally:
        await provider.api.close()


async def run(root: Path, request: dict, run_id: str) -> int:
    request = validate_request(request)
    if os.environ.get("GITHUB_RUN_ATTEMPT", "1") != "1":
        raise ValueError("inspect the prior run, then commit an explicit new request")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", run_id):
        raise ValueError("invalid run ID")
    state = root / ".epivra" / f"live-{run_id}"
    output = root / "artifacts" / "live-eval"
    if state.exists() or output.exists():
        raise ValueError("fresh run and export directory required; never blindly replay paid checks")
    # Check legacy runner paths before any provider call, too.
    legacy = root / ".epivra" / (
        f"review-{run_id}" if request["mode"] == "review"
        else f"closed-{request['cases'][0]}-{run_id}" if request["mode"] == "closed"
        else f"probe-{run_id}"
    )
    if legacy.exists():
        raise ValueError("existing diagnostic run; inspect it instead of restarting")
    private_directory(state)
    output.mkdir(parents=True)
    keys = credentials(root / ".env")
    secrets = tuple(v for key, value in keys.items() for v in (
        value, *(k.strip() for k in value.split(","))
    ) if v)
    summary = {
        "version": 1, "run_id": run_id, "request": request,
        "commit": os.environ.get("GITHUB_SHA"), "started_at": time.time(),
        "execution_pass": False, "semantic_acceptance": "not_evaluated",
        "provider_probes": [],
    }
    save(output / "summary.json", summary, secrets)
    save(output / "environment.json", environment(), secrets)
    save(output / "request.json", request)
    fingerprints = {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for pattern in ("src/epivra/*.py", "tools/*eval*.py", "evals/*.json", "evals/*.py")
        for p in sorted(root.glob(pattern))
    }
    save(output / "code-manifest.json", fingerprints)
    database = legacy / "research.db"
    try:
        if not keys.get("DEEPSEEK_API_KEY", "").strip():
            raise ValueError("DeepSeek credential missing")
        if request["probe_providers"]:
            if not keys.get("TAVILY_API_KEY", "").strip():
                raise ValueError("Tavily credential missing")

            def record(row):
                summary["provider_probes"].append(row)
                save(output / "summary.json", summary, secrets)

            if not await provider_probe(keys, record):
                raise ValueError("provider functionality probe failed")
        with (state / "private-runner.log").open("w", encoding="utf-8") as log:
            # Existing diagnostic stdout may contain domain data. Only projections leave the runner.
            with redirect_stdout(log), redirect_stderr(log):
                if request["mode"] == "review":
                    await review_run(root, run_id, mechanisms=True, only=request["cases"])
                elif request["mode"] == "closed":
                    await closed_run(root, request["cases"][0], run_id)
        if request["mode"] == "review":
            rows = json.loads((legacy / "result.json").read_text(encoding="utf-8"))
            checks = review_checks(rows, request["cases"])
            save(output / "review-decisions.json", rows, secrets)
            summary.update(checks)
            summary["execution_pass"] = checks["execution_complete"]
            summary["validation_pass"] = checks["decision_gate"]
        elif request["mode"] == "closed":
            result = json.loads((legacy / "result.json").read_text(encoding="utf-8"))
            save(output / "closed-result.json", result, secrets)
            summary["execution_pass"] = bool(result.get("published")) and not result.get("errors")
            summary["validation_pass"] = summary["execution_pass"]
            summary["semantic_acceptance"] = "pending_primary_review"
            report = legacy / "report.md"
            if report.is_file():
                (output / "report.md").write_text(
                    str(scrub(report.read_text(encoding="utf-8"), secrets)), encoding="utf-8"
                )
        else:
            summary.update(execution_pass=True, validation_pass=True)
    except BaseException as exc:
        # Never log an exception message or provider body that might echo a key.
        summary.update(error_type=type(exc).__name__, validation_pass=False)
        if isinstance(exc, (KeyboardInterrupt, SystemExit, asyncio.CancelledError)):
            raise
    finally:
        if database.is_file():
            try:
                projection = collect(database)
                for field, name in (("artifacts", "public-artifacts.json"),
                                    ("windows", "window-manifest.json"), ("calls", "calls.json")):
                    save(output / name, projection[field], secrets)
                summary.update(usage=projection["usage"], unknown_operations=projection["unknown_operations"])
                if projection["unknown_operations"]:
                    summary["validation_pass"] = False
            except Exception as exc:
                summary.update(export_error_type=type(exc).__name__, validation_pass=False)
        summary["finished_at"] = time.time()
        summary["elapsed_seconds"] = summary["finished_at"] - summary["started_at"]
        save(output / "summary.json", summary, secrets)
        save(output / "artifact-manifest.json", {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir())
            if p.is_file() and p.name != "artifact-manifest.json"
        })
    print(json.dumps(scrub(summary, secrets), ensure_ascii=False), flush=True)
    return 0 if summary.get("validation_pass") else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        request = json.loads((root / "evals/live-request.json").read_text(encoding="utf-8"))
        code = asyncio.run(run(root, request, args.run_id))
    except Exception as exc:
        print(json.dumps({"validation_pass": False, "error_type": type(exc).__name__}))
        code = 1
    raise SystemExit(code)
