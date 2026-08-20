"""Per-invocation context: the smallest sufficient view for one role.

Every model call gets a freshly built private context.  Long-term continuity
comes from artifact references, not from a growing message thread, so no role
ever inherits another role's reasoning, tool traces, or scratch work.

Two properties matter more than convenience:

**Minimal but sufficient.**  Context is a finite attention budget, and recall
degrades as it fills.  A role receives the references it needs and hydrates
bodies on demand, rather than being handed the whole store.

**No silent truncation.**  When the necessary basis does not fit, the operation
raises :class:`ContextCapacityError` *before* the provider is called.  Dropping
counter-evidence to make a request fit would produce a confident report built on
a quietly narrowed evidence base -- the exact failure this architecture exists
to prevent.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from .artifact_store import SqliteArtifactStore
from .citations import CitationHandle, build_handles
from .contract import ResearchContract
from .sources import MaterialBody, SourceSnapshotBody


class ContextCapacityError(RuntimeError):
    """The basis a role needs cannot be expressed within the provider's limit."""


@dataclass(frozen=True, slots=True)
class MaterialView:
    """One material as a role sees it: claim, boundaries, and citable handles."""

    material_ref: str
    body: MaterialBody
    handles: tuple[CitationHandle, ...]

    def render(self, *, with_handles: bool) -> str:
        lines = [f"- {self.body.content}", f"  边界：{self.body.boundaries}"]
        for handle in self.handles:
            source = handle.source
            quote = handle.anchor.exact_quote
            excerpt = quote if len(quote) <= 220 else f"{quote[:217]}..."
            marker = f"[[cite:{handle.handle}]] " if with_handles else ""
            lines.append(f'  {marker}原文「{excerpt}」— {source.title}')
        return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class EvidenceView:
    """The current evidence set, projected once and shared by the roles that read it."""

    evidence_set_id: str
    materials: tuple[MaterialView, ...]
    sources: Mapping[str, SourceSnapshotBody] = field(default_factory=dict)

    @property
    def material_refs(self) -> tuple[str, ...]:
        return tuple(view.material_ref for view in self.materials)

    @property
    def handles(self) -> tuple[CitationHandle, ...]:
        return tuple(handle for view in self.materials for handle in view.handles)

    def render(self, *, with_handles: bool) -> str:
        if not self.materials:
            return "（当前证据集为空）"
        return "\n".join(view.render(with_handles=with_handles) for view in self.materials)

    def source_summary(self) -> str:
        lines = []
        for index, (ref, source) in enumerate(sorted(self.sources.items()), start=1):
            lines.append(f"{index}. {source.title} — {source.url}")
        return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class RoleContext:
    """One compiled invocation: what the role may read and how large it is."""

    role: str
    purpose: str
    body: str
    input_refs: tuple[str, ...]
    handles: tuple[CitationHandle, ...] = ()

    def __post_init__(self) -> None:
        if not self.body.strip():
            raise ContextCapacityError(f"{self.role} context is empty")

    @property
    def char_count(self) -> int:
        return len(self.body)

    @property
    def digest(self) -> str:
        """Exact identity of this invocation's basis.

        The operation ledger replays a completed call when the same work is
        requested again, so "the same work" must mean "the same basis".  Without
        this, a baseline review and a closure review of a *revised* report look
        identical to the ledger -- same role, same materials, same purpose -- and
        the closure silently replays the baseline's verdict on a body it never
        read.  A scripted test caught exactly that.
        """

        payload = f"{self.role}\n{self.purpose}\n{self.body}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def require_fits(self, limit: int) -> None:
        """Fail before the call rather than truncate the basis to fit."""

        if self.char_count > limit:
            raise ContextCapacityError(
                f"{self.role} context needs {self.char_count} characters but the "
                f"limit is {limit}; reduce scope rather than dropping evidence"
            )


async def load_contract(store: SqliteArtifactStore) -> ResearchContract:
    """Read the approved Contract from its artifact head."""

    view = await store.active_view()
    head = view.head("research_contract")
    if head is None:
        raise ContextCapacityError("no approved Contract exists for this task")
    return ResearchContract.decode(await store.body(head))


