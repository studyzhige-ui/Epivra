"""Resource utilisation as an evaluation axis, measured across runs.

Phase 1e established why this is a separate axis rather than a footnote on cost
(`docs/ARCHITECTURE.md` §10.6): every fixture passed on its own terms -- each
ended in an honest report -- while yield per search varied a hundredfold between
them, tracking the share of branches that hit their tool ceiling.  A judge that
reads one report at a time is structurally blind to that.

It is also a *correctness* axis.  The run that discarded evidence concluded that
official regulatory text was unreachable when it had already been fetched and
stored, so a resource defect can arrive disguised as a research finding.

Everything here reads a finished database.  It never calls a provider, so a cost
report costs nothing to produce.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

#: Columns added when spend accounting was introduced.  Databases written before
#: that keep NULL, and a run with no measured call is reported as unmeasured
#: rather than free -- conflating the two under-counts in the direction that
#: looks reassuring.
_SPEND_COLUMNS = ("input_tokens", "output_tokens", "cached_input_tokens")


@dataclass(frozen=True, slots=True)
class ProviderSpend:
    """One provider's share of a run, in the units that provider bills in."""

    provider: str
    calls: int = 0
    input_tokens: int | None = None
    output_tokens: int | None = None
    cached_input_tokens: int | None = None

    @property
    def measured(self) -> bool:
        return self.input_tokens is not None or self.output_tokens is not None


@dataclass(frozen=True, slots=True)
class RunResources:
    """What one research run consumed, and what it produced for it.

    The ratios matter more than the totals: 1e's defect was invisible in any
    single total and obvious in ``materials_per_search`` across runs.
    """

    task_id: str
    database: str
    model_calls: int = 0
    searches: int = 0
    fetches_ok: int = 0
    fetches_failed: int = 0
    frozen_operations: int = 0
    source_snapshots: int = 0
    materials: int = 0
    published: int = 0
    input_tokens: int | None = None
    output_tokens: int | None = None
    cached_input_tokens: int | None = None
    wall_clock_seconds: float | None = None
    by_provider: tuple[ProviderSpend, ...] = ()
    by_role: tuple[ProviderSpend, ...] = ()

    @property
    def measured(self) -> bool:
        """Whether this run recorded spend at all."""

        return self.input_tokens is not None or self.output_tokens is not None

    @property
    def total_tokens(self) -> int | None:
        if not self.measured:
            return None
        return (self.input_tokens or 0) + (self.output_tokens or 0)

    @property
    def materials_per_search(self) -> float | None:
        """The ratio that exposed the discarded-evidence defect."""

        return self.materials / self.searches if self.searches else None

    @property
    def materials_per_snapshot(self) -> float | None:
        """Material committed per snapshot fetched.

        Can exceed 1.0 -- one source legitimately yields several Materials -- so
        this is a yield figure, not a percentage.  What matters is the low end: a
        large snapshot count with a small ratio is the signature of evidence
        bought and then discarded, which is how the 1e defect presented.
        """

        if not self.source_snapshots:
            return None
        return self.materials / self.source_snapshots

    @property
    def label(self) -> str:
        """Task plus which database it came from; the same task appears in several."""

        return f"{self.task_id}@{Path(self.database).stem}"

    @property
    def fetch_failure_rate(self) -> float | None:
        attempted = self.fetches_ok + self.fetches_failed
        return self.fetches_failed / attempted if attempted else None


@dataclass(frozen=True, slots=True)
class Cohort:
    """A set of runs compared side by side, which is the only view that works."""

    runs: tuple[RunResources, ...]

    @property
    def searches(self) -> int:
        return sum(run.searches for run in self.runs)

    @property
    def materials(self) -> int:
        return sum(run.materials for run in self.runs)

    @property
    def total_tokens(self) -> int | None:
        """None when no run in the cohort recorded spend, rather than zero."""

        measured = [run.total_tokens for run in self.runs if run.measured]
        return sum(value or 0 for value in measured) if measured else None

    @property
    def unmeasured_runs(self) -> tuple[str, ...]:
        """Runs whose spend predates accounting; excluded from token totals."""

        return tuple(run.label for run in self.runs if not run.measured)

    def yield_spread(self) -> tuple[RunResources, RunResources] | None:
        """The best and worst run by Material yield per search.

        Reported as a pair rather than a ratio because the useful question is
        *which* runs sit at the extremes -- that is what points at the cause.
        """

        ranked = [run for run in self.runs if run.materials_per_search is not None]
        if len(ranked) < 2:
            return None
        ranked.sort(key=lambda run: run.materials_per_search or 0.0)
        return ranked[-1], ranked[0]


def _columns(connection: sqlite3.Connection) -> set[str]:
    return {row[1] for row in connection.execute("PRAGMA table_info(operations)")}


def _sum_or_none(connection: sqlite3.Connection, column: str, task_id: str) -> int | None:
    """Total a spend column, distinguishing "no data" from "zero"."""

    row = connection.execute(
        f"SELECT SUM({column}), COUNT({column}) FROM operations "
        "WHERE task_id = ? AND status = 'completed'",
        (task_id,),
    ).fetchone()
    if row is None or not row[1]:
        return None
    return int(row[0] or 0)


