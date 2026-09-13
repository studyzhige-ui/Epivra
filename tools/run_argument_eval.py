"""Opt-in controlled handoff regression using an actual prior report, never ideal findings.

The fixture schedules checks -> final review -> one writer revision -> fresh checks
and review. All findings and revisions come from the production Harness. This is
not an autonomous lead test; use run_closed_loop_eval for that.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from epivra.adapters import DeepSeek, JsonAPI, credentials
from epivra.domain import identity
from epivra.harness import Harness
from epivra.storage import Store
from tools.run_closed_loop_eval import export
from tools.run_review_eval import bind_run, source_snapshot


async def run(root: Path, run_id: str, report_db: Path, tasks_file: Path):
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", run_id):
        raise ValueError("invalid run ID")
    tasks = json.loads(tasks_file.read_text(encoding="utf-8"))
    if (
        not isinstance(tasks, list)
        or not tasks
        or any(not isinstance(t, str) or not t.strip() for t in tasks)
    ):
        raise ValueError("provide a JSON list of complete argument-check tasks")
    snapshot = {"path": str(report_db.resolve()), **source_snapshot(report_db)}
    folder = root / ".epivra" / f"argument-{run_id}"
    bind_run(
        root,
        folder,
        [
            {
                "tasks": tasks,
                "driver": identity(Path(__file__).read_text(encoding="utf-8")),
            }
        ],
        "high",
        snapshot,
    )
    database = folder / "research.db"
    if not database.exists():
        with closing(
            sqlite3.connect(report_db.resolve().as_uri() + "?mode=ro", uri=True)
        ) as source:
            with closing(sqlite3.connect(database)) as destination:
                source.backup(destination)
        if source_snapshot(database) != {
            k: v for k, v in snapshot.items() if k != "path"
        }:
            (folder / "fixture.json").unlink()
            raise ValueError("source changed while copying; use a new run ID")
    store = Store(database)
    api = JsonAPI(
        "https://api.deepseek.com", credentials(root / ".env")["DEEPSEEK_API_KEY"]
    )
    harness = Harness(store, DeepSeek(api, stream=True, reasoning_effort="high"))
    study = snapshot["study"]
    control = store.control(study)
    owner = store.work(
        study,
        control.ref,
        "lead",
        "受控协作回归：复用原稿验证论证检查、修订及整稿裁决。",
    )
    initial = store.get(study, snapshot["report"])
    initial_seq = store.get(study, snapshot["report"]).seq
    reports = []

    async def drive(work):
        while not harness.finished(study, work.ref):
            if harness.waiting(study, work.ref):
                raise ValueError(
                    "fixture requires lead clarification; not a semantic failure"
                )
            await harness.step(study, work.ref)
            print(
                json.dumps(
                    {
                        "role": work.body["role"],
                        "mode": work.body.get("review_mode"),
                        "steps": len(harness._steps(study, "step", work.ref)),
                    }
                ),
                flush=True,
            )
        return harness._steps(study, "work_result", work.ref)[-1]

    try:
        report = initial
        for round_number in range(2):
            checks = []
            for task in tasks:
                work = store.work(
                    study,
                    control.ref,
                    "reviewer",
                    task,
                    (report.ref, *report.body["evidence"]),
                    owner.ref,
                    review_mode="check",
                )
                checks.append(await drive(work))
            work = store.work(
                study,
                control.ref,
                "reviewer",
                "依据用户原用途和同版本论证检查原成果，完成整稿裁决。复用已完成检查，检查实际覆盖、理由及跨部分一致性；只以影响正常使用的实质问题阻断。无需查找旧核查结论。",
                (report.ref, *(c.ref for c in checks)),
                owner.ref,
            )
            decision = store.get(study, (await drive(work)).body["ref"])
            reports.append(
                {
                    "report": report.ref,
                    "checks": [c.ref for c in checks],
                    "review": decision.ref,
                    "accepted": decision.body["accepted"],
                }
            )
            (folder / "handoffs.json").write_text(
                json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            if decision.body["accepted"]:
                if round_number:
                    store.publish(
                        study, owner.ref, control.epoch, report.ref, decision.ref
                    )
                break
            if round_number:
                break
            research = tuple(
                ref
                for ref in initial.parents
                if store.get(study, ref).kind == "work_result"
                and store.get(study, store.get(study, ref).body["producer"]).body[
                    "role"
                ]
                in {"investigator", "synthesizer"}
            )
            writer = store.work(
                study,
                control.ref,
                "writer",
                "根据当前核查及原研究成果修订成可正常交付的报告。自行确认缺陷影响，更新受影响的摘要、表格、论证及建议，保留仍成立的内容；不要求原建议必须改变，也不限定只能换词。成品服务原用户用途，删去不必要的重复和内部纠错日志。handoff说明前提变化与相关结论如何处理。",
                (report.ref, decision.ref, *(c.ref for c in checks), *research),
                owner.ref,
            )
            report = store.get(study, (await drive(writer)).body["ref"])
        (folder / "candidate.md").write_text(report.body["text"], encoding="utf-8")
    finally:
        export(store, study, folder, {}, running=False)
        # Export() includes the seed history. Keep the new-work boundary explicit.
        (folder / "scope.json").write_text(
            json.dumps(
                {
                    "owner": owner.ref,
                    "seed_report": initial.ref,
                    "seed_report_seq": initial_seq,
                    "scope": "controlled actual-output handoffs, one revision; not autonomous lead acceptance",
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        await api.close()
        store.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--report-db", required=True, type=Path)
    parser.add_argument("--tasks-file", required=True, type=Path)
    args = parser.parse_args()
    asyncio.run(
        run(
            Path(__file__).resolve().parents[1],
            args.run_id,
            args.report_db,
            args.tasks_file,
        )
    )
