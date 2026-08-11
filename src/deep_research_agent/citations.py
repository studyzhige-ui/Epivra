"""Deterministic compilation of stable source markers into numbered citations."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

from .state import SourceDocument


class CitationClosureError(ValueError):
    """A draft citation cannot be closed against the saved Source Corpus."""


_SOURCE_ID = r"[A-Za-z0-9][A-Za-z0-9_.:-]*"
_MARKER_TEXT = rf"\[\[cite:\s*{_SOURCE_ID}(?:\s*,\s*{_SOURCE_ID})*\s*\]\]"
_MARKER_RE = re.compile(
    rf"\[\[cite:\s*(?P<ids>{_SOURCE_ID}(?:\s*,\s*{_SOURCE_ID})*)\s*\]\]"
)
_MARKER_RUN_RE = re.compile(rf"{_MARKER_TEXT}(?:[ \t]*{_MARKER_TEXT})*")
_CITATION_LIKE_RE = re.compile(r"(?<![\w\]])\[(?:\d+\s*(?:,\s*\d+\s*)*)\](?!\s*[:(])")
_REFERENCE_HEADING_RE = re.compile(
    r"^\s{0,3}#{1,6}\s+(?:references|参考文献|参考资料)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_MALFORMED_MARKER_RE = re.compile(r"\[\[\s*cite\s*:", re.IGNORECASE)


def _validate_uncompiled_report(markdown: str) -> None:
    if _REFERENCE_HEADING_RE.search(markdown):
        raise CitationClosureError(
            "report must not contain a hand-written references section"
        )
    if _CITATION_LIKE_RE.search(_MARKER_RE.sub("", markdown)):
        raise CitationClosureError(
            "report contains hand-written numeric citations; use stable markers"
        )


@dataclass(frozen=True, slots=True)
class CitationRenderResult:
    """A rendered report and its deterministic citation closure."""

    markdown: str
    cited_source_ids: tuple[str, ...]
    numbering: Mapping[str, int]


def _reference_line(number: int, source: SourceDocument) -> str:
    title = " ".join(source.title.split())
    return f"[{number}] {title}. {source.url}"


class CitationRenderer:
    """Compile citation markers without making semantic evidence judgments.

    A single marker may contain one or more comma-separated source IDs::

        [[cite:src_a]]
        [[cite:src_a, src_b]]

    Adjacent markers are also collapsed into one ordered set. Number assignment
    follows first appearance in the final body, and repeated sources reuse their
    original number.
    """

    def __init__(self, *, references_heading: str = "## References") -> None:
        if not isinstance(references_heading, str) or not references_heading.strip():
            raise ValueError("references_heading must be a non-empty string")
        self.references_heading = references_heading.strip()

    def render(
        self,
        markdown: str,
        source_corpus: Mapping[str, SourceDocument],
    ) -> CitationRenderResult:
        if not isinstance(markdown, str):
            raise TypeError("markdown must be a string")
        _validate_uncompiled_report(markdown)

        numbering: dict[str, int] = {}
        cited_source_ids: list[str] = []

        def replace_run(match: re.Match[str]) -> str:
            run_ids: list[str] = []
            for marker in _MARKER_RE.finditer(match.group(0)):
                for source_id in (
                    item.strip() for item in marker.group("ids").split(",")
                ):
                    source = source_corpus.get(source_id)
                    if source is None:
                        raise CitationClosureError(
                            f"citation references unknown source {source_id}"
                        )
                    if source.source_id != source_id:
                        raise CitationClosureError(
                            f"Source Corpus key {source_id} does not match the source artifact"
                        )
                    if source_id not in numbering:
                        numbering[source_id] = len(numbering) + 1
                        cited_source_ids.append(source_id)
                    if source_id not in run_ids:
                        run_ids.append(source_id)

            numbers = sorted(numbering[source_id] for source_id in run_ids)
            return "[" + ", ".join(str(number) for number in numbers) + "]"

        rendered_body = _MARKER_RUN_RE.sub(replace_run, markdown)
        if _MALFORMED_MARKER_RE.search(rendered_body):
            raise CitationClosureError("report contains a malformed citation marker")

        if not cited_source_ids:
            return CitationRenderResult(
                markdown=rendered_body,
                cited_source_ids=(),
                numbering={},
            )

        references = [
            _reference_line(numbering[source_id], source_corpus[source_id])
            for source_id in cited_source_ids
        ]
        complete = (
            rendered_body.rstrip()
            + "\n\n"
            + self.references_heading
            + "\n\n"
            + "\n".join(references)
            + "\n"
        )
        return CitationRenderResult(
            markdown=complete,
            cited_source_ids=tuple(cited_source_ids),
            numbering=dict(numbering),
        )


def render_citations(
    markdown: str, source_corpus: Mapping[str, SourceDocument]
) -> CitationRenderResult:
    """Render with the default reference heading."""

    return CitationRenderer().render(markdown, source_corpus)


def extract_citation_ids(markdown: str) -> tuple[str, ...]:
    """Return stable source IDs in first-appearance order.

    This is also a syntax check used before publication to ensure a Writer did
    not cite a Source Corpus item that never entered the formal material chain.
    """

    if not isinstance(markdown, str):
        raise TypeError("markdown must be a string")
    _validate_uncompiled_report(markdown)
    source_ids: list[str] = []
    for marker in _MARKER_RE.finditer(markdown):
        for source_id in (item.strip() for item in marker.group("ids").split(",")):
            if source_id not in source_ids:
                source_ids.append(source_id)
    without_valid_markers = _MARKER_RE.sub("", markdown)
    if _MALFORMED_MARKER_RE.search(without_valid_markers):
        raise CitationClosureError("report contains a malformed citation marker")
    return tuple(source_ids)


def citation_marker_signature(
    markdown: str,
) -> tuple[tuple[int, tuple[str, ...]], ...]:
    """Describe each marker and its position in the citation-free body.

    The signature changes when a marker is added, removed, regrouped, reordered,
    or moved to a different claim location.  It is a publication safety signal,
    not a semantic judgment about whether the new association is correct.
    """

    if not isinstance(markdown, str):
        raise TypeError("markdown must be a string")
    _validate_uncompiled_report(markdown)
    signature: list[tuple[int, tuple[str, ...]]] = []
    plain_position = 0
    previous_end = 0
    for marker in _MARKER_RE.finditer(markdown):
        plain_position += len(markdown[previous_end : marker.start()])
        source_ids = tuple(
            item.strip() for item in marker.group("ids").split(",")
        )
        signature.append((plain_position, source_ids))
        previous_end = marker.end()
    without_valid_markers = _MARKER_RE.sub("", markdown)
    if _MALFORMED_MARKER_RE.search(without_valid_markers):
        raise CitationClosureError("report contains a malformed citation marker")
    return tuple(signature)


__all__ = [
    "CitationClosureError",
    "CitationRenderResult",
    "CitationRenderer",
    "citation_marker_signature",
    "extract_citation_ids",
    "render_citations",
]
