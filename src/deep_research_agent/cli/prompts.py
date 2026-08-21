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

Every prompt is a coroutine, and that is not a style choice.  questionary's
synchronous ``ask()`` calls ``asyncio.run()`` internally, so it cannot be used
from inside a running loop -- and the workspace runs inside one, because the
service it drives is async.  ``ask_async()`` is the same prompt on the loop that
is already running.

Every prompt also erases itself once answered.  A selection is not a record: the
first run left a wall of ``? 模型厂商 DeepSeek`` lines behind it that read as a
debug trace and buried the outcome.  ``erase_when_done`` is prompt_toolkit's own
mechanism for this -- reachable through questionary because ``select`` forwards
unknown keyword arguments to ``Application`` and ``text`` forwards them to
``PromptSession`` -- so nothing here reimplements terminal control.
"""

from __future__ import annotations

import asyncio
import getpass
from collections.abc import Mapping, Sequence

import questionary
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
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

INSTRUCTION = "↑↓ 选择 · Enter 确认 · Esc 返回"


def _escape_bindings() -> KeyBindings:
    """Bind Escape to "go back", which questionary does not do on its own.

    questionary binds Ctrl-C and Ctrl-Q and nothing else, so the "Esc 返回" this
    interface promises did precisely nothing -- a navigation contract that lies
    is worse than no contract.  Exiting with no result maps onto the ``None``
    every caller already treats as "the user backed out".

    Not eager, deliberately: an arrow key arrives as an escape sequence, and an
    eager binding on Escape would swallow it.  prompt_toolkit waits out its
    flush timeout before deciding a lone Escape really was alone.
    """

    bindings = KeyBindings()

    @bindings.add(Keys.Escape, eager=False)
    def _back(event: object) -> None:
        event.app.exit()  # type: ignore[attr-defined]

    return bindings


def _allow_escape(question: questionary.Question) -> questionary.Question:
    """Attach the Escape binding to a prompt that builds its own key bindings."""

    bindings = getattr(question.application, "key_bindings", None)
    if isinstance(bindings, KeyBindings):

        @bindings.add(Keys.Escape, eager=False)
        def _back(event: object) -> None:
            event.app.exit()  # type: ignore[attr-defined]

    return question


async def ask_text(
    message: str, *, default: str = "", multiline: bool = False
) -> str | None:
    """Free text.  ``None`` means the user backed out."""

    question = questionary.text(
        message,
        default=default,
        multiline=multiline,
        style=STYLE,
        erase_when_done=True,
        # Multiline input submits with Esc-then-Enter, so Escape cannot also mean
        # "go back" there.
        **({} if multiline else {"key_bindings": _escape_bindings()}),
    )
    answer = await question.ask_async()
    return None if answer is None else str(answer).strip()


async def ask_secret(message: str) -> str | None:
    """A credential, read with nothing at all echoed.

    Not questionary's password prompt: that masks each character with ``*``, which
    still displays the key's length and reads to a user as "my key is on screen".
    ``getpass`` echoes nothing whatsoever, which is what the interface promises.
    It is blocking, so it runs in a thread rather than stalling the event loop.

    Returns ``None`` only when there is no way to read at all; an empty string is
    a real answer ("the user pressed Enter") and the caller decides what it means.
    """

    def read() -> str | None:
        try:
            return getpass.getpass(f"  {message}: ")
        except (EOFError, KeyboardInterrupt):
            return None
        except (OSError, getpass.GetPassWarning):  # pragma: no cover - no tty
            return input(f"  {message}（注意：输入会显示）: ")

    answer = await asyncio.to_thread(read)
    return None if answer is None else answer.strip()


async def choose(
    message: str,
    options: Sequence[tuple[str, str]],
    *,
    back_label: str = "",
    default: str = "",
    disabled: Mapping[str, str] | None = None,
) -> str | None:
    """One choice from ``(key, label)`` pairs.

    ``back_label`` adds an explicit back entry, so a user who never learns Esc is
    not trapped.  Returns ``None`` for either route out.

    ``disabled`` maps a key to the reason it cannot be chosen.  Showing an action
    greyed out with its reason beats hiding it: the user learns the action exists
    and what would unlock it, and the menu stays the same shape between states.
    """

    blocked = disabled or {}
    choices = [
        questionary.Choice(
            title=label, value=key, disabled=blocked.get(key) or None
        )
        for key, label in options
    ]
    if back_label:
        choices.append(questionary.Choice(title=back_label, value=BACK))
    question = _allow_escape(
        questionary.select(
            message,
            choices=choices,
            style=STYLE,
            default=default or None,
            instruction=INSTRUCTION,
            use_shortcuts=False,
            erase_when_done=True,
        )
    )
    answer = await question.ask_async()
    if answer is None or answer == BACK:
        return None
    return str(answer)


async def choose_many(
    message: str,
    options: Sequence[tuple[str, str, bool]],
) -> tuple[str, ...] | None:
    """Zero or more from ``(key, label, preselected)``."""

    choices = [
        questionary.Choice(title=label, value=key, checked=checked)
        for key, label, checked in options
    ]
    question = _allow_escape(
        questionary.checkbox(
            message,
            choices=choices,
            style=STYLE,
            instruction="↑↓ 移动 · 空格 选择 · Enter 确认 · Esc 返回",
            erase_when_done=True,
        )
    )
    answer = await question.ask_async()
    return None if answer is None else tuple(str(item) for item in answer)


async def confirm_destructive(message: str, *, keep: str, destroy: str) -> bool:
    """A deliberately asymmetric confirmation for irreversible actions.

    The safe option is first and selected by default, and the destructive one is
    spelled out rather than being a bare "yes" -- a reflexive Enter must not
    delete a study.  Escape is not bound here: backing out of a confirmation is
    what the first option already is.
    """

    answer = await questionary.select(
        message,
        choices=[
            questionary.Choice(title=keep, value=False),
            questionary.Choice(title=destroy, value=True),
        ],
        style=STYLE,
        instruction="↑↓ 选择 · Enter 确认",
        erase_when_done=True,
    ).ask_async()
    return bool(answer)


__all__ = [
    "BACK",
    "INSTRUCTION",
    "STYLE",
    "ask_secret",
    "ask_text",
    "choose",
    "choose_many",
    "confirm_destructive",
]