def _wall_clock(
    connection: sqlite3.Connection, task_id: str, *, timed: bool
) -> float | None:
    """Elapsed time from the first request sent to the last one settled.

    This is wall clock over the whole run, not summed call latency: branches run
    concurrently, so summing would report far more time than actually passed.
    """

    if not timed:
        return None
    row = connection.execute(
        "SELECT MIN(started_at), MAX(settled_at) FROM operations "
        "WHERE task_id = ? AND started_at != '' AND settled_at != ''",
        (task_id,),
    ).fetchone()
    if row is None or not row[0] or not row[1]:
        return None
    try:
        start = datetime.fromisoformat(row[0])
        end = datetime.fromisoformat(row[1])
    except ValueError:
        return None
    seconds = (end - start).total_seconds()
    return seconds if seconds >= 0 else None


def _grouped(
    connection: sqlite3.Connection, task_id: str, expression: str, measured: bool
) -> tuple[ProviderSpend, ...]:
    columns = (
        ", SUM(input_tokens), SUM(output_tokens), SUM(cached_input_tokens)"
        if measured
        else ""
    )
    rows = connection.execute(
        f"SELECT {expression} AS bucket, COUNT(*){columns} FROM operations "
        "WHERE task_id = ? AND status = 'completed' AND kind = 'model_call' "
        "GROUP BY bucket ORDER BY bucket",
        (task_id,),
    ).fetchall()
    spend: list[ProviderSpend] = []
    for row in rows:
        spend.append(
            ProviderSpend(
                provider=str(row[0] or "(unknown)"),
                calls=int(row[1]),
                input_tokens=int(row[2]) if measured and row[2] is not None else None,
                output_tokens=int(row[3]) if measured and row[3] is not None else None,
                cached_input_tokens=(
                    int(row[4]) if measured and row[4] is not None else None
                ),
            )
        )
    return tuple(spend)


def _count(connection: sqlite3.Connection, sql: str, parameters: Sequence[object]) -> int:
    row = connection.execute(sql, tuple(parameters)).fetchone()
    return int(row[0]) if row else 0


def read_run(database: Path, task_id: str) -> RunResources:
    """Measure one task inside one database.  Read-only; never calls a provider."""

    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    try:
        columns = _columns(connection)
        measured = set(_SPEND_COLUMNS) <= columns
        timed = {"started_at", "settled_at"} <= columns
        ops = "SELECT COUNT(*) FROM operations WHERE task_id = ?"
        return RunResources(
            task_id=task_id,
            database=str(database),
            model_calls=_count(
                connection, f"{ops} AND kind = 'model_call' AND status = 'completed'",
                (task_id,),
            ),
            searches=_count(
                connection, f"{ops} AND kind = 'search' AND status = 'completed'",
                (task_id,),
            ),
            fetches_ok=_count(
                connection, f"{ops} AND kind = 'fetch' AND status = 'completed'",
                (task_id,),
            ),
            fetches_failed=_count(
                connection, f"{ops} AND kind = 'fetch' AND status != 'completed'",
                (task_id,),
            ),
            frozen_operations=_count(
                connection, f"{ops} AND status = 'needs_reconciliation'", (task_id,)
            ),
            source_snapshots=_count(
                connection,
                "SELECT COUNT(*) FROM artifacts WHERE task_id = ? AND kind = ?",
                (task_id, "source_snapshot"),
            ),
            materials=_count(
                connection,
                "SELECT COUNT(*) FROM artifacts WHERE task_id = ? AND kind = ?",
                (task_id, "material"),
            ),
            published=_count(
                connection,
                "SELECT COUNT(*) FROM artifacts WHERE task_id = ? AND kind = ?",
                (task_id, "publication_receipt"),
            ),
            input_tokens=(
                _sum_or_none(connection, "input_tokens", task_id) if measured else None
            ),
            output_tokens=(
                _sum_or_none(connection, "output_tokens", task_id) if measured else None
            ),
            cached_input_tokens=(
                _sum_or_none(connection, "cached_input_tokens", task_id)
                if measured
                else None
            ),
            wall_clock_seconds=_wall_clock(connection, task_id, timed=timed),
            by_provider=_grouped(
                connection,
                task_id,
                "json_extract(execution, '$.model_id')",
                measured,
            ),
            by_role=_grouped(connection, task_id, "role", measured),
        )
    finally:
        connection.close()


def task_ids(database: Path) -> tuple[str, ...]:
    """Every task the database holds artifacts for.

    Returns nothing for a database that is not one of ours -- the runs directory
    also holds a legacy corpus and LangGraph checkpoint files, and a cost report
    should skip those rather than fail on the first one it meets.
    """

    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    try:
        tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        if not {"artifacts", "operations"} <= tables:
            return ()
        rows = connection.execute(
            "SELECT DISTINCT task_id FROM artifacts ORDER BY task_id"
        ).fetchall()
        return tuple(str(row[0]) for row in rows)
    finally:
        connection.close()


def read_cohort(databases: Iterable[Path]) -> Cohort:
    """Measure every task in every database, skipping ones with no operations."""

    runs: list[RunResources] = []
    for database in databases:
        if not Path(database).is_file():
            continue
        for task_id in task_ids(Path(database)):
            run = read_run(Path(database), task_id)
            if run.model_calls or run.searches:
                runs.append(run)
    return Cohort(runs=tuple(runs))


__all__ = [
    "Cohort",
    "ProviderSpend",
    "RunResources",
    "read_cohort",
    "read_run",
    "task_ids",
]
