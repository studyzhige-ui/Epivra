"""Provider setup: credentials, then assignment.

These are deliberately two steps, because they answer different questions.
*Credentials* say which vendors this installation can reach — several at once, and
adding Anthropic never removes DeepSeek. *Assignment* says which of them actually
does the work. Collapsing them would mean configuring a second vendor implied
switching to it.

Every key is proven against the vendor before it is saved. A key that is merely
present is not a key that works, and the alternative is discovering that an hour
into a study the user has already paid for.

Assignment exposes two choices rather than seven, because the seven roles already
fall into exactly two groups by cognitive load: the Investigator makes the most
calls over the most sources, and the other six do open-ended judgment. That split
is the runtime's existing tier structure, so nothing new is invented here.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING

from ..config import load_config
from ..providers.llm import LLM_PROVIDER_BY_NAME, LLM_PROVIDERS
from ..providers.validation import (
    search_credential_variables,
    suggest_models,
    validate_llm_credentials,
    validate_search_credentials,
)
from . import journal, prompts, theme
from .paths import config_file
from .settings import ModelChoice, ResearchDefaults

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .workspace import Workspace


def _write_credential(path: Path, env_var: str, value: str) -> None:
    """Add or replace one variable, leaving every other line untouched.

    Rewriting the whole file would drop a user's own settings, and several
    credentials must be able to coexist -- that is the entire point of keeping
    them separate from assignment.
    """

    lines: list[str] = []
    if path.is_file():
        lines = [
            line
            for line in path.read_text(encoding="utf-8").splitlines()
            if not line.strip().startswith(f"{env_var}=")
        ]
    else:
        lines = ["# Deep Research 配置。包含密钥，不要提交到 git。"]
    lines.append(f"{env_var}={value}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass


def _model_provider_options(workspace: Workspace) -> list[tuple[str, str]]:
    """Vendors that already have a saved key first, then the rest.

    Ordering is the whole point: a returning user is looking for the vendor they
    already configured, and burying it alphabetically among six they have never
    used makes the list actively unhelpful.  The mark says "已保存密钥" rather than
    "验证通过", because a saved key is not a working key -- that is only known
    after the vendor is asked, which happens when one is chosen.
    """

    keyed: list[tuple[str, str]] = []
    rest: list[tuple[str, str]] = []
    for spec in sorted(LLM_PROVIDERS, key=lambda item: item.name):
        if spec.api_key(workspace.environ):
            mark = workspace.t("setup.has_key")
            keyed.append((spec.name, f"{spec.label}（{mark}）"))
        else:
            rest.append((spec.name, spec.label))
    return keyed + rest


async def _ask_key(workspace: Workspace, label: str) -> str | None:
    """Read one credential, refusing silence rather than backing out on it.

    Pressing Enter on an empty prompt used to drop the user back a screen with no
    explanation, which reads as the tool ignoring them.  An empty entry now says
    what was wrong and offers the two moves that make sense.
    """

    while True:
        theme.dim(workspace.console, workspace.t("setup.key_hidden"))
        key = await prompts.ask_secret(
            workspace.t("setup.enter_key", provider=label)
        )
        if key is None:
            return None
        if key:
            return key
        theme.status_line(
            workspace.console, theme.GLYPH["warn"], workspace.t("setup.key_empty")
        )
        again = await prompts.choose(
            "",
            [
                ("retry", workspace.t("action.reenter")),
                ("back", workspace.t("action.back")),
            ],
        )
        if again != "retry":
            return None


async def _add_model_credential(workspace: Workspace) -> bool:
    """Collect and prove one model vendor's key.  Returns whether one was saved."""

    chosen = await prompts.choose(
        workspace.t("setup.choose_provider"),
        _model_provider_options(workspace),
        back_label=workspace.t("action.back"),
    )
    if chosen is None:
        return False
    spec = LLM_PROVIDER_BY_NAME[chosen]

    while True:
        key = await _ask_key(workspace, spec.label)
        if not key:
            return False
        with workspace.console.status(
            f"  {workspace.t('setup.validating')}", spinner="dots"
        ):
            result = await validate_llm_credentials(spec, key)
        if result.ok:
            _write_credential(config_file(), spec.key_env_var, key)
            workspace.reload_environment()
            theme.status_line(
                workspace.console,
                theme.GLYPH["done"],
                workspace.t("setup.valid", provider=spec.label),
            )
            return True

        theme.status_line(
            workspace.console,
            theme.GLYPH["blocked"],
            workspace.t("setup.invalid", provider=spec.label, reason=result.reason),
        )
        again = await prompts.choose(
            "",
            [
                ("retry", workspace.t("action.reenter")),
                ("back", workspace.t("action.back")),
            ],
        )
        if again != "retry":
            return False


