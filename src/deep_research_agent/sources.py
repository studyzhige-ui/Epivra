"""Source identity, quote anchors, and the two structured artifact bodies.

Most artifact bodies are prose, so they need no schema.  Two are structured
because their meaning is mechanically checkable, and checking it is the whole
point: a :class:`SourceSnapshotBody` records where exact text came from, and a
:class:`MaterialBody` records a curated statement together with the quotes that
must actually support it.

Anchors are verified against saved text, never against a live URL.  A page that
changed after it was read cannot silently repair a citation.

This module is pure domain logic and the lowest layer of the package: it must
not import providers, HTTP clients, or database drivers.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from urllib.parse import parse_qsl, urlsplit, urlunsplit

#: Query parameters that carry credentials.  A URL holding one of these is
#: refused outright rather than stored and later replayed in a References list.
_SENSITIVE_QUERY_NAMES = frozenset(
    {
        "access_token",
        "api_key",
        "apikey",
        "auth",
        "authorization",
        "credential",
        "key",
        "password",
        "sig",
        "signature",
        "token",
        "x-amz-credential",
        "x-amz-signature",
        "x-goog-credential",
        "x-goog-signature",
    }
)


class ArtifactValidationError(ValueError):
    """A formal artifact cannot be trusted as constructed."""


def _require_text(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ArtifactValidationError(f"{label} must be a non-empty string")
    return value.strip()


def _canonical_json(payload: object) -> str:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def canonical_url(url: str) -> str:
    """Return a conservative public URL identity without a document fragment."""

    value = _require_text(url, "url")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ArtifactValidationError("url must not contain control characters")
    parts = urlsplit(value)
    if parts.scheme.casefold() not in {"http", "https"} or not parts.hostname:
        raise ArtifactValidationError("url must be a public HTTP or HTTPS URL")
    if parts.username or parts.password:
        raise ArtifactValidationError("url must not contain credentials")
    hostname = parts.hostname.casefold().rstrip(".")
    if hostname == "localhost" or hostname.endswith(".localhost"):
        raise ArtifactValidationError("url must not identify a local host")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise ArtifactValidationError("url must not identify a private IP address")
    if any(
        key.casefold() in _SENSITIVE_QUERY_NAMES for key, _ in parse_qsl(parts.query)
    ):
        raise ArtifactValidationError("url query appears to contain a credential")
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), parts.path, parts.query, "")
    )


#: Prefix marking a source that came from the user's own corpus rather than the
#: web.  The reference is kept **relative to the corpus root**: an absolute path
#: would put the user's directory layout into an artifact body and then into the
#: published reference list, which is a disclosure the user never asked for.
LOCAL_SCHEME = "local:"


def canonical_local_ref(value: str) -> str:
    """Return a corpus-relative identity for a file the user supplied.

    Deliberately *not* folded into :func:`canonical_url`.  The two guard against
    different attacks -- a web URL must not reach a private address, a local path
    must not escape the granted corpus -- and a single validator trying to do both
    would weaken each.  Keeping them apart also means the web checks cannot be
    bypassed by dressing a request up as a local read.

    Shape only.  Whether the path resolves inside the real corpus root, symlinks
    included, is enforced by the reader, which is the component that knows the
    root and can touch the filesystem.
    """

    text = _require_text(value, "local source reference")
    body = text[len(LOCAL_SCHEME):] if text.startswith(LOCAL_SCHEME) else text
    if any(ord(character) < 32 or ord(character) == 127 for character in body):
        raise ArtifactValidationError(
            "local source reference must not contain control characters"
        )
    normalised = body.replace("\\", "/")
    if normalised.startswith("/"):
        # Stripping the slash would silently reinterpret an absolute path as a
        # relative one -- accepting a reference the caller did not write.
        raise ArtifactValidationError(
            "local source reference must be relative to the corpus root, not absolute"
        )
    normalised = normalised.strip("/")
    if not normalised:
        raise ArtifactValidationError("local source reference must name a file")
    segments = [segment for segment in normalised.split("/") if segment != "."]
    if any(segment == ".." for segment in segments):
        raise ArtifactValidationError(
            "local source reference must not climb out of the corpus with '..'"
        )
    if not segments:
        raise ArtifactValidationError("local source reference must name a file")
    if ":" in segments[0]:
        # A Windows drive letter makes the reference absolute, which both leaks
        # the layout and escapes the root.
        raise ArtifactValidationError(
            "local source reference must be relative to the corpus root"
        )
    return LOCAL_SCHEME + "/".join(segments)


def source_locator(value: str) -> str:
    """Canonical identity for any source, web or local, dispatched by scheme."""

    text = _require_text(value, "source locator")
    if text.startswith(LOCAL_SCHEME):
        return canonical_local_ref(text)
    return canonical_url(text)


def is_local_source(value: str) -> bool:
    """Whether a canonical locator names the user's corpus rather than the web."""

    return isinstance(value, str) and value.startswith(LOCAL_SCHEME)


