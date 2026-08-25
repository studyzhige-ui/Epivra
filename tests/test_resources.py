"""Resource metrics have to be honest about what they do not know.

A cost report is only useful if it cannot flatter itself.  Two ways it could:
counting an unmeasured run as free, and counting a replayed call as spend.  Both
are pinned here, along with cross-run yield and tool-ceiling ratios.
"""

from __future__ import annotations

import asyncio
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

import aiosqlite

from deep_research_agent.artifact_store import SqliteArtifactStore
from deep_research_agent.content_store import SqliteContentStore
from deep_research_agent.operations import (
    ExecutionIdentity,
    OperationRequest,
    SqliteOperationLedger,
    run_once,
)

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "eval_resources", ROOT / "evals" / "resources.py"
)
assert _spec is not None and _spec.loader is not None
resources = importlib.util.module_from_spec(_spec)
sys.modules["eval_resources"] = resources
_spec.loader.exec_module(resources)

EXECUTION = ExecutionIdentity(provider="scripted", model_id="test-model")


def _request(kind: str, index: int, task_id: str = "task-1") -> OperationRequest:
    return OperationRequest(
        task_id=task_id,
        kind=kind,
        role="investigator" if kind != "model_call" else "analyst",
        execution=EXECUTION,
        parameters={"n": str(index)},
    )


class RunResourcesTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._directory = tempfile.TemporaryDirectory()
        self.path = Path(self._directory.name) / "run.sqlite3"
        self._connection = await aiosqlite.connect(self.path)
        content = SqliteContentStore(self._connection)
        await content.setup()
        self.store = SqliteArtifactStore(self._connection, content, task_id="task-1")
        await self.store.setup()
        self.ledger = SqliteOperationLedger(self._connection, content)
        await self.ledger.setup()

    async def asyncTearDown(self) -> None:
        await self._connection.close()
        self._directory.cleanup()

    async def _spend(self, kind: str, index: int, usage: dict[str, int] | None) -> None:
        async def send() -> str:
            return f"outcome {kind} {index}"

        await run_once(
            self.ledger,
            _request(kind, index),
            send,
            usage_of=(lambda _outcome: usage) if usage else None,
        )

    async def test_a_run_reports_tokens_time_and_yield(self) -> None:
        await self._spend("model_call", 1, {"input_tokens": 9000, "output_tokens": 800})
        await self._spend("model_call", 2, {"input_tokens": 1000, "output_tokens": 200})
        for index in range(4):
            await self._spend("search", index, None)
        await self.store.put(kind="source_snapshot", body="s1")
        await self.store.put(kind="source_snapshot", body="s2")
        await self.store.put(kind="material", body="m1")
        await self.store.put(kind="material", body="m2")
        await self.store.put(kind="material", body="m3")
        await self._connection.commit()

        run = resources.read_run(self.path, "task-1")
        self.assertEqual(2, run.model_calls)
        self.assertEqual(4, run.searches)
        self.assertEqual(10_000, run.input_tokens)
        self.assertEqual(1_000, run.output_tokens)
        self.assertEqual(11_000, run.total_tokens)
        self.assertAlmostEqual(0.75, run.materials_per_search or 0.0)
        self.assertAlmostEqual(1.5, run.materials_per_snapshot or 0.0)
        self.assertIsNotNone(run.wall_clock_seconds)
        self.assertGreaterEqual(run.wall_clock_seconds or -1.0, 0.0)

    async def test_a_replayed_call_is_not_counted_twice(self) -> None:
        usage = {"input_tokens": 400, "output_tokens": 90}
        await self._spend("model_call", 1, usage)
        await self._spend("model_call", 1, usage)

        run = resources.read_run(self.path, "task-1")
        self.assertEqual(1, run.model_calls)
        self.assertEqual(400, run.input_tokens)

    async def test_an_unmeasured_run_is_unmeasured_not_free(self) -> None:
        await self._spend("model_call", 1, None)

        run = resources.read_run(self.path, "task-1")
        self.assertFalse(run.measured)
        self.assertIsNone(run.total_tokens)
        self.assertIsNone(run.input_tokens)

    async def test_spend_is_attributed_by_role_and_by_model(self) -> None:
        await self._spend("model_call", 1, {"input_tokens": 100, "output_tokens": 10})

        run = resources.read_run(self.path, "task-1")
        self.assertEqual(("analyst",), tuple(item.provider for item in run.by_role))
        self.assertEqual(
            ("test-model",), tuple(item.provider for item in run.by_provider)
        )
        self.assertEqual(100, run.by_role[0].input_tokens)

    async def test_a_frozen_operation_is_surfaced(self) -> None:
        record = await self.ledger.reserve(_request("fetch", 1))
        await self.ledger.mark_sent(record.operation_id)
        await self.ledger.flag_reconciliation(record.operation_id, "unknown")
        await self._connection.commit()

        run = resources.read_run(self.path, "task-1")
        self.assertEqual(1, run.frozen_operations)


