"""An append-only record of what the workspace did, separate from what it drew.

The interface replaces the screen as the user moves, which is right -- navigation
is not a record worth keeping.  But some of what scrolled past *was* worth
keeping: which vendor was validated and when, which model a study was assigned,
which research was deleted.  Terminal scrollback is the wrong place for that.  It
is lost on clear, on resize, on closing the window, and it is not readable by
anything but a human squinting at it.

So outcomes go here instead: one JSON object per line, appended, never rewritten.
The operation ledger already records every paid provider call; this covers the
interface actions the ledger has no reason to know about.

**Never a credential.** Callers pass provider names and outcomes; the key itself
has no field to travel in, and a failure records the reason, not the input.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from .paths import journal_file

#: Field names that must never carry a secret, whatever a caller intends.
_FORBIDDEN = ("key", "secret", "token", "password", "credential")


def record(kind: str, **fields: Any) -> None:
    """Append one outcome.  Best-effort: journalling must never break a session.

    A read-only home directory, a full disk or a locked file are all reasons to
    lose the record, and none of them are reasons to interrupt a user's research.
    """

    for name in fields:
        if any(hint in name.casefold() for hint in _FORBIDDEN):
            raise ValueError(f"journal field {name!r} could carry a credential")
    entry = {
        "at": datetime.now(UTC).isoformat(timespec="seconds"),
        "kind": kind,
        **fields,
    }
    try:
        path = journal_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
    except OSError:
        return


__all__ = ["record"]
