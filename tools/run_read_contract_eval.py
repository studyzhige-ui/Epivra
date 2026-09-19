"""Run identical small probes against one explicitly selected implementation.

The workflow runs this same script with baseline/candidate PYTHONPATH in separate
processes. No runtime monkeypatch, private database upload or prompt relabeling.
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
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import epivra
from epivra.adapters import DEFAULT_MODEL, DeepSeek, JsonAPI, credentials
from epivra.citations import render
from epivra.diagnostics import environment
from epivra.domain import identity
from epivra.harness import Harness
from epivra.local_security import private_directory
from epivra.prompts import ROLES
from epivra.storage import Store
from evals.read_contract_cases import REPORT_CASES, SOURCE_CASES, selection
from tools.run_live_eval import collect, save, scrub

BASELINE = "96968e399832aea53e016434841fa9be52d48fb5"


def seed(store: Store, case_id: str):
    report_case = REPORT_CASES.get(case_id)
    if report_case:
        # Independent reference counts; only the user constraint enters context.
        author_text = report_case["template"].replace("@CITE0@", "[1]")
        expected_count = sum(not c.isspace() for c in author_text)
        maximum = expected_count + report_case["allowance"]
        request = (
            "Produce a short report using the supplied record. The maximum is "
            f"{maximum} non-whitespace Unicode code points of author-supplied text "
            "before the automatically appended references. Include the title, "
            "headings, Markdown and inline citation markers in that count; exclude "
            "only the host-generated reference list. State the recorded result accurately."
        )
        source_case = report_case
        role = "reviewer"
    else:
        role, key = case_id.split("-", 1)
        source_case = SOURCE_CASES[key]
        request = source_case["task"]
    c = store.create(case_id, request, {"network": False, "as_of_date": "2026-09-19"})
    plan = store.put(case_id, "plan", {"text": "Use only the supplied original record."}, (c.direction,))
    c = store.command(case_id, "fixture-approval", c.ref, "approve", {"plan": plan.ref})
    source = store.put(case_id, "source", {"text": source_case["source"], "origin": source_case["origin"], "title": source_case.get("title", source_case["origin"])})
    if role == "lead":
        work = store.work(case_id, c.ref, role, "Continue the approved task by arranging the necessary examination of the supplied original record.", (source.ref,))
        expected = {"action": "delegate_source_examination"}
    else:
        owner = store.work(case_id, c.ref, "lead", "Coordinate supplied-record research.")
        if report_case:
            investigator = store.work(case_id, c.ref, "investigator", "Examine record.", (source.ref,), owner.ref)
            finding = store.put(case_id, "work_result", {"text": source_case["source"], "producer": investigator.ref}, (investigator.ref, source.ref))
            writer = store.work(case_id, c.ref, "writer", "Write the supplied result.", (finding.ref,), owner.ref)
            rendered = render(report_case["template"].replace("@CITE0@", "[[cite:" + source.ref + "]]"), [source.ref], lambda ref: store.get(case_id, ref))
            assert rendered["text"][:rendered["citation_body_length"]] == author_text
            report = store.put(case_id, "report", {**rendered, "evidence": [source.ref], "producer": writer.ref}, (writer.ref, c.direction, source.ref, finding.ref))
            work = store.work(case_id, c.ref, role, "Independently review the exact report against the original task and source; give your review with its actual basis.", (report.ref, source.ref), owner.ref)
            expected = {"accept": report_case["accept"], "author_non_whitespace_characters": expected_count, "maximum": maximum}
        else:
            work = store.work(case_id, c.ref, role, request, (source.ref,), owner.ref)
            expected = {"action": "read_original_source"}
    return work, source, expected


def assess(store: Store, case_id: str, work, source, expected: dict) -> dict:
    observations = [a.body for a in store.list(case_id, "observation")]
    failed = [o for o in observations if o.get("failure") or o.get("error")]
    row = {"case": case_id, "expected": expected, "tools": [o.get("tool") for o in observations], "tool_failures": len(failed)}
    if work.body["role"] == "reviewer":
        reviews = [a.body for a in store.list(case_id, "review") if a.body.get("work") == work.ref]
        row["review"] = reviews[-1] if reviews else None
        row["observed"] = reviews[-1]["accepted"] if reviews else None
        row["contract_match"] = bool(reviews) and row["observed"] is expected["accept"]
        row["scope"] = "final review decision; reasons still require independent inspection"
    else:
        delegated = any(a.body["role"] == "investigator" and a.body.get("owner") == work.ref for a in store.list(case_id, "work"))
        read = any(o.get("tool") in {"read_source", "read_artifact", "read_artifact_range"} and o.get("result", {}).get("ref") == source.ref and not o.get("failure") for o in observations)
        row["observed"] = {"delegated": delegated, "source_read": read}
        row["contract_match"] = not failed and (delegated if work.body["role"] == "lead" else read)
        row["scope"] = "first model turn only; not completed research"
    return row


async def run(root: Path, request: dict, run_id: str, arm: str) -> int:
    cases = selection(request)  # Reject selections before touching credentials.
    if arm not in {"baseline", "candidate"} or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", run_id):
        raise ValueError("invalid run identity")
    if os.environ.get("GITHUB_RUN_ATTEMPT", "1") != "1":
        raise ValueError("inspect the original attempt instead of blindly repeating paid calls")
    source_root = Path(epivra.__file__).resolve().parent
    expected_root = root / (".baseline/src/epivra" if arm == "baseline" else "src/epivra")
    if source_root != expected_root.resolve():
        raise ValueError("PYTHONPATH does not identify the requested implementation")
    folder = root / ".epivra" / f"read-contract-{run_id}-{arm}"
    output = root / "artifacts" / f"read-contract-{arm}"
    if folder.exists() or output.exists():
        raise ValueError("fresh run required; existing records are audit-only")
    private_directory(folder)
    output.mkdir(parents=True)
    keys = credentials(root / ".env")
    secret = keys.get("DEEPSEEK_API_KEY", "").strip()
    if not secret:
        raise ValueError("DeepSeek credential missing")
    secrets = (secret,)
    summary = {"arm": arm, "request": request, "execution_commit": os.environ.get("GITHUB_SHA"), "source_commit": BASELINE if arm == "baseline" else os.environ.get("GITHUB_SHA"), "model": DEFAULT_MODEL, "role_instructions_hash": identity(ROLES), "started_at": time.time(), "results": [], "semantic_acceptance": "not_a_general_research_quality_score"}
    save(output / "environment.json", environment(), secrets)
    save(output / "source-manifest.json", {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(source_root.glob("*.py"))})
    save(output / "eval-manifest.json", {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__), root / "evals/read_contract_cases.py", root / "evals/read-contract-request.json")})
    store = Store(folder / "research.db")
    api = JsonAPI("https://api.deepseek.com", secret)
    harness = Harness(store, DeepSeek(api, stream=True))
    try:
        with (folder / "private-runner.log").open("w", encoding="utf-8") as log, redirect_stdout(log), redirect_stderr(log):
            for case_id in cases:
                try:
                    work, source, expected = seed(store, case_id)
                    if work.body["role"] == "reviewer":
                        while not harness.finished(case_id, work.ref):
                            if harness.waiting(case_id, work.ref):
                                break  # A clarification is incomplete, not an acceptance.
                            await harness.step(case_id, work.ref)
                    else:
                        await harness.step(case_id, work.ref)
                    row = assess(store, case_id, work, source, expected)
                except Exception as exc:
                    row = {"case": case_id, "error_type": type(exc).__name__, "contract_match": False}
                summary["results"].append(row)
                save(output / "summary.json", summary, secrets)
    finally:
        await api.close()
        store.close()
        projection = collect(folder / "research.db")
        for name, field in (("public-artifacts.json", "artifacts"), ("window-manifest.json", "windows"), ("calls.json", "calls")):
            save(output / name, projection[field], secrets)
        summary.update(usage=projection["usage"], unknown_operations=projection["unknown_operations"], elapsed_seconds=time.time()-summary["started_at"])
        summary["contract_gate"] = len(summary["results"]) == len(cases) and all(r["contract_match"] for r in summary["results"]) and not projection["unknown_operations"]
        save(output / "summary.json", summary, secrets)
        save(output / "artifact-manifest.json", {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir()) if p.name != "artifact-manifest.json"})
    print(json.dumps(scrub(summary, secrets), ensure_ascii=False), flush=True)
    return 0 if summary["contract_gate"] else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--arm", choices=("baseline", "candidate"), required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        code = asyncio.run(run(root, json.loads((root / "evals/read-contract-request.json").read_text(encoding="utf-8")), args.run_id, args.arm))
    except Exception as exc:
        print(json.dumps({"contract_gate": False, "error_type": type(exc).__name__}))
        code = 1
    raise SystemExit(code)
