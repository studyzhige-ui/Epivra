"""Where configuration and studies live on disk.

One module owns these paths so the interactive workspace, the subcommands and the
tests cannot disagree about where a user's data is.

A project-local ``.env`` wins over the home directory: running inside a checkout
should use that checkout's configuration, while an installed command run from
anywhere still finds the user's own.
"""

from __future__ import annotations

from pathlib import Path

from .settings import SETTINGS_FILENAME

#: Everything a user accumulates: studies, preferences, and their credentials
#: when they are not working inside a project.
HOME = Path.home() / ".deep-research-agent"


def config_file() -> Path:
    """The ``.env`` holding credentials."""

    local = Path.cwd() / ".env"
    return local if local.is_file() else HOME / ".env"


def settings_file() -> Path:
    """Interface preferences and research defaults.

    Always in the home directory, unlike credentials: the interface language a
    person prefers follows them between projects, whereas an API key may well be
    project-specific.
    """

    return HOME / SETTINGS_FILENAME


def default_database() -> Path:
    """One database holding every study, since the stores are task-isolated."""

    return HOME / "tasks.sqlite3"


__all__ = ["HOME", "config_file", "default_database", "settings_file"]
