"""The interactive workspace: a place to do research, not a menu of commands.

The shape follows from what the product is.  A study takes tens of minutes and
needs a human decision in the middle, so the interface cannot be "run a command,
get a result, exit".  It has to be somewhere the user stays while work happens,
and somewhere they can leave and come back to.

Three rules hold this together:

* **The home screen is derived from state, not fixed.**  A user with a plan
  waiting sees that plan; a user with nothing sees a question.  Showing everyone
  the same menu forces them to work out what to do next.
* **The session holds no state.**  Everything durable is in the artifact store
  and the ledger, so closing the terminal loses nothing and the next run picks up
  where this one stopped.
* **The direction gate is never bypassed.**  Nothing expensive starts until the
  user has read the direction and chosen to start.

Task IDs exist and are shown in details, but they are infrastructure identifiers.
Nobody should have to read one to navigate.
"""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import aiosqlite
from rich.console import Console
from rich.markdown import Markdown

from ..application import load_environment
from ..config import load_config
from ..contract import parse_question_lines
from ..providers.llm import LLM_PROVIDERS
from ..service import (
    EXPECTED_FAILURES,
    Event,
    ResearchService,
    Task,
    TaskAction,
)
from . import journal, prompts, theme
from .i18n import CLI_LANGUAGES, Translator
from .paths import config_file, settings_file
from .settings import (
    CliSettings,
    ResearchDefaults,
    runtime_environment,
    with_defaults,
    with_language,
)
from .settings import (
    load as load_settings,
)
from .settings import (
    save as save_settings,
)
from .setup_flow import configure_providers, ensure_models_assigned

#: Report languages offered by name.  Anything else is typed in; the runtime
#: passes the value through, so the list is convenience rather than a limit.
REPORT_LANGUAGES: tuple[tuple[str, str], ...] = (
    ("zh", "中文"),
    ("en", "English"),
    ("ja", "日本語"),
    ("ko", "한국어"),
    ("de", "Deutsch"),
    ("fr", "Français"),
    ("es", "Español"),
)

ACCESS_OPTIONS: tuple[tuple[str, str], ...] = (
    ("public_web", "access.public_web"),
    ("user_files", "access.user_files"),
    ("local_only", "access.local_only"),
)

