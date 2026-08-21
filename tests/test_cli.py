"""The CLI's two entry points, and the state logic behind the home screen.

What matters here is not how a prompt looks but what the interface *decides*:
which surface a given invocation reaches, and which action a given task state is
allowed to offer.  Both are the kind of thing that silently regresses.

No test in this file touches a terminal or a provider.
"""

from __future__ import annotations

import argparse
import contextlib
import inspect
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput

import deep_research_agent.cli.commands as commands
import deep_research_agent.cli.main as cli_main
from deep_research_agent.cli import i18n, theme
from deep_research_agent.cli import prompts as prompts_module
from deep_research_agent.cli import settings as cli_settings
from deep_research_agent.cli.settings import (
    CliSettings,
    ModelChoice,
    ResearchDefaults,
    runtime_environment,
)
from deep_research_agent.cli.workspace import Workspace
from deep_research_agent.providers import validation
from deep_research_agent.service import Task


class TranslationTest(unittest.TestCase):
    """A half-translated interface is worse than a loud failure."""

    def test_every_message_exists_in_every_language(self) -> None:
        catalogue = i18n.catalogue()
        for code, _label in i18n.CLI_LANGUAGES:
            for message_id, entry in catalogue.items():
                with self.subTest(language=code, message=message_id):
                    self.assertIn(code, entry, f"{message_id} missing {code}")
                    self.assertTrue(entry[code].strip())

    def test_an_unknown_message_id_raises(self) -> None:
        with self.assertRaises(KeyError):
            i18n.Translator("en")("no.such.message")

    def test_cli_language_is_independent_of_report_language(self) -> None:
        """A Chinese interface must be able to order an English report."""

        settings = CliSettings(
            cli_language="zh-CN",
            defaults=ResearchDefaults(report_language="en"),
        )
        self.assertEqual("zh-CN", settings.language)
        self.assertEqual("en", settings.defaults.report_language)

    def test_an_unknown_language_falls_back_rather_than_crashing(self) -> None:
        self.assertEqual("zh-CN", i18n.Translator("kl-KL").language)


class DispatchTest(unittest.TestCase):
    """Which surface an invocation reaches.

    ``deep-research`` is the product; ``deep-research <command>`` is the shell
    interface.  Conflating them was the change this refactor exists to make, so
    it is pinned in both directions.
    """

    def _args(self, argv: list[str]) -> argparse.Namespace:
        return cli_main.build_parser().parse_args(argv)

    def test_a_bare_invocation_on_a_terminal_enters_the_workspace(self) -> None:
        with (
            mock.patch.object(theme, "is_interactive", return_value=True),
            mock.patch(
                "deep_research_agent.cli.workspace.run_workspace", return_value=0
            ) as workspace,
        ):
            self.assertEqual(0, cli_main.main([]))
        workspace.assert_called_once()

    def test_a_bare_invocation_without_a_terminal_prints_help(self) -> None:
        """A pipe must never reach a prompt nobody can answer."""

        with (
            mock.patch.object(theme, "is_interactive", return_value=False),
            mock.patch(
                "deep_research_agent.cli.workspace.run_workspace"
            ) as workspace,
        ):
            self.assertEqual(0, cli_main.main([]))
        workspace.assert_not_called()

    def test_doctor_runs_doctor_and_not_the_workspace(self) -> None:
        self.assertIs(self._args(["doctor"]).run, cli_main.commands.cmd_doctor)

    def test_list_runs_list_and_not_the_workspace(self) -> None:
        self.assertIs(self._args(["list"]).run, cli_main.commands.cmd_list)

    def test_every_documented_command_still_dispatches(self) -> None:
        """Backwards compatibility: the shell interface must not regress."""

        expected = {
            "new": "cmd_new",
            "list": "cmd_list",
            "show": "cmd_show",
            "approve": "cmd_approve",
            "continue": "cmd_continue",
            "report": "cmd_report",
            "init": "cmd_init",
            "doctor": "cmd_doctor",
            "delete": "cmd_delete",
        }
        for command, handler in expected.items():
            with self.subTest(command=command):
                argv = [command]
                if command in ("show", "approve", "continue", "report", "delete"):
                    argv.append("t_test")
                args = self._args(argv)
                self.assertEqual(handler, args.run.__name__)

    def test_help_lists_the_commands_and_explains_the_bare_form(self) -> None:
        self.assertIn("Without a command", cli_main.USAGE)
        for command in ("new", "list", "show", "approve", "continue", "report"):
            self.assertIn(command, cli_main.USAGE)


