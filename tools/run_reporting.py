"""Drive the reporting transaction over a recovered evidence database.

This is the first live exercise of the segment that never completed before, so
it is deliberately a thin script: build the role runtimes from configuration,
commit a Contract if the task has none, and run the transaction.  Everything it
does is already covered by scripted tests; what it adds is a real provider.

Usage::

    python tools/run_reporting.py --database <recovered.sqlite3> --task-id <id>
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys
from pathlib import Path

import aiosqlite

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from deep_research_agent.artifact_store import SqliteArtifactStore  # noqa: E402
from deep_research_agent.config import Role, load_config  # noqa: E402
from deep_research_agent.content_store import SqliteContentStore  # noqa: E402
from deep_research_agent.contract import build_contract  # noqa: E402
from deep_research_agent.model import OpenAICompatibleClient  # noqa: E402
from deep_research_agent.operations import (  # noqa: E402
    ExecutionIdentity,
    SqliteOperationLedger,
)
from deep_research_agent.reporting import RoleRuntime, run_reporting  # noqa: E402

REPORTING_ROLES: tuple[Role, ...] = ("analyst", "author", "reviewer")


def load_env(path: Path) -> dict[str, str]:
    """Read a .env file without adding a dependency for one small format."""

    values = dict(os.environ)
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*)$", line)
        if match:
            values[match.group(1)] = match.group(2).strip()
    return values


def build_runtimes(environ: dict[str, str]) -> dict[str, RoleRuntime]:
    """Bind each role to the model its tier resolves to."""

    config = load_config(environ)
    runtimes: dict[str, RoleRuntime] = {}
    for role in REPORTING_ROLES:
        chosen = config.model_for(role)
        runtimes[role] = RoleRuntime(
            model=OpenAICompatibleClient(
                chosen.api_key(environ),
                model=chosen.model_id,
                api_base=chosen.api_base,
            ),
            execution=ExecutionIdentity(
                provider=chosen.provider.name,
                endpoint=chosen.api_base,
                model_id=chosen.model_id,
            ),
        )
        print(f"  {role:<9} {chosen.tier:<10} {chosen.model_id}")
    return runtimes


async def ensure_contract(store: SqliteArtifactStore, contract_path: Path) -> None:
    """Commit the approved Contract if this task does not already have one."""

    view = await store.active_view()
    if view.head("research_contract") is not None:
        return
    body = contract_path.read_text(encoding="utf-8")
    build_contract(body)  # reject a Contract without a usable question model
    await store.put(kind="research_contract", body=body)


async def drive(
    database: Path,
    *,
    task_id: str,
    contract_path: Path,
    report_brief: str,
    stop_rationale: str,
    environ: dict[str, str],
    output: Path,
) -> int:
    connection = await aiosqlite.connect(database)
    try:
        content = SqliteContentStore(connection)
        await content.setup()
        store = SqliteArtifactStore(connection, content, task_id=task_id)
        await store.setup()
        ledger = SqliteOperationLedger(connection, content)
        await ledger.setup()

        await ensure_contract(store, contract_path)
        view = await store.active_view()
        print(f"evidence set: {view.evidence_set_id()}")
        print(f"materials:    {len(view.active('material'))}")
        print(f"sources:      {len(view.active('source_snapshot'))}")

        print("\nroles:")
        runtimes = build_runtimes(environ)

        print("\nrunning reporting transaction...")
        outcome = await run_reporting(
            store,
            ledger,
            runtimes,
            report_brief=report_brief,
            stop_rationale=stop_rationale,
        )

        print(f"\nsynthesis:  {outcome.synthesis_ref}")
        print(f"commission: {outcome.commission_ref}")
        for index, ref in enumerate(outcome.report_refs, start=1):
            print(f"report {index}:   {ref}")
        for index, review in enumerate(outcome.reviews, start=1):
            verdict = "approved" if review.approved else "blocked"
            print(f"review {index}:   {verdict} ({len(review.findings)} findings)")
            for finding in review.findings:
                print(f"    - {finding.splitlines()[0]}")

        if not outcome.published:
            print(f"\nnot published: {outcome.halted_reason}")
            return 1

        assert outcome.rendered is not None
        output.write_text(outcome.rendered.markdown, encoding="utf-8")
        print(f"\npublication: {outcome.publication_ref}")
        print(f"references:  {len(outcome.rendered.references)}")
        print(f"cited materials: {len(outcome.rendered.used_material_refs)}")
        print(f"written to:  {output} ({len(outcome.rendered.markdown)} chars)")
        return 0
    finally:
        await connection.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--env", type=Path, default=Path(".env"))
    parser.add_argument(
        "--brief", default="面向医院母婴护理团队的决策简报，用于选择婴儿 RSV 预防路径。"
    )
    parser.add_argument(
        "--stop-rationale",
        default="已恢复的公开证据覆盖监管标签、ACIP 记录与关键试验，达到当前能力边界。",
    )
    args = parser.parse_args(argv)

    return asyncio.run(
        drive(
            args.database,
            task_id=args.task_id,
            contract_path=args.contract,
            report_brief=args.brief,
            stop_rationale=args.stop_rationale,
            environ=load_env(args.env),
            output=args.output,
        )
    )


if __name__ == "__main__":
    sys.exit(main())
