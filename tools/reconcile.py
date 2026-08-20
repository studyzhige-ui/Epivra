"""Inspect and clear operations frozen with an unknown provider outcome.

``needs_reconciliation`` means the ledger sent a request and cannot tell whether
the provider executed it.  It refuses to retry (that risks paying twice) and
refuses to record a failure (that risks discarding a result already paid for), so
it stops and waits for a human.  Automation must not clear it -- that is the whole
point of the state.

The ledger has always been able to list these; nothing surfaced them, so a human
had no instrument for the one job only a human can do.  In practice every frozen
row so far came from two classification bugs since fixed, which is exactly why the
tool matters: without a way to look, "55 frozen operations" was invisible until
someone went digging.

Usage::

    python tools/reconcile.py --glob '.deep-research-agent/*.sqlite3'
    python tools/reconcile.py --database run.sqlite3 --resolve op_ab12... --note "..."
"""

from __future__ import annotations

import argparse
import asyncio
import glob as globbing
import sys
from pathlib import Path

import aiosqlite

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from deep_research_agent.content_store import SqliteContentStore  # noqa: E402
from deep_research_agent.operations import (  # noqa: E402
    OperationError,
    SqliteOperationLedger,
)


async def inspect(database: Path) -> int:
    """List frozen operations with enough detail to decide what happened."""

    connection = await aiosqlite.connect(database)
    try:
        content = SqliteContentStore(connection)
        await content.setup()
        ledger = SqliteOperationLedger(connection, content)
        await ledger.setup()
        # The ledger scopes reconciliation by task, so ask it per task rather
        # than reaching past it into the table.
        tasks = [
            str(row[0])
            for row in await connection.execute_fetchall(
                "SELECT DISTINCT task_id FROM operations "
                "WHERE status = 'needs_reconciliation' ORDER BY task_id"
            )
        ]
        frozen = [
            record for task in tasks for record in await ledger.pending_reconciliation(task)
        ]
        if not frozen:
            return 0
        print(f"\n=== {database} ===")
        for record in frozen:
            print(
                f"  {record.operation_id}  {record.kind}/{record.role}"
                f"  attempts={record.attempts}/{record.max_attempts}"
            )
            print(f"      task    : {record.task_id}")
            print(
                f"      execution: {record.execution.provider}/{record.execution.model_id}"
            )
            print(f"      detail  : {record.detail or '(none)'}")
        print(
            f"  共 {len(frozen)} 条。每一条都要人工判断供应商到底执行了没有：\n"
            "    - 确认没执行 → --resolve <op> 之后可重跑（会重新发起）\n"
            "    - 确认执行过但结果拿不回来 → --resolve <op> 并在 note 里写明放弃该结果\n"
            "  不要因为想让运行继续就批量清除：这个状态存在的意义就是不猜。"
        )
        return len(frozen)
    finally:
        await connection.close()


async def resolve(database: Path, operation_id: str, note: str) -> int:
    """Clear one frozen operation after a human decided what happened.

    Deliberately one at a time and requiring a note.  A bulk clear would turn a
    deliberate stop into a formality, which is how "we may have paid twice"
    becomes nobody's problem.
    """

    if not note.strip():
        print("必须给出 --note：说明你判断供应商到底执行了没有，以及依据。")
        return 2
    connection = await aiosqlite.connect(database)
    try:
        content = SqliteContentStore(connection)
        await content.setup()
        ledger = SqliteOperationLedger(connection, content)
        await ledger.setup()
        record = await ledger.get(operation_id)
        if record is None:
            print(f"{operation_id} 不在这个库里。")
            return 1
        if record.status != "needs_reconciliation":
            print(f"{operation_id} 当前状态是 {record.status}，不需要对账。")
            return 1
        try:
            # Recorded as a decided, unbilled failure so the operation becomes
            # retryable; the note carries the human judgment that made it so.
            await ledger.fail(
                operation_id,
                category="not_executed",
                detail=f"reconciled by operator: {note.strip()}",
            )
        except OperationError as error:
            print(f"无法对账：{error}")
            return 1
        await connection.commit()
        print(f"{operation_id} 已对账并恢复为可重试。理由：{note.strip()}")
        return 0
    finally:
        await connection.close()


async def run(args: argparse.Namespace) -> int:
    paths = list(args.databases)
    if args.glob:
        paths.extend(Path(item) for item in sorted(globbing.glob(args.glob)))
    paths = [path for path in paths if path.is_file()]
    if not paths:
        print("给出至少一个数据库路径，或用 --glob")
        return 2

    if args.resolve:
        if len(paths) != 1:
            print("--resolve 只能对一个数据库使用，请用 --database 指定。")
            return 2
        return await resolve(paths[0], args.resolve, args.note)

    total = 0
    for path in paths:
        total += await inspect(path)
    if not total:
        print("没有需要对账的操作。")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", dest="databases", nargs="*", default=[], type=Path)
    parser.add_argument("--glob", default="")
    parser.add_argument("--resolve", default="", help="要对账的 operation_id")
    parser.add_argument("--note", default="", help="人工判断的依据，--resolve 时必填")
    return asyncio.run(run(parser.parse_args(argv)))


if __name__ == "__main__":
    sys.exit(main())
