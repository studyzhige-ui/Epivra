from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from deep_research_agent.api import (
    DEFAULT_WORKFLOW_RECURSION_LIMIT,
    ResearchAgent,
    TaskAlreadyExistsError,
    create_memory_agent,
    inspect_sqlite_task,
    open_sqlite_agent,
)
from deep_research_agent.checkpoint import CheckpointWriterBusyError
from tests.test_workflow import OfflineRoles


class ResearchAgentApiTest(unittest.IsolatedAsyncioTestCase):
    async def test_start_status_and_approval_use_one_thread(self) -> None:
        roles = OfflineRoles()
        agent = create_memory_agent(
            roles.executors(), content_store=roles.content_store
        )

        started = await agent.start("测试问题", task_id="api-thread")
        inspected = await agent.status("api-thread")
        completed = await agent.resume("api-thread", {"action": "approve"})

        self.assertEqual("awaiting_approval", started.status)
        self.assertEqual(started, inspected)
        self.assertEqual("completed", completed.status)
        self.assertEqual("api-thread", completed.task_id)
        self.assertIn("## References", completed.final_report)

    async def test_revision_regenerates_a_complete_approval_card(self) -> None:
        roles = OfflineRoles()
        agent = create_memory_agent(
            roles.executors(), content_store=roles.content_store
        )
        await agent.start("测试问题", task_id="revision")

        revised = await agent.resume(
            "revision", {"action": "revise", "feedback": "缩小到 2026 年"}
        )

        self.assertEqual("awaiting_approval", revised.status)
        self.assertEqual(2, roles.planner_calls)
        self.assertTrue(revised.approval_card.startswith("# 研究计划"))

    async def test_start_refuses_to_reuse_an_existing_thread(self) -> None:
        roles = OfflineRoles()
        agent = create_memory_agent(
            roles.executors(), content_store=roles.content_store
        )
        await agent.start("first question", task_id="same-thread")

        with self.assertRaises(TaskAlreadyExistsError):
            await agent.start("different question", task_id="same-thread")

    async def test_concurrent_start_runs_planner_only_once(self) -> None:
        class BlockingRoles(OfflineRoles):
            def __init__(self) -> None:
                super().__init__()
                self.entered = asyncio.Event()
                self.release = asyncio.Event()

            async def planner(self, context):  # type: ignore[no-untyped-def]
                self.entered.set()
                await self.release.wait()
                return await super().planner(context)

        roles = BlockingRoles()
        agent = create_memory_agent(
            roles.executors(), content_store=roles.content_store
        )
        first = asyncio.create_task(agent.start("first", task_id="one-writer"))
        await roles.entered.wait()
        second = asyncio.create_task(
            agent.start("second", task_id="one-writer")
        )
        await asyncio.sleep(0)
        roles.release.set()

        started = await first
        with self.assertRaises(TaskAlreadyExistsError):
            await second
        self.assertEqual("awaiting_approval", started.status)
        self.assertEqual(1, roles.planner_calls)

    async def test_concurrent_resume_consumes_one_interrupt_only_once(self) -> None:
        roles = OfflineRoles()
        agent = create_memory_agent(
            roles.executors(), content_store=roles.content_store
        )
        await agent.start("测试问题", task_id="one-approval")

        first, second = await asyncio.gather(
            agent.resume("one-approval", {"action": "approve"}),
            agent.resume("one-approval", {"action": "approve"}),
            return_exceptions=True,
        )

        outcomes = (first, second)
        self.assertEqual(
            1,
            sum(
                not isinstance(outcome, BaseException)
                and outcome.status == "completed"
                for outcome in outcomes
            ),
        )
        rejected = next(
            outcome for outcome in outcomes if isinstance(outcome, BaseException)
        )
        self.assertIsInstance(rejected, ValueError)
        self.assertIn("not awaiting user input", str(rejected))
        self.assertEqual(2, len(roles.researcher_contexts))

    async def test_sqlite_runtime_enforces_one_writer_process(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "checkpoints.sqlite3"
            roles = OfflineRoles().executors()

            async with open_sqlite_agent(roles, database):
                with self.assertRaises(CheckpointWriterBusyError):
                    async with open_sqlite_agent(roles, database):
                        self.fail("a second writer must never open")

    async def test_unknown_task_is_consistent_for_status_and_resume(self) -> None:
        roles = OfflineRoles()
        agent = create_memory_agent(
            roles.executors(), content_store=roles.content_store
        )

        with self.assertRaises(KeyError):
            await agent.status("missing")
        with self.assertRaises(KeyError):
            await agent.resume("missing", {"action": "approve"})

    async def test_readonly_status_does_not_create_a_missing_database(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "missing.sqlite3"

            with self.assertRaises(KeyError):
                await inspect_sqlite_task(database, "missing")
            self.assertFalse(database.exists())

    async def test_pending_checkpoint_has_a_distinct_continue_operation(self) -> None:
        class PendingGraph:
            def __init__(self) -> None:
                self.pending = True
                self.configs: list[dict[str, object]] = []

            async def aget_state(self, _config):  # type: ignore[no-untyped-def]
                return SimpleNamespace(
                    values={"task_id": "pending", "stage": "researching"},
                    tasks=(),
                    interrupts=(),
                    next=("supervisor",) if self.pending else (),
                )

            async def ainvoke(self, value, config):  # type: ignore[no-untyped-def]
                if value is not None:
                    raise AssertionError("continue must use ainvoke(None)")
                self.configs.append(config)
                self.pending = False
                return {"stage": "finished", "final_report": "完成"}

        graph = PendingGraph()
        agent = ResearchAgent(graph, recursion_limit=17)

        inspected = await agent.status("pending")
        self.assertEqual("recoverable_pause", inspected.status)
        with self.assertRaisesRegex(ValueError, "no retryable failure"):
            await agent.retry("pending")
        with self.assertRaisesRegex(ValueError, "not awaiting user input"):
            await agent.resume("pending", {"response": "wrong operation"})

        completed = await agent.continue_task("pending")
        self.assertEqual("completed", completed.status)
        self.assertEqual(17, graph.configs[0]["recursion_limit"])
        with self.assertRaisesRegex(ValueError, "no pending work"):
            await agent.continue_task("pending")

    async def test_continue_rejects_an_actual_interrupt(self) -> None:
        roles = OfflineRoles()
        agent = create_memory_agent(
            roles.executors(), content_store=roles.content_store
        )
        await agent.start("测试问题", task_id="needs-human")

        with self.assertRaisesRegex(ValueError, "use resume"):
            await agent.continue_task("needs-human")

    async def test_real_sqlite_pending_checkpoint_is_readonly_inspectable(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "recoverable.sqlite3"
            role_state = OfflineRoles()

            async with open_sqlite_agent(
                role_state.executors(), database, recursion_limit=1
            ) as agent:
                paused = await agent.start("测试问题", task_id="recoverable")

            self.assertEqual("recoverable_pause", paused.status)
            planner_calls = role_state.planner_calls
            inspected = await inspect_sqlite_task(database, "recoverable")
            self.assertEqual("recoverable_pause", inspected.status)
            self.assertEqual(planner_calls, role_state.planner_calls)

            async with open_sqlite_agent(
                role_state.executors(),
                database,
                recursion_limit=DEFAULT_WORKFLOW_RECURSION_LIMIT,
            ) as agent:
                continued = await agent.continue_task("recoverable")

            self.assertEqual("awaiting_approval", continued.status)

    async def test_real_sqlite_failure_is_readonly_inspectable(self) -> None:
        class FailingRoles(OfflineRoles):
            async def planner(self, context):  # type: ignore[no-untyped-def]
                del context
                raise RuntimeError("private provider detail")

        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "failed.sqlite3"
            roles = FailingRoles()
            async with open_sqlite_agent(roles.executors(), database) as agent:
                failed = await agent.start("测试问题", task_id="failed")

            self.assertEqual("retryable_failure", failed.status)
            inspected = await inspect_sqlite_task(database, "failed")
            self.assertEqual("retryable_failure", inspected.status)
            self.assertNotIn("private provider detail", inspected.error_summary)

    async def test_failed_checkpoint_requires_explicit_retry(self) -> None:
        class RetryGraph:
            def __init__(self) -> None:
                self.failed = True
                self.inputs: list[object] = []

            async def aget_state(self, _config):  # type: ignore[no-untyped-def]
                tasks = (
                    (SimpleNamespace(error="private timeout detail"),)
                    if self.failed
                    else ()
                )
                return SimpleNamespace(
                    values={"task_id": "retryable", "stage": "researching"},
                    tasks=tasks,
                    interrupts=(),
                    next=("planner",) if self.failed else (),
                )

            async def ainvoke(self, value, _config):  # type: ignore[no-untyped-def]
                self.inputs.append(value)
                if value is not None:
                    raise AssertionError("retry must not masquerade as resume")
                self.failed = False
                return {"stage": "finished", "final_report": "完成"}

        graph = RetryGraph()
        agent = ResearchAgent(graph)

        failed = await agent.status("retryable")
        self.assertEqual("retryable_failure", failed.status)
        self.assertNotIn("private timeout detail", failed.error_summary)
        with self.assertRaisesRegex(ValueError, "use retry"):
            await agent.resume("retryable", {"response": "not a retry"})
        with self.assertRaisesRegex(ValueError, "use retry"):
            await agent.continue_task("retryable")

        completed = await agent.retry("retryable")
        self.assertEqual("completed", completed.status)
        self.assertEqual([None], graph.inputs)

    async def test_fundamental_clarification_precedes_plan_approval(self) -> None:
        roles = OfflineRoles(clarify_first=True)
        agent = create_memory_agent(
            roles.executors(), content_store=roles.content_store
        )

        question = await agent.start("ambiguous", task_id="clarification")
        plan = await agent.resume(
            "clarification", {"response": "研究整个市场"}
        )

        self.assertEqual("awaiting_user", question.status)
        self.assertIn("产品还是整个市场", question.user_prompt)
        self.assertEqual("awaiting_approval", plan.status)
        self.assertEqual(2, roles.planner_calls)


if __name__ == "__main__":
    unittest.main()
