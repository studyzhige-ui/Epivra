"""Shared terminal presentation: one console, one visual vocabulary.

Kept in one place so pages cannot drift into different idioms -- the failure mode
of a CLI grown page by page is that one screen uses a boxed panel, the next a bare
list, and a third an emoji, until the tool reads as several tools.

The style is a professional research instrument: a single brand header, status
glyphs rather than colour alone, generous whitespace, and dim text for anything
the reader does not need in order to act.  Colour is never the only carrier of
meaning, because terminals and colour vision both vary.
"""

from __future__ import annotations

import sys
from collections.abc import Mapping, Sequence

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

#: Terminal widths this layout must survive.  Anything narrower wraps rather
#: than being truncated into nonsense.
MIN_WIDTH = 60
COMFORTABLE_WIDTH = 84

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
    "paused": GLYPH["pending"],
}


def console() -> Console:
    """One console for the process.

    ``soft_wrap`` is off so Rich wraps to the real terminal width; a fixed width
    would break the narrow-terminal requirement.
    """

    return Console(highlight=False, emoji=False)


def is_interactive() -> bool:
    """Whether a human is on both ends of this process.

    Both directions matter: output redirected to a file must not carry interactive
    chrome, and input from a pipe must never reach a prompt that waits forever.
    """

    return sys.stdin.isatty() and sys.stdout.isatty()


def width(target: Console) -> int:
    return max(MIN_WIDTH, min(target.size.width, 120))


def header(target: Console, *, name: str, tagline: str) -> None:
    """The brand header.  Shown by the workspace, never by a subcommand.

    A subcommand prints its own result; reprinting the product description on
    every invocation is noise for someone who ran ``doctor`` for the third time.
    """

    body = Text(name, style="bold")
    body.append("\n")
    body.append(tagline, style="dim")
    target.print(
        Panel(body, width=width(target), border_style="dim", padding=(0, 2))
    )


def rule_title(target: Console, title: str) -> None:
    """A page title without a box; used inside the workspace for sub-pages."""

    target.print()
    target.print(Text(title, style="bold"))
    target.print(Text("─" * min(width(target), 60), style="dim"))


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
    "COMFORTABLE_WIDTH",
    "GLYPH",
    "MIN_WIDTH",
    "STATE_GLYPH",
    "console",
    "dim",
    "fields",
    "header",
    "is_interactive",
    "rule_title",
    "status_line",
    "timeline",
    "truncate",
    "width",
]
