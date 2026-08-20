"""The report-quality rubric, as a layered judgment rather than a score.

Ported from `deep-research-mcp/knowledge/06_evaluation/rubric.yaml` with one
deliberate break: the source sets ``publish_minimum_average: 3.0``, and an
average is the wrong instrument.  AMSTAR 2 states outright that it does not
generate an overall score, because a mean lets one fatal flaw be diluted by nine
respectable dimensions -- exactly the failure a publication gate must not have.
So the verdict here is **tiered on critical-domain outcomes**, and no total is
ever produced.

Three authorities shape the structure, each checked against its primary text
rather than recalled (`docs/ARCHITECTURE.md` §10):

* **AMSTAR 2** (Shea et al., BMJ 2017) -- "AMSTAR 2 is not intended to generate
  an overall score", and "we strongly recommend that individual item ratings are
  not combined to create an overall score", because a total "may disguise
  critical weaknesses".  Its four confidence bands are reproduced exactly in
  :attr:`RubricVerdict.tier`.  Its own critical list is explicitly advisory --
  "appraisers may add or substitute domains" -- which is what licenses the
  research-report-specific set below rather than copying a review-appraisal one.
* **GRADE** -- certainty is judged **per outcome** ("outcome centric"), never for
  a document as a whole, and GRADE "is not a quantitative system for grading the
  quality of evidence".  Its *defining* feature is that certainty and strength of
  recommendation are decoupled: high certainty need not produce a strong
  recommendation, and low certainty can still support one where benefits clearly
  dominate.  An earlier version of this rubric had that backwards and treated
  "recommendation stronger than certainty" as a failure.  It is not.
* **PRISMA 2020** -- evidence limitations (23b) and process limitations (23c) are
  separate items.  "The studies are small" and "we searched only the open web"
  must be stated apart, or a reader cannot tell what to go and fix.

**The rubric answers to those sources and to nothing else.**  Reports this system
produces are *subjects* of measurement and hold no authority over the standard: a
low score changes the report or the system, never the criteria.  Only new external
authority may change what is written here.  Calibrating the standard toward our
own output would build a mirror rather than an instrument.

The five critical domains are the same five the Reviewer must block on, stated
once here so the offline judge and the in-run gate cannot drift into disagreeing
about what publication requires.  :func:`reviewer_rules` exposes the phrases a
test checks against the Reviewer's prompt.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

Tier = Literal["不可依赖", "不可发布", "可发布·中", "可发布·高"]


@dataclass(frozen=True, slots=True)
class Domain:
    """One thing the judge decides, with the failure it is looking for."""

    key: str
    title: str
    question: str
    failure: str
    #: For critical domains: a distinctive phrase that must still appear in the
    #: Reviewer's prompt.  Deliberately brittle -- rewording the prompt trips the
    #: test, which forces someone to confirm the gate and the judge still agree.
    reviewer_rule: str = ""

    def render(self) -> str:
        return f"- **{self.title}**（{self.key}）：{self.question}\n  失败的样子：{self.failure}"


#: Any single failure here blocks publication.  They are ordered by how
#: irreversible the damage is: a fabricated citation misleads a reader who
#: checks, while a merged fact/inference boundary misleads one who does not.
CRITICAL: tuple[Domain, ...] = (
    Domain(
        key="citation_grounding",
        title="引用落地",
        question="每条重要主张能否反向追溯到具体来源正文，并且该正文真的支持它？",
        failure="捏造引用、引用无法回放、或引用支持的是邻近但不同的主张（跨层引用）。",
        reviewer_rule="引用无法支持它附近的主张",
    ),
    Domain(
        key="within_evidence",
        title="不越证据",
        question=(
            "每条中心主张的措辞是否与它自己的证据相称——对象、时期、地域、"
            "口径、因果强度、确定性都不超出锚点？"
        ),
        failure="把关联写成因果、把他人群外推为本地结论、把单中心数据当作普遍情况。",
        reviewer_rule="主要主张超出、歪曲或选择性使用证据",
    ),
    Domain(
        key="scope_fidelity",
        title="范围忠实",
        question="报告是否回答了合同的 Q1，或诚实说明为何不能回答？",
        failure="答了一个更容易的问题，或悄悄把 Q1 换成自己能答的版本。",
        reviewer_rule="没有回答合同的核心问题",
    ),
    Domain(
        key="counter_evidence",
        title="反证未隐",
        question="与结论相悖的证据、真实冲突与替代解释是否都出现在报告里？",
        failure="删掉不显著结果、只呈现一方证据、把方法学分歧含糊成「学界无定论」。",
        reviewer_rule="关键反证、真实冲突、替代解释或限制被隐藏",
    ),
    Domain(
        key="layer_separation",
        title="层级可分",
        question="事实、分析推断、建议与未知是否可被读者逐句区分？",
        failure="把推断写成事实，或把来源描述冒充建议。",
        reviewer_rule="事实、分析推断与建议混为一谈",
    ),
)

#: Weaknesses that degrade the tier when they accumulate but never block on
#: their own.  A report can be honest and still be hard to use.
SUPPORTING: tuple[Domain, ...] = (
    Domain(
        key="search_transparency",
        title="检索透明",
        question="检索范围、纳入与排除标准是否写清，读者能否判断漏了什么？",
        failure="只说「广泛检索」，不说查了哪里、排除了什么。",
    ),
    Domain(
        key="dual_limitations",
        title="双重局限",
        question="证据局限与研究过程局限是否分开陈述（PRISMA 23b / 23c）？",
        failure="把「只检索了公开网络」和「现有研究样本太小」混成一段。",
    ),
    Domain(
        key="per_claim_certainty",
        title="逐主张确定性",
        question="确定性是否按结局/主张分别给出，而不是对整份报告给一个总评？",
        failure="用一句「证据总体中等」覆盖强弱差异极大的多条结论。",
    ),
    Domain(
        key="conflict_explanation",
        title="冲突解释",
        question="来源冲突是否归因到具体差异（时期、口径、方法、人群）？",
        failure="对矛盾估计取平均、投票，或并列而不解释。",
    ),
    Domain(
        key="source_independence",
        title="来源独立性",
        question="同源、转载与利益相关来源是否被识别，不被当作多重印证？",
        failure="把厂商公告与转载它的媒体算作两个独立来源。",
    ),
    Domain(
        key="actionable_recommendations",
        title="建议可执行且与确定性解耦",
        question=(
            "建议是否绑定条件、触发点与风险，并说明它依据的是收益—危害平衡、"
            "受众重视什么、资源与可行性——而不是直接由证据确定性推导出来？"
        ),
        failure=(
            "把建议强度当成证据确定性的读数（两个方向都算错：低确定性就不敢给建议，"
            "或高确定性就自动给强建议）；或给出无依据的明确建议。"
        ),
    ),
    Domain(
        key="reader_fit",
        title="读者适配",
        question="措辞、术语与结构是否匹配合同声明的受众与用途？",
        failure="对技术委员会用管理者话术，或反之。",
    ),
    Domain(
        key="structure_usable",
        title="结构可用",
        question="读者能否快速定位到自己要的答案，摘要是否不重复正文？",
        failure="流水账、层级不稳、摘要与正文大段重复。",
    ),
    Domain(
        key="visual_honesty",
        title="视觉诚实",
        question="表格与图示是否只承载真实可比的数据？",
        failure="为「专业感」造图、并列不可比数字、编造缺失的数值。",
    ),
    Domain(
        key="audit_hygiene",
        title="审计洁净",
        question="读者版是否不含内部 ID、检索日志与运行状态？",
        failure="正文混入 artifact ID 或把审计体积冒充研究深度。",
    ),
)

DOMAINS: tuple[Domain, ...] = CRITICAL + SUPPORTING
_BY_KEY = {domain.key: domain for domain in DOMAINS}


def reviewer_rules() -> tuple[tuple[str, str], ...]:
    """``(domain key, phrase)`` pairs the Reviewer's prompt must still contain."""

    return tuple(
        (domain.key, domain.reviewer_rule) for domain in CRITICAL if domain.reviewer_rule
    )


