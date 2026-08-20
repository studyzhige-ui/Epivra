"""Evidence Analyst: cross-source analysis over formal materials only.

Runs exactly once per material change, and once more before writing if the
current Synthesis is not bound to the exact evidence set the report will use.
It explains what the evidence supports, where sources genuinely conflict, and
what remains unknown -- and it does not decide what happens next.  That
separation exists because an analyst that also chooses the next action will
reliably conclude that its own analysis was sufficient.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..model import ToolSpec
from . import AgentSpec, ToolError

SYSTEM_PROMPT = """\
你是 Evidence Analyst。你只在已经正式策展的 Materials 之上做跨来源分析。

你的产出是一份按研究问题组织的综合，不是按来源罗列的摘要。它必须明确写出：

- 当前证据能支持的事实与判断，以及各自的强度；
- 支持证据、反证与替代解释；
- 来源之间的真实冲突，以及冲突来自时间、定义、人群、方法、适用范围还是来源本身；
- 来源独立性：哪些看似独立的来源其实共享同一上游；
- 事实、分析推断、假设与未知之间的界线；
- 结论的适用边界——对象、时期、地域、方法与因果强度；
- Evidence Frontier：还缺什么、为什么拿不到、什么新证据可能改变判断。

硬性要求：

- 只使用给定证据集中的内容。不得引入模型记忆里的事实，也不得引用证据集外的资料。
- 素材的"边界"字段是它不能支持什么。你的表述不得强于素材边界允许的范围。
- 证据不足时明确说不足。用更自信的措辞掩盖弱证据是失败，诚实的有限结论不是。
- 案例集合只代表被审查的案例，没有分母就不能外推为"普遍"。
- 不要决定下一步做什么、是否继续研究、是否可以写报告——那是 Research Lead 的判断。
- 不要写面向用户的报告，也不要设计报告章节。

用「交付语言」一节指定的语言提交，通过 publish_synthesis 一次性给出完整综合。\
"""

PUBLISH_SYNTHESIS = ToolSpec(
    name="publish_synthesis",
    description=(
        "提交一份绑定当前证据集的完整跨来源综合。这是本次调用唯一的终结动作。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "synthesis_markdown": {
                "type": "string",
                "minLength": 200,
                "description": (
                    "按研究问题组织的完整综合，包含支持证据、反证、冲突解释、"
                    "适用边界与 Evidence Frontier。"
                ),
            }
        },
        "required": ["synthesis_markdown"],
        "additionalProperties": False,
    },
)

SPEC = AgentSpec(
    role="analyst",
    system_prompt=SYSTEM_PROMPT,
    tools=(PUBLISH_SYNTHESIS,),
    terminal_tools=frozenset({"publish_synthesis"}),
)


def validate(name: str, arguments: Mapping[str, Any]) -> ToolError | None:
    """Reject an empty or trivially short synthesis before it is committed."""

    text = str(arguments.get("synthesis_markdown", "")).strip()
    if len(text) < 200:
        return ToolError(
            action=name,
            problem="综合过短，无法覆盖支持证据、反证、冲突与适用边界",
            allowed="提交一份完整综合",
        )
    return None


__all__ = ["SPEC", "SYSTEM_PROMPT", "validate"]
