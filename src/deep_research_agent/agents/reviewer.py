"""Independent Reviewer: the only role that can approve, and it never writes.

A fresh invocation per report version, with the whole active evidence set
visible rather than only what the Author chose to cite -- otherwise selective
omission, the most consequential reporting failure, would be structurally
invisible.

The tool choice *is* the publication branch.  ``approve_report`` and
``block_report`` are distinct actions, so the runtime never parses prose or a
severity field to guess whether something blocks.  Advisories exist only on the
approve path, which removes the ambiguity that lets a reviewer accumulate
non-blocking suggestions into an unbounded revision loop.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..model import ToolSpec
from . import AgentSpec, ToolError

SYSTEM_PROMPT = """\
你是 Independent Reviewer。你只审查当前这一份精确报告及其合同、综合与正式证据。
你不参与研究，不改稿，也不决定下一个角色。

你可以看到当前证据集的全部素材，包括报告没有引用的那些。请主动检查是否有重要
反证被遗漏。

必须阻断发布的情形：

- 报告没有回答合同的核心问题，也没有诚实说明为何不能回答；
- 主要主张超出、歪曲或选择性使用证据；
- 数字、比较、因果、时期、对象或适用范围错误；
- 关键反证、真实冲突、替代解释或限制被隐藏；
- 事实、分析推断与建议混为一谈；
- 引用无法支持它附近的主张；
- 表格或结构会实质误导读者。

不得阻断的情形：

- 证据世界本身不完整，但报告已经准确限定并披露；
- 你觉得"也许还能再搜一些"，却说不出具体是什么证据、以及它会如何改变结论；
- 纯文风、措辞或排版偏好；
- 报告给出了"当前无法确定"的诚实结论；
- 你的建议尚未被采纳，但它并不影响结论的正确性。

低确定性不是失败。过度自信、隐瞒限制、伪造支持才是。

判断后二选一：
- 报告在其边界内可信 → approve_report，说明理由，可附非阻断的 advisory；
- 存在发布阻断项 → block_report，逐项给出位置、问题、影响与可验证的关闭条件。

每一条 block_report 里的 finding 都必须是真正的发布阻断项。仅供改进的建议只能
放在 approve_report 的 advisories 里。用中文提交。\
"""

APPROVE_REPORT = ToolSpec(
    name="approve_report",
    description=(
        "批准这一份精确报告。选择这个动作即表示不存在发布阻断项；"
        "非阻断的改进建议放在 advisories。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "rationale": {
                "type": "string",
                "minLength": 50,
                "description": "为什么这份报告在其证据边界内可信且可发布。",
            },
            "advisories": {
                "type": "array",
                "items": {"type": "string"},
                "description": "非阻断的改进建议，不影响发布。",
            },
        },
        "required": ["rationale"],
        "additionalProperties": False,
    },
)

BLOCK_REPORT = ToolSpec(
    name="block_report",
    description=(
        "阻断发布。这里的每一项都必须是真正的发布阻断项，不能放改进建议。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "findings": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "报告中的具体位置（章节或原句）。",
                        },
                        "problem": {"type": "string", "minLength": 15},
                        "impact": {
                            "type": "string",
                            "minLength": 10,
                            "description": "会如何影响用户的判断。",
                        },
                        "acceptance_condition": {
                            "type": "string",
                            "minLength": 10,
                            "description": "怎样修改才算关闭这一项，必须可验证。",
                        },
                    },
                    "required": [
                        "location",
                        "problem",
                        "impact",
                        "acceptance_condition",
                    ],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["findings"],
        "additionalProperties": False,
    },
)

SPEC = AgentSpec(
    role="reviewer",
    system_prompt=SYSTEM_PROMPT,
    tools=(APPROVE_REPORT, BLOCK_REPORT),
    terminal_tools=frozenset({"approve_report", "block_report"}),
)


def validate(name: str, arguments: Mapping[str, Any]) -> ToolError | None:
    """Keep each finding individually addressable and genuinely blocking."""

    if name == "block_report":
        findings = arguments.get("findings", ())
        if not findings:
            return ToolError(
                action=name,
                problem="阻断必须至少给出一项具体的发布阻断项",
                allowed="没有阻断项时改用 approve_report",
            )
        for index, finding in enumerate(findings, start=1):
            if not isinstance(finding, dict):
                return ToolError(action=name, problem=f"第 {index} 项不是结构化对象")
            if not str(finding.get("acceptance_condition", "")).strip():
                return ToolError(
                    action=name,
                    problem=f"第 {index} 项缺少可验证的关闭条件",
                    allowed="每一项都要说明怎样修改才算关闭",
                )
    return None


def findings_as_text(arguments: Mapping[str, Any]) -> tuple[str, ...]:
    """Render blocking findings for the Author's revision context."""

    rendered: list[str] = []
    for finding in arguments.get("findings", ()):
        if not isinstance(finding, dict):
            continue
        rendered.append(
            f"位置：{finding.get('location', '')}\n"
            f"   问题：{finding.get('problem', '')}\n"
            f"   影响：{finding.get('impact', '')}\n"
            f"   关闭条件：{finding.get('acceptance_condition', '')}"
        )
    return tuple(rendered)


__all__ = ["SPEC", "SYSTEM_PROMPT", "findings_as_text", "validate"]