@dataclass(slots=True)
class Workspace:
    """One interactive session over one database."""

    args: argparse.Namespace
    console: Console
    settings: CliSettings
    translate: Translator
    environ: dict[str, str]
    service: ResearchService | None = None
    #: A question typed on the home screen, or a revised brief, waiting to become
    #: the next study.  Declared because slots=True forbids stray attributes --
    #: the same mistake cost a crash on the first run of the previous CLI.
    _pending_request: str = ""
    #: The outcome of the last completed action, waiting to be shown once on the
    #: page the user lands on.  Selection is transient; this is how the outcome
    #: survives the screen being replaced.
    _receipt: tuple[str, str] = ("", "")

    # ---------------------------------------------------------------- helpers

    def t(self, message_id: str, **values: object) -> str:
        return self.translate(message_id, **values)

    def persist(self) -> None:
        save_settings(settings_file(), self.settings)

    def flash(self, glyph: str, message: str) -> None:
        """Leave one line for the next page to show, then forget it."""

        self._receipt = (glyph, message)

    def show_receipt(self) -> None:
        """Render a pending outcome at the top of the page, once."""

        glyph, message = self._receipt
        if not message:
            return
        self._receipt = ("", "")
        self.console.print()
        theme.status_line(self.console, glyph, message)

    def page(self, *, brand: str = "", title: str = "") -> None:
        """Begin a page and show any outcome that led the user here."""

        theme.page(self.console, brand=brand, title=title)
        self.show_receipt()

    async def hold(self) -> None:
        """Wait before the next page replaces this one.

        For anything the user has to actually read: an approval card, a finished
        run's log.  Without it, a repaint would wipe forty minutes of progress the
        instant the study ended.
        """

        await prompts.choose("", [("back", self.t("action.back"))])

    def reload_environment(self) -> None:
        """Re-read credentials and re-project the model assignment onto config.

        Only *new* studies are affected.  Each existing task keeps the execution
        configuration frozen when it was created, so the service is told about the
        credential change and nothing else.
        """

        base = dict(load_environment(config_file()))
        self.environ = runtime_environment(self.settings.defaults, base)
        if self.service is not None:
            self.service.rebind_credentials(self.environ)

    def configured_vendors(self) -> tuple[str, ...]:
        return tuple(
            spec.name for spec in LLM_PROVIDERS if spec.api_key(self.environ)
        )

    def is_configured(self) -> bool:
        """Whether a study could actually run: a model chosen and a key for it."""

        return bool(
            self.settings.defaults.models_configured and self.configured_vendors()
        )

    # ------------------------------------------------------------------- home

    def show_configuration(self) -> None:
        """The current configuration, on the way in, before anything is asked.

        A returning user's first question is "what is this going to use", and the
        answer is two models and a set of search sources.  Showing it here means
        nobody has to open Settings to find out, and anyone who wants to change it
        knows there is something to change.
        """

        defaults = self.settings.defaults
        if not self.is_configured():
            theme.status_line(
                self.console, theme.GLYPH["warn"], self.t("ready.unconfigured")
            )
            return

        config = load_config(self.environ)
        theme.status_line(self.console, theme.GLYPH["done"], self.t("ready.prefix"))
        theme.fields(
            self.console,
            [
                (self.t("ready.investigator"), defaults.investigator.render()),
                (self.t("ready.other_roles"), defaults.other_roles.render()),
                (self.t("cfg.web_search"), " · ".join(config.search_providers) or "—"),
                (self.t("cfg.academic"), " · ".join(config.academic_providers) or "—"),
            ],
        )

    async def home(self) -> str | None:
        """Render the state-driven home screen and return the chosen action.

        One screen in every state.  An unconfigured install used to get a
        different, smaller screen, which meant the first thing a new user saw was
        not the product but a two-item menu; now the same page says what is
        missing and greys out what that blocks.
        """

        assert self.service is not None
        self.page(brand=self.t("brand.name"))
        self.show_configuration()

        configured = self.is_configured()
        tasks = await self.service.tasks()
        asking = [
            item for item in tasks if item.state == "clarification_requested"
        ]
        awaiting = [item for item in tasks if item.state == "awaiting_approval"]
        paused = [item for item in tasks if "resume" in item.allowed_actions]
        frozen = [item for item in tasks if item.state == "needs_reconciliation"]
        done = [item for item in tasks if item.state == "published"]

        options: list[tuple[str, str]] = []
        if asking:
            # A question waiting on the user outranks everything else: the study
            # cannot even be planned until they answer it.
            self.console.print()
            self.console.print(f"  {self.t('home.clarification_waiting')}")
            self._preview(asking[0])
            options.append(
                ("answer", self.t("action.answer_clarification"))
                if asking[0].clarification_id
                else ("replan", self.t("action.replan"))
            )
        elif awaiting:
            self.console.print()
            message = (
                self.t("home.awaiting_one")
                if len(awaiting) == 1
                else self.t("home.awaiting_many", count=len(awaiting))
            )
            self.console.print(f"  {message}")
            self._preview(awaiting[0])
            options.append(("approve", self.t("action.review_approve")))
        elif paused:
            self.console.print()
            self._preview(paused[0])
            options.append(("resume", self.t("action.resume")))
        elif frozen:
            # Shown rather than hidden, and with no resume: it is stuck on a human
            # decision, and a study that needs one must not be invisible just
            # because this screen has no button for it.
            self.console.print()
            self._preview(frozen[0])
            options.append(("frozen", self.t("action.view_plan")))
        elif done:
            self.console.print()
            theme.dim(self.console, self.t("home.recent_done"))
            self._preview(done[0])
            options.append(("report", self.t("action.read_report")))

        options.append(("new", self.t("action.new_research")))
        if tasks:
            options.append(("tasks", self.t("action.all_research")))
        if configured:
            options.append(("settings", self.t("action.settings")))
        else:
            # Directive rather than generic: the one thing this user must do is
            # name a model, so the entry says that instead of "Settings".
            options.append(("setup", self.t("action.configure")))
        options.append(("exit", self.t("action.exit")))

        # Research is offered but not selectable without a model: the user learns
        # the action exists and what unlocks it, rather than finding it missing.
        disabled = (
            {}
            if configured
            else {
                key: self.t("home.configure_first")
                for key in ("new", "approve", "resume", "answer")
            }
        )

        if configured and not tasks:
            # Nothing pending: the fastest useful thing is to accept a question
            # directly rather than make the user pick "new" from a list first.
            self.console.print()
            theme.dim(self.console, self.t("home.prompt_hint"))
            typed = await prompts.ask_text(self.t("home.prompt"), multiline=False)
            if typed:
                self._pending_request = typed
                return "new"
            # Escape here means "I did not want to type"; it drops to the menu
            # below rather than leaving the product.  Only the menu's own exit --
            # chosen or by Escape -- ends the session.
        return await prompts.choose("", options, disabled=disabled)

    def _plan_title(self, task: Task) -> str:
        """The plan's own name, so a user always knows which version they hold."""

        if task.plan_version > 1:
            return self.t("plan.version", version=task.plan_version)
        return self.t("plan.title")

    def _preview(self, task: Task) -> None:
        title = theme.truncate(task.request, 52)
        glyph = theme.STATE_GLYPH.get(task.state, theme.GLYPH["info"])
        state = self.t(f"state.{task.state}")
        detail = state
        if task.materials:
            detail = f"{state} · {self.t('run.materials', count=task.materials)}"
        theme.status_line(self.console, glyph, title)
        theme.dim(self.console, f"  {detail}")

    # ------------------------------------------------------------------- loop

    async def loop(self) -> int:
        assert self.service is not None
        while True:
            action = await self.home()
            if action in (None, "exit"):
                self.console.print()
                theme.dim(self.console, self.t("generic.goodbye"))
                return 0
            try:
                if action == "setup":
                    await self._run_setup()
                elif action == "new":
                    await self._new_research()
                elif action in ("answer", "replan"):
                    await self._first_of("clarification_requested")
                elif action == "approve":
                    await self._first_of("awaiting_approval")
                elif action == "resume":
                    await self._first_with_action("resume")
                elif action == "frozen":
                    await self._first_of("needs_reconciliation")
                elif action == "report":
                    await self._first_of("published")
                elif action == "tasks":
                    await self._task_browser()
                elif action == "settings":
                    await self._settings_page()
            except KeyboardInterrupt:
                # An interrupt inside a page returns to the workspace; only the
                # home screen's exit choice leaves the product.
                self.console.print()
                theme.status_line(
                    self.console, theme.GLYPH["pending"], self.t("interrupt.paused")
                )
                theme.dim(self.console, self.t("interrupt.explain"))
            except EXPECTED_FAILURES as error:
                # A provider outage, an exhausted quota, a frozen operation: things
                # that go wrong outside this process.  Every artifact is already
                # committed, so the session continues with one readable line
                # instead of ending in a traceback.
                journal.record("failure", kind=type(error).__name__)
                self.flash(theme.GLYPH["blocked"], theme.truncate(str(error), 160))

    async def _first_of(self, *states: str) -> None:
        assert self.service is not None
        for task in await self.service.tasks():
            if task.state in states:
                await self._task_detail(task.task_id)
                return

    async def _first_with_action(self, action: TaskAction) -> None:
        """Open the first task whose fact projection permits ``action``."""

        assert self.service is not None
        for task in await self.service.tasks():
            if action in task.allowed_actions:
                await self._task_detail(task.task_id)
                return

    # --------------------------------------------------------------- setup

    async def _run_setup(self) -> None:
        changed = await configure_providers(self)
        if changed:
            self.reload_environment()
            self.persist()

    # ------------------------------------------------------- research flows

    async def _new_research(self) -> None:
        assert self.service is not None
        self.page(title=self.t("new.title"))

        request = self._pending_request
        if request:
            self._pending_request = ""
        else:
            self.console.print()
            typed = await prompts.ask_text(self.t("home.prompt"))
            if not typed:
                return
            request = typed

        defaults = await self._confirm_settings()
        if defaults is None:
            return

        self.console.print()
        with self.console.status(f"  {self.t('new.generating')}", spinner="dots"):
            task = await self.service.open_task(
                request,
                language=defaults.report_language,
                source_access=defaults.source_access,  # type: ignore[arg-type]
                created_at=_stamp(),
                listen=self._collect,
            )
        await self._task_detail(task.task_id)

    def _render_defaults(self, defaults: ResearchDefaults) -> None:
        """The research settings a study would inherit, as page body."""

        config = load_config(self.environ)
        rows = [
            (self.t("cfg.report_language"), _language_label(defaults.report_language)),
            (self.t("cfg.sources"), self.t(_access_message(defaults.source_access))),
            (
                self.t("cfg.model"),
                f"{defaults.other_roles.render()} / {defaults.investigator.render()}",
            ),
            (self.t("cfg.web_search"), " · ".join(config.search_providers) or "—"),
            (self.t("cfg.academic"), " · ".join(config.academic_providers) or "—"),
        ]
        if defaults.corpus_root:
            rows.append((self.t("cfg.corpus"), defaults.corpus_root))
        theme.fields(self.console, rows)

    def _defaults_fields(self) -> list[tuple[str, str]]:
        return [
            ("language", self.t("cfg.report_language")),
            ("sources", self.t("cfg.sources")),
            ("models", self.t("cfg.model")),
            ("search", self.t("cfg.web_search")),
        ]

    async def _confirm_settings(self) -> ResearchDefaults | None:
        """Show inherited settings; let them be changed without re-asking all."""

        defaults = self.settings.defaults
        while True:
            self.page(title=self.t("cfg.title"))
            self._render_defaults(defaults)

            action = await prompts.choose(
                "",
                [
                    ("use", self.t("action.use_these")),
                    ("change", self.t("action.change")),
                ],
                back_label=self.t("action.back"),
            )
            if action is None:
                return None
            if action == "use":
                return defaults
            field_key = await prompts.choose(
                self.t("action.change"),
                self._defaults_fields(),
                back_label=self.t("action.back"),
            )
            if field_key is None:
                continue
            updated = await self._edit_field(defaults, field_key)
            if updated is not None:
                defaults = updated
                self.settings = with_defaults(self.settings, defaults)
                self.persist()
                self.reload_environment()
                self.flash(theme.GLYPH["done"], self.t("receipt.defaults_saved"))

    async def _edit_field(
        self, defaults: ResearchDefaults, field_key: str
    ) -> ResearchDefaults | None:
        """Change one research default.  ``None`` means the user backed out."""

        if field_key == "language":
            chosen = await prompts.choose(
                self.t("cfg.report_language"),
                [*REPORT_LANGUAGES, ("other", self.t("generic.other"))],
                back_label=self.t("action.back"),
            )
            if chosen == "other":
                typed = await prompts.ask_text(self.t("cfg.report_language"), default="en")
                chosen = typed or None
            if chosen:
                from dataclasses import replace

                return replace(defaults, report_language=chosen)
            return None
        if field_key == "sources":
            return await self._edit_source_access(defaults)
        if field_key == "models":
            return await ensure_models_assigned(self, force=True)
        if field_key == "search":
            return await self._edit_search(defaults)
        return None

    async def _edit_source_access(
        self, defaults: ResearchDefaults
    ) -> ResearchDefaults | None:
        from dataclasses import replace

        chosen = await prompts.choose(
            self.t("cfg.sources"),
            [(key, self.t(message)) for key, message in ACCESS_OPTIONS],
            back_label=self.t("action.back"),
        )
        if chosen is None:
            return None
        access = (
            ("public_web",)
            if chosen == "public_web"
            else ("public_web", "user_files")
            if chosen == "user_files"
            else ("local_only",)
        )
        corpus = defaults.corpus_root
        if chosen in ("user_files", "local_only"):
            while True:
                typed = await prompts.ask_text(self.t("cfg.corpus"), default=corpus)
                if typed is None:
                    return None
                if typed and Path(typed).expanduser().is_dir():
                    corpus = typed
                    break
                theme.dim(self.console, self.t("generic.path_not_dir"))
        return replace(defaults, source_access=access, corpus_root=corpus)

    async def _edit_search(self, defaults: ResearchDefaults) -> ResearchDefaults | None:
        from dataclasses import replace

        from ..providers import search_credentials

        options = [
            (
                name,
                f"{name}"
                + ("" if self.environ.get(env_var, "").strip() else "（未配置密钥）"),
                name in defaults.search_providers,
            )
            for name, env_var in sorted(search_credentials().items())
        ]
        options.append(("duckduckgo", "duckduckgo（无需密钥）", True))
        chosen = await prompts.choose_many(self.t("cfg.web_search"), options)
        if chosen is None:
            return None
        academic = await prompts.choose_many(
            self.t("cfg.academic"),
            [
                (name, name, name in defaults.academic_providers)
                for name in ("arxiv", "crossref", "pubmed")
            ],
        )
        return replace(
            defaults,
            search_providers=chosen,
            academic_providers=academic if academic is not None else defaults.academic_providers,
        )

    async def _replan(self, task: Task) -> None:
        """Retry a plan the Architect never produced.

        Reached when the first attempt failed outside this program -- a provider
        outage, an expired key -- which left a study with a Commission and nothing
        else.  Nothing has been paid for yet, so retrying is cheap and safe.
        """

        assert self.service is not None
        self.page(title=self.t("plan.title"))
        with self.console.status(f"  {self.t('new.generating')}", spinner="dots"):
            updated = await self.service.replan(task.task_id)
        journal.record("replanned", task_id=task.task_id, state=updated.state)
        if updated.state == "clarification_requested" and updated.clarification_id:
            self.flash(theme.GLYPH["info"], self.t("clarify.another"))
        elif updated.state == "awaiting_approval":
            self.flash(theme.GLYPH["done"], self.t("clarify.resolved"))

    async def _answer_clarification(self, task: Task) -> None:
        """Answer the Architect's open question, on this task, and let it retry.

        This used to concatenate the answer onto the request and call
        ``_new_research``, which opened a *second* study and left the first
        stranded at ``clarification_requested`` forever.  The answer is now bound
        to the exact question it answers, and the study keeps its identity.
        """

        assert self.service is not None
        self.page(title=self.t("clarify.title"))
        self.console.print()
        self.console.print(f"  {task.clarification_question}")
        if task.clarification_why:
            theme.dim(self.console, self.t("clarify.why", why=task.clarification_why))
        self.console.print()

        answer = await prompts.ask_text(self.t("clarify.prompt"))
        if not answer:
            return

        try:
            with self.console.status(f"  {self.t('clarify.working')}", spinner="dots"):
                updated = await self.service.answer_clarification(
                    task.task_id, task.clarification_id, answer
                )
        except EXPECTED_FAILURES as error:
            self.flash(theme.GLYPH["warn"], str(error))
            return

        journal.record("clarification_answered", task_id=task.task_id)
        if updated.state == "clarification_requested":
            # The Architect needs one more thing; still the same study.
            self.flash(theme.GLYPH["info"], self.t("clarify.another"))
        else:
            self.flash(theme.GLYPH["done"], self.t("clarify.resolved"))

    # ------------------------------------------------------- task navigation

    async def _task_browser(self) -> None:
        assert self.service is not None
        while True:
            tasks = await self.service.tasks()
            self.page(title=self.t("list.title"))
            if not tasks:
                theme.dim(self.console, self.t("list.empty"))
                return
            options = [
                (
                    task.task_id,
                    f"{theme.STATE_GLYPH.get(task.state, '·')} "
                    f"{theme.truncate(task.request, 44)} · "
                    f"{self.t(f'state.{task.state}')}",
                )
                for task in tasks
            ]
            chosen = await prompts.choose(
                "", options, back_label=self.t("action.back_workspace")
            )
            if chosen is None:
                return
            await self._task_detail(chosen)

    async def _task_detail(self, task_id: str) -> None:
        assert self.service is not None
        while True:
            task = await self.service.task(task_id)
            self.page(title=theme.truncate(task.request, 56))
            rows = [(self.t("detail.status"), self.t(f"state.{task.state}"))]
            if task.sources:
                rows.append(
                    (self.t("run.collected"), self.t("run.sources", count=task.sources))
                )
            if task.materials:
                rows.append(("", self.t("run.materials", count=task.materials)))
            # The frozen model, not the current default: a user who has since
            # changed their settings must be able to see that this study did not.
            if task.state == "awaiting_approval" and task.plan_version > 1:
                rows.append((self.t("plan.label"), self._plan_title(task)))
            if task.clarification_question:
                rows.append(
                    (
                        self.t("clarify.label"),
                        theme.truncate(task.clarification_question, 52),
                    )
                )
            rows.append(
                (self.t("cfg.model"), await self.service.execution_summary(task_id))
            )
            rows.append((self.t("detail.task_id"), task.task_id))
            theme.fields(self.console, rows)

            if task.state == "needs_reconciliation":
                # The one state this interface cannot resolve, so it says what
                # would resolve it rather than offering an action that must fail.
                self.console.print()
                theme.status_line(
                    self.console, theme.GLYPH["warn"], self.t("reconcile.title")
                )
                theme.dim(self.console, self.t("reconcile.body"))

            if task.state == "awaiting_approval":
                theme.rule_title(self.console, self._plan_title(task))
                self._render_direction(await self.service.approval_card(task_id))
                theme.dim(self.console, self.t("plan.read_these"))

            action = await prompts.choose("", self._actions_for(task))
            if action in (None, "back"):
                return
            if action == "plan":
                await self._show_plan(task)
            elif action == "approve":
                await self._approve_and_run(task)
            elif action == "resume":
                await self._run_research(task_id)
            elif action == "report":
                await self._read_report(task_id)
            elif action == "export":
                await self._export_report(task_id)
            elif action == "answer":
                await self._answer_clarification(task)
            elif action == "replan":
                await self._replan(task)
            elif action == "revise":
                if await self._revise(task):
                    return
            elif action == "delete":
                if await self._delete(task):
                    return

    def _actions_for(self, task: Task) -> list[tuple[str, str]]:
        """Translate projected actions; the interface defines no action policy."""

        labels = {
            "answer": "action.answer_clarification",
            "approve": "action.approve_start",
            "back": (
                "action.save_for_later"
                if task.state in {"awaiting_approval", "clarification_requested"}
                else "action.back_workspace"
            ),
            "delete": (
                "action.delete_done"
                if task.state == "published"
                else "action.delete_running"
            ),
            "export": "action.export_report",
            "plan": "action.view_plan",
            "report": "action.read_report",
            "replan": "action.replan",
            "resume": "action.resume",
            "revise": "action.request_changes",
        }
        return [(action, self.t(labels[action])) for action in task.allowed_actions]

    async def _show_plan(self, task: Task) -> None:
        assert self.service is not None
        card = await self.service.approval_card(task.task_id)
        self.page(title=self._plan_title(task))
        self._render_direction(card)
        # A direction from a running or paused study is read-only here.  A task
        # waiting to start renders it directly on the decision page instead.
        await self.hold()

    def _render_direction(self, markdown: str) -> None:
        """Render the Contract topic predictably, then its exact remaining body.

        Rich gives level-one Markdown headings a centred block treatment.  That
        looked like a code block when copied from the terminal, so the one derived
        topic is rendered as ordinary bold text.  No content is summarized or
        rewritten; only the ``#`` presentation marker is consumed.
        """

        lines = markdown.strip().splitlines()
        first = next((index for index, line in enumerate(lines) if line.strip()), -1)
        heading = lines[first].lstrip() if first >= 0 else ""
        if heading.startswith("# "):
            self.console.print()
            self.console.print(heading[2:].strip(), style="bold", markup=False)
            del lines[first]
        for index, line in enumerate(lines):
            parsed = parse_question_lines(line)
            if parsed:
                label, text = parsed[0]
                lines[index] = f"- {label}. {text}"
        body = "\n".join(lines).strip()
        if body:
            self.console.print(Markdown(body))

    async def _approve_and_run(self, task: Task) -> None:
        assert self.service is not None
        # From here the screen is a live log, not a page: a run's own history is
        # what the user is watching, so nothing below clears it.
        self.page(title=self.t("plan.approved"))
        theme.dim(self.console, self.t("new.after_approve_costs"))
        try:
            await self.service.approve(task.task_id, task.plan_id)
        except EXPECTED_FAILURES as error:
            self.flash(theme.GLYPH["warn"], str(error))
            return
        journal.record(
            "research_approved", task_id=task.task_id, version=task.plan_version
        )
        await self._run_research(task.task_id)

    async def _run_research(self, task_id: str) -> None:
        assert self.service is not None
        # A local capture rather than session state: the published event carries
        # counts only the renderer knows, and they are wanted one screen later.
        published: dict[str, object] = {}

        def watch(event: Event) -> None:
            if event.kind == "published":
                published.update(event.detail)
            self._render_progress(event)

        try:
            state = await self.service.advance(task_id, listen=watch)
        except KeyboardInterrupt:
            self.console.print()
            theme.status_line(
                self.console, theme.GLYPH["pending"], self.t("interrupt.paused")
            )
            theme.dim(self.console, self.t("interrupt.explain"))
            await self.hold()
            return
        if state == "published":
            await self._completion(task_id, published)
        await self.hold()

    async def _completion(self, task_id: str, published: Mapping[str, object]) -> None:
        assert self.service is not None
        task = await self.service.task(task_id)
        report = await self.service.report(task_id)
        theme.rule_title(self.console, self.t("done.title"))
        # The cited count comes from the renderer, not from the evidence set: they
        # are different numbers, and this line used to show the second under a
        # label that promised the first.
        cited = int(published.get("cited_materials", task.materials))
        theme.fields(
            self.console,
            [
                (
                    self.t("done.report_chars"),
                    self.t("done.chars", count=len(report or "")),
                ),
                (self.t("run.collected"), self.t("run.sources", count=task.sources)),
                (self.t("done.cited"), self.t("run.materials", count=cited)),
            ],
        )

    async def _read_report(self, task_id: str) -> None:
        assert self.service is not None
        report = await self.service.report(task_id)
        if report is None:
            theme.dim(self.console, self.t("generic.no_report"))
            return
        # A pager keeps a 20,000-character report navigable; q returns, which is
        # the one place q is used.
        with self.console.pager(styles=True):
            self.console.print(Markdown(report))

    async def _export_report(self, task_id: str) -> None:
        assert self.service is not None
        report = await self.service.report(task_id)
        if report is None:
            theme.dim(self.console, self.t("generic.no_report"))
            return
        typed = await prompts.ask_text(self.t("generic.export_path"), default="report.md")
        if not typed:
            return
        path = Path(typed).expanduser()
        if path.exists() and not await prompts.confirm_destructive(
            self.t("generic.overwrite", path=path),
            keep=self.t("action.back"),
            destroy=self.t("generic.yes"),
        ):
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(report, encoding="utf-8")
        journal.record("report_exported", task_id=task_id, characters=len(report))
        self.flash(
            theme.GLYPH["done"],
            self.t("generic.exported", path=path, count=len(report)),
        )

    async def _revise(self, task: Task) -> bool:
        """Send the plan back with an instruction, and show the next version.

        The same study throughout.  This used to build ``request + 补充：…`` and
        open a *new* task, so a user who adjusted a plan twice ended up with three
        studies and two abandoned plans -- and the Architect saw a longer brief
        rather than "here is your plan, change this".
        """

        assert self.service is not None
        instruction = await prompts.ask_text(self.t("plan.revise_prompt"))
        if not instruction:
            return False

        self.console.print()
        try:
            with self.console.status(f"  {self.t('plan.revising')}", spinner="dots"):
                revised = await self.service.request_revision(
                    task.task_id, task.plan_id, instruction
                )
        except EXPECTED_FAILURES as error:
            self.flash(theme.GLYPH["warn"], str(error))
            return False

        journal.record(
            "plan_revised", task_id=task.task_id, version=revised.plan_version
        )
        self.flash(
            theme.GLYPH["done"],
            self.t("receipt.plan_revised", version=revised.plan_version),
        )
        # Stays on this task: the next thing to do is read the new version.
        return False

    async def _delete(self, task: Task) -> bool:
        assert self.service is not None
        self.console.print()
        theme.status_line(
            self.console, theme.GLYPH["warn"], self.t("delete.confirm_title")
        )
        theme.dim(self.console, self.t("delete.confirm_body"))
        if not await prompts.confirm_destructive(
            "",
            keep=self.t("delete.keep"),
            destroy=self.t("delete.confirm"),
        ):
            return False
        await self.service.delete_research(task.task_id)
        journal.record("research_deleted", task_id=task.task_id, state=task.state)
        self.flash(theme.GLYPH["done"], self.t("delete.done"))
        return True

    # ---------------------------------------------------------- settings page

    async def _settings_page(self) -> None:
        while True:
            self.page(title=self.t("settings.title"))
            action = await prompts.choose(
                "",
                [
                    ("language", self.t("settings.cli_language")),
                    ("providers", self.t("settings.providers")),
                    ("defaults", self.t("settings.defaults")),
                ],
                back_label=self.t("action.back_workspace"),
            )
            if action is None:
                return
            if action == "language":
                chosen = await prompts.choose(
                    self.t("setup.choose_cli_language"),
                    list(CLI_LANGUAGES),
                    back_label=self.t("action.back"),
                )
                if chosen:
                    self.settings = with_language(self.settings, chosen)
                    self.translate = Translator(chosen)
                    self.persist()
                    journal.record("cli_language_changed", language=chosen)
                    self.flash(theme.GLYPH["done"], self.t("receipt.language_saved"))
            elif action == "providers":
                await self._run_setup()
            elif action == "defaults":
                await self._defaults_page()

    async def _defaults_page(self) -> None:
        """Research defaults: current values, and the one to change.

        Not the new-research confirmation screen, which this used to reuse.  That
        screen's first option is "use these settings", which means nothing when a
        user opened Settings to *change* something.
        """

        while True:
            self.page(title=self.t("cfg.title"))
            self._render_defaults(self.settings.defaults)
            field_key = await prompts.choose(
                "",
                self._defaults_fields(),
                back_label=self.t("action.back_settings"),
            )
            if field_key is None:
                return
            updated = await self._edit_field(self.settings.defaults, field_key)
            if updated is None:
                continue
            self.settings = with_defaults(self.settings, updated)
            self.persist()
            self.reload_environment()
            self.flash(theme.GLYPH["done"], self.t("receipt.defaults_saved"))

    # ------------------------------------------------------------- rendering

    def _collect(self, event: Event) -> None:
        """Swallow plan-stage chatter; the page that follows shows the outcome."""

    def _render_progress(self, event: Event) -> None:
        if event.kind == "wave_started":
            round_index = event.detail.get("round", 0)
            stage = "breadth" if round_index == 1 else "focus"
            self.console.print()
            theme.timeline(
                self.console,
                [
                    ("done", self.t("run.stage.baseline")),
                    (
                        "done" if stage == "focus" else "active",
                        self.t("run.stage.breadth"),
                    ),
                    (
                        "active" if stage == "focus" else "pending",
                        self.t("run.stage.focus"),
                    ),
                    ("pending", self.t("run.stage.analysis")),
                    ("pending", self.t("run.stage.writing")),
                    ("pending", self.t("run.stage.review")),
                ],
            )
            self.console.print()
            theme.dim(self.console, f"{self.t('run.current')}: {event.message}")
            for focus in event.detail.get("assignments", ()):
                theme.dim(self.console, f"  · {theme.truncate(str(focus), 62)}")
        elif event.kind == "wave_finished":
            theme.status_line(self.console, theme.GLYPH["done"], event.message)
        elif event.kind == "review":
            glyph = theme.GLYPH["done"] if event.detail.get("approved") else theme.GLYPH["warn"]
            theme.status_line(
                self.console, glyph, f"{self.t('run.stage.review')} · {event.message}"
            )
            if self.args.verbose:
                for finding in event.detail.get("findings", ()):
                    theme.dim(self.console, f"    {str(finding).splitlines()[0]}")
        elif event.kind in ("paused", "halted", "researching"):
            theme.status_line(self.console, theme.GLYPH["pending"], event.message)
            journal.record("research_" + event.kind, message=event.message)
        elif event.kind == "needs_reconciliation":
            # Its own branch because it is the one stop that will not clear by
            # running again, and the message has to say so.
            theme.status_line(self.console, theme.GLYPH["blocked"], event.message)
            theme.dim(self.console, self.t("reconcile.body"))
            journal.record("research_needs_reconciliation", message=event.message)
        elif event.kind == "configuration_not_frozen":
            # A warning, so never behind --verbose: it says this study may
            # continue on a model that did not produce its existing evidence.
            theme.status_line(self.console, theme.GLYPH["warn"], event.message)
        elif event.kind == "published":
            theme.status_line(self.console, theme.GLYPH["done"], event.message)
            journal.record("research_published", message=event.message)
        elif self.args.verbose:
            theme.dim(self.console, event.message)


