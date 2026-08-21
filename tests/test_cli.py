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
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import questionary
from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput

import deep_research_agent.cli.commands as commands
import deep_research_agent.cli.main as cli_main
from deep_research_agent.cli import i18n, journal, paths, setup_flow, theme
from deep_research_agent.cli import prompts as prompts_module
from deep_research_agent.cli import settings as cli_settings
from deep_research_agent.cli import workspace as workspace_module
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
            console=theme.console(file=self.output),
            settings=CliSettings(cli_language="zh-CN", defaults=defaults),
            translate=i18n.Translator("zh-CN"),
            environ={"DEEPSEEK_API_KEY": "k"} if configured else {},
        )
        workspace.service = FakeService()  # type: ignore[assignment]
        return workspace

    def setUp(self) -> None:
        self.output = io.StringIO()
        self.blocked: dict[str, str] = {}

    async def _offered(self, tasks, *, configured=True) -> set[str]:  # noqa: ANN001
        workspace = self._workspace(tasks, configured=configured)
        captured: list[list[tuple[str, str]]] = []

        async def fake_choose(_message, options, **kwargs):  # noqa: ANN001, ANN202
            captured.append(list(options))
            self.blocked.update(kwargs.get("disabled") or {})
            return "exit"

        with (
            mock.patch.object(prompts_module, "choose", fake_choose),
            # An empty answer at the research prompt falls through to the menu,
            # which is what this helper is here to inspect.
            mock.patch.object(prompts_module, "ask_text", mock.AsyncMock(return_value="")),
        ):
            await workspace.home()
        return {key for options in captured for key, _label in options}

    async def test_an_unconfigured_install_shows_the_same_page_with_research_blocked(
        self,
    ) -> None:
        """One page in every state; what is missing greys out what it blocks.

        A separate, smaller screen for an unconfigured install meant a new user's
        first sight of the product was a two-item menu.  The action stays visible
        with the reason attached, so they learn it exists and what unlocks it.
        """

        offered = await self._offered([], configured=False)
        self.assertIn("new", offered)
        self.assertIn("setup", offered)
        self.assertIn("new", self.blocked)
        self.assertTrue(self.blocked["new"])
        # And no research question is asked when none could be answered.
        self.assertNotIn("今天想研究点什么", self.output.getvalue())

    async def test_a_configured_install_shows_what_it_will_use(self) -> None:
        """The two model choices and the search sources, before anything is asked."""

        await self._offered([])
        printed = self.output.getvalue()
        self.assertIn("deepseek/deepseek-v4-flash", printed)
        self.assertIn("deepseek/deepseek-v4-pro", printed)
        self.assertIn("duckduckgo", printed)
        self.assertEqual({}, self.blocked)

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
        self.assertIn("今天想研究点什么", self.output.getvalue())
        self.assertIn("给我一个主题", self.output.getvalue())


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


class SetupFlowTest(unittest.IsolatedAsyncioTestCase):
    """Configuring a vendor: what is offered, in what order, and what is saved."""

    def _workspace(self, environ: dict[str, str]) -> Workspace:
        return Workspace(
            args=argparse.Namespace(database="", verbose=False),
            console=theme.console(file=io.StringIO()),
            settings=CliSettings(cli_language="zh-CN"),
            translate=i18n.Translator("zh-CN"),
            environ=environ,
        )

    def test_a_vendor_with_a_saved_key_is_listed_first(self) -> None:
        """A returning user is looking for the one they already configured.

        Alphabetical order buried DeepSeek below Anthropic on an install where
        only DeepSeek had a key, which makes the list actively unhelpful.
        """

        workspace = self._workspace({"DEEPSEEK_API_KEY": "k"})
        options = setup_flow._model_provider_options(workspace)
        self.assertEqual("deepseek", options[0][0])
        self.assertIn("已保存密钥", options[0][1])
        self.assertNotIn("已保存密钥", options[1][1])

    def test_the_mark_claims_a_saved_key_not_a_working_one(self) -> None:
        """A saved key is not a proven key; only asking the vendor settles that."""

        workspace = self._workspace({"DEEPSEEK_API_KEY": "not-a-real-key"})
        label = dict(setup_flow._model_provider_options(workspace))["deepseek"]
        self.assertIn("已保存密钥", label)
        self.assertNotIn("验证", label)

    async def test_an_empty_key_is_refused_rather_than_silently_backing_out(
        self,
    ) -> None:
        """Enter on an empty prompt used to drop a screen with no explanation."""

        workspace = self._workspace({})
        # ask_secret's contract is "stripped, or None", so an all-blank paste
        # arrives here as the empty string.
        answers = iter(["", "", "sk-real"])
        with (
            mock.patch.object(
                prompts_module,
                "ask_secret",
                mock.AsyncMock(side_effect=lambda *_a, **_k: next(answers)),
            ),
            mock.patch.object(
                prompts_module, "choose", mock.AsyncMock(return_value="retry")
            ),
        ):
            key = await setup_flow._ask_key(workspace, "DeepSeek")
        self.assertEqual("sk-real", key)
        self.assertIn("密钥不能为空", workspace.console.file.getvalue())

    async def test_choosing_back_after_an_empty_key_gives_up(self) -> None:
        workspace = self._workspace({})
        with (
            mock.patch.object(
                prompts_module, "ask_secret", mock.AsyncMock(return_value="")
            ),
            mock.patch.object(
                prompts_module, "choose", mock.AsyncMock(return_value="back")
            ),
        ):
            self.assertIsNone(await setup_flow._ask_key(workspace, "DeepSeek"))


