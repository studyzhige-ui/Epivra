from __future__ import annotations

import unittest

from deep_research_agent.__main__ import _exit_code, _parser
from deep_research_agent.api import (
    DEFAULT_WORKFLOW_RECURSION_LIMIT,
    RunResult,
)


class CliContractTest(unittest.TestCase):
    def test_nonterminal_operational_pauses_return_nonzero(self) -> None:
        for status in ("retryable_failure", "recoverable_pause", "paused"):
            with self.subTest(status=status):
                self.assertEqual(2, _exit_code(RunResult("task", status)))

    def test_user_waits_and_terminal_results_return_zero(self) -> None:
        for status in (
            "awaiting_approval",
            "awaiting_user",
            "completed",
            "cancelled",
        ):
            with self.subTest(status=status):
                self.assertEqual(0, _exit_code(RunResult("task", status)))

    def test_continue_command_and_recursion_guard_are_explicit(self) -> None:
        args = _parser().parse_args(["continue", "thread-1"])

        self.assertEqual("continue", args.command)
        self.assertEqual("thread-1", args.thread_id)
        self.assertEqual(DEFAULT_WORKFLOW_RECURSION_LIMIT, args.recursion_limit)


if __name__ == "__main__":
    unittest.main()
