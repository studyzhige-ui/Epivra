"""Report Author: the only role that writes, and it cannot approve itself.

The Author receives a sealed Evidence Package and no search tools.  When the
evidence cannot support what the Contract asks for, the honest actions are to
qualify, disclose, or return the problem upstream -- never to fill the gap from
model memory.  Writing guidance comes from published report practice (ODI, RAND,
NIST, OECD): length is a delivery setting rather than a quality proxy, and
sections run conclusion first, then evidence, then counter-evidence, then limits.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ..citations import citation_syntax_problem, extract_handles
from ..model import ToolSpec
from . import AgentSpec, ToolError

#: Delivery profiles in Chinese characters.  Falling short because the evidence
#: is thin is correct; padding to reach a number is not.
LENGTH_PROFILES: Mapping[str, tuple[int, int]] = {
    "quick": (2_000, 4_000),
    "standard": (5_000, 12_000),
    "deep": (12_000, 30_000),
}

SYSTEM_PROMPT = """\
你是 Report Author。你根据已批准的研究合同、当前综合和可引用素材，写出一份完整报告。

结构由用户用途和证据形状决定，不套万能目录。常见形态：

- 决策简报：直接答案、条件、选项、权衡、风险、行动边界；
- 系统证据综述：问题、方法、结果、异质性、确定性、局限；
- 技术报告：需求、机制、约束、失效模式、迁移路径；
- 比较研究：统一维度、逐项证据、不可比条件、条件性选择；
- 趋势研究：基线、变化、驱动因素、反向信号、情景。

写作要求：

- 执行摘要必须能独立回答用户最关心的问题，约占正文 8%–15%；
- 正文按问题或判断组织，不按来源流水账；
- 每节顺序为：结论句 → 证据 → 解释 → 反证或差异 → 局限或含义；
- 事实、分析推断、建议与未知必须让读者能够区分；
- 重要限制放在受影响结论的附近，不要只堆在末尾；
- 多对象、多维度比较用表格；不可比时保留不可比条件，不要压成单一排名。

引用规则（硬性）：

- 只能使用上下文给出的引用标记，原样嵌入，形如 [[cite:h7]]；
- 不得自己编号、不得手写 [1] 这类数字引用、不得自建"参考文献"章节——
  编号和参考资料由确定性渲染器生成；
- 每个重要的可核查事实、数字、时间敏感陈述和关键比较，都要就近关联引用；
- 不得引用上下文没有给出的标记。

边界：

- 你没有搜索工具，也不得从模型记忆补充外部事实；
- 不得修改综合，不得创建素材，不得批准自己的报告；
- 证据不足时，删除、弱化、限定或明确披露都是正确做法；
- 只有当合同的核心交付确实依赖证据集中不存在的事实时，才调用 raise_evidence_issue
  把问题交回 Research Lead，而不是在文字中补造。

用中文写作。\
"""

SUBMIT_REPORT = ToolSpec(
    name="submit_report",
    description="提交完整报告全文。这是终结动作之一。",
    parameters={
        "type": "object",
        "properties": {
            "report_markdown": {
                "type": "string",
                "minLength": 500,
                "description": "完整报告 Markdown，引用只用 [[cite:handle]] 标记。",
            }
        },
        "required": ["report_markdown"],
        "additionalProperties": False,
    },
)

SUBMIT_REVISED_REPORT = ToolSpec(
    name="submit_revised_report",
    description=(
        "提交完整修订报告，并对每一条发布阻断项逐项说明处置。"
        "必须提交完整替代全文，不能只给补丁。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "report_markdown": {"type": "string", "minLength": 500},
            "finding_dispositions": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "properties": {
                        "finding_index": {"type": "integer", "minimum": 1},
                        "response": {
                            "type": "string",
                            "minLength": 10,
                            "description": "已如何纠正、删除、限定或充分披露。",
                        },
                    },
                    "required": ["finding_index", "response"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["report_markdown", "finding_dispositions"],
        "additionalProperties": False,
    },
)

RAISE_EVIDENCE_ISSUE = ToolSpec(
    name="raise_evidence_issue",
    description=(
        "当合同的核心交付依赖证据集中不存在的事实时，把问题交回 Research Lead。"
        "这会立即结束本次写作事务，不会同时提交半成品报告。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "description": {"type": "string", "minLength": 20},
            "affected_claims": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
            },
            "why_writing_cannot_resolve_it": {"type": "string", "minLength": 20},
        },
        "required": [
            "description",
            "affected_claims",
            "why_writing_cannot_resolve_it",
        ],
        "additionalProperties": False,
    },
)

SPEC = AgentSpec(
    role="author",
    system_prompt=SYSTEM_PROMPT,
    tools=(SUBMIT_REPORT, RAISE_EVIDENCE_ISSUE),
    terminal_tools=frozenset({"submit_report", "raise_evidence_issue"}),
)

REVISION_SPEC = AgentSpec(
    role="author",
    system_prompt=SYSTEM_PROMPT,
    tools=(SUBMIT_REVISED_REPORT, RAISE_EVIDENCE_ISSUE),
    terminal_tools=frozenset({"submit_revised_report", "raise_evidence_issue"}),
)


def make_validator(
    known_handles: Sequence[str], *, finding_count: int = 0
):
    """Validate a submission against the handles this invocation actually exposed.

    Checking handles here rather than at publication gives the Author a
    correctable error instead of a failed transaction, while still making an
    invented citation impossible.
    """

    allowed = frozenset(known_handles)

    def validate(name: str, arguments: Mapping[str, Any]) -> ToolError | None:
        if name == "raise_evidence_issue":
            return None

        markdown = str(arguments.get("report_markdown", ""))
        # Syntax first: a malformed marker is invisible to extract_handles, so
        # without this the submission passed validation, became a report,
        # survived review, and then failed at the render step with the whole
        # report already approved. One live run was lost exactly there.
        syntax = citation_syntax_problem(markdown)
        if syntax:
            return ToolError(
                action=name,
                problem=syntax,
                allowed=f"只用上下文给出的标记，例如 [[cite:{next(iter(sorted(allowed)), 'h1')}]]",
            )
        used = extract_handles(markdown)
        if not used:
            return ToolError(
                action=name,
                problem="报告没有任何引用标记，可核查事实必须就近关联证据",
                allowed=f"使用上下文给出的标记，例如 [[cite:{next(iter(sorted(allowed)), 'h1')}]]",
            )
        unknown = sorted(set(used) - allowed)
        if unknown:
            return ToolError(
                action=name,
                problem=f"引用了上下文没有给出的标记 {unknown}",
                allowed="只能使用当前证据集暴露的引用标记",
            )
        if name == "submit_revised_report":
            responses = arguments.get("finding_dispositions", ())
            indexes = {
                int(item.get("finding_index", 0))
                for item in responses
                if isinstance(item, dict)
            }
            expected = set(range(1, finding_count + 1))
            missing = sorted(expected - indexes)
            if missing:
                return ToolError(
                    action=name,
                    problem=f"发布阻断项 {missing} 没有对应处置",
                    allowed="逐项处置全部阻断项，不能静默忽略",
                )
        return None

    return validate


__all__ = [
    "LENGTH_PROFILES",
    "REVISION_SPEC",
    "SPEC",
    "SYSTEM_PROMPT",
    "make_validator",
]
