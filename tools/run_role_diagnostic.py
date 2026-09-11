"""Opt-in role isolation: vary a delegation or a writer's input, not both."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sqlite3
import sys
from collections import Counter
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from deep_research_agent.adapters import DeepSeek, JsonAPI, credentials
from deep_research_agent.harness import Harness
from deep_research_agent.storage import Store
from tools.run_closed_loop_eval import export
from tools.run_review_eval import bind_run


async def run(
    root: Path,
    run_id: str,
    trace_path: Path,
    variant: str,
    reference: Path | None = None,
):
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", run_id):
        raise ValueError("invalid run ID")
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    investigations = [
        a["body"]
        for a in trace
        if a["kind"] == "work" and a["body"]["role"] == "investigator"
    ]
    if len(investigations) != 1:
        raise ValueError("diagnostic requires one unambiguous investigator task")
    case = next(
        c
        for c in json.loads(
            (root / "evals/closed_loop_cases.json").read_text(encoding="utf-8")
        )
        if c["id"] == "measurement"
    )
    task = (
        "完整回答用户的研究问题，形成供后续写作使用的调查成果。"
        if variant == "direct"
        else investigations[0]["task"]
    )
    writing = variant.startswith("writer-")
    answer = None
    if writing:
        if reference is None:
            raise ValueError("writer comparison requires a frozen reference file")
        reference_data = json.loads(reference.read_text(encoding="utf-8"))
        if (
            reference_data["sources"] != case["sources"]
            or reference_data["task"] != case["task"]
        ):
            raise ValueError("reference describes a different research problem")
        reference_text = reference_data["investigation"]
        outputs = [
            a["body"]
            for a in trace
            if a["kind"] == "work_result"
            and a["body"].get("producer")
            == next(
                x["ref"]
                for x in trace
                if x["kind"] == "work" and x["body"] == investigations[0]
            )
        ]
        if len(outputs) != 1:
            raise ValueError("expected one investigation result")
        answer = reference_text if variant == "writer-reference" else outputs[0]["text"]
        task = (
            "依据选定调查成果，为用户撰写可直接使用的报告；实质研究缺口按角色职责处理。"
        )
    # Preserve the original authorized directory for both arms. Neither arm
    # changes source availability, role instructions, tools, or user direction.
    plan = next(a["body"] for a in trace if a["kind"] == "plan")
    with closing(
        sqlite3.connect(
            f"{(trace_path.parent / 'research.db').resolve().as_uri()}?mode=ro",
            uri=True,
        )
    ) as db:
        records = {
            ref: [kind, json.loads(body), json.loads(parents)]
            for ref, kind, body, parents in db.execute(
                "SELECT ref,kind,body,parents FROM artifacts WHERE kind IN ('source','material_bytes','catalog')"
            )
        }
    catalogs = [body for kind, body, _ in records.values() if kind == "catalog"]
    if len(catalogs) != 1:
        raise ValueError("diagnostic requires exactly one source catalog")
    if any(
        parent not in records
        for _, _, parents in records.values()
        for parent in parents
    ):
        raise ValueError("source ancestry is incomplete")
    if Counter(
        body["text"] for kind, body, _ in records.values() if kind == "source"
    ) != Counter(case["sources"]):
        raise ValueError("trace sources differ from the diagnostic case")
    catalog = catalogs[0]

    def check_corpus():
        corpus = Path(catalog["root"]).resolve()
        paths = {corpus / entry["path"] for entry in catalog["entries"]}
        if paths != {p for p in corpus.rglob("*") if p.is_file()} or any(
            not p.resolve().is_relative_to(corpus) for p in paths
        ):
            raise ValueError("authorized diagnostic corpus changed")
        if Counter(p.read_text(encoding="utf-8") for p in paths) != Counter(
            case["sources"]
        ):
            raise ValueError("disk materials differ from frozen diagnostic sources")

    check_corpus()
    folder = root / ".deep-research-agent" / f"diagnostic-{run_id}-{variant}"
    bind_run(
        root,
        folder,
        [
            {
                "request": case["task"],
                "sources": case["sources"],
                "task": task,
                "answer": answer,
                "plan": plan,
                "records": records,
                "diagnostic_code": Path(__file__).read_text(encoding="utf-8"),
            }
        ],
        "high",
    )
    store = Store(folder / "research.db")
    api = None
    try:
        if not store.list("measurement", "direction"):
            c = store.create(
                "measurement",
                case["task"],
                {"network": False, "local_roots": [catalog["root"]]},
            )
            approved = store.put("measurement", "plan", plan, (c.direction,))
            store.command(
                "measurement", "fixture", c.ref, "approve", {"plan": approved.ref}
            )
            # Copy only domain source/catalog artifacts. No previous conclusions,
            # review labels or provider records enter either investigator.
            copied = set()

            def copy(ref):
                if ref in copied:
                    return
                kind, body, parents = records[ref]
                for parent in parents:
                    copy(parent)
                item = store.put("measurement", kind, body, tuple(parents))
                if item.ref != ref:
                    raise ValueError("source identity changed")
                copied.add(ref)

            for ref in records:
                copy(ref)
        c = store.control("measurement")
        owner = store.work("measurement", c.ref, "lead", "Diagnostic fixture")
        inputs = ()
        if writing:
            producer = store.work(
                "measurement",
                c.ref,
                "investigator",
                "Fixture investigation",
                (),
                owner.ref,
            )
            refs = [ref for ref, (kind, _, _) in records.items() if kind == "source"]
            result = store.put(
                "measurement",
                "work_result",
                {"text": answer, "refs": refs, "producer": producer.ref},
                (producer.ref, c.direction, *refs),
            )
            inputs = (result.ref,)
        work = store.work(
            "measurement",
            c.ref,
            "writer" if writing else "investigator",
            task,
            inputs,
            owner.ref,
        )
        api = JsonAPI(
            "https://api.deepseek.com", credentials(root / ".env")["DEEPSEEK_API_KEY"]
        )
        harness = Harness(store, DeepSeek(api, stream=True))
        while not harness.finished("measurement", work.ref):
            await harness.step("measurement", work.ref)
            print(
                json.dumps(
                    {
                        "variant": variant,
                        "steps": len(store.list("measurement", "step")),
                    }
                ),
                flush=True,
            )
        check_corpus()
        export(store, "measurement", folder, {})
        reports = [
            a
            for a in store.list("measurement", "report")
            if a.body.get("producer") == work.ref
        ]
        if reports:
            (folder / "report.md").write_text(
                reports[-1].body["text"], encoding="utf-8"
            )
    finally:
        if api:
            await api.close()
        store.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument(
        "--variant",
        choices=("direct", "delegated", "writer-reference", "writer-actual"),
        required=True,
    )
    parser.add_argument("--reference", type=Path)
    args = parser.parse_args()
    asyncio.run(
        run(
            Path(__file__).resolve().parents[1],
            args.run_id,
            args.trace,
            args.variant,
            args.reference,
        )
    )
