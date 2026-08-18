"""Research Lead: the only role that decides what happens next.

The Lead governs, and governance is all it does.  It does not search, read,
curate, synthesise, write, or review -- if it did any of those, the role that
decides when research ends would also be the role producing the evidence that
decision rests on, and it would reliably conclude that its own work sufficed.

"Long-lived" here means continuity of responsibility, not of conversation.  Each
activation is a fresh context rebuilt from current artifacts, so continuity comes
from :class:`MemoryBody` -- a compact working memory the Lead replaces wholesale
with every terminal action, rather than a transcript that grows until it rots.

No capability pack reaches this role (see ``packs.PACK_PROJECTION``): pack text
that could influence when research ends would be a stopping rule at one remove.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from ..contract import ResearchContract
from ..model import ToolSpec
from ..sources import ArtifactValidationError
from . import AgentSpec, ToolError


@dataclass(frozen=True, slots=True)
class MemoryBody:
    """The Lead's working memory: what was tried, decided, and left open.

    Deliberately excludes evidence judgments, conflicts, and unknowns -- those
    live in the Synthesis, and duplicating them here would create a second,
    drifting account of what the evidence says.  This artifact answers only
    "what has governance already done and why".
    """

    tried_paths: tuple[str, ...] = ()
    decisions: tuple[str, ...] = ()
    open_intents: tuple[str, ...] = ()
    user_items: tuple[str, ...] = ()

    def encode(self) -> str:
        return json.dumps(
            {
                "tried_paths": list(self.tried_paths),
                "decisions": list(self.decisions),
                "open_intents": list(self.open_intents),
                "user_items": list(self.user_items),
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    @classmethod
    def decode(cls, body: str) -> MemoryBody:
        value = json.loads(body)
        return cls(
            tried_paths=tuple(str(x) for x in value.get("tried_paths", ())),
            decisions=tuple(str(x) for x in value.get("decisions", ())),
            open_intents=tuple(str(x) for x in value.get("open_intents", ())),
            user_items=tuple(str(x) for x in value.get("user_items", ())),
        )

    @classmethod
    def from_snapshot(cls, snapshot: Mapping[str, Any]) -> MemoryBody:
        """Build from the ``memory_snapshot`` a terminal action supplied."""

        def items(key: str) -> tuple[str, ...]:
            raw = snapshot.get(key, ()) or ()
            if isinstance(raw, str):
                raw = [raw]
            return tuple(str(item).strip() for item in raw if str(item).strip())

        return cls(
            tried_paths=items("tried_paths"),
            decisions=items("decisions"),
            open_intents=items("open_intents"),
            user_items=items("user_items"),
        )

    def render(self) -> str:
        sections = (
            ("已尝试的路径", self.tried_paths),
            ("治理决定与理由", self.decisions),
            ("仍开放的研究意图", self.open_intents),
            ("待用户处理的事项", self.user_items),
        )
        parts = [
            f"**{title}**\n" + "\n".join(f"- {item}" for item in items)
            for title, items in sections
            if items
        ]
        return "\n\n".join(parts) or "（尚无研究记忆）"


SYSTEM_PROMPT = """\
你是 Research Lead。你只负责研究治理：在当前已策展、已分析的证据状态下，选择下一项
最有价值的研究行动，或决定以完整/有限结论委托报告。

你每次都使用新的上下文。ResearchMemory、Synthesis 和上一次 Wave 结果是连续性的唯一
来源，所以每个终结动作都必须附带一份**完整替代**的 memory_snapshot。

你不搜索、不读网页、不策展素材、不做跨来源综合、不写报告、不审报告。

**发起 Wave 时**：一个 Wave 是一组当前可以并行、互不依赖、服务于同一个下一步决策的
Assignment。不要把每个主题机械地发一个任务，也不要把一次查询当成一个 Wave。

- 第一个 Wave 通常"全局广度、局部浅探"：覆盖当前独立且决策价值高的核心问题，建立
  来源生态、基线事实、明显冲突与可得性；不要一次穷尽所有主题。
- 后续 Wave 聚焦可能**改变结论**的具体缺口、冲突、适用性或新来源类别。
- 每个 Assignment 必须说明：聚焦什么问题、为什么它影响当前判断、希望取得什么类型的
  证据、需要主动寻找什么反证或替代解释。