def _language_label(code: str) -> str:
    return dict(REPORT_LANGUAGES).get(code, code)


def _access_message(access: tuple[str, ...]) -> str:
    if "local_only" in access:
        return "access.local_only"
    if "user_files" in access:
        return "access.user_files"
    return "access.public_web"


def _stamp() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat(timespec="seconds")


async def _run(args: argparse.Namespace) -> int:
    console = theme.console()
    settings = load_settings(settings_file())
    translate = Translator(settings.language)

    # The very first thing a new user is asked, before any other screen: an
    # interface they cannot read is not an interface.
    if not settings.language_chosen:
        theme.page(console, brand="Deep Research")
        chosen = await prompts.choose("Language / 界面语言", list(CLI_LANGUAGES))
        if chosen is None:
            return 0
        settings = with_language(settings, chosen)
        save_settings(settings_file(), settings)
        translate = Translator(chosen)

    base = dict(load_environment(config_file()))
    workspace = Workspace(
        args=args,
        console=console,
        settings=settings,
        translate=translate,
        environ=runtime_environment(settings.defaults, base),
    )

    database = Path(args.database)
    database.parent.mkdir(parents=True, exist_ok=True)
    connection = await aiosqlite.connect(database)
    try:
        workspace.service = ResearchService(
            connection=connection,
            environ=workspace.environ,
            corpus_root=(
                Path(settings.defaults.corpus_root)
                if settings.defaults.corpus_root
                else None
            ),
        )
        await workspace.service.setup()
        return await workspace.loop()
    finally:
        await connection.close()


def run_workspace(args: argparse.Namespace) -> int:
    try:
        return asyncio.run(_run(args))
    except KeyboardInterrupt:
        print()
        print(Translator(load_settings(settings_file()).language)("interrupt.on_exit"))
        return 130


__all__ = [
    "ACCESS_OPTIONS",
    "REPORT_LANGUAGES",
    "Workspace",
    "run_workspace",
]
