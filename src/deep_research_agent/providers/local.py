"""Reading the user's own corpus, under a root they granted.

The web reader's threat model is where a request goes; this one's is which bytes
come back.  A path arriving from a model is untrusted, so containment is checked
against the *resolved* root -- symlinks included -- because a link inside the
corpus pointing at ``~/.ssh`` would otherwise pass every textual check.

Identity stays **relative to the root**.  An absolute path would put the user's
directory layout into an artifact body and from there into the published
reference list, which is a disclosure nobody asked for.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path

from ..config import ConfigError
from ..sources import LOCAL_SCHEME, canonical_local_ref
from ..tools import ReadResult
from ._http import SourceReadError

#: Extensions read as text.  Anything else is refused by name rather than
#: decoded hopefully: a silently mis-decoded binary becomes "evidence" that
#: cannot be traced back to anything a human would recognise.
TEXT_SUFFIXES: frozenset[str] = frozenset(
    {".txt", ".md", ".markdown", ".csv", ".tsv", ".json", ".yaml", ".yml", ".html", ".htm"}
)
PDF_SUFFIXES: frozenset[str] = frozenset({".pdf"})


@dataclass(slots=True)
class LocalCorpusReader:
    """Reads files beneath one granted root, and nothing else.

    Constructed only when the Commission authorises ``user_files`` or
    ``local_only``; the permission itself is enforced by the caller, so this class
    is never the thing deciding whether local reading is allowed.
    """

    root: Path
    max_bytes: int = 8 * 1024 * 1024
    max_text_chars: int = 400_000
    max_pdf_pages: int = 200
    pdf_timeout_seconds: float = 30.0
    #: Injected so the PDF path is shared with the web reader rather than
    #: reimplemented; extraction stays in a killable subprocess either way.
    extract_pdf: object | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        resolved = Path(self.root).expanduser().resolve()
        if not resolved.is_dir():
            # A ConfigError rather than a bare ValueError because this is the
            # user's setting failing to hold, not a caller passing nonsense: they
            # granted a folder and it is no longer there, which an interface has
            # to be able to report instead of dying on.
            raise ConfigError(f"local corpus root is not a directory: {resolved}")
        self.root = resolved
        if self.max_bytes < 1 or self.max_text_chars < 1:
            raise ValueError("local reader limits must be positive")

    def resolve(self, reference: str) -> Path:
        """Resolve a corpus-relative reference, refusing anything outside the root.

        ``Path.resolve()`` follows symlinks, and the containment check runs on the
        result, so a link inside the corpus cannot be used to read outside it.
        """

        relative = canonical_local_ref(reference)[len(LOCAL_SCHEME) :]
        candidate = (self.root / relative).expanduser().resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise SourceReadError(
                "local source resolves outside the granted corpus root"
            )
        return candidate

    def listing(self, limit: int = 500) -> tuple[str, ...]:
        """Corpus-relative references for readable files, so a role can choose.

        A role cannot guess filenames, and inventing them would be authoring
        identity.  It selects from what this returns.
        """

        allowed = TEXT_SUFFIXES | PDF_SUFFIXES
        found: list[str] = []
        for path in sorted(self.root.rglob("*")):
            if len(found) >= limit:
                break
            if path.is_file() and path.suffix.casefold() in allowed:
                found.append(
                    LOCAL_SCHEME + path.relative_to(self.root).as_posix()
                )
        return tuple(found)

    async def read(self, url: str) -> ReadResult:
        """Read one corpus file into exact immutable text."""

        reference = canonical_local_ref(url)
        path = self.resolve(reference)
        if not path.is_file():
            raise SourceReadError(f"local source does not exist: {reference}")

        suffix = path.suffix.casefold()
        if suffix not in TEXT_SUFFIXES | PDF_SUFFIXES:
            raise SourceReadError(
                f"local source type {suffix or '(none)'} is not readable as text"
            )

        size = path.stat().st_size
        if size > self.max_bytes:
            raise SourceReadError("local source exceeds the configured read size")
        if size == 0:
            raise SourceReadError("local source is empty")

        body = await asyncio.to_thread(path.read_bytes)
        if suffix in PDF_SUFFIXES:
            if self.extract_pdf is None:
                raise SourceReadError("no PDF extractor is configured")
            declared, content = await asyncio.to_thread(
                self.extract_pdf,  # type: ignore[arg-type]
                body,
                max_pages=self.max_pdf_pages,
                max_text_chars=self.max_text_chars,
                timeout_seconds=self.pdf_timeout_seconds,
            )
            title = declared or path.name
        else:
            content = body.decode("utf-8", errors="replace").strip()
            title = path.name

        if not content:
            raise SourceReadError("local source returned no readable text")
        if len(content) > self.max_text_chars:
            raise SourceReadError("local source text exceeds the configured size")
        return ReadResult(title=title, url=reference, content=content)


__all__ = ["PDF_SUFFIXES", "TEXT_SUFFIXES", "LocalCorpusReader"]