- Assignment 只能引用当前 Contract 暴露的问题标签（Q1、Q2…）。
- 投入量参考：单个明确事实核查约 3–10 次工具调用；需要对比的问题通常 2–4 个
  Assignment、每个 10–15 次调用；复杂议题可以更多。这是投入校准，不是完成阈值。

**委托报告时**：说明当前证据能支持什么、不能支持什么、重要反证与冲突如何处置。
证据合理穷尽但仍不足时，委托一份诚实披露限制的完整报告，而不是无限搜索。

**判断停止时必须回答**：
- 当前证据能否在 Contract 边界内诚实回答核心问题；
- 重要反证、替代解释、冲突和适用性是否已有处置；
- 是否仍存在一个具体、合法、可执行且**可能实质改变结论**的新路径。

以下都**不是**证据饱和的信号：供应商故障、超时、权限不足、某个 Investigator 没找到
内容、已经跑了几个 Wave、花了多少钱。工具故障是运行结果，不是证据世界的结论。

你只输出语义意图。不要输出节点名、路由、分支 ID、阶段、哈希或数据库字段——这些由
运行时分配。\
"""

_MEMORY_SCHEMA = {
    "type": "object",
    "description": (
        "下一次 Lead 决策所需的完整替代研究记忆。只保存治理信息，"
        "不复制证据判断、冲突、网页正文或 Synthesis 内容。"
    ),
    "properties": {
        "tried_paths": {
            "type": "array",
            "items": {"type": "string"},
            "description": "已尝试过的研究路径及其结果概要。",
        },
        "decisions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "治理决定及其理由。",
        },
        "open_intents": {
            "type": "array",
            "items": {"type": "string"},
            "description": "仍然开放、可能值得追查的研究意图。",
        },
        "user_items": {
            "type": "array",
            "items": {"type": "string"},
            "description": "需要用户处理或决定的事项。",
        },
    },
    "additionalProperties": False,
}

COMMISSION_WAVE = ToolSpec(
    name="commission_wave",
    description=(
        "发起一组可以并行、互不依赖、服务于同一个下一步决策的调查任务。"
        "运行时分配全部 Wave 与 Assignment 身份。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "wave_intent": {
                "type": "string",
                "minLength": 20,
                "description": "这一个 Wave 服务于哪一个下一步研究决策。",
            },
            "assignments": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "properties": {
                        "question_labels": {
                            "type": "array",
                            "minItems": 1,
                            "items": {"type": "string"},
                            "description": "本任务服务的 Contract 问题标签，如 [\"Q2\"]。",
                        },
                        "focus": {
                            "type": "string",
                            "minLength": 10,
                            "description": "要回答的聚焦问题。",
                        },
                        "why_it_matters": {
                            "type": "string",
                            "minLength": 10,
                            "description": "为什么它可能改变当前判断。",
                        },
                        "evidence_sought": {
                            "type": "string",
                            "minLength": 5,
                            "description": "希望取得的证据类型或来源角色。",
                        },
                        "counter_evidence": {
                            "type": "string",
                            "description": "需要主动寻找的反证、替代解释或适用边界。",
                        },
                    },
                    "required": [
                        "question_labels",
                        "focus",
                        "why_it_matters",
                        "evidence_sought",
                    ],
                    "additionalProperties": False,
                },
            },
            "memory_snapshot": _MEMORY_SCHEMA,
        },
        "required": ["wave_intent", "assignments", "memory_snapshot"],
        "additionalProperties": False,
    },
)

COMMISSION_REPORT = ToolSpec(
    name="commission_report",
    description=(
        "基于当前证据委托一份报告。运行时封存当前证据集并绑定当前综合；"
        "不要填写任何哈希或引用。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "stop_rationale": {
                "type": "string",
                "minLength": 50,
                "description": (
                    "当前证据能支持什么、不能支持什么、重要反证与冲突如何处置，"
                    "以及为什么继续检索不再可能实质改变结论。"
                ),
            },
            "report_brief": {
                "type": "string",
                "minLength": 30,
                "description": "面向 Author 的任务简报：受众、用途、必须回答什么。",
            },
            "memory_snapshot": _MEMORY_SCHEMA,
        },
        "required": ["stop_rationale", "report_brief", "memory_snapshot"],
        "additionalProperties": False,
    },
)

REQUEST_USER_INPUT = ToolSpec(
    name="request_user_input",
    description="研究无法在没有用户输入的情况下继续时，向用户提问并暂停。",
    parameters={
        "type": "object",
        "properties": {
            "question": {"type": "string", "minLength": 10},
            "reason": {"type": "string", "minLength": 20},
            "memory_snapshot": _MEMORY_SCHEMA,
        },
        "required": ["question", "reason", "memory_snapshot"],
        "additionalProperties": False,
    },
)

REQUEST_CONTRACT_REAPPROVAL = ToolSpec(
    name="request_contract_reapproval",
    description=(
        "研究发现必须实质改变已批准的用途、核心问题、关键边界或交付时，"
        "请求用户重新批准。你不能自行修改 Contract。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "reason": {"type": "string", "minLength": 20},
            "proposed_change": {"type": "string", "minLength": 20},
            "memory_snapshot": _MEMORY_SCHEMA,
        },
        "required": ["reason", "proposed_change", "memory_snapshot"],
        "additionalProperties": False,
    },
)

SPEC = AgentSpec(
    role="lead",
    system_prompt=SYSTEM_PROMPT,
    tools=(
        COMMISSION_WAVE,
        COMMISSION_REPORT,
        REQUEST_USER_INPUT,
        REQUEST_CONTRACT_REAPPROVAL,
    ),
    terminal_tools=frozenset(
        {
            "commission_wave",
            "commission_report",
            "request_user_input",
            "request_contract_reapproval",
        }
    ),
)


@dataclass(frozen=True, slots=True)
class AssignmentDraft:
    """One parallel investigation the Lead asked for, before it gets an ID."""

    question_labels: tuple[str, ...]
    focus: str
    why_it_matters: str
    evidence_sought: str
    counter_evidence: str = ""
    known_refs: tuple[str, ...] = field(default_factory=tuple)

    def render(self, questions: Sequence[Any]) -> str:
        lines = [
            "## 你的调查任务",
            f"聚焦问题：{self.focus}",
            f"为什么重要：{self.why_it_matters}",
            f"希望取得的证据：{self.evidence_sought}",
        ]
        if self.counter_evidence.strip():
            lines.append(f"必须主动寻找的反证或边界：{self.counter_evidence}")
        if questions:
            lines.append(
                "服务的合同问题：\n"
                + "\n".join(f"- {q.label}. {q.text}" for q in questions)
            )
        return "\n".join(lines)


def parse_assignments(
    contract: ResearchContract, raw: Sequence[Mapping[str, Any]]
) -> tuple[AssignmentDraft, ...]:
    """Resolve drafts against the Contract, rejecting labels it does not expose.

    This is the single gate that stops the Lead inventing a target: labels must
    come from the Contract the user approved.
    """

    drafts: list[AssignmentDraft] = []
    for item in raw:
        labels = tuple(str(x) for x in item.get("question_labels", ()) or ())
        contract.resolve(labels)  # raises if unknown, duplicated, or empty
        drafts.append(
            AssignmentDraft(
                question_labels=labels,
                focus=str(item.get("focus", "")).strip(),
                why_it_matters=str(item.get("why_it_matters", "")).strip(),
                evidence_sought=str(item.get("evidence_sought", "")).strip(),
                counter_evidence=str(item.get("counter_evidence", "")).strip(),
            )
        )
    return tuple(drafts)


def make_validator(contract: ResearchContract):
    """Validate a governance action's mechanical shape against this Contract."""

    def validate(name: str, arguments: Mapping[str, Any]) -> ToolError | None:
        snapshot = arguments.get("memory_snapshot")
        if not isinstance(snapshot, Mapping):
            return ToolError(
                action=name,
                problem="缺少 memory_snapshot；每个终结动作都必须附带完整替代研究记忆",
            )

        if name == "commission_wave":
            raw = arguments.get("assignments", ())
            if not raw:
                return ToolError(
                    action=name, problem="一个 Wave 至少需要一个 Assignment"
                )
            try:
                parse_assignments(contract, raw)
            except ArtifactValidationError as error:
                return ToolError(
                    action=name,
                    problem=str(error),
                    allowed="只能引用当前合同的问题标签：" + "、".join(contract.labels),
                )
        return None

    return validate


__all__ = [
    "COMMISSION_REPORT",
    "COMMISSION_WAVE",
    "REQUEST_CONTRACT_REAPPROVAL",
    "REQUEST_USER_INPUT",
    "SPEC",
    "SYSTEM_PROMPT",
    "AssignmentDraft",
    "MemoryBody",
    "make_validator",
    "parse_assignments",
]