async def _add_search_credential(workspace: Workspace) -> bool:
    variables = search_credential_variables()
    keyed: list[tuple[str, str]] = []
    rest: list[tuple[str, str]] = []
    for name, env_var in sorted(variables.items()):
        if workspace.environ.get(env_var, "").strip():
            keyed.append((name, f"{name}（{workspace.t('setup.has_key')}）"))
        else:
            rest.append((name, name))
    chosen = await prompts.choose(
        workspace.t("setup.configure_search"),
        keyed + rest,
        back_label=workspace.t("action.skip_for_now"),
    )
    if chosen is None:
        return False

    while True:
        key = await _ask_key(workspace, chosen)
        if not key:
            return False
        with workspace.console.status(
            f"  {workspace.t('setup.validating')}", spinner="dots"
        ):
            result = await validate_search_credentials(chosen, key)
        if result.ok:
            _write_credential(config_file(), variables[chosen], key)
            workspace.reload_environment()
            defaults = workspace.settings.defaults
            if chosen not in defaults.search_providers:
                workspace.settings = replace(
                    workspace.settings,
                    defaults=replace(
                        defaults,
                        search_providers=(*defaults.search_providers, chosen),
                    ),
                )
            theme.status_line(
                workspace.console,
                theme.GLYPH["done"],
                workspace.t("setup.valid", provider=chosen),
            )
            return True

        theme.status_line(
            workspace.console,
            theme.GLYPH["blocked"],
            workspace.t("setup.invalid", provider=chosen, reason=result.reason),
        )
        again = await prompts.choose(
            "",
            [
                ("retry", workspace.t("action.reenter")),
                ("back", workspace.t("action.skip_for_now")),
            ],
        )
        if again != "retry":
            return False


async def _choose_model(
    workspace: Workspace, spec, *, fast: bool, title_id: str
) -> str | None:  # noqa: ANN001
    """Pick one model from the list this key can actually reach.

    The catalogue comes from the vendor's ``/models`` endpoint every time.  When
    that call fails -- a dead key, a rotated key, a network without egress -- the
    failure is reported and the user is offered a manual model id.  It must never
    fall back to a name this program made up: that is what made a 401 look like
    "your vendor offers exactly one model", which is the opposite of informative.
    """

    while True:
        with workspace.console.status(
            f"  {workspace.t('setup.loading_models', provider=spec.label)}",
            spinner="dots",
        ):
            result = await validate_llm_credentials(spec, spec.api_key(workspace.environ))
        catalogue = suggest_models(spec, result.models, fast=fast)

        if catalogue:
            return await prompts.choose(
                workspace.t("setup.choose_model"),
                [(name, name) for name in catalogue],
                back_label=workspace.t("action.back"),
            )

        theme.status_line(
            workspace.console,
            theme.GLYPH["blocked"],
            workspace.t(
                "setup.no_catalogue",
                provider=spec.label,
                reason=result.reason or workspace.t("setup.key_empty"),
            ),
        )
        action = await prompts.choose(
            "",
            [
                ("key", workspace.t("action.reenter")),
                ("manual", workspace.t("setup.type_model")),
                ("back", workspace.t("action.back")),
            ],
        )
        if action == "key":
            if not await _add_model_credential(workspace):
                return None
        elif action == "manual":
            typed = await prompts.ask_text(workspace.t("setup.model_id_prompt"))
            if typed:
                return typed
            return None
        else:
            return None


async def _assign_one(
    workspace: Workspace, *, fast: bool, title_id: str, hint_id: str
) -> ModelChoice | None:
    """Pick a vendor that has a saved key, then a model that vendor lists."""

    ready = [spec for spec in LLM_PROVIDERS if spec.api_key(workspace.environ)]
    if not ready:
        return None

    theme.page(workspace.console, title=workspace.t(title_id))
    theme.dim(workspace.console, workspace.t(hint_id))
    provider = await prompts.choose(
        workspace.t("setup.choose_provider"),
        [(spec.name, spec.label) for spec in ready],
        back_label=workspace.t("action.back"),
    )
    if provider is None:
        return None
    spec = LLM_PROVIDER_BY_NAME[provider]
    model = await _choose_model(workspace, spec, fast=fast, title_id=title_id)
    if model is None:
        return None
    return ModelChoice(provider=provider, model=model)


