"""Persistent CLI settings, separate from credentials and from task state.

Three kinds of configuration live in three places, on purpose:

* **Credentials** stay in ``.env``.  They are secrets, they are already what
  :func:`deep_research_agent.application.load_environment` reads, and a user may
  hold several at once -- a saved DeepSeek key does not stop them adding Anthropic.
* **Preferences** live here: interface language, and the defaults a new study
  inherits so nobody answers five questions twice.
* **Task state** lives in the artifact store and the ledger.  Nothing in this
  file is authoritative about a study.

The distinction that matters most is between *credentials available* and *models
assigned*.  Configuring a vendor makes it selectable; it does not make it used.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path

from .i18n import DEFAULT_CLI_LANGUAGE

SETTINGS_FILENAME = "settings.json"


@dataclass(frozen=True, slots=True)
class ModelChoice:
    """One resolved (provider, model) pair."""

    provider: str = ""
    model: str = ""

    @property
    def configured(self) -> bool:
        return bool(self.provider and self.model)

    def render(self) -> str:
        return f"{self.provider}/{self.model}" if self.configured else ""


@dataclass(frozen=True, slots=True)
class ResearchDefaults:
    """What a new study inherits unless the user changes it for that study.

    Inheriting is the point: asking for report language, sources and vendors on
    every single study turns a research tool into a configuration exercise.
    """

    report_language: str = "zh"
    source_access: tuple[str, ...] = ("public_web",)
    corpus_root: str = ""
    investigator: ModelChoice = field(default_factory=ModelChoice)
    other_roles: ModelChoice = field(default_factory=ModelChoice)
    search_providers: tuple[str, ...] = ()
    academic_providers: tuple[str, ...] = ("arxiv", "crossref", "pubmed")

    @property
    def models_configured(self) -> bool:
        return self.investigator.configured and self.other_roles.configured


@dataclass(frozen=True, slots=True)
class CliSettings:
    """Everything the interface remembers between runs."""

    cli_language: str = ""
    defaults: ResearchDefaults = field(default_factory=ResearchDefaults)

    @property
    def language_chosen(self) -> bool:
        """Whether the user has ever picked an interface language.

        Empty rather than defaulted, because "the user chose Chinese" and "nobody
        has asked yet" must be distinguishable -- the first run has to offer the
        choice, and every run after it must not.
        """

        return bool(self.cli_language)

    @property
    def language(self) -> str:
        return self.cli_language or DEFAULT_CLI_LANGUAGE


def _model_choice(payload: object) -> ModelChoice:
    if not isinstance(payload, Mapping):
        return ModelChoice()
    return ModelChoice(
        provider=str(payload.get("provider", "") or ""),
        model=str(payload.get("model", "") or ""),
    )


def _string_tuple(payload: object, fallback: Sequence[str] = ()) -> tuple[str, ...]:
    if not isinstance(payload, (list, tuple)):
        return tuple(fallback)
    return tuple(str(item) for item in payload if str(item).strip())


def decode(payload: Mapping[str, object]) -> CliSettings:
    """Read settings tolerantly; an unreadable field falls back to its default.

    A settings file that fails to parse must not stop a user from researching, so
    every field degrades independently rather than the whole file being rejected.
    """

    raw_defaults = payload.get("defaults")
    defaults = ResearchDefaults()
    if isinstance(raw_defaults, Mapping):
        defaults = ResearchDefaults(
            report_language=str(raw_defaults.get("report_language") or "zh"),
            source_access=_string_tuple(
                raw_defaults.get("source_access"), ("public_web",)
            ),
            corpus_root=str(raw_defaults.get("corpus_root") or ""),
            investigator=_model_choice(raw_defaults.get("investigator")),
            other_roles=_model_choice(raw_defaults.get("other_roles")),
            search_providers=_string_tuple(raw_defaults.get("search_providers")),
            academic_providers=_string_tuple(
                raw_defaults.get("academic_providers"),
                ("arxiv", "crossref", "pubmed"),
            ),
        )
    return CliSettings(
        cli_language=str(payload.get("cli_language") or ""),
        defaults=defaults,
    )


def load(path: Path) -> CliSettings:
    if not path.is_file():
        return CliSettings()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return CliSettings()
    return decode(payload) if isinstance(payload, Mapping) else CliSettings()


def save(path: Path, settings: CliSettings) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "cli_language": settings.cli_language,
        "defaults": {
            **asdict(settings.defaults),
            "source_access": list(settings.defaults.source_access),
            "search_providers": list(settings.defaults.search_providers),
            "academic_providers": list(settings.defaults.academic_providers),
        },
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def with_language(settings: CliSettings, language: str) -> CliSettings:
    return replace(settings, cli_language=language)


def with_defaults(settings: CliSettings, defaults: ResearchDefaults) -> CliSettings:
    return replace(settings, defaults=defaults)


def runtime_environment(
    defaults: ResearchDefaults, base: Mapping[str, str]
) -> dict[str, str]:
    """Project the chosen models onto the variables ``load_config`` already reads.

    The two user-facing choices map exactly onto the tiers the runtime already
    has -- the Investigator is the only role on the ``fast`` tier and the other
    six are on ``reasoning`` -- so no new configuration mechanism is needed and
    ``config.py`` is untouched.
    """

    overlay = dict(base)
    if defaults.investigator.configured:
        overlay["DEEP_RESEARCH_INVESTIGATOR_PROVIDER"] = defaults.investigator.provider
        overlay["DEEP_RESEARCH_INVESTIGATOR_MODEL"] = defaults.investigator.model
    if defaults.other_roles.configured:
        overlay["DEEP_RESEARCH_LLM_PROVIDER"] = defaults.other_roles.provider
        overlay["DEEP_RESEARCH_REASONING_MODEL"] = defaults.other_roles.model
    if defaults.search_providers:
        overlay["DEEP_RESEARCH_SEARCH_PROVIDERS"] = ",".join(defaults.search_providers)
    for name, flag in (
        ("arxiv", "ARXIV_SEARCH"),
        ("crossref", "CROSSREF_SEARCH"),
        ("pubmed", "PUBMED_SEARCH"),
    ):
        enabled = name in defaults.academic_providers
        overlay[f"DEEP_RESEARCH_{flag}"] = "true" if enabled else "false"
    return overlay


__all__ = [
    "SETTINGS_FILENAME",
    "CliSettings",
    "ModelChoice",
    "ResearchDefaults",
    "decode",
    "load",
    "runtime_environment",
    "save",
    "with_defaults",
    "with_language",
]
