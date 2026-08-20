"""Evidence Investigator: discovery inside one assignment, and nothing beyond it.

The Investigator is the only role that reaches the open web, and the only one
that runs a genuine tool loop -- searching, reading, following upstream
references, adjusting strategy as it learns.  Its output is candidate sources
plus a transparent account of what it tried; it cannot promote anything to formal
evidence, which is the Curator's separate judgment on a fresh context.

Two boundaries carry most of the weight.  A search snippet is a lead, never
evidence: a claim may only rest on saved full text.  And a provider failure is an
operational fact, never a finding -- "the API returned 429" must never become
"no evidence exists", because that is how a tooling problem silently becomes a
research conclusion.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..model import ToolSpec
from . import AgentSpec, ToolError

SYSTEM_PROMPT = """\
你是一个临时 Evidence Investigator，只负责当前这一个 Assignment 内的来源发现与战术
调查。

方法：

- 从任务目的出发形成**多个不同的检索表达**，不要堆叠相似查询；
- 先识别术语、关键记录与权威来源族，再针对具体缺口定向追查；
- 优先原始、官方、方法透明、相互独立的来源；必要时用高质量二手来源定位上游；
- **阅读原文**。搜索摘要只是发现线索，不能作为证据；要引用的内容必须先保存正文；
- 主动寻找负面结果、批评、撤回、限制、替代解释，以及不同语言的资料；
- 记录当前来源适用的时间、对象、方法与推断边界；
- 当你已经改变过查询方式、来源类型和上游路径，结果仍然主要重复，或本 Assignment
  已在能力内得到答案时，就结束调查。

硬性边界：

- 你**不能**把内容晋升为正式 Material——那是 Curator 在新上下文中的判断；
- 你**不能**形成跨来源最终结论，也不判断整个研究是否完成；
- 你**不能**修改 Contract；
- 你**不能**编造来源身份；只能保存工具实际返回的结果；
- 不要把自己的推断伪装成来源陈述。

访问失败、付费墙、权限不足、供应商报错、结果为空，都是**运行结果**，必须如实记录为
运行限制。**绝不要**把它们写成"没有证据"或"证据已饱和"——那会让一个工具问题变成一个
研究结论。

完成时用 complete_investigation 交回：做了什么、发现了什么、尝试过哪些路径、遇到哪些
限制、还有什么没解决。区分来源陈述、你自己的暂时解释、冲突与未解决问题。\
"""

SEARCH = ToolSpec(
    name="search",
    description=(
        "检索候选来源。返回标题、URL 与发现摘要；摘要不是证据，要引用必须先 read。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "minLength": 2},
            "intent": {
                "type": "string",
                "description": "这次检索想找什么，用于路由与审计。",
            },
            "scope": {
                "type": "string",
                "enum": ["academic", "web", "both"],
                "description": (
                    "该去哪一类来源找：academic=同行评议文献、预印本、DOI；"
                    "web=官方站点、法规原文、新闻、技术文档；both=两边都要。"
                    "选对能少打无关的检索接口——查法规不必问文献库，"
                    "查试验报告不必问通用搜索。不确定时用 both。"
                ),
            },
        },
        "required": ["query", "intent", "scope"],
        "additionalProperties": False,
    },
)

READ = ToolSpec(
    name="read",
    description=(
        "读取一个来源的正文并保存快照。只有读过并保存的正文才能成为证据。"
        "公开网络的 URL 必须来自本次检索结果；本地资料用「用户本地资料库」一节"
        "列出的 local: 标识，两者都不能自己编造。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "minLength": 8},
            "why": {"type": "string", "description": "为什么这一篇值得读。"},
        },
        "required": ["url"],
        "additionalProperties": False,
    },
)

SAVE_CANDIDATE = ToolSpec(
    name="save_candidate_source",
    description=(
        "把一个已读取的来源标记为候选，交给 Curator 审视。"
        "只能标记本次已经 read 成功的 URL。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "minLength": 8},
            "relevance_note": {
                "type": "string",
                "minLength": 10,
                "description": "这个来源可能支撑本任务的哪一点，以及它的明显边界。",
            },
        },
        "required": ["url", "relevance_note"],
        "additionalProperties": False,
    },
)

COMPLETE_INVESTIGATION = ToolSpec(
    name="complete_investigation",
    description=(
        "结束本次调查。运行时从你已提交的 save_candidate_source 推导候选清单，"
        "不要在这里重复列出 URL。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "minLength": 30,
                "description": "发现了什么，区分来源陈述与你的暂时解释。",
            },
            "attempted_paths": {
                "type": "array",
                "minItems": 1,
                "items": {"type": "string"},
                "description": "尝试过的检索方向与上游路径，含没有产出的。",
            },
            "limitations": {
                "type": "array",
                "items": {"type": "string"},
                "description": "访问失败、付费墙、缺失记录、工具错误等运行限制。",
            },
            "unresolved": {
                "type": "array",
                "items": {"type": "string"},
                "description": "本任务内仍未解决的问题。",
            },
        },
        "required": ["summary", "attempted_paths"],
        "additionalProperties": False,
    },
)

SPEC = AgentSpec(
    role="investigator",
    system_prompt=SYSTEM_PROMPT,
    tools=(SEARCH, READ, SAVE_CANDIDATE, COMPLETE_INVESTIGATION),
    terminal_tools=frozenset({"complete_investigation"}),
)


def make_validator(saved: Mapping[str, Any]):
    """Require at least a transparent account, even when nothing was found.

    An empty-handed investigation is a legitimate outcome, but it must arrive
    with the paths that were tried -- otherwise a downstream Lead cannot tell
    "this line is exhausted" from "the tooling failed".
    """

    def validate(name: str, arguments: Mapping[str, Any]) -> ToolError | None:
        paths = arguments.get("attempted_paths", ())
        if not paths:
            return ToolError(
                action=name,
                problem="必须记录尝试过的路径，即使没有找到任何来源",
                allowed="列出你实际用过的检索方向与上游路径",
            )
        if not saved and not arguments.get("limitations"):
            return ToolError(
                action=name,
                problem=(
                    "没有保存任何候选来源，也没有记录任何运行限制。"
                    "如果确实一无所获，请说明是检索路径已穷尽还是遇到了访问限制"
                ),
                allowed="补充 limitations，或先保存候选来源",
            )
        return None

    return validate


__all__ = [
    "COMPLETE_INVESTIGATION",
    "READ",
    "SAVE_CANDIDATE",
    "SEARCH",
    "SPEC",
    "SYSTEM_PROMPT",
    "make_validator",
]
