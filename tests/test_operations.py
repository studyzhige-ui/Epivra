from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import aiosqlite

from deep_research_agent.content_store import SqliteContentStore
from deep_research_agent.operations import (
    ExecutionIdentity,
    OperationBudgetExhausted,
    OperationError,
    OperationReconciliationRequired,
    OperationRequest,
    SqliteOperationLedger,
    require_operation_id,
    run_once,
)
from deep_research_agent.sources import ArtifactValidationError


def execution() -> ExecutionIdentity:
    return ExecutionIdentity(
        provider="deepseek",
        endpoint="https://api.example.test/v1/chat",
        model_id="test-model",
        limits={"max_input_chars": "400000"},
    )


def request(**overrides: object) -> OperationRequest:
    defaults: dict[str, object] = {
        "task_id": "task-1",
        "kind": "model_call",
        "role": "analyst",
        "execution": execution(),
        "input_refs": ("syn_000000000000000000000001",),
        "parameters": {"purpose": "incremental synthesis"},
    }
    defaults.update(overrides)
    return OperationRequest(**defaults)  # type: ignore[arg-type]


class LedgerFixture(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._directory = tempfile.TemporaryDirectory()
        self._path = Path(self._directory.name) / "ledger.sqlite3"
        self._connection = await aiosqlite.connect(self._path)
        self.content_store = SqliteContentStore(self._connection)
        await self.content_store.setup()
        self.ledger = SqliteOperationLedger(self._connection, self.content_store)
        await self.ledger.setup()

    async def asyncTearDown(self) -> None:
        await self._connection.close()
        self._directory.cleanup()

    async def reopen(self) -> SqliteOperationLedger:
        """Simulate a process restart against the same durable database."""

        await self._connection.close()
        self._connection = await aiosqlite.connect(self._path)
        self.content_store = SqliteContentStore(self._connection)
        self.ledger = SqliteOperationLedger(self._connection, self.content_store)
        return self.ledger


class FingerprintTest(unittest.TestCase):
    def test_identical_work_shares_one_operation_id(self) -> None:
        self.assertEqual(request().operation_id(), request().operation_id())
        require_operation_id(request().operation_id())

    def test_input_order_and_duplicates_do_not_change_identity(self) -> None:
        first = request(input_refs=("mat_a", "mat_b"))
        second = request(input_refs=("mat_b", "mat_a", "mat_b"))
        self.assertEqual(first.operation_id(), second.operation_id())

    def test_different_task_role_or_inputs_are_different_operations(self) -> None:
        base = request().operation_id()
        self.assertNotEqual(base, request(task_id="task-2").operation_id())
        self.assertNotEqual(base, request(role="author").operation_id())
        self.assertNotEqual(base, request(input_refs=("mat_other",)).operation_id())
        self.assertNotEqual(
            base, request(parameters={"purpose": "consolidation"}).operation_id()
        )

    def test_a_different_model_is_a_different_operation(self) -> None:
        other = ExecutionIdentity(
            provider="deepseek",
            endpoint="https://api.example.test/v1/chat",
            model_id="other-model",
        )
        self.assertNotEqual(
            request().operation_id(), request(execution=other).operation_id()
        )

    def test_credential_shaped_fields_are_refused(self) -> None:
        with self.assertRaisesRegex(ArtifactValidationError, "credential"):
            ExecutionIdentity(provider="tavily", limits={"api_key": "secret"})
        with self.assertRaisesRegex(ArtifactValidationError, "credential"):
            request(parameters={"Authorization": "Bearer x"})
        with self.assertRaisesRegex(ArtifactValidationError, "credential"):
            request(parameters={"session_token": "x"})

    def test_malformed_operation_ids_are_rejected(self) -> None:
        for value in ("op_short", "operation-1", "", "OP_000000000000000000000001"):
            with self.subTest(value=value):
                with self.assertRaises(ArtifactValidationError):
                    require_operation_id(value)


class ReplayTest(LedgerFixture):
    async def test_a_completed_call_replays_without_calling_out_again(self) -> None:
        calls: list[int] = []

        async def send() -> str:
            calls.append(1)
            return "provider outcome"

        first = await run_once(self.ledger, request(), send)
        second = await run_once(self.ledger, request(), send)

        self.assertEqual("provider outcome", first)
        self.assertEqual("provider outcome", second)
        self.assertEqual(1, len(calls))

    async def test_replay_survives_a_process_restart(self) -> None:
        calls: list[int] = []

        async def send() -> str:
            calls.append(1)
            return "expensive answer"

        await run_once(self.ledger, request(), send)
        ledger = await self.reopen()
        replayed = await run_once(ledger, request(), send)

        self.assertEqual("expensive answer", replayed)
        self.assertEqual(1, len(calls))

    async def test_reserving_twice_returns_the_same_record(self) -> None:
        first = await self.ledger.reserve(request())
        second = await self.ledger.reserve(request())

        self.assertEqual(first.operation_id, second.operation_id)
        self.assertEqual("reserved", second.status)
        self.assertEqual(0, second.attempts)


class UnknownOutcomeTest(LedgerFixture):
    async def test_a_crash_after_sending_forces_reconciliation(self) -> None:
        record = await self.ledger.reserve(request())
        await self.ledger.mark_sent(record.operation_id)

        ledger = await self.reopen()

        async def send() -> str:  # pragma: no cover - must never run
            raise AssertionError("an unknown outcome must never be re-sent")

        with self.assertRaises(OperationReconciliationRequired):
            await run_once(ledger, request(), send)

        frozen = await ledger.get(record.operation_id)
        assert frozen is not None
        self.assertEqual("needs_reconciliation", frozen.status)

    async def test_a_raised_provider_error_is_treated_as_possibly_executed(self) -> None:
        async def send() -> str:
            raise TimeoutError("no response")

        with self.assertRaises(TimeoutError):
            await run_once(self.ledger, request(), send)

        record = await self.ledger.get(request().operation_id())
        assert record is not None
        self.assertEqual("needs_reconciliation", record.status)
        self.assertIn("TimeoutError", record.detail)

    async def test_reconciliation_blocks_every_ordinary_retry(self) -> None:
        async def send() -> str:
            raise ConnectionResetError("mid-flight")

        with self.assertRaises(ConnectionResetError):
            await run_once(self.ledger, request(), send)

        for _ in range(3):
            with self.assertRaises(OperationReconciliationRequired):
                await run_once(self.ledger, request(), _never_called)

    async def test_pending_reconciliation_is_visible_per_task(self) -> None:
        async def send() -> str:
            raise TimeoutError("unknown")

        with self.assertRaises(TimeoutError):
            await run_once(self.ledger, request(), send)

        blocked = await self.ledger.pending_reconciliation("task-1")
        self.assertEqual(1, len(blocked))
        self.assertEqual((), await self.ledger.pending_reconciliation("task-2"))

    async def test_several_unknown_operations_can_block_at_once(self) -> None:
        async def send() -> str:
            raise TimeoutError("unknown")

        for role in ("investigator", "curator"):
            with self.assertRaises(TimeoutError):
                await run_once(self.ledger, request(role=role), send)

        blocked = await self.ledger.pending_reconciliation("task-1")
        self.assertEqual(2, len(blocked))

    async def test_a_completed_operation_cannot_be_reconciled(self) -> None:
        async def send() -> str:
            return "done"

        await run_once(self.ledger, request(), send)
        with self.assertRaisesRegex(OperationError, "already completed"):
            await self.ledger.flag_reconciliation(request().operation_id())


class DecidedCapacityFailureTest(LedgerFixture):
    """A failure the provider stated plainly must never reach reconciliation.

    This is the regression test for the worst defect the audit found.  Truncation
    used to fall through to the catch-all, so the ledger froze the operation as
    "we cannot know whether the provider ran" -- when in fact the provider had
    said exactly what happened.  Frozen is terminal for automation, and the
    fingerprint is deterministic, so **retrying with a perfectly healthy model
    raised the same frozen error forever**: one over-long report made a study
    permanently unadvanceable, recoverable only through a developer script.
    """

    class Truncated(RuntimeError):
        pass

    async def test_capacity_failures_settle_instead_of_freezing(self) -> None:
        async def send() -> str:
            raise self.Truncated("output hit the ceiling")

        with self.assertRaises(self.Truncated):
            await run_once(
                self.ledger, request(), send, capacity=(self.Truncated,)
            )

        record = await self.ledger.get(request().operation_id())
        assert record is not None
        self.assertEqual("failed", record.status)
        self.assertEqual("capacity", record.failure)
        # Nothing to reconcile: a human has no question to answer here.
        self.assertEqual((), await self.ledger.pending_reconciliation("task-1"))

    async def test_raising_the_limit_is_a_new_operation(self) -> None:
        """The fix for a capacity failure has to be reachable, and this is how.

        Execution limits are part of the fingerprint, so raising the output
        ceiling is different work rather than a retry of work that cannot
        succeed.  Without this the settled failure would be just as terminal as
        the frozen one -- same key, same outcome, forever.
        """

        async def send() -> str:
            raise self.Truncated("output hit the ceiling")

        with self.assertRaises(self.Truncated):
            await run_once(
                self.ledger, request(), send, capacity=(self.Truncated,)
            )

        raised = request(
            execution=ExecutionIdentity(
                provider="deepseek",
                endpoint="https://api.example.test/v1/chat",
                model_id="test-model",
                # Named "ceiling" rather than "max_output_tokens" because the
                # ledger bars any field whose name contains "token" as
                # credential-like.  That guard is deliberately blunt and worth
                # more than the nicer name.
                limits={"max_input_chars": "400000", "output_ceiling": "64000"},
            )
        )
        self.assertNotEqual(request().operation_id(), raised.operation_id())

        async def succeed() -> str:
            return "the whole report, this time"

        self.assertEqual(
            "the whole report, this time",
            await run_once(self.ledger, raised, succeed, capacity=(self.Truncated,)),
        )

    async def test_an_unknown_outcome_still_freezes(self) -> None:
        """The narrowing must not weaken the case reconciliation exists for.

        The caller sees the real exception -- a timeout is more useful to report
        than a wrapper -- while the ledger records the freeze.
        """

        async def send() -> str:
            raise TimeoutError("no answer came back")

        with self.assertRaises(TimeoutError):
            await run_once(
                self.ledger, request(), send, capacity=(self.Truncated,)
            )
        self.assertEqual(1, len(await self.ledger.pending_reconciliation("task-1")))


class RetryTest(LedgerFixture):
    async def test_a_provably_unexecuted_failure_retries_on_the_same_key(self) -> None:
        record = await self.ledger.reserve(request(max_attempts=2))
        await self.ledger.mark_sent(record.operation_id)
        failed = await self.ledger.fail(
            record.operation_id,
            category="not_executed",
            detail="provider rejected before executing",
        )

        self.assertEqual("failed", failed.status)
        self.assertTrue(failed.may_retry)

        async def send() -> str:
            return "second attempt succeeded"

        outcome = await run_once(self.ledger, request(max_attempts=2), send)
        self.assertEqual("second attempt succeeded", outcome)

    async def test_the_retry_budget_is_bounded(self) -> None:
        operation = request(max_attempts=1)
        record = await self.ledger.reserve(operation)
        await self.ledger.mark_sent(record.operation_id)
        await self.ledger.fail(record.operation_id, category="not_executed")

        with self.assertRaises(OperationBudgetExhausted):
            await run_once(self.ledger, operation, _never_called)

    async def test_an_unknown_outcome_never_becomes_retryable(self) -> None:
        record = await self.ledger.reserve(request())
        await self.ledger.mark_sent(record.operation_id)
        outcome = await self.ledger.flag_reconciliation(
            record.operation_id, "provider connection dropped after sending"
        )

        self.assertEqual("needs_reconciliation", outcome.status)
        self.assertFalse(outcome.may_retry)
        self.assertTrue(outcome.is_terminal)

    async def test_only_not_executed_failures_are_retryable(self) -> None:
        for category in ("capacity", "integrity", "terminal"):
            with self.subTest(category=category):
                operation = request(role=f"role-{category}")
                record = await self.ledger.reserve(operation)
                await self.ledger.mark_sent(record.operation_id)
                failed = await self.ledger.fail(
                    record.operation_id, category=category
                )

                self.assertEqual("failed", failed.status)
                self.assertFalse(failed.may_retry)

    async def test_cancellation_is_its_own_terminal_state(self) -> None:
        record = await self.ledger.reserve(request())
        await self.ledger.mark_sent(record.operation_id)
        cancelled = await self.ledger.fail(
            record.operation_id, category="cancelled"
        )

        self.assertEqual("cancelled", cancelled.status)
        self.assertTrue(cancelled.is_terminal)
        with self.assertRaisesRegex(OperationError, "cancelled"):
            await run_once(self.ledger, request(), _never_called)


class TransitionGuardTest(LedgerFixture):
    async def test_completing_requires_a_sent_request(self) -> None:
        record = await self.ledger.reserve(request())
        with self.assertRaisesRegex(OperationError, "cannot complete"):
            await self.ledger.complete(record.operation_id, "outcome")

    async def test_completing_twice_is_idempotent(self) -> None:
        record = await self.ledger.reserve(request())
        await self.ledger.mark_sent(record.operation_id)
        first = await self.ledger.complete(record.operation_id, "outcome")
        second = await self.ledger.complete(record.operation_id, "outcome")

        self.assertEqual(first.outcome_ref, second.outcome_ref)
        self.assertEqual(1, second.attempts)

    async def test_a_completed_operation_cannot_fail(self) -> None:
        record = await self.ledger.reserve(request())
        await self.ledger.mark_sent(record.operation_id)
        await self.ledger.complete(record.operation_id, "outcome")

        with self.assertRaisesRegex(OperationError, "already completed"):
            await self.ledger.fail(record.operation_id, category="terminal")

    async def test_unknown_operations_are_refused(self) -> None:
        missing = request(task_id="absent").operation_id()
        self.assertIsNone(await self.ledger.get(missing))
        with self.assertRaisesRegex(OperationError, "unknown"):
            await self.ledger.mark_sent(missing)

    async def test_the_outcome_body_lives_in_the_content_store(self) -> None:
        async def send() -> str:
            return "a large provider outcome body"

        await run_once(self.ledger, request(), send)
        record = await self.ledger.get(request().operation_id())
        assert record is not None and record.outcome_ref is not None

        self.assertEqual(
            "a large provider outcome body",
            await self.content_store.get(record.outcome_ref),
        )

    async def test_execution_identity_round_trips_without_credentials(self) -> None:
        await self.ledger.reserve(request())
        record = await self.ledger.get(request().operation_id())
        assert record is not None

        self.assertEqual("deepseek", record.execution.provider)
        self.assertEqual("test-model", record.execution.model_id)
        self.assertEqual({"max_input_chars": "400000"}, dict(record.execution.limits))


async def _never_called() -> str:  # pragma: no cover - guards unreachable sends
    raise AssertionError("this operation must not call the provider")


class SpendAccountingTest(LedgerFixture):
    """What the ledger records must be what was actually paid.

    Phase 1e could not answer "what did that cost" at all: the table held no
    token counts and no timestamps, so the resource axis had to be argued from
    call counts and output characters. Both are now recorded, and the property
    that makes the numbers trustworthy is that a replay adds nothing -- a
    resumed task must not be billed twice in the report any more than it is
    billed twice by the provider.
    """

    async def _spend(self) -> tuple[int, int, int]:
        rows = await self._connection.execute_fetchall(
            "select coalesce(sum(input_tokens),0), coalesce(sum(output_tokens),0), "
            "count(*) from operations where status='completed'"
        )
        return int(rows[0][0]), int(rows[0][1]), int(rows[0][2])

    async def test_completed_calls_record_the_tokens_they_used(self) -> None:
        async def send() -> str:
            return '{"content": "done", "usage": {"input_tokens": 1200}}'

        await run_once(
            self.ledger,
            request(),
            send,
            usage_of=lambda _outcome: {"input_tokens": 1200, "output_tokens": 340},
        )
        self.assertEqual((1200, 340, 1), await self._spend())

    async def test_a_replay_does_not_bill_twice(self) -> None:
        async def send() -> str:
            return "outcome"

        usage = {"input_tokens": 500, "output_tokens": 100}
        await run_once(self.ledger, request(), send, usage_of=lambda _o: usage)
        await run_once(self.ledger, request(), send, usage_of=lambda _o: usage)
        self.assertEqual((500, 100, 1), await self._spend())

    async def test_an_unmeasured_call_stays_null_rather_than_zero(self) -> None:
        async def send() -> str:
            return "outcome"

        # A provider that reports no usage must not look like a free call.
        await run_once(self.ledger, request(), send)
        rows = await self._connection.execute_fetchall(
            "select input_tokens, output_tokens from operations"
        )
        self.assertEqual((None, None), tuple(rows[0]))

    async def test_every_settled_operation_carries_a_start_and_an_end(self) -> None:
        async def send() -> str:
            return "outcome"

        await run_once(self.ledger, request(), send)
        rows = await self._connection.execute_fetchall(
            "select started_at, settled_at from operations"
        )
        started, settled = rows[0]
        self.assertTrue(started, "mark_sent must stamp the start")
        self.assertTrue(settled, "complete must stamp the end")
        self.assertLessEqual(started, settled)

    async def test_a_database_written_before_accounting_gains_the_columns(
        self,
    ) -> None:
        """An older run must stay readable and resumable, not be migrated away."""

        for column in (
            "started_at",
            "settled_at",
            "input_tokens",
            "output_tokens",
            "cached_input_tokens",
        ):
            await self._connection.execute(
                f"ALTER TABLE operations DROP COLUMN {column}"
            )
        await self._connection.commit()

        await self.ledger.setup()
        columns = {
            row[1]
            for row in await self._connection.execute_fetchall(
                "PRAGMA table_info(operations)"
            )
        }
        self.assertLessEqual(
            {
                "started_at",
                "settled_at",
                "input_tokens",
                "output_tokens",
                "cached_input_tokens",
            },
            columns,
        )

        async def send() -> str:
            return "outcome"

        self.assertEqual("outcome", await run_once(self.ledger, request(), send))


if __name__ == "__main__":
    unittest.main()
