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
