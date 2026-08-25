"""Shared terminal presentation: one console, one visual vocabulary.

Kept in one place so pages cannot drift into different idioms -- the failure mode
of a CLI grown page by page is that one screen uses a boxed panel, the next a bare
list, and a third an emoji, until the tool reads as several tools.

The style is a professional research instrument: a single brand header, status
glyphs rather than colour alone, generous whitespace, and dim text for anything
the reader does not need in order to act.  Colour is never the only carrier of
meaning, because terminals and colour vision both vary.

One rule governs what stays on screen:

    **Selection is transient.  Outcome is persistent.  State is always visible.**

Navigating is not a record worth keeping.  A first run that configured two models
and a search key left forty lines of ``? 模型厂商 DeepSeek`` behind it, which read
as a debug trace rather than a product, and buried the one line that mattered.  So
:func:`page` *replaces* the screen instead of appending to it, every page repaints
the state it is about, and an outcome travels to the next page as a receipt.  What
needs to survive the screen goes to the journal, not the scrollback.
"""

from __future__ import annotations

import sys
from collections.abc import Mapping, Sequence
from typing import IO

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

#: Terminal widths this layout must survive.  Anything narrower wraps rather
#: than being truncated into nonsense.
MIN_WIDTH = 60

#: Status glyphs.  Chosen so meaning survives a monochrome terminal.
GLYPH: Mapping[str, str] = {
    "done": "✓",
    "active": "●",
    "pending": "○",
    "blocked": "✗",
    "warn": "!",
    "info": "·",
}

STATE_GLYPH: Mapping[str, str] = {
    "clarification_requested": GLYPH["warn"],
    "awaiting_approval": GLYPH["active"],
    "researching": "◐",
    "published": GLYPH["done"],
    "halted": GLYPH["blocked"],
    # Blocked rather than pending: nothing the user does in this interface will
    # move it, so it must not look like something that resumes on its own.
    "needs_reconciliation": GLYPH["blocked"],
    "paused": GLYPH["pending"],
}


def console(file: IO[str] | None = None) -> Console:
    """One console for the process, or one over a given stream.

    ``soft_wrap`` is off so Rich wraps to the real terminal width; a fixed width
    would break the narrow-terminal requirement.

    ``file`` exists so tests can exercise the interface without writing to the
    terminal.  Passing a stream is also the honest way to keep test output clean:
    a decision test has no business painting a home screen.
    """

    return Console(highlight=False, emoji=False, file=file)


def is_interactive() -> bool:
    """Whether a human is on both ends of this process.

    Both directions matter: output redirected to a file must not carry interactive
    chrome, and input from a pipe must never reach a prompt that waits forever.
    """

    return sys.stdin.isatty() and sys.stdout.isatty()


def width(target: Console) -> int:
    return max(MIN_WIDTH, min(target.size.width, 120))


def clear(target: Console) -> None:
    """Hand the screen back before repainting.

    A no-op unless output is a real terminal, so a redirect, a pipe and the test
    suite all keep receiving plain text in the order it was written.
    """

    if target.is_terminal:
        target.clear()


def page(target: Console, *, brand: str = "", title: str = "") -> None:
    """Begin a page, replacing whatever the last one drew.

    Every screen in the workspace starts here.  That is what makes the terminal
    show *where the user is* rather than everywhere they have been.
    """

    clear(target)
    if brand:
        header(target, name=brand)
    if title:
        rule_title(target, title, spacer=bool(brand))


def header(target: Console, *, name: str) -> None:
    """The brand header, deliberately just the name.

    A tagline repeated at the top of every page is an advertisement to someone
    who has already bought the thing; the welcome belongs in the body of the home
    screen, once.
    """

    target.print(
        Panel(
            Text(name, style="bold"),
            width=width(target),
            border_style="dim",
            padding=(0, 2),
        )
    )


def rule_title(target: Console, title: str, *, spacer: bool = True) -> None:
    """A page title without a box; used inside the workspace for sub-pages."""

    if spacer:
        target.print()
    target.print(Text(title, style="bold"))
    target.print(Text("─" * min(width(target), 60), style="dim"))


def section(target: Console, title: str) -> None:
    """A group label inside a page, for state that has more than one part."""

    target.print()
    target.print(Text(f"  {title}", style="dim"))


def status_line(target: Console, glyph: str, text: str, *, style: str = "") -> None:
    line = Text(f"  {glyph} ", style=style or "default")
    line.append(text, style=style or "default")
    target.print(line)


def dim(target: Console, text: str) -> None:
    target.print(Text(f"  {text}", style="dim"))


def fields(target: Console, rows: Sequence[tuple[str, str]]) -> None:
    """Label/value pairs, aligned, no borders.

    A bordered table for six short values is visual noise, and horizontal rules
    break badly in a narrow terminal.
    """

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="dim", no_wrap=True)
    table.add_column(overflow="fold")
    for label, value in rows:
        table.add_row(label, value)
    target.print(table)


def timeline(target: Console, stages: Sequence[tuple[str, str]]) -> None:
    """Research progress as stages, each ``(state, label)``.

    A long study emits hundreds of log lines; a reader wants to know which phase
    it is in, not to follow every provider call.  The detailed log stays available
    behind --verbose.
    """

    for state, label in stages:
        glyph = GLYPH.get(state, GLYPH["info"])
        style = {
            "done": "green",
            "active": "bold",
            "pending": "dim",
            "blocked": "red",
        }.get(state, "")
        status_line(target, glyph, label, style=style)


def truncate(text: str, limit: int) -> str:
    """Shorten to fit, marking that something was cut."""

    collapsed = " ".join(text.split())
    return collapsed if len(collapsed) <= limit else collapsed[: limit - 1] + "…"


__all__ = [
    "GLYPH",
    "MIN_WIDTH",
    "STATE_GLYPH",
    "clear",
    "console",
    "dim",
    "fields",
    "header",
    "is_interactive",
    "page",
    "rule_title",
    "section",
    "status_line",
    "timeline",
    "truncate",
    "width",
]