class SettingsTest(unittest.TestCase):
    def test_settings_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            original = CliSettings(
                cli_language="en",
                defaults=ResearchDefaults(
                    report_language="ja",
                    source_access=("public_web", "user_files"),
                    corpus_root="/tmp/corpus",
                    investigator=ModelChoice("deepseek", "deepseek-v4-flash"),
                    other_roles=ModelChoice("anthropic", "claude-opus-5"),
                    search_providers=("tavily", "duckduckgo"),
                ),
            )
            cli_settings.save(path, original)
            self.assertEqual(original, cli_settings.load(path))

    def test_a_missing_file_yields_defaults_with_no_language_chosen(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            settings = cli_settings.load(Path(directory) / "absent.json")
            self.assertFalse(settings.language_chosen)
            self.assertEqual("zh-CN", settings.language)

    def test_an_unreadable_file_does_not_stop_the_user(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text("{ not json", encoding="utf-8")
            self.assertEqual(CliSettings(), cli_settings.load(path))

    def test_first_run_is_distinguishable_from_a_chosen_default(self) -> None:
        """Empty means "never asked"; the first run has to offer the choice."""

        self.assertFalse(CliSettings().language_chosen)
        self.assertTrue(CliSettings(cli_language="zh-CN").language_chosen)

    def test_model_assignment_projects_onto_the_existing_tiers(self) -> None:
        """The two user-facing choices are the runtime's two tiers already."""

        defaults = ResearchDefaults(
            investigator=ModelChoice("qwen", "qwen3-turbo"),
            other_roles=ModelChoice("deepseek", "deepseek-v4-pro"),
        )
        overlay = runtime_environment(defaults, {})
        self.assertEqual("qwen", overlay["DEEP_RESEARCH_INVESTIGATOR_PROVIDER"])
        self.assertEqual("qwen3-turbo", overlay["DEEP_RESEARCH_INVESTIGATOR_MODEL"])
        self.assertEqual("deepseek", overlay["DEEP_RESEARCH_LLM_PROVIDER"])
        self.assertEqual("deepseek-v4-pro", overlay["DEEP_RESEARCH_REASONING_MODEL"])

    def test_an_unset_assignment_leaves_configuration_alone(self) -> None:
        overlay = runtime_environment(ResearchDefaults(), {"KEEP": "me"})
        self.assertEqual("me", overlay["KEEP"])
        self.assertNotIn("DEEP_RESEARCH_LLM_PROVIDER", overlay)

    def test_academic_indexes_are_switched_both_ways(self) -> None:
        overlay = runtime_environment(
            ResearchDefaults(academic_providers=("arxiv",)), {}
        )
        self.assertEqual("true", overlay["DEEP_RESEARCH_ARXIV_SEARCH"])
        self.assertEqual("false", overlay["DEEP_RESEARCH_PUBMED_SEARCH"])


def _task(state: str, **kwargs: object) -> Task:
    return Task(
        task_id=str(kwargs.get("task_id", "t_abc123")),
        request=str(kwargs.get("request", "调研 AI Agent 行业")),
        language="zh",
        source_access=("public_web",),
        state=state,  # type: ignore[arg-type]
        materials=int(kwargs.get("materials", 0)),
        sources=int(kwargs.get("sources", 0)),
    )


class ActionMappingTest(unittest.TestCase):
    """UI state -> allowed actions.  A state must not offer an impossible move."""

    def setUp(self) -> None:
        self.workspace = Workspace(
            args=argparse.Namespace(database="", verbose=False),
            console=theme.console(file=io.StringIO()),
            settings=CliSettings(cli_language="zh-CN"),
            translate=i18n.Translator("zh-CN"),
            environ={},
        )

    def _keys(self, state: str) -> set[str]:
        return {key for key, _label in self.workspace._actions_for(_task(state))}

    def test_awaiting_approval_can_approve_but_not_resume(self) -> None:
        keys = self._keys("awaiting_approval")
        self.assertIn("approve", keys)
        self.assertIn("plan", keys)
        self.assertIn("revise", keys)
        self.assertNotIn("resume", keys)
        self.assertNotIn("report", keys)

    def test_a_completed_study_cannot_be_approved(self) -> None:
        keys = self._keys("published")
        self.assertIn("report", keys)
        self.assertIn("export", keys)
        self.assertNotIn("approve", keys)
        self.assertNotIn("resume", keys)

    def test_a_paused_study_offers_resume(self) -> None:
        keys = self._keys("paused")
        self.assertIn("resume", keys)
        self.assertNotIn("approve", keys)

    def test_every_state_allows_deletion(self) -> None:
        """A user must be able to abandon a study from any state."""

        for state in (
            "awaiting_approval",
            "researching",
            "paused",
            "halted",
            "published",
            "clarification_requested",
        ):
            with self.subTest(state=state):
                self.assertIn("delete", self._keys(state))

    def test_a_running_study_separates_leaving_from_deleting(self) -> None:
        """Pause keeps everything; delete destroys it. Never the same choice."""

        actions = dict(self.workspace._actions_for(_task("researching")))
        self.assertIn("delete", actions)
        self.assertIn("back", actions)
        self.assertNotEqual(actions["delete"], actions["back"])

    def test_awaiting_approval_does_not_offer_a_bare_cancel(self) -> None:
        """"取消" is ambiguous between "go back" and "destroy"; both are spelled out."""

        labels = dict(self.workspace._actions_for(_task("awaiting_approval"))).values()
        self.assertNotIn("取消", labels)
        joined = " ".join(labels)
        self.assertIn("保存以后处理", joined)
        self.assertIn("取消并删除研究", joined)


class ThemeTest(unittest.TestCase):
    def test_narrow_terminals_are_clamped_not_broken(self) -> None:
        console = theme.console(file=io.StringIO())
        self.assertGreaterEqual(theme.width(console), theme.MIN_WIDTH)
        self.assertLessEqual(theme.width(console), 120)

    def test_every_task_state_has_a_glyph_and_a_label(self) -> None:
        translate = i18n.Translator("en")
        for state in theme.STATE_GLYPH:
            with self.subTest(state=state):
                self.assertTrue(theme.STATE_GLYPH[state])
                self.assertTrue(translate(f"state.{state}"))

    def test_truncation_marks_that_something_was_cut(self) -> None:
        self.assertEqual("abc…", theme.truncate("abcdefgh", 4))
        self.assertEqual("short", theme.truncate("short", 20))


class HomeSurfaceTest(unittest.IsolatedAsyncioTestCase):
    """The home screen must surface the user's most likely next action.

    Everyone seeing the same menu is the failure this replaces: a user with a
    plan waiting should be offered that plan, not asked to find it.
    """

    def _workspace(self, tasks, *, configured=True) -> Workspace:  # noqa: ANN001
        defaults = ResearchDefaults(
            investigator=ModelChoice("deepseek", "deepseek-v4-flash"),
            other_roles=ModelChoice("deepseek", "deepseek-v4-pro"),
        ) if configured else ResearchDefaults()

        class FakeService:
            async def tasks(self):  # noqa: ANN202
                return tuple(tasks)

        workspace = Workspace(
            args=argparse.Namespace(database="", verbose=False),
            console=theme.console(file=io.StringIO()),
            settings=CliSettings(cli_language="zh-CN", defaults=defaults),
            translate=i18n.Translator("zh-CN"),
            environ={"DEEPSEEK_API_KEY": "k"} if configured else {},
        )
        workspace.service = FakeService()  # type: ignore[assignment]
        return workspace

    async def _offered(self, tasks, *, configured=True) -> set[str]:  # noqa: ANN001
        workspace = self._workspace(tasks, configured=configured)
        captured: list[list[tuple[str, str]]] = []

        async def fake_choose(_message, options, **_kwargs):  # noqa: ANN001, ANN202
            captured.append(list(options))
            return "exit"

        with mock.patch.object(prompts_module, "choose", fake_choose):
            await workspace.home()
        return {key for options in captured for key, _label in options}

    async def test_an_unconfigured_install_offers_setup_and_nothing_else(self) -> None:
        offered = await self._offered([], configured=False)
        self.assertIn("setup", offered)
        self.assertNotIn("new", offered)

    async def test_a_waiting_plan_is_surfaced_for_approval(self) -> None:
        offered = await self._offered([_task("awaiting_approval")])
        self.assertIn("approve", offered)

    async def test_a_paused_study_is_surfaced_for_resuming(self) -> None:
        offered = await self._offered([_task("paused", materials=78)])
        self.assertIn("resume", offered)

    async def test_a_completed_study_is_surfaced_for_reading(self) -> None:
        offered = await self._offered([_task("published", sources=62)])
        self.assertIn("report", offered)

    async def test_approval_outranks_a_paused_study(self) -> None:
        """With several pending things, the decision waiting on a human wins."""

        offered = await self._offered(
            [_task("paused", task_id="t_1"), _task("awaiting_approval", task_id="t_2")]
        )
        self.assertIn("approve", offered)
        self.assertNotIn("resume", offered)

    async def test_with_no_tasks_the_user_is_asked_for_a_question_directly(self) -> None:
        """No "type new first": a question typed at the prompt starts a study."""

        workspace = self._workspace([])
        with (
            mock.patch.object(
                prompts_module,
                "ask_text",
                mock.AsyncMock(return_value="调研 AI Agent 行业"),
            ),
            mock.patch.object(
                prompts_module, "choose", mock.AsyncMock(return_value="exit")
            ),
        ):
            action = await workspace.home()
        self.assertEqual("new", action)
        self.assertEqual("调研 AI Agent 行业", workspace._pending_request)


class PromptContractTest(unittest.IsolatedAsyncioTestCase):
    """Every prompt must be awaitable.

    questionary's synchronous ``ask()`` calls ``asyncio.run()`` internally, so
    reaching it from the workspace -- which always runs inside a loop -- raises
    "cannot be called from a running event loop" on the very first screen.  That
    is exactly what happened on the first real terminal run, and a unit test can
    only catch it by pinning the shape.
    """

    async def test_a_real_prompt_survives_a_running_event_loop(self) -> None:
        """The crash itself, driven end to end with a piped keyboard.

        ``create_app_session`` substitutes the ambient terminal, so this exercises
        the production prompt -- real questionary, real prompt_toolkit -- from
        inside a running loop, which is the one condition that broke it.
        """

        with create_pipe_input() as pipe:
            pipe.send_text("\r")
            with create_app_session(input=pipe, output=DummyOutput()):
                chosen = await prompts_module.choose(
                    "pick", [("first", "First"), ("second", "Second")]
                )
        self.assertEqual("first", chosen)

    def test_every_prompt_is_a_coroutine_function(self) -> None:
        for name in (
            "ask_text",
            "ask_secret",
            "choose",
            "choose_many",
            "confirm_destructive",
        ):
            with self.subTest(prompt=name):
                self.assertTrue(
                    inspect.iscoroutinefunction(getattr(prompts_module, name))
                )

    def test_no_caller_invokes_a_prompt_without_awaiting_it(self) -> None:
        """A missed ``await`` is silent: the coroutine is truthy and never runs."""

        root = Path(cli_main.__file__).parent
        offenders: list[str] = []
        for path in sorted(root.glob("*.py")):
            for number, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), start=1
            ):
                for name in ("ask_text", "ask_secret", "choose", "confirm_destructive"):
                    call = f"prompts.{name}("
                    if call in line and f"await prompts.{name}(" not in line:
                        offenders.append(f"{path.name}:{number}")
        self.assertEqual([], offenders)