class ModelCatalogueTest(unittest.TestCase):
    """The model list must come from the vendor, or be admitted as missing."""

    def _spec(self):  # noqa: ANN202
        return validation.LlmProviderSpec(
            name="deepseek",
            label="DeepSeek",
            api_base="https://api.deepseek.com",
            key_env_var="DEEPSEEK_API_KEY",
            reasoning_model="deepseek-v4-pro",
            fast_model="deepseek-v4-flash",
        )

    def test_an_unreachable_vendor_yields_no_models_rather_than_an_invented_one(
        self,
    ) -> None:
        """The defect this fixes made a 401 look like a one-model catalogue.

        A dead key failed the listing call, the catalogue came back empty, and the
        interface substituted the registry's suggestion -- so the user was shown
        exactly one model and told it was what their subscription offered.
        """

        self.assertEqual(
            (), validation.suggest_models(self._spec(), (), fast=True)
        )

    def test_the_registry_suggestion_leads_only_when_the_vendor_lists_it(self) -> None:
        catalogue = ("deepseek-v4-pro", "deepseek-v4-flash")
        self.assertEqual(
            "deepseek-v4-flash",
            validation.suggest_models(self._spec(), catalogue, fast=True)[0],
        )
        self.assertEqual(
            "deepseek-v4-pro",
            validation.suggest_models(self._spec(), catalogue, fast=False)[0],
        )

    def test_nothing_offered_by_the_vendor_is_dropped_from_the_list(self) -> None:
        """Ordering is a recommendation; it must never narrow the choice."""

        catalogue = ("some-other-model", "deepseek-v4-pro")
        self.assertEqual(
            set(catalogue),
            set(validation.suggest_models(self._spec(), catalogue, fast=False)),
        )

    def test_non_text_models_are_filtered_out_of_a_listing(self) -> None:
        """A /models listing mixes in embeddings, speech and image models."""

        payload = {
            "data": [
                {"id": "deepseek-v4-pro"},
                {"id": "text-embedding-3-large"},
                {"id": "whisper-1"},
                {"id": "dall-e-3"},
                {"id": "tts-1-hd"},
                {"id": "omni-moderation-latest"},
                {"id": "models/gemini-3-pro"},
            ]
        }
        self.assertEqual(
            ("deepseek-v4-pro", "gemini-3-pro"),
            validation._extract_models(payload),
        )

    def test_a_reasoner_is_not_mistaken_for_a_realtime_model(self) -> None:
        """Prefix matching runs on word tokens, not raw substrings."""

        self.assertTrue(validation.is_text_model("deepseek-reasoner"))
        self.assertTrue(validation.is_text_model("glm-5-air"))
        self.assertFalse(validation.is_text_model("gpt-4o-realtime-preview"))



    """The product's front door, driven end to end with a piped keyboard.

    Every other test here mocks the prompts away, which is why the first real
    terminal run still crashed on screen one.  This drives the actual workspace
    -- real questionary, real settings file, real database -- through the first
    two screens a new user sees, in a throwaway home directory.
    """

    def test_a_new_user_can_choose_a_language_and_reach_the_home_screen(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            buffer = io.StringIO()
            with (
                mock.patch.object(paths, "HOME", home),
                contextlib.redirect_stdout(buffer),
            ):
                args = argparse.Namespace(
                    database=str(home / "tasks.sqlite3"), verbose=False
                )
                with create_pipe_input() as pipe:
                    pipe.send_text("\r")  # language: the first entry
                    pipe.send_text("\x1b[B\r")  # home: down to exit, then Enter
                    with create_app_session(input=pipe, output=DummyOutput()):
                        code = workspace_module.run_workspace(args)

            self.assertEqual(0, code)
            settings = cli_settings.load(home / "settings.json")
            self.assertEqual("zh-CN", settings.cli_language)
            self.assertTrue(settings.language_chosen)
            # An install with no model credential says so, and offers the fix.
            self.assertIn("还没有配置模型", buffer.getvalue())


class TransientSelectionTest(unittest.IsolatedAsyncioTestCase):
    """Selection is transient.  Outcome is persistent.  State is always visible.

    The first real session left a wall of ``? 模型厂商 DeepSeek`` lines behind it
    and buried the one line that mattered.  These pin the three halves of the fix:
    prompts erase themselves, pages replace rather than append, and an outcome
    travels to the page the user lands on.
    """

    async def test_every_prompt_erases_itself_once_answered(self) -> None:
        captured: dict[str, object] = {}
        real = questionary.select

        def spy(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
            captured.update(kwargs)
            return real(*args, **kwargs)

        with (
            create_pipe_input() as pipe,
            mock.patch.object(questionary, "select", spy),
        ):
            pipe.send_text("\r")
            with create_app_session(input=pipe, output=DummyOutput()):
                await prompts_module.choose("pick", [("a", "A")])
        self.assertIs(True, captured.get("erase_when_done"))

    async def test_a_text_prompt_erases_itself_too(self) -> None:
        captured: dict[str, object] = {}
        real = questionary.text

        def spy(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
            captured.update(kwargs)
            return real(*args, **kwargs)

        with (
            create_pipe_input() as pipe,
            mock.patch.object(questionary, "text", spy),
        ):
            pipe.send_text("hi\r")
            with create_app_session(input=pipe, output=DummyOutput()):
                await prompts_module.ask_text("name")
        self.assertIs(True, captured.get("erase_when_done"))

    def test_a_page_replaces_the_screen_only_on_a_terminal(self) -> None:
        """Clearing must never reach a redirect: a pipe wants plain text in order."""

        buffer = io.StringIO()
        quiet = theme.console(file=buffer)
        self.assertFalse(quiet.is_terminal)
        theme.page(quiet, brand="Deep Research", title="Settings")
        self.assertNotIn("\x1b[2J", buffer.getvalue())
        self.assertIn("Deep Research", buffer.getvalue())

    def test_the_header_carries_no_tagline(self) -> None:
        """Rule: the header is the product name.  The welcome lives in the body."""

        self.assertNotIn("tagline", inspect.signature(theme.header).parameters)
        self.assertNotIn("brand.tagline", i18n.catalogue())

    def test_a_receipt_is_shown_once_and_then_forgotten(self) -> None:
        buffer = io.StringIO()
        workspace = Workspace(
            args=argparse.Namespace(database="", verbose=False),
            console=theme.console(file=buffer),
            settings=CliSettings(cli_language="zh-CN"),
            translate=i18n.Translator("zh-CN"),
            environ={},
        )
        workspace.flash(theme.GLYPH["done"], "研究已删除。")
        workspace.show_receipt()
        self.assertIn("研究已删除。", buffer.getvalue())

        buffer.truncate(0)
        buffer.seek(0)
        workspace.show_receipt()
        self.assertEqual("", buffer.getvalue())

    def test_the_journal_refuses_a_field_that_could_carry_a_key(self) -> None:
        """Re-rendering must never put a credential anywhere it can be read."""

        with self.assertRaises(ValueError):
            journal.record("credential_added", api_key="sk-secret")
        with self.assertRaises(ValueError):
            journal.record("credential_added", token="sk-secret")

    def test_the_journal_records_an_outcome_the_screen_no_longer_holds(self) -> None:
        with tempfile.TemporaryDirectory() as home:
            target = Path(home) / "journal.jsonl"
            with mock.patch.object(journal, "journal_file", lambda: target):
                journal.record("research_deleted", task_id="t_1", state="paused")
            entry = json.loads(target.read_text(encoding="utf-8").strip())
        self.assertEqual("research_deleted", entry["kind"])
        self.assertEqual("t_1", entry["task_id"])
        self.assertIn("at", entry)


class NavigationTest(unittest.IsolatedAsyncioTestCase):
    """Esc goes up exactly one level, and a sub-page returns to its parent."""

    def _workspace(self, tasks=()) -> Workspace:  # noqa: ANN001
        defaults = ResearchDefaults(
            investigator=ModelChoice("deepseek", "deepseek-v4-flash"),
            other_roles=ModelChoice("deepseek", "deepseek-v4-pro"),
        )

        class FakeService:
            async def tasks(self):  # noqa: ANN202
                return tuple(tasks)

        workspace = Workspace(
            args=argparse.Namespace(database="", verbose=False),
            console=theme.console(file=io.StringIO()),
            settings=CliSettings(cli_language="zh-CN", defaults=defaults),
            translate=i18n.Translator("zh-CN"),
            environ={"DEEPSEEK_API_KEY": "k"},
        )
        workspace.service = FakeService()  # type: ignore[assignment]
        return workspace

    async def test_escape_at_the_typed_question_falls_to_the_menu_not_out(self) -> None:
        """It used to exit the product, which is two levels, not one."""

        workspace = self._workspace()
        offered: list[list[tuple[str, str]]] = []

        async def fake_choose(_message, options, **_kwargs):  # noqa: ANN001, ANN202
            offered.append(list(options))
            return "exit"

        with (
            mock.patch.object(
                prompts_module, "ask_text", mock.AsyncMock(return_value=None)
            ),
            mock.patch.object(prompts_module, "choose", fake_choose),
        ):
            action = await workspace.home()

        self.assertEqual("exit", action)
        self.assertEqual(1, len(offered), "the home menu must still be offered")
        self.assertIn("new", {key for key, _label in offered[0]})

    async def test_escape_in_settings_returns_to_the_workspace_and_stays(self) -> None:
        """Backing out of Settings must not end the session."""

        workspace = self._workspace()
        with mock.patch.object(
            prompts_module, "choose", mock.AsyncMock(return_value=None)
        ):
            self.assertIsNone(await workspace._settings_page())

    async def test_escape_in_research_defaults_returns_to_settings(self) -> None:
        workspace = self._workspace()
        with mock.patch.object(
            prompts_module, "choose", mock.AsyncMock(return_value=None)
        ):
            self.assertIsNone(await workspace._defaults_page())

    async def test_research_defaults_never_offers_use_these_settings(self) -> None:
        """That option only makes sense on the way into a new study."""

        workspace = self._workspace()
        offered: list[list[tuple[str, str]]] = []

        async def fake_choose(_message, options, **_kwargs):  # noqa: ANN001, ANN202
            offered.append(list(options))
            return None

        with mock.patch.object(prompts_module, "choose", fake_choose):
            await workspace._defaults_page()

        keys = {key for options in offered for key, _label in options}
        self.assertNotIn("use", keys)
        self.assertEqual({"language", "sources", "models", "search"}, keys)

    async def test_changing_a_model_returns_to_the_models_page_not_the_home(
        self,
    ) -> None:
        """Rule 3: a sub-configuration lands back on its parent page.

        Changing the Investigator model and then a search key must be two choices,
        not two round trips through the top-level menu.
        """

        workspace = self._workspace()
        titles: list[str] = []
        real_page = theme.page

        def spy_page(target, *, brand="", title=""):  # noqa: ANN001, ANN202
            titles.append(title or brand)
            real_page(target, brand=brand, title=title)

        answers = iter(["investigator", "search", None])

        async def fake_choose(_message, _options, **_kwargs):  # noqa: ANN001, ANN202
            return next(answers, None)

        with (
            mock.patch.object(theme, "page", spy_page),
            mock.patch.object(prompts_module, "choose", fake_choose),
            mock.patch.object(
                setup_flow,
                "_assign_one",
                mock.AsyncMock(return_value=ModelChoice("deepseek", "deepseek-r1")),
            ),
            mock.patch.object(
                setup_flow, "_add_search_credential", mock.AsyncMock(return_value=False)
            ),
            mock.patch.object(journal, "record", lambda *_a, **_k: None),
        ):
            changed = await setup_flow.configure_providers(workspace)

        self.assertTrue(changed)
        page_title = i18n.Translator("zh-CN")("settings.providers")
        self.assertGreaterEqual(
            titles.count(page_title),
            3,
            "the models-and-search page must be repainted after each change",
        )
        self.assertEqual(
            "deepseek-r1",
            workspace.settings.defaults.investigator.model,
        )
        self.assertEqual(
            "deepseek-v4-pro",
            workspace.settings.defaults.other_roles.model,
            "the investigator choice must not overwrite the other-roles slot",
        )

    async def test_the_models_page_shows_the_current_state_before_asking(self) -> None:
        """State is always visible: arriving to change a model shows the model."""

        buffer = io.StringIO()
        workspace = self._workspace()
        workspace.console = theme.console(file=buffer)
        with mock.patch.object(
            prompts_module, "choose", mock.AsyncMock(return_value=None)
        ):
            await setup_flow.configure_providers(workspace)
        printed = buffer.getvalue()
        self.assertIn("deepseek-v4-flash", printed)
        self.assertIn("deepseek-v4-pro", printed)
        self.assertIn("duckduckgo", printed)


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