async def ensure_models_assigned(
    workspace: Workspace, *, force: bool = False
) -> ResearchDefaults | None:
    """Assign both models in one pass, for a first run that has neither."""

    defaults = workspace.settings.defaults
    if defaults.models_configured and not force:
        return defaults

    investigator = await _assign_one(
        workspace,
        fast=True,
        title_id="setup.investigator_model",
        hint_id="setup.investigator_hint",
    )
    if investigator is None:
        return None
    other = await _assign_one(
        workspace,
        fast=False,
        title_id="setup.other_roles_model",
        hint_id="setup.other_roles_hint",
    )
    if other is None:
        return None
    return replace(defaults, investigator=investigator, other_roles=other)


def _render_state(workspace: Workspace) -> None:
    """What is configured right now, as the body of the page.

    This is the "state is always visible" half of the contract.  It replaces a
    menu that only listed verbs: a user arriving to change a model could not see
    what the model currently was without changing it.
    """

    defaults = workspace.settings.defaults
    unset = workspace.t("setup.unset")
    theme.section(workspace.console, workspace.t("setup.section_models"))
    theme.fields(
        workspace.console,
        [
            (
                workspace.t("setup.investigator_model"),
                defaults.investigator.render() or unset,
            ),
            (
                workspace.t("setup.other_roles_model"),
                defaults.other_roles.render() or unset,
            ),
        ],
    )

    theme.section(workspace.console, workspace.t("setup.section_search"))
    enabled = load_config(workspace.environ).search_providers
    for name in enabled:
        theme.status_line(workspace.console, theme.GLYPH["done"], name)
    if not enabled:
        theme.dim(workspace.console, workspace.t("setup.no_search_keys"))


async def configure_providers(workspace: Workspace) -> bool:
    """The models-and-search page: current state, then what can be changed.

    One page for the first run and for Settings, because they are the same
    question.  Each change returns *here* rather than to the workspace home, so
    adjusting the Investigator model and then the search key is two choices
    instead of two trips through the top-level menu.

    Returns whether anything changed, so the caller knows to persist and rebind.
    """

    changed = False

    if not any(spec.api_key(workspace.environ) for spec in LLM_PROVIDERS):
        theme.page(workspace.console, title=workspace.t("settings.providers"))
        theme.dim(workspace.console, workspace.t("setup.need_model"))
        if not await _add_model_credential(workspace):
            return changed
        changed = True
        updated = await ensure_models_assigned(workspace)
        if updated is not None:
            workspace.settings = replace(workspace.settings, defaults=updated)

    while True:
        theme.page(workspace.console, title=workspace.t("settings.providers"))
        workspace.show_receipt()
        _render_state(workspace)
        action = await prompts.choose(
            "",
            [
                ("investigator", workspace.t("action.change_investigator")),
                ("other", workspace.t("action.change_other_roles")),
                ("vendors", workspace.t("action.manage_vendors")),
                ("search", workspace.t("action.manage_search")),
            ],
            back_label=workspace.t("action.back_settings"),
        )
        if action is None:
            return changed

        if action in ("investigator", "other"):
            fast = action == "investigator"
            chosen = await _assign_one(
                workspace,
                fast=fast,
                title_id=(
                    "setup.investigator_model" if fast else "setup.other_roles_model"
                ),
                hint_id=(
                    "setup.investigator_hint" if fast else "setup.other_roles_hint"
                ),
            )
            if chosen is None:
                continue
            defaults = workspace.settings.defaults
            workspace.settings = replace(
                workspace.settings,
                defaults=(
                    replace(defaults, investigator=chosen)
                    if fast
                    else replace(defaults, other_roles=chosen)
                ),
            )
            changed = True
            journal.record(
                "model_assigned",
                role="investigator" if fast else "other_roles",
                provider=chosen.provider,
                model=chosen.model,
            )
            workspace.flash(
                theme.GLYPH["done"],
                workspace.t(
                    "receipt.investigator_updated"
                    if fast
                    else "receipt.other_roles_updated"
                ),
            )
        elif action == "vendors":
            theme.page(workspace.console, title=workspace.t("action.manage_vendors"))
            changed = await _add_model_credential(workspace) or changed
        elif action == "search":
            theme.page(workspace.console, title=workspace.t("action.manage_search"))
            theme.dim(workspace.console, workspace.t("setup.search_optional"))
            changed = await _add_search_credential(workspace) or changed


__all__ = ["configure_providers", "ensure_models_assigned"]
