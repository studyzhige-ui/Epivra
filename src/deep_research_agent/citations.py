"""Deterministic citation closure and reference rendering.

The Author never writes a number.  It embeds opaque handles the runtime handed
it -- ``[[cite:h3]]`` -- and this module resolves every handle, numbers them by
first appearance, and renders the References section.  That split exists because
numbering is mechanical while *choosing* what to cite is semantic, and mixing
the two is how reports end up with citations that renumber themselves.

The renderer fails closed.  An unknown handle, a hand-written ``[1]``, or a
pre-existing References heading aborts publication rather than producing a
plausible-looking document with an unverifiable claim in it.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .sources import MaterialBody, SourceAnchor, SourceSnapshotBody

#: Handles are runtime-issued and deliberately opaque, so a model cannot derive
#: one from a source it merely knows about.
_HANDLE = r"h[0-9]+"
_MARKER_RE = re.compile(rf"\[\[cite:\s*({_HANDLE})\s*\]\]")
_MALFORMED_MARKER_RE = re.compile(r"\[\[\s*cite\s*:", re.IGNORECASE)
#: A bare ``[1]`` or ``[2, 3]`` that is not a link or footnote definition.
_MANUAL_NUMERIC_RE = re.compile(r"(?<![\w\]])\[(?:\d+\s*(?:,\s*\d+\s*)*)\](?!\s*[:(])")
_REFERENCE_HEADING_RE = re.compile(
    r"^\s{0,3}#{1,6}\s*(references|参考(?:文献|资料))\s*$",
    re.IGNORECASE | re.MULTILINE,
)


class CitationClosureError(ValueError):
    """A report cannot be published with its citations as written."""


@dataclass(frozen=True, slots=True)
class CitationHandle:
    """One citable position: a material, the anchor used, and its source."""

    handle: str
    material_ref: str
    anchor: SourceAnchor
    source: SourceSnapshotBody

    def __post_init__(self) -> None:
        if not re.fullmatch(_HANDLE, self.handle):
            raise CitationClosureError(f"malformed citation handle {self.handle!r}")


@dataclass(frozen=True, slots=True)
class RenderedCitations:
    """The publishable report plus the closure that justified publishing it."""

    markdown: str
    references: tuple[str, ...]
    used_material_refs: tuple[str, ...]


def build_handles(
    materials: Mapping[str, MaterialBody],
    sources: Mapping[str, SourceSnapshotBody],
) -> tuple[CitationHandle, ...]:
    """Issue one stable handle per (material, anchor) pair a role may cite.

    Ordering is by material ref then anchor identity, so the same evidence set
    always yields the same handles regardless of dictionary iteration order.
    """

    handles: list[CitationHandle] = []
    for material_ref in sorted(materials):
        body = materials[material_ref]
        for anchor in body.anchors:
            source = sources.get(anchor.source_ref)
            if source is None:
                raise CitationClosureError(
                    f"material {material_ref} anchors unknown source "
                    f"{anchor.source_ref}"
                )
            handles.append(
                CitationHandle(
                    handle=f"h{len(handles) + 1}",
                    material_ref=material_ref,
                    anchor=anchor,
                    source=source,
                )
            )
    return tuple(handles)


def extract_handles(markdown: str) -> tuple[str, ...]:
    """Return cited handles in first-appearance order, without duplicates."""

    seen: list[str] = []
    for match in _MARKER_RE.finditer(markdown):
        handle = match.group(1)
        if handle not in seen:
            seen.append(handle)
    return tuple(seen)


def _first_malformed_marker(markdown: str) -> str:
    """Quote the first ``[[cite:`` opening that is not a well-formed marker.

    "There is a malformed marker somewhere" is not actionable in a
    forty-thousand-character report carrying a hundred markers, and a role that
    cannot locate the fault cannot fix it: one live Author was told exactly that,
    corrected nothing, and lost the run on its second attempt.  Everything else
    the validators report is something the role can act on from the message
    alone, so this one has to be too.
    """

    well_formed = [match.span() for match in _MARKER_RE.finditer(markdown)]
    for opening in _MALFORMED_MARKER_RE.finditer(markdown):
        start = opening.start()
        if any(begin <= start < end for begin, end in well_formed):
            continue
        excerpt = markdown[start : start + 60].replace("\n", " ")
        return excerpt
    return ""


def citation_syntax_problem(markdown: str) -> str:
    """Describe the first citation-syntax fault in ``markdown``, or "".

    Publication runs the same three checks and raises, because a report whose
    markers cannot be resolved must never reach a reader.  But failing there
    means discarding a report that was already written, reviewed and approved --
    a live run lost one that way, at the last step, with no path back.

    Every fault here is mechanical and fixable from its own description, so the
    Author's submission validator calls this and hands the text back as a
    correction.  Exposing one definition rather than two keeps the correctable
    check and the fail-closed check from drifting apart, which is the only way
    the guarantee at publication stays a genuine last resort instead of a
    second, slightly different rule.
    """

    if len(_MALFORMED_MARKER_RE.findall(markdown)) != len(
        _MARKER_RE.findall(markdown)
    ):
        excerpt = _first_malformed_marker(markdown)
        where = f"第一处出现在这里：「{excerpt}」" if excerpt else ""
        return (
            "报告里有格式错误的引用标记；每个标记必须严格写成 [[cite:<handle>]]，"
            "不能加空格、不能一个标记里放多个 handle、不能漏掉右侧的 ]]。"
            f"{where}"
        )
    manual = _MANUAL_NUMERIC_RE.search(markdown)
    if manual is not None:
        return (
            f"报告里有手写的数字引用 {manual.group(0)!r}；编号由渲染器统一分配，"
            "正文只能使用 [[cite:<handle>]]"
        )
    if _REFERENCE_HEADING_RE.search(markdown) is not None:
        return "报告里已经有参考资料小节；该小节在发布时自动生成，不要自己写"
    return ""


def _reject_hand_written_citations(markdown: str) -> None:
    problem = citation_syntax_problem(markdown)
    if problem:
        raise CitationClosureError(problem)


def _reference_line(number: int, source: SourceSnapshotBody) -> str:
    # A reference carries the day a source was captured, not the microsecond:
    # the timestamp exists so a reader can judge currency, and full ISO
    # precision only obscures that.
    captured = source.fetched_at.strip()[:10]
    published = f" ({captured})" if captured else ""
    return f"{number}. {source.title}{published}. {source.url}"


#: A run of adjacent rendered citations, e.g. ``[1][1][2]``.
_ADJACENT_RUN_RE = re.compile(r"(?:\[\d+\]){2,}")
_NUMBER_RE = re.compile(r"\[(\d+)\]")


def _collapse_adjacent(markdown: str) -> str:
    """Merge neighbouring citations into one bracket.

    Several materials often anchor the same canonical source, so independent
    substitution yields ``[1][1][1]``, which reads as a defect to anyone
    skimming the report.  Collapsing runs is presentation only: it drops no
    citation, because the material-level provenance lives in the artifact
    lineage rather than in the rendered digits.
    """

    def merge(match: re.Match[str]) -> str:
        seen: list[str] = []
        for number in _NUMBER_RE.findall(match.group(0)):
            if number not in seen:
                seen.append(number)
        return f"[{', '.join(seen)}]"

    return _ADJACENT_RUN_RE.sub(merge, markdown)


def render_citations(
    markdown: str,
    handles: Sequence[CitationHandle],
    *,
    evidence_set: Sequence[str] | None = None,
    heading: str = "## 参考资料",
) -> RenderedCitations:
    """Resolve every marker, number by first appearance, and append References.

    ``evidence_set`` is the active material set the report was commissioned
    against.  Passing it makes citing a withdrawn or superseded material a
    publication failure rather than a silent inconsistency.
    """

    _reject_hand_written_citations(markdown)

    by_handle = {item.handle: item for item in handles}
    if len(by_handle) != len(handles):
        raise CitationClosureError("citation handles must be unique")
    allowed = None if evidence_set is None else frozenset(evidence_set)

    cited = extract_handles(markdown)
    if not cited:
        raise CitationClosureError(
            "the report cites no evidence; every publishable report must ground "
            "its verifiable claims"
        )

    numbering: dict[str, int] = {}
    references: list[str] = []
    used_materials: list[str] = []
    for handle in cited:
        entry = by_handle.get(handle)
        if entry is None:
            raise CitationClosureError(
                f"citation handle {handle!r} does not exist in the current "
                "evidence set"
            )
        if allowed is not None and entry.material_ref not in allowed:
            raise CitationClosureError(
                f"citation handle {handle!r} resolves to material "
                f"{entry.material_ref}, which is not in the current evidence set"
            )
        # Handles pointing at the same canonical source share a display number so
        # a reader sees one entry, while each handle keeps its own anchor for audit.
        if entry.source.url not in numbering:
            numbering[entry.source.url] = len(numbering) + 1
            references.append(
                _reference_line(numbering[entry.source.url], entry.source)
            )
        if entry.material_ref not in used_materials:
            used_materials.append(entry.material_ref)

    def substitute(match: re.Match[str]) -> str:
        return f"[{numbering[by_handle[match.group(1)].source.url]}]"

    body = _MARKER_RE.sub(substitute, markdown)
    body = _collapse_adjacent(body).rstrip()
    rendered = f"{body}\n\n{heading}\n\n" + "\n".join(references) + "\n"
    return RenderedCitations(
        markdown=rendered,
        references=tuple(references),
        used_material_refs=tuple(sorted(used_materials)),
    )


__all__ = [
    "CitationClosureError",
    "CitationHandle",
    "RenderedCitations",
    "build_handles",
    "citation_syntax_problem",
    "extract_handles",
    "render_citations",
]
