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
import sys
from pathlib import Path

import aiosqlite

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from deep_research_agent.application import (  # noqa: E402
    build_runtimes,
    load_environment,
    render_role_models,
)
from deep_research_agent.artifact_store import SqliteArtifactStore  # noqa: E402
from deep_research_agent.config import Role, load_config  # noqa: E402
from deep_research_agent.content_store import SqliteContentStore  # noqa: E402
from deep_research_agent.contract import build_contract  # noqa: E402
from deep_research_agent.operations import SqliteOperationLedger  # noqa: E402
from deep_research_agent.reporting import run_reporting  # noqa: E402

#: The reporting transaction touches only these three; building the others
#: would demand credentials the segment never uses.
REPORTING_ROLES: tuple[Role, ...] = ("analyst", "author", "reviewer")


async def ensure_contract(store: SqliteArtifactStore, contract_path: Path) -> None:
    """Commit the approved Contract if this task does not already have one.

    The Contract is stored in its own canonical encoding, not as raw markdown:
    a body written one way and read another is what made the reporting segment
    fail on a database that had a perfectly valid Contract in it.
    """

    view = await store.active_view()
    if view.head("research_contract") is not None:
        return
    contract = build_contract(contract_path.read_text(encoding="utf-8"))
    await store.put(kind="research_contract", body=contract.encode())


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
        print(render_role_models(load_config(environ), REPORTING_ROLES))
        runtimes = build_runtimes(environ, roles=REPORTING_ROLES)

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
            environ=load_environment(args.env),
            output=args.output,
        )
    )


if __name__ == "__main__":
    sys.exit(main())