class DoctorLiveTest(unittest.IsolatedAsyncioTestCase):
    """``doctor --live`` must actually reach the vendors, and cost nothing extra.

    Without ``--live`` no provider is contacted: a diagnostic that spends a search
    credit every time someone checks their setup is a diagnostic people stop
    running.
    """

    def _args(self, *, live: bool) -> argparse.Namespace:
        return argparse.Namespace(database="unused.sqlite3", live=live)

    def _patched(self, *, ok: bool):  # noqa: ANN202
        result = validation.ValidationResult(
            provider="deepseek",
            ok=ok,
            reason="" if ok else "密钥无效",
            models=("m1", "m2"),
        )
        return (
            mock.patch.object(
                commands, "validate_llm_credentials", mock.AsyncMock(return_value=result)
            ),
            mock.patch.object(
                commands,
                "validate_search_credentials",
                mock.AsyncMock(return_value=result),
            ),
            mock.patch.object(
                commands,
                "load_environment",
                return_value={"DEEPSEEK_API_KEY": "k", "TAVILY_API_KEY": "t"},
            ),
        )

    async def test_without_live_no_vendor_is_contacted(self) -> None:
        llm, search, environ = self._patched(ok=True)
        buffer = io.StringIO()
        with llm as llm_mock, search as search_mock, environ:
            with contextlib.redirect_stdout(buffer):
                self.assertEqual(0, await commands.cmd_doctor(self._args(live=False)))
        llm_mock.assert_not_called()
        search_mock.assert_not_called()
        self.assertIn("--live", buffer.getvalue())

    async def test_live_validates_every_configured_vendor(self) -> None:
        llm, search, environ = self._patched(ok=True)
        buffer = io.StringIO()
        with llm as llm_mock, search as search_mock, environ:
            with contextlib.redirect_stdout(buffer):
                self.assertEqual(0, await commands.cmd_doctor(self._args(live=True)))
        llm_mock.assert_awaited_once()
        search_mock.assert_awaited_once()
        printed = buffer.getvalue()
        self.assertIn("deepseek", printed)
        self.assertIn("tavily", printed)

    async def test_a_failing_credential_makes_doctor_exit_nonzero(self) -> None:
        """Exit status is what a CI job reads; a broken key must fail the check."""

        llm, search, environ = self._patched(ok=False)
        buffer = io.StringIO()
        with llm, search, environ, contextlib.redirect_stdout(buffer):
            self.assertEqual(1, await commands.cmd_doctor(self._args(live=True)))
        self.assertIn("密钥无效", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
