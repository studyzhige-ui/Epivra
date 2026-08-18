"""Evidence Curator: the one gate between a saved source and formal evidence.

The Curator answers a single question per candidate: can something in this saved
text become a Material that is faithful, locatable, and honest about its own
boundaries?  It searches for nothing, ranks nothing, and synthesises nothing --
it guards the Source-to-Material boundary, and that boundary is the reason a
finished report can be traced back to a real sentence in a real document.

Its quote must exist verbatim in the saved snapshot, which the runtime verifies
mechanically.  What the runtime cannot verify is whether the paraphrase around
that quote widened it, so that judgment is the Curator's whole job and the reason
this role stays on the reasoning tier.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..model import ToolSpec
from . import AgentSpec, ToolError

SYSTEM_PROMPT = """\
你是 Evidence Curator。你只判断候选来源中的内容能否忠实、可定位地成为正式 Material。

核对：

- 来源身份、发布者、日期、版本与来源角色；
- 引文是否在保存的正文中**逐字存在**；
- 改写是否保留了会改变意义的语境：数值的单位/分母/总体/时期、法律的辖区与生效版本、
  医疗的人群/干预/对照/结局、基准测试的环境与调优；
- 摘录是否**扩大**了人群、时期、强度、因果或比较范围；
- 是否为转载、共同上游或重复报道——这些不能被当作相互独立的支持；
- 该来源是否适合支撑这条具体命题。声誉高不等于对每个命题都适用。

Material 的 content 是你的改写，boundaries 必须写明**它不能支持什么**。边界不是套话：
它是下游 Author 不会把一个窄结论悄悄放大的唯一依据。

反证、真实冲突、失败结果、"该来源不支持更强结论"，同样可以且应该成为正式 Material。

无法定位引文、正文缺失、语境不足、或改写强于原文时——**拒绝**，不要猜测，也不要替
来源补全。

你不搜索新来源、不排名、不做跨来源综合、不判断研究是否完成、不写报告语言。\
"""

READ_SAVED_SOURCE = ToolSpec(
    name="read_saved_source",
    description="读取一个候选来源已保存的正文，用于核对引文与语境。",
    parameters={
        "type": "object",
        "properties": {
            "source_ref": {
                "type": "string",
                "description": "本次上下文列出的候选来源引用。",
            },
            "offset": {"type": "integer", "minimum": 0},
        },
        "required": ["source_ref"],
        "additionalProperties": False,
    },
)

RECORD_MATERIAL = ToolSpec(
    name="record_material",
    description=(
        "把一段内容晋升为正式 Material。引文必须在保存正文中逐字存在，"
        "运行时会机械校验并分配身份。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "source_ref": {"type": "string"},
            "exact_quote": {
                "type": "string",
                "minLength": 10,
                "description": "保存正文中逐字存在的原文片段。",
            },
            "content": {
                "type": "string",
                "minLength": 10,
                "description": "忠于原文的改写，强度不得超过引文所支持的范围。",
            },
            "boundaries": {
                "type": "string",
                "minLength": 10,
                "description": "这条素材不能支持什么：对象、时期、地域、方法、因果边界。",
            },
        },
        "required": ["source_ref", "exact_quote", "content", "boundaries"],
        "additionalProperties": False,
    },
)

REJECT_CANDIDATE = ToolSpec(
    name="reject_candidate",
    description="明确拒绝一个候选来源，并说明原因。拒绝是正常且有价值的结果。",
    parameters={
        "type": "object",
        "properties": {
            "source_ref": {"type": "string"},
            "reason": {"type": "string", "minLength": 10},
        },
        "required": ["source_ref", "reason"],
        "additionalProperties": False,
    },
)

COMPLETE_CURATION = ToolSpec(
    name="complete_curation",
    description=(
        "结束本次策展。运行时从你已提交的 record_material 与 reject_candidate "
        "推导结果清单，不要在这里重复列出。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "minLength": 20,
                "description": "接纳了什么、拒绝了什么及原因、发现了哪些同源或重复。",
            }
        },
        "required": ["summary"],
        "additionalProperties": False,
    },
)

SPEC = AgentSpec(
    role="curator",
    system_prompt=SYSTEM_PROMPT,
    tools=(READ_SAVED_SOURCE, RECORD_MATERIAL, REJECT_CANDIDATE, COMPLETE_CURATION),
    terminal_tools=frozenset({"complete_curation"}),
)


def make_validator(handled: Mapping[str, Any], candidate_count: int):
    """Require every candidate to receive a decision before curation closes.

    Leaving a candidate untouched is the one outcome that must not be possible:
    it would silently drop a source an Investigator paid to fetch, with no record
    of whether it was unusable or merely overlooked.
    """

    def validate(name: str, arguments: Mapping[str, Any]) -> ToolError | None:
        outstanding = candidate_count - len(handled)
        if outstanding > 0:
            return ToolError(
                action=name,
                problem=f"还有 {outstanding} 个候选来源没有处置",
                allowed="对每个候选来源调用 record_material 或 reject_candidate",
            )
        return None

    return validate


__all__ = [
    "COMPLETE_CURATION",
    "READ_SAVED_SOURCE",
    "RECORD_MATERIAL",
    "REJECT_CANDIDATE",
    "SPEC",
    "SYSTEM_PROMPT",
    "make_validator",
]