@dataclass(frozen=True, slots=True)
class DomainVerdict:
    """One domain's outcome, with the reason that justifies it.

    ``passed`` is the only field the tier depends on.  A reason is required
    because an unexplained verdict cannot be audited or disputed, which is what
    a human spot-check exists to do.
    """

    key: str
    passed: bool
    reason: str

    def __post_init__(self) -> None:
        if self.key not in _BY_KEY:
            raise ValueError(f"unknown rubric domain {self.key!r}")
        if not self.reason.strip():
            raise ValueError(f"{self.key} verdict needs a reason")

    @property
    def domain(self) -> Domain:
        return _BY_KEY[self.key]


@dataclass(frozen=True, slots=True)
class RubricVerdict:
    """A layered judgment.  Deliberately has no score and no average."""

    critical: tuple[DomainVerdict, ...]
    supporting: tuple[DomainVerdict, ...]

    def __post_init__(self) -> None:
        for group, expected, label in (
            (self.critical, CRITICAL, "critical"),
            (self.supporting, SUPPORTING, "supporting"),
        ):
            keys = [verdict.key for verdict in group]
            if len(set(keys)) != len(keys):
                raise ValueError(f"{label} domains judged more than once")
            missing = sorted({domain.key for domain in expected} - set(keys))
            if missing:
                raise ValueError(f"{label} domains not judged: {missing}")

    @property
    def critical_failures(self) -> tuple[DomainVerdict, ...]:
        return tuple(verdict for verdict in self.critical if not verdict.passed)

    @property
    def weaknesses(self) -> tuple[DomainVerdict, ...]:
        return tuple(verdict for verdict in self.supporting if not verdict.passed)

    @property
    def publishable(self) -> bool:
        return not self.critical_failures

    @property
    def tier(self) -> Tier:
        """Four tiers, matching AMSTAR 2's confidence bands exactly.

        AMSTAR 2 Box 2, verified against Shea et al. BMJ 2017: high = "no or one
        non-critical weakness"; moderate = "more than one non-critical weakness"
        with no critical flaw; low = "one critical flaw"; critically low = "more
        than one critical flaw", a review that "should not be relied on".

        The distinction between one critical flaw and several is not cosmetic.
        One is a defect to fix; several mean the document cannot be trusted as a
        summary of anything, which is a different message to its reader.  An
        earlier version of this rubric collapsed the two and lost that.

        An honest "we cannot determine this yet" still reaches 可发布·高: low
        certainty is not a defect, and only over-confidence, hidden limitations
        or fabricated support are.  Nothing here averages anything -- AMSTAR 2
        says outright that item ratings must not be combined into a score, and
        GRADE that it "is not a quantitative system".
        """

        failures = len(self.critical_failures)
        if failures > 1:
            return "不可依赖"
        if failures == 1:
            return "不可发布"
        return "可发布·高" if len(self.weaknesses) <= 1 else "可发布·中"

    def render(self) -> str:
        lines = [f"判定：{self.tier}"]
        if self.critical_failures:
            lines.append(
                "关键域失败（1 项 → 不可发布；>1 项 → 不可依赖）："
            )
            lines.extend(
                f"  ✗ {verdict.domain.title}：{verdict.reason}"
                for verdict in self.critical_failures
            )
        else:
            lines.append("五个关键域全部通过。")
        weaknesses = self.weaknesses
        if weaknesses:
            lines.append(f"非关键弱点 {len(weaknesses)} 项：")
            lines.extend(
                f"  - {verdict.domain.title}：{verdict.reason}" for verdict in weaknesses
            )
        else:
            lines.append("非关键域没有弱点。")
        return "\n".join(lines)


def render_rubric() -> str:
    """The rubric as the judge is shown it."""

    return "\n".join(
        [
            "## 关键域（任一失败 → 不可发布）",
            *(domain.render() for domain in CRITICAL),
            "",
            "## 非关键域（累积则降级，单项不阻断）",
            *(domain.render() for domain in SUPPORTING),
        ]
    )


def build_verdict(
    critical: Sequence[tuple[str, bool, str]],
    supporting: Sequence[tuple[str, bool, str]],
) -> RubricVerdict:
    """Assemble a verdict from ``(key, passed, reason)`` triples."""

    return RubricVerdict(
        critical=tuple(DomainVerdict(*item) for item in critical),
        supporting=tuple(DomainVerdict(*item) for item in supporting),
    )


__all__ = [
    "CRITICAL",
    "DOMAINS",
    "SUPPORTING",
    "Domain",
    "DomainVerdict",
    "RubricVerdict",
    "Tier",
    "build_verdict",
    "render_rubric",
    "reviewer_rules",
]