async def load_evidence(store: SqliteArtifactStore) -> EvidenceView:
    """Project the active evidence set, resolving anchors to citable handles."""

    view = await store.active_view()
    material_refs = view.active("material")

    materials: dict[str, MaterialBody] = {}
    sources: dict[str, SourceSnapshotBody] = {}
    for ref in material_refs:
        body = MaterialBody.decode(await store.body(ref))
        materials[ref] = body
        for source_ref in body.source_refs:
            if source_ref not in sources:
                sources[source_ref] = SourceSnapshotBody.decode(
                    await store.body(source_ref)
                )

    handles = build_handles(materials, sources)
    by_material: dict[str, list[CitationHandle]] = {}
    for handle in handles:
        by_material.setdefault(handle.material_ref, []).append(handle)

    return EvidenceView(
        evidence_set_id=view.evidence_set_id(),
        materials=tuple(
            MaterialView(
                material_ref=ref,
                body=materials[ref],
                handles=tuple(by_material.get(ref, ())),
            )
            for ref in material_refs
        ),
        sources=sources,
    )


async def latest_body(store: SqliteArtifactStore, kind: str) -> tuple[str, str] | None:
    """Return ``(artifact_id, body)`` of a singleton head, or None if absent."""

    view = await store.active_view()
    head = view.head(kind)
    if head is None:
        return None
    return head, await store.body(head)


def _section(title: str, content: str) -> str:
    return f"## {title}\n\n{content.strip()}\n"


def _delivery_language(contract: ResearchContract) -> str:
    """State the deliverable's language once, from the approved Contract.

    Roles used to carry "write in Chinese" fixed in their prompts while the
    Architect's context announced a delivery language beside it.  The two
    contradicted each other and the prompt won, so the language field was
    decorative and non-Chinese output was impossible rather than merely untested.
    """

    return _section(
        "交付语言",
        f"{contract.language}\n\n"
        "本次交付物用这个语言撰写。来源正文与锚点引文保持原语言，不翻译。",
    )


def analyst_context(
    contract: ResearchContract,
    evidence: EvidenceView,
    *,
    prior_synthesis: str = "",
) -> RoleContext:
    """Cross-source analysis over the exact evidence set, nothing else.

    The Analyst sees materials and boundaries but no citation handles: its job is
    to explain what the evidence supports and where it conflicts, and handles
    exist for the Author's prose, not for analysis.
    """

    parts = [
        _section("研究合同", contract.body_markdown),
        _delivery_language(contract),
        _section(
            "当前证据集",
            f"标识：{evidence.evidence_set_id}\n"
            f"素材数：{len(evidence.materials)}\n\n"
            + evidence.render(with_handles=False),
        ),
    ]
    if prior_synthesis.strip():
        parts.append(_section("上一份综合（供你说明判断如何改变）", prior_synthesis))
    return RoleContext(
        role="analyst",
        purpose="在正式素材上完成跨来源综合",
        body="\n".join(parts),
        input_refs=evidence.material_refs,
    )


def author_context(
    contract: ResearchContract,
    evidence: EvidenceView,
    synthesis: str,
    report_brief: str,
) -> RoleContext:
    """The Evidence Package: a read-only projection, not a third data store."""

    parts = [
        _section("研究合同", contract.body_markdown),
        _delivery_language(contract),
        _section("委托说明", report_brief),
        _section("当前综合", synthesis),
        _section(
            "可引用素材（引用标记只能原样使用）",
            evidence.render(with_handles=True),
        ),
    ]
    return RoleContext(
        role="author",
        purpose="根据已封存证据写出完整报告",
        body="\n".join(parts),
        input_refs=evidence.material_refs,
        handles=evidence.handles,
    )


def reviewer_context(
    contract: ResearchContract,
    evidence: EvidenceView,
    synthesis: str,
    report: str,
    *,
    prior_findings: Sequence[str] = (),
    dispositions: Sequence[str] = (),
) -> RoleContext:
    """A fresh basis per report version, with the whole evidence set visible.

    The Reviewer sees every active material, not only what the Author chose to
    cite.  Restricting it to the Author's selection would make selective
    omission -- the most consequential reporting failure -- structurally
    invisible.
    """

    parts = [
        _section("研究合同", contract.body_markdown),
        _delivery_language(contract),
        _section("当前综合", synthesis),
        _section(
            "当前证据集全集（含报告未引用的素材）",
            evidence.render(with_handles=True),
        ),
        _section("待审报告", report),
    ]
    if prior_findings:
        parts.append(
            _section(
                "上一轮的发布阻断项",
                "\n".join(f"{i}. {text}" for i, text in enumerate(prior_findings, 1)),
            )
        )
    if dispositions:
        parts.append(
            _section(
                "作者对每一项的处置",
                "\n".join(f"{i}. {text}" for i, text in enumerate(dispositions, 1)),
            )
        )
    return RoleContext(
        role="reviewer",
        purpose="独立审查这一份精确报告",
        body="\n".join(parts),
        input_refs=evidence.material_refs,
        handles=evidence.handles,
    )


