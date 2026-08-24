"""The composition root must build the transport each vendor actually speaks.

Both driver scripts previously constructed an OpenAI client directly, so the
protocol registry was exercised only by its own unit tests and never by a run.
The property worth pinning is therefore not "build_chat_model dispatches" --
that is already tested -- but "the entry points go through it".
"""

from __future__ import annotations

import unittest

from deep_research_agent.application import (
    build_runtimes,
    load_environment,
    render_role_models,
)
from deep_research_agent.config import ROLES, load_config
from deep_research_agent.model import OpenAICompatibleClient
from deep_research_agent.providers.anthropic import AnthropicClient


class TransportSelectionTest(unittest.TestCase):
    def test_an_anthropic_deployment_gets_the_native_messages_transport(self) -> None:
        runtimes = build_runtimes(
            {
                "DEEP_RESEARCH_LLM_PROVIDER": "anthropic",
                "ANTHROPIC_API_KEY": "sk-ant-test",
            }
        )

        self.assertEqual(set(ROLES), set(runtimes))
        for role, runtime in runtimes.items():
            with self.subTest(role=role):
                self.assertIsInstance(runtime.model, AnthropicClient)
                self.assertEqual("anthropic", runtime.execution.provider)

    def test_an_openai_protocol_deployment_gets_the_openai_transport(self) -> None:
        runtimes = build_runtimes(
            {
                "DEEP_RESEARCH_LLM_PROVIDER": "deepseek",
                "DEEPSEEK_API_KEY": "sk-test",
            }
        )

        for runtime in runtimes.values():
            self.assertIsInstance(runtime.model, OpenAICompatibleClient)

    def test_the_execution_identity_carries_the_model_that_will_answer(self) -> None:
        """Replay is keyed on it, so a wrong value attributes work to a model
        that never ran."""

        environ = {
            "DEEP_RESEARCH_LLM_PROVIDER": "deepseek",
            "DEEPSEEK_API_KEY": "sk-test",
            "DEEP_RESEARCH_FAST_MODEL": "deepseek-chat-lite",
        }
        config = load_config(environ)
        runtimes = build_runtimes(environ, config=config)

        investigator = runtimes["investigator"].execution
        self.assertEqual("deepseek-chat-lite", investigator.model_id)
        self.assertEqual(
            config.model_for("investigator").api_base, investigator.endpoint
        )

    def test_only_the_requested_roles_are_built(self) -> None:
        """The reporting driver must not demand credentials it never uses."""

        runtimes = build_runtimes(
            {"DEEP_RESEARCH_LLM_PROVIDER": "deepseek", "DEEPSEEK_API_KEY": "sk-test"},
            roles=("analyst", "author", "reviewer"),
        )

        self.assertEqual({"analyst", "author", "reviewer"}, set(runtimes))


class ExecutionLimitWiringTest(unittest.TestCase):
    """Limits must reach the transport, the runner, and the fingerprint.

    Three separate consumers, and missing any one of them reproduces a defect the
    audit found: the transport needs the output ceiling (a deep report used to be
    truncated), the runner needs the input ceiling (§8.3's red line had no value to
    check against), and the fingerprint needs both (raising a ceiling had to be a
    new operation, or the fix would replay the failure).
    """

    ANTHROPIC = {
        "DEEP_RESEARCH_LLM_PROVIDER": "anthropic",
        "ANTHROPIC_API_KEY": "sk-ant-test",
    }

    def test_the_runner_is_given_the_input_ceiling(self) -> None:
        runtimes = build_runtimes(self.ANTHROPIC)
        for role, runtime in runtimes.items():
            with self.subTest(role=role):
                self.assertGreater(runtime.context_limit, 0)

    def test_large_output_streams_and_small_output_does_not(self) -> None:
        """One decision, made here: a large ceiling is only safe when streaming."""

        runtimes = build_runtimes(self.ANTHROPIC)
        author = runtimes["author"].model
        investigator = runtimes["investigator"].model

        self.assertTrue(author.stream, "a deep report must stream")
        self.assertGreater(author.max_output_tokens, 33_000)
        self.assertFalse(investigator.stream, "a bounded role need not stream")

    def test_effort_reaches_the_transport_that_accepts_it(self) -> None:
        runtimes = build_runtimes(self.ANTHROPIC)
        self.assertEqual("low", runtimes["investigator"].model.effort)
        self.assertEqual("xhigh", runtimes["reviewer"].model.effort)

    def test_the_fingerprint_covers_the_limits_the_call_ran_under(self) -> None:
        from deep_research_agent.operations import OperationRequest

        def author_operation(environ: dict[str, str]) -> str:
            runtime = build_runtimes(environ)["author"]
            return OperationRequest(
                task_id="t", kind="model_call", role="author",
                execution=runtime.execution,
            ).operation_id()

        base = author_operation(dict(self.ANTHROPIC))
        raised = author_operation(
            {**self.ANTHROPIC, "DEEP_RESEARCH_AUTHOR_OUTPUT_CEILING": "90000"}
        )
        deeper = author_operation(
            {**self.ANTHROPIC, "DEEP_RESEARCH_AUTHOR_EFFORT": "max"}
        )

        # This is the escape route from a capacity failure: without it, the fix
        # for a truncated report would replay the truncation.
        self.assertNotEqual(base, raised)
        self.assertNotEqual(base, deeper)

    def test_no_limit_field_looks_like_a_credential(self) -> None:
        """The ledger bars credential-shaped field names; the limits must pass."""

        for runtime in build_runtimes(self.ANTHROPIC).values():
            self.assertIn("context_ceiling", runtime.execution.limits)
            self.assertIn("output_ceiling", runtime.execution.limits)
            self.assertIn("effort", runtime.execution.limits)


class EnvironmentTest(unittest.TestCase):
    def test_a_missing_env_file_is_not_an_error(self) -> None:
        from pathlib import Path

        values = load_environment(Path("no-such-file.env"))
        self.assertIsInstance(values, dict)

    def test_every_role_appears_in_the_rendered_account(self) -> None:
        rendered = render_role_models(
            load_config({"DEEP_RESEARCH_LLM_PROVIDER": "deepseek"})
        )
        for role in ROLES:
            self.assertIn(role, rendered)


if __name__ == "__main__":
    unittest.main()
