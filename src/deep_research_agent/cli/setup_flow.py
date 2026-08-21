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

from ..providers.llm import LLM_PROVIDER_BY_NAME, LLM_PROVIDERS
from ..providers.validation import (
    search_credential_variables,
    suggest_models,
    validate_llm_credentials,
    validate_search_credentials,
)
from . import prompts, theme
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


async def _add_model_credential(workspace: Workspace) -> bool:
    """Collect and prove one model vendor's key.  Returns whether one was saved."""

    options = []
    for spec in sorted(LLM_PROVIDERS, key=lambda item: item.name):
        ready = bool(spec.api_key(workspace.environ))
        mark = f" {theme.GLYPH['done']}" if ready else ""
        options.append((spec.name, f"{spec.label}{mark}"))
    chosen = await prompts.choose(
        workspace.t("setup.choose_provider"),
        options,
        back_label=workspace.t("action.back"),
    )
    if chosen is None:
        return False
    spec = LLM_PROVIDER_BY_NAME[chosen]

    while True:
        theme.dim(workspace.console, workspace.t("setup.key_hidden"))
        key = await prompts.ask_secret(
            workspace.t("setup.enter_key", provider=spec.label)
        )
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
    options = []
    for name, env_var in sorted(variables.items()):
        ready = bool(workspace.environ.get(env_var, "").strip())
        options.append((name, f"{name}{' ' + theme.GLYPH['done'] if ready else ''}"))
    chosen = await prompts.choose(
        workspace.t("setup.configure_search"),
        options,
        back_label=workspace.t("action.skip_for_now"),
    )
    if chosen is None:
        return False

    while True:
        theme.dim(workspace.console, workspace.t("setup.key_hidden"))
        key = await prompts.ask_secret(workspace.t("setup.enter_key", provider=chosen))
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


async def _assign_one(
    workspace: Workspace, *, fast: bool, title_id: str, hint_id: str
) -> ModelChoice | None:
    """Pick a provider that has *already validated*, then a model it lists."""

    ready = [spec for spec in LLM_PROVIDERS if spec.api_key(workspace.environ)]
    if not ready:
        return None

    theme.rule_title(workspace.console, workspace.t(title_id))
    theme.dim(workspace.console, workspace.t(hint_id))
    provider = await prompts.choose(
        workspace.t("setup.choose_provider"),
        [(spec.name, spec.label) for spec in ready],
        back_label=workspace.t("action.back"),
    )
    if provider is None:
        return None
    spec = LLM_PROVIDER_BY_NAME[provider]

    with workspace.console.status(
        f"  {workspace.t('setup.loading_models', provider=spec.label)}", spinner="dots"
    ):
        result = await validate_llm_credentials(spec, spec.api_key(workspace.environ))
    catalogue = suggest_models(spec, result.models, fast=fast)
    model = await prompts.choose(
        workspace.t(title_id),
        [(name, name) for name in catalogue[:40]],
        back_label=workspace.t("action.back"),
    )
    if model is None:
        return None
    return ModelChoice(provider=provider, model=model)


async def ensure_models_assigned(
    workspace: Workspace, *, force: bool = False
) -> ResearchDefaults | None:
    """Assign the Investigator model and the model for the other six roles."""

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


async def configure_providers(workspace: Workspace) -> bool:
    """The first-run path and the Settings path, which are the same path.

    Returns whether anything changed, so the caller knows to persist and rebind.
    """

    theme.rule_title(workspace.console, workspace.t("setup.welcome"))
    changed = False

    if not any(spec.api_key(workspace.environ) for spec in LLM_PROVIDERS):
        theme.dim(workspace.console, workspace.t("setup.need_model"))
        if not await _add_model_credential(workspace):
            return changed
        changed = True

    while True:
        action = await prompts.choose(
            "",
            [
                ("model", workspace.t("setup.choose_provider")),
                ("search", workspace.t("setup.configure_search")),
                ("assign", workspace.t("cfg.model")),
            ],
            back_label=workspace.t("action.back_workspace"),
        )
        if action is None:
            break
        if action == "model":
            changed = await _add_model_credential(workspace) or changed
        elif action == "search":
            theme.dim(workspace.console, workspace.t("setup.search_optional"))
            changed = await _add_search_credential(workspace) or changed
        elif action == "assign":
            updated = await ensure_models_assigned(workspace, force=True)
            if updated is not None:
                workspace.settings = replace(workspace.settings, defaults=updated)
                changed = True

    if changed:
        updated = await ensure_models_assigned(workspace)
        if updated is not None:
            workspace.settings = replace(workspace.settings, defaults=updated)
        theme.status_line(
            workspace.console, theme.GLYPH["done"], workspace.t("setup.done")
        )
    return changed


__all__ = ["configure_providers", "ensure_models_assigned"]