class CohortTest(unittest.TestCase):
    """The cross-run view is the only one that shows a resource defect."""

    def _run(self, task: str, searches: int, materials: int, **kwargs) -> object:  # noqa: ANN003
        return resources.RunResources(
            task_id=task,
            database=f"/tmp/{task}.sqlite3",
            searches=searches,
            materials=materials,
            **kwargs,
        )

    def test_the_spread_names_the_extreme_runs(self) -> None:
        cohort = resources.Cohort(
            runs=(
                self._run("no-visual-needed", 70, 88),
                self._run("sparse-evidence", 100, 62),
                self._run("regulatory-timepoint", 382, 5),
            )
        )
        spread = cohort.yield_spread()
        assert spread is not None
        best, worst = spread
        self.assertEqual("no-visual-needed", best.task_id)
        self.assertEqual("regulatory-timepoint", worst.task_id)

    def test_a_cohort_with_no_measured_run_reports_none_not_zero(self) -> None:
        cohort = resources.Cohort(runs=(self._run("a", 10, 2), self._run("b", 10, 3)))
        self.assertIsNone(cohort.total_tokens)
        self.assertEqual(2, len(cohort.unmeasured_runs))

    def test_measured_and_unmeasured_runs_do_not_contaminate_each_other(self) -> None:
        cohort = resources.Cohort(
            runs=(
                self._run("measured", 10, 5, input_tokens=900, output_tokens=100),
                self._run("legacy", 10, 5),
            )
        )
        self.assertEqual(1000, cohort.total_tokens)
        self.assertEqual(("legacy@legacy",), cohort.unmeasured_runs)

    def test_a_label_distinguishes_the_same_task_in_two_databases(self) -> None:
        first = resources.RunResources(task_id="t", database="/x/one.sqlite3")
        second = resources.RunResources(task_id="t", database="/x/two.sqlite3")
        self.assertNotEqual(first.label, second.label)


class ForeignDatabaseTest(unittest.TestCase):
    def test_a_database_that_is_not_ours_is_skipped_rather_than_fatal(self) -> None:
        """A scan may encounter SQLite files that belong to another application."""

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "foreign.sqlite3"

            async def build() -> None:
                connection = await aiosqlite.connect(path)
                await connection.execute("CREATE TABLE unrelated (id INTEGER)")
                await connection.commit()
                await connection.close()

            asyncio.run(build())
            self.assertEqual((), resources.task_ids(path))
            self.assertEqual((), resources.read_cohort([path]).runs)


class SurvivalTest(unittest.IsolatedAsyncioTestCase):
    """Spending is only justified by what reaches the reader.

    The resource requirement is not "spend less" but "spend nothing that does not
    survive into the deliverable". genre-shift fetched 151 sources and cited 15:
    136 paid fetches no reader will ever see.
    """

    async def asyncSetUp(self) -> None:
        self._directory = tempfile.TemporaryDirectory()
        self.path = Path(self._directory.name) / "survival.sqlite3"
        self._connection = await aiosqlite.connect(self.path)
        content = SqliteContentStore(self._connection)
        await content.setup()
        self.store = SqliteArtifactStore(self._connection, content, task_id="task-1")
        await self.store.setup()
        self.ledger = SqliteOperationLedger(self._connection, content)
        await self.ledger.setup()

    async def asyncTearDown(self) -> None:
        await self._connection.close()
        self._directory.cleanup()

    async def _publish(self, body: str, snapshots: int) -> None:
        for index in range(snapshots):
            await self.store.put(kind="source_snapshot", body=f"s{index}")
        await self.store.put(kind="publication_receipt", body=body)
        await self._connection.commit()

    async def test_only_the_reference_list_is_counted(self) -> None:
        """Report bodies are full of numbered lists; counting them inflates it."""

        body = "\n".join(
            [
                "# 报告",
                "",
                "## 缺口清单",
                "",
                "1. 本土负担未量化",
                "2. 可及性未确认",
                "3. 季节性缺失",
                "",
                "## 参考资料",
                "",
                "1. A trial. https://a.example/1",
                "2. B guidance. https://b.example/2",
            ]
        )
        await self._publish(body, snapshots=10)

        run = resources.read_run(self.path, "task-1")
        self.assertEqual(2, run.cited_sources)
        self.assertAlmostEqual(0.2, run.source_survival or 0.0)

    async def test_an_unpublished_run_has_no_survival_rate(self) -> None:
        for index in range(3):
            await self.store.put(kind="source_snapshot", body=f"s{index}")
        await self._connection.commit()

        run = resources.read_run(self.path, "task-1")
        self.assertIsNone(run.cited_sources)
        self.assertIsNone(run.source_survival)

    async def test_a_report_without_a_reference_section_is_not_guessed_at(self) -> None:
        await self._publish("# 报告\n\n1. 一条编号列表\n", snapshots=4)

        run = resources.read_run(self.path, "task-1")
        self.assertIsNone(run.cited_sources)


if __name__ == "__main__":
    unittest.main()