def content_digest(content: str) -> str:
    """Hash exact saved content; whitespace is evidence and is not normalized."""

    if not isinstance(content, str) or not content:
        raise ArtifactValidationError("source content must not be empty")
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _require_content_hash(value: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ArtifactValidationError(
            "body content_hash must be a lowercase SHA-256 digest"
        )
    return value


@dataclass(frozen=True, slots=True)
class BodyRef:
    """A durable reference to one exact immutable UTF-8 body."""

    content_hash: str
    char_count: int

    def __post_init__(self) -> None:
        _require_content_hash(self.content_hash)
        if (
            isinstance(self.char_count, bool)
            or not isinstance(self.char_count, int)
            or self.char_count < 1
        ):
            raise ArtifactValidationError("body char_count must be a positive integer")

    @classmethod
    def from_content(cls, content: str) -> BodyRef:
        """Build the canonical reference for exact text."""

        return cls(content_hash=content_digest(content), char_count=len(content))

    def as_json(self) -> Mapping[str, object]:
        return {"hash": self.content_hash, "chars": self.char_count}

    @classmethod
    def from_json(cls, value: Mapping[str, object]) -> BodyRef:
        return cls(
            content_hash=str(value["hash"]), char_count=int(value["chars"])  # type: ignore[arg-type]
        )


@dataclass(frozen=True, slots=True)
class TextLocator:
    """An end-exclusive character range in exact saved text."""

    start: int
    end: int

    def __post_init__(self) -> None:
        for name in ("start", "end"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise ArtifactValidationError(f"locator {name} must be an integer")
        if self.start < 0 or self.end <= self.start:
            raise ArtifactValidationError(
                "locator must be a non-empty, end-exclusive character range"
            )

    def __str__(self) -> str:
        return f"chars:{self.start}-{self.end}"


@dataclass(frozen=True, slots=True)
class SourceAnchor:
    """A source-faithful quote and its exact location in one source snapshot."""

    source_ref: str
    exact_quote: str
    locator: TextLocator

    def __post_init__(self) -> None:
        _require_text(self.source_ref, "anchor source_ref")
        if not isinstance(self.exact_quote, str) or not self.exact_quote:
            raise ArtifactValidationError("anchor exact_quote must not be empty")
        if not isinstance(self.locator, TextLocator):
            raise ArtifactValidationError("anchor locator must be a TextLocator")

    @property
    def identity(self) -> tuple[str, int, int, str]:
        """Stable ordering key so anchor order never changes material identity."""

        return (self.source_ref, self.locator.start, self.locator.end, self.exact_quote)

    def as_json(self) -> Mapping[str, object]:
        return {
            "source": self.source_ref,
            "quote": self.exact_quote,
            "start": self.locator.start,
            "end": self.locator.end,
        }

    @classmethod
    def from_json(cls, value: Mapping[str, object]) -> SourceAnchor:
        return cls(
            source_ref=str(value["source"]),
            exact_quote=str(value["quote"]),
            locator=TextLocator(start=int(value["start"]), end=int(value["end"])),  # type: ignore[arg-type]
        )


def locate_quote(text: str, exact_quote: str) -> TextLocator:
    """Locate the first occurrence of an exact quote in saved text.

    The first, because :class:`SourceAnchor` records character offsets and has no
    field for "which occurrence" -- the offsets are what
    :func:`validate_anchor` checks, so a quote appearing twice is anchored
    unambiguously either way.
    """

    if not isinstance(exact_quote, str) or not exact_quote:
        raise ArtifactValidationError("exact_quote must not be empty")

    start = text.find(exact_quote)
    if start < 0:
        raise ArtifactValidationError("the quote is not present in the saved text")
    return TextLocator(start=start, end=start + len(exact_quote))


def validate_anchor(anchor: SourceAnchor, text: str) -> None:
    """Require an anchor to select its exact quote from the saved source text."""

    if anchor.locator.end > len(text):
        raise ArtifactValidationError("anchor locator exceeds the saved source body")
    located = text[anchor.locator.start : anchor.locator.end]
    if located != anchor.exact_quote:
        raise ArtifactValidationError(
            "anchor quote does not match the saved text at its locator"
        )


@dataclass(frozen=True, slots=True)
class SourceSnapshotBody:
    """The body of a ``source_snapshot`` artifact: where exact text came from.

    The text itself stays in the content store under ``text_ref``, so a large
    page costs one small artifact body plus one shared blob.
    """

    url: str
    title: str
    text_ref: BodyRef
    fetched_at: str = ""
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "url", source_locator(self.url))
        _require_text(self.title, "source title")
        if not isinstance(self.text_ref, BodyRef):
            raise ArtifactValidationError("source text_ref must be a BodyRef")
        if not isinstance(self.fetched_at, str):
            raise ArtifactValidationError("fetched_at must be a string")
        if not isinstance(self.metadata, Mapping) or any(
            not isinstance(key, str) or not isinstance(value, str)
            for key, value in self.metadata.items()
        ):
            raise ArtifactValidationError("source metadata must map strings to strings")

    def encode(self) -> str:
        """Canonical body text; identical sources produce an identical artifact."""

        return _canonical_json(
            {
                "url": self.url,
                "title": self.title.strip(),
                "text": self.text_ref.as_json(),
                "fetched_at": self.fetched_at,
                "metadata": dict(sorted(self.metadata.items())),
            }
        )

    @classmethod
    def decode(cls, body: str) -> SourceSnapshotBody:
        value = json.loads(body)
        return cls(
            url=str(value["url"]),
            title=str(value["title"]),
            text_ref=BodyRef.from_json(value["text"]),
            fetched_at=str(value.get("fetched_at", "")),
            metadata={
                str(key): str(item)
                for key, item in dict(value.get("metadata", {})).items()
            },
        )


@dataclass(frozen=True, slots=True)
class MaterialBody:
    """The body of a ``material`` artifact: a curated claim and its support.

    ``boundaries`` is not decoration.  It records what the material does *not*
    establish -- population, period, comparator, causal strength -- which is what
    stops a downstream writer from quietly widening a narrow finding.
    """

    content: str
    boundaries: str
    anchors: tuple[SourceAnchor, ...]

    def __post_init__(self) -> None:
        _require_text(self.content, "material content")
        _require_text(self.boundaries, "material boundaries")
        if not self.anchors:
            raise ArtifactValidationError(
                "curated material requires at least one SourceAnchor"
            )
        ordered = tuple(sorted(self.anchors, key=lambda anchor: anchor.identity))
        if ordered != tuple(self.anchors):
            raise ArtifactValidationError(
                "material anchors must be sorted; use MaterialBody.create()"
            )

    @classmethod
    def create(
        cls, *, content: str, boundaries: str, anchors: Sequence[SourceAnchor]
    ) -> MaterialBody:
        """Build a material body with anchors in canonical order."""

        return cls(
            content=content,
            boundaries=boundaries,
            anchors=tuple(sorted(anchors, key=lambda anchor: anchor.identity)),
        )

    @property
    def source_refs(self) -> tuple[str, ...]:
        """Distinct source snapshots this material depends on, in sorted order.

        These are exactly the artifact's parent refs, so lineage is derived from
        the evidence rather than restated by hand.
        """

        return tuple(sorted({anchor.source_ref for anchor in self.anchors}))

    def encode(self) -> str:
        """Canonical body text; identical materials produce an identical artifact."""

        return _canonical_json(
            {
                "content": self.content.strip(),
                "boundaries": self.boundaries.strip(),
                "anchors": [anchor.as_json() for anchor in self.anchors],
            }
        )

    @classmethod
    def decode(cls, body: str) -> MaterialBody:
        value = json.loads(body)
        return cls.create(
            content=str(value["content"]),
            boundaries=str(value["boundaries"]),
            anchors=tuple(
                SourceAnchor.from_json(item) for item in value["anchors"]
            ),
        )


__all__ = [
    "ArtifactValidationError",
    "BodyRef",
    "LOCAL_SCHEME",
    "MaterialBody",
    "SourceAnchor",
    "SourceSnapshotBody",
    "TextLocator",
    "canonical_local_ref",
    "canonical_url",
    "content_digest",
    "is_local_source",
    "source_locator",
    "locate_quote",
    "validate_anchor",
]