def investigator_context(
    contract: ResearchContract,
    *,
    assignment: str,
    question_labels: Sequence[str],
    known_claims: Sequence[str] = (),
    source_access: Sequence[str] = ("public_web",),
    pack_text: str = "",
) -> RoleContext:
    """One assignment's brief, and deliberately nothing about the wider task.

    The Investigator sees the questions its assignment serves and a short list of
    what is already established, so it does not re-find known ground.  It does
    not see the full evidence set, other branches, or the Lead's reasoning: a
    branch that knew what its siblings were doing would coordinate, and
    coordination between parallel workers is exactly what the fan-out avoids.
    """

    questions = contract.resolve(question_labels)
    parts = [
        _section(
            "研究合同（相关部分）",
            "\n".join(f"- {q.label}. {q.text}" for q in questions),
        ),
        _section("本次任务", assignment),
        _section(
            "来源权限",
            "允许使用：" + "、".join(source_access)
            + "\n未获授权的来源族不得访问。",
        ),
    ]
    if known_claims:
        parts.append(
            _section(
                "已确立的内容（不必重复发现）",
                "\n".join(f"- {claim}" for claim in known_claims),
            )
        )
    if pack_text.strip():
        parts.append(pack_text.strip() + "\n")
    return RoleContext(
        role="investigator",
        purpose="在单个 Assignment 内发现并阅读候选来源",
        body="\n".join(parts),
        input_refs=(),
    )


def curator_context(
    contract: ResearchContract,
    *,
    assignment: str,
    candidates: Mapping[str, SourceSnapshotBody],
    notes: Mapping[str, str] | None = None,
    pack_text: str = "",
) -> RoleContext:
    """Candidate snapshots plus the purpose they were gathered for.

    The Curator gets a fresh context precisely so it does not inherit the
    Investigator's reasoning about why a source seemed promising -- it judges the
    saved text on its own terms.
    """

    relevance = notes or {}
    lines: list[str] = []
    for index, (ref, source) in enumerate(sorted(candidates.items()), start=1):
        lines.append(
            f"{index}. `{ref}`\n"
            f"   标题：{source.title}\n"
            f"   URL：{source.url}\n"
            f"   正文长度：{source.text_ref.char_count:,} 字符"
        )
        note = relevance.get(ref, "").strip()
        if note:
            lines.append(f"   调查者备注（仅供参考，不是判断）：{note}")

    parts = [
        _section("研究合同", contract.body_markdown),
        _delivery_language(contract),
        _section("这批来源为何被收集", assignment),
        _section(
            "候选来源（用 read_saved_source 读取正文后再判断）",
            "\n".join(lines) or "（没有候选来源）",
        ),
    ]
    if pack_text.strip():
        parts.append(pack_text.strip() + "\n")
    return RoleContext(
        role="curator",
        purpose="判断候选来源能否忠实、可定位地成为正式素材",
        body="\n".join(parts),
        input_refs=tuple(sorted(candidates)),
    )


def lead_context(
    contract: ResearchContract,
    evidence: EvidenceView,
    *,
    synthesis: str = "",
    memory: str = "",
    latest_outcome: str = "",
) -> RoleContext:
    """Governance input: heads and summaries, never raw evidence bodies.

    The Lead decides what to do next.  Giving it the full corpus would invite it
    to do the Analyst's work in its own context, which is how a governance role
    quietly turns into a second synthesiser.
    """

    parts = [
        _section("研究合同", contract.body_markdown),
        _section(
            "可选择的问题标签",
            "、".join(contract.labels) + "\n\n（Assignment 只能引用这些标签）",
        ),
        _section(
            "证据状态",
            f"证据集标识：{evidence.evidence_set_id}\n"
            f"当前活动素材：{len(evidence.materials)} 份\n"
            f"覆盖来源：{len(evidence.sources)} 个\n\n"
            + (evidence.source_summary() or "（尚无来源）"),
        ),
    ]
    parts.append(_section("当前综合", synthesis or "（尚无综合）"))
    if memory.strip():
        parts.append(_section("研究记忆", memory))
    if latest_outcome.strip():
        parts.append(_section("最近一次结果", latest_outcome))
    return RoleContext(
        role="lead",
        purpose="选择下一项最有价值的研究行动",
        body="\n".join(parts),
        input_refs=evidence.material_refs,
    )


__all__ = [
    "ContextCapacityError",
    "EvidenceView",
    "MaterialView",
    "RoleContext",
    "analyst_context",
    "author_context",
    "latest_body",
    "lead_context",
    "load_contract",
    "load_evidence",
    "reviewer_context",
]
