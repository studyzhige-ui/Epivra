"""Keyboard interaction, with one navigation contract for every page.

Consistency matters more than which key does what, so the rules are fixed here
rather than chosen per page:

* **↑↓** move, **Enter** confirms.
* **Esc** goes back one level, and every menu also carries an explicit "back"
  entry -- discoverability for anyone who does not know Esc works.
* **Ctrl-C** interrupts the long-running thing, never the whole product; the
  workspace decides what to do with it.
* **q** is reserved for the report pager and used nowhere else.

Every prompt returns ``None`` for "go back", so callers handle cancellation the
same way whether the user pressed Esc or chose the back entry.
"""

from __future__ import annotations

from collections.abc import Sequence

import questionary
from prompt_toolkit.styles import Style

#: Muted, single-accent styling.  A prompt that colours every element competes
#: with the content it is asking about.
STYLE = Style(
    [
        ("qmark", "bold"),
        ("question", "bold"),
        ("pointer", "bold"),
        ("highlighted", "bold reverse"),
        ("selected", "noreverse"),
        ("answer", "nobold"),
        ("instruction", "fg:#808080"),
    ]
)

BACK = "__back__"


def ask_text(message: str, *, default: str = "", multiline: bool = False) -> str | None:
    """Free text.  ``None`` means the user backed out."""

    answer = questionary.text(
        message, default=default, multiline=multiline, style=STYLE
    ).ask()
    return None if answer is None else str(answer).strip()


def ask_secret(message: str) -> str | None:
    """A credential.  Never echoed, never placed in shell history."""

    answer = questionary.password(message, style=STYLE).ask()
    return None if answer is None else str(answer).strip()


def choose(
    message: str,
    options: Sequence[tuple[str, str]],
    *,
    back_label: str = "",
    default: str = "",
) -> str | None:
    """One choice from ``(key, label)`` pairs.

    ``back_label`` adds an explicit back entry, so a user who never learns Esc is
    not trapped.  Returns ``None`` for either route out.
    """

    choices = [questionary.Choice(title=label, value=key) for key, label in options]
    if back_label:
        choices.append(questionary.Choice(title=back_label, value=BACK))
    answer = questionary.select(
        message,
        choices=choices,
        style=STYLE,
        default=default or None,
        instruction="↑↓ 选择 · Enter 确认 · Esc 返回",
        use_shortcuts=False,
    ).ask()
    if answer is None or answer == BACK:
        return None
    return str(answer)


def choose_many(
    message: str,
    options: Sequence[tuple[str, str, bool]],
) -> tuple[str, ...] | None:
    """Zero or more from ``(key, label, preselected)``."""

    choices = [
        questionary.Choice(title=label, value=key, checked=checked)
        for key, label, checked in options
    ]
    answer = questionary.checkbox(
        message,
        choices=choices,
        style=STYLE,
        instruction="↑↓ 移动 · 空格 选择 · Enter 确认",
    ).ask()
    return None if answer is None else tuple(str(item) for item in answer)


def confirm_destructive(message: str, *, keep: str, destroy: str) -> bool:
    """A deliberately asymmetric confirmation for irreversible actions.

    The safe option is first and selected by default, and the destructive one is
    spelled out rather than being a bare "yes" -- a reflexive Enter must not
    delete a study.
    """

    answer = questionary.select(
        message,
        choices=[
            questionary.Choice(title=keep, value=False),
            questionary.Choice(title=destroy, value=True),
        ],
        style=STYLE,
        instruction="↑↓ 选择 · Enter 确认",
    ).ask()
    return bool(answer)


__all__ = [
    "BACK",
    "STYLE",
    "ask_secret",
    "ask_text",
    "choose",
    "choose_many",
    "confirm_destructive",
]
