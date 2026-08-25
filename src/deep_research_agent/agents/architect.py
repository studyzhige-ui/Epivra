"""Research Architect: turns an open commission into an approvable Contract.

The Architect is the only role that speaks to the user before research starts,
and the only one that may shape what the research is *for*.  It does not
research, does not judge whether research is finished, and does not approve
anything -- the user does that.

Its hardest judgment is restraint.  A commission almost always contains
ambiguity, and most of it should become a **visible default assumption** in the
Contract rather than a question, because a list of clarifying questions in front
of an eager user is a worse product than a clearly-stated assumption they can
correct in one edit.  Only ambiguity that would produce two fundamentally
different research tasks earns a question.

Its second duty is to **reframe a commission whose premise does not hold**.  A
user may ask for a proof of a conclusion they have already chosen, or a ranking
the available evidence cannot support.  Q1 is what the whole report must answer
and every later role works for it, so an unsound Q1 propagates through the entire
run -- filing the objection under "known limitations" while leaving the original
question as Q1 is not honesty, it is a footnote on a research plan that is
already pointed the wrong way.  Two live runs failed exactly this way before the
rule was written down.

"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

from ..contract import (
    CONTRACT_SECTIONS,
    ResearchContract,
    build_contract,
    parse_question_lines,
    section_title,
)
from ..model import ToolSpec
from ..sources import ArtifactValidationError
from . import AgentSpec, ToolError

SYSTEM_PROMPT = """\
你是 Research Architect。你的唯一职责是把用户的原始委托整理成一份简洁、可直接开始
执行的 Research Contract。用户看到的正文与后续 Agent 执行的正文是同一份，不存在隐藏
的内部方案。

先弄清三件事：用户真正要理解或决定什么、研究必须覆盖什么、最后交付什么。正文应当让
用户在一页内回答：「方向对不对？会研究什么？最后得到什么？」只保留最小充分信息；同一
事实只出现一次，不用换一种说法在多个区块重复。

第一行用一级标题写简短研究主题。随后只写以下五个同名区块：

## 研究目标
说明为什么研究、供谁使用、支持什么理解或决定。若原委托预设结论、要求证据无法支持的
精确排名或把关联当因果，在这里用一句话说明如何把问题改写为可诚实回答的形式。

## 重点问题
用最少的编号问题覆盖完整委托。`Q1` 是统摄用户全部用途和交付要求的核心问题，不能只取
委托中的一个并列部分；`Q2` 起是支撑问题，每个都必须能说明如何帮助回答 Q1。若委托包含
多个并列目标，先把它们合成一个可诚实回答的总问题，再拆成支撑问题。每个问题单独写成
Markdown 列表项 `- Q1. 问题正文`；标签后必须是完整问句，不是「核心问题」之类的空标题。

## 范围与排除
写会改变答案的对象、时期、地域、纳入/排除边界和关键默认假设。只列用户需要确认的
边界，并明确最容易造成方向漂移的不包含内容。涉及「当前」「最新」「截至目前」时，必须
以运行时上下文给出的当前日期为准，不能使用模型知识截止时间或自行猜测年份。除非用户
点名必须覆盖，不要把研究本应发现的候选对象、方案、组织、人物或来源提前锁成完整名单；
可以说明由当前证据决定代表性对象。

## 研究方式
只写本题特有的来源类型、比较维度、时间线口径或推断边界。通用的引用、反证、来源忠实、
独立审查和安全规则是产品固有能力，不要在每份 Contract 中重复。

## 交付内容
写用户最终会拿到什么，包括必要的时间线、对比表、建议形态或其他核心组成，以及交付语言。
不要预设结论或套用固定文章目录。

硬性要求：

- 保持紧凑。每节只保留会改变方向或交付的信息，不写为了显得完整而存在的套话。
- 不写内部 Agent 角色、查询和来源顺序、并行度、Wave、状态、重新确认规则、prompt、
  validator 或其他运行机制。
- 不写具体查询词、URL、固定来源数、固定 Wave 数或尚未研究就无法知道的结论。
- 不承诺已经找到结论、固定完成时间或确定能取得某类证据。你还没有做任何研究。
- 只在缺少答案会产生两个根本不同的研究方向时提问；其余不确定性写成醒目的默认假设。
- 除研究目标可用短段落外，重点问题、范围与排除、研究方式、交付内容优先使用扁平列表；
  不使用嵌套列表，不把多个编号问题挤在同一段。

使用上下文中指定的交付语言撰写 Contract。用户将直接阅读这份正文并决定开始或调整方向。\
"""

PROPOSE_CONTRACT = ToolSpec(
    name="propose_contract",
    description=(
        "提交一份用户可直接阅读、后续 Agent 可直接执行的完整研究方向。"
        "这是终结动作之一。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "contract_markdown": {
                "type": "string",
                "description": (
                    "以研究主题开头、覆盖五个用户区块的完整 Contract，"
                    "含编号问题 Q1..Qn。"
                ),
            },
            "question_supports": {
                "type": "object",
                "description": (
                    "可选。支撑问题的层级关系，如 {\"Q3\": [\"Q2\"]}。"
                    "省略则所有支撑问题直接支撑 Q1。"
                ),
                "additionalProperties": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
        },
        "required": ["contract_markdown"],
        "additionalProperties": False,
    },
)

ASK_SCOPE_QUESTION = ToolSpec(
    name="ask_scope_question",
    description=(
        "仅在缺少答案会导致两个根本不同的研究任务时，向用户提一个澄清问题。"
        "普通不确定性应写成 Contract 中的默认假设，不要用这个动作。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "question": {"type": "string", "minLength": 10},
            "why_it_changes_the_plan": {
                "type": "string",
                "minLength": 20,
                "description": "说明两种答案会分别导致什么根本不同的研究。",
            },
        },
        "required": ["question", "why_it_changes_the_plan"],
        "additionalProperties": False,
    },
)

SPEC = AgentSpec(
    role="architect",
    system_prompt=SYSTEM_PROMPT,
    tools=(PROPOSE_CONTRACT, ASK_SCOPE_QUESTION),
    terminal_tools=frozenset({"propose_contract", "ask_scope_question"}),
)

def contract_from_action(
    arguments: Mapping[str, Any], *, language: str = "zh"
) -> ResearchContract:
    """Build the Contract a ``propose_contract`` action describes.

    This lives beside the tool schema on purpose.  A caller that re-derives the
    argument shape by hand drifts from the schema silently, and the drift only
    surfaces on the first commission that actually populates the optional field.
    One did: the runner read ``question_supports`` as a list of objects while the
    schema declares an object, and seven fixtures passed before the eighth --
    the first to declare a question hierarchy -- crashed on it.

    Raises :class:`ArtifactValidationError` for a shape the schema forbids, so a
    wrong shape reaches the Architect as a correction instead of killing the run.
    """

    raw = arguments.get("question_supports") or {}
    if not isinstance(raw, Mapping):
        raise ArtifactValidationError(
            "question_supports must be an object mapping a question label to the "
            'labels it supports, for example {"Q3": ["Q2"]}'
        )
    return build_contract(
        str(arguments.get("contract_markdown", "")),
        supports={
            str(label): tuple(str(item) for item in targets)
            for label, targets in raw.items()
        },
        # The deliverable's language comes from the Commission, not from the
        # Architect: it is the user's choice, not a research judgment.
        language=language,
    )


def make_validator():
    """Validate a Contract candidate's mechanical shape, not its quality.

    Everything checked here is something the Architect can see and fix from the
    error alone: the visible topic and five blocks are present, and the question
    model is coherent.  Whether the direction is *right* is the user's judgment,
    not a schema's.
    """

    def validate(name: str, arguments: Mapping[str, Any]) -> ToolError | None:
        if name == "ask_scope_question":
            return None

        try:
            contract = contract_from_action(arguments)
        except ArtifactValidationError as error:
            return ToolError(
                action=name,
                problem=str(error),
                allowed="Q1 为核心问题，Q2 起须说明支撑关系，编号必须从 Q1 连续",
            )

        if not contract.title:
            return ToolError(
                action=name,
                problem="缺少研究主题",
                allowed="正文第一行用一级标题写一个简短、具体的研究主题",
            )

        missing = contract.missing_sections()
        if missing:
            titles = "、".join(section_title(section) for section in missing)
            return ToolError(
                action=name,
                problem=f"缺少必需区块：{titles}",
                allowed="五个区块各用同名标题：" + "、".join(
                    section_title(section) for section in CONTRACT_SECTIONS
                ),
            )

        unbulleted = [
            parsed[0][0]
            for line in contract.body_markdown.splitlines()
            if (parsed := parse_question_lines(line))
            and not line.lstrip().startswith(("- ", "* "))
        ]
        if unbulleted:
            return ToolError(
                action=name,
                problem="编号问题没有使用独立列表项：" + "、".join(unbulleted),
                allowed="每个问题单独写成 Markdown 列表项，例如 `- Q1. 完整问题？`",
            )

        return None

    return validate


def architect_context_body(
    request: str,
    *,
    source_access: Sequence[str],
    language: str,
    constraints: Sequence[str] = (),
    clarifications: Sequence[tuple[str, str]] = (),
    revision_note: str = "",
    previous_contract: str = "",
    as_of_date: str = "",
) -> str:
    """Compose the Architect's context from the Commission.

    Three kinds of added context, kept separate because they mean different
    things.  ``clarifications`` are answered questions -- the Architect asked what
    it needed in order to plan at all -- and every plan version carries the whole
    exchange, including a revision: an answer the user has already given does not
    stop being true because the plan is now on its second draft.  A revision
    additionally passes the previous candidate and the user's note, because the
    Architect must produce a *complete replacement* Contract rather than append an
    amendment -- an approval binds one exact body, so patching a prior one would
    leave nothing coherent to approve.

    None of them are folded into ``request``.  The Commission is the one artifact
    no rewrite may touch, and gluing answers onto it would hand the Architect an
    ever-longer brief in place of "here is what they asked, and here is what they
    have since told you".

    **Section order is fixed, and stable-first within one as-of date.**  Everything the Commission
    settles comes before anything that accumulates: the clarification exchange
    only ever grows by appending, and the revision pair is last.  So each
    successive call sends the previous call's prompt plus a suffix, which is the
    one shape a vendor prefix cache can actually reuse -- and it costs nothing
    beyond deciding the order, which is why there is no cache bookkeeping here.
    Crossing a calendar date intentionally changes the date fact and therefore
    the operation input; an old cache is not allowed to turn "current" into
    yesterday silently.
    """

    effective_date = as_of_date.strip() or date.today().isoformat()
    parts = [
        "## 用户原始委托（不可改写）\n\n" + request.strip(),
        "## 来源授权\n\n"
        + "、".join(source_access)
        + ("\n\n没有授权公开网络检索，方案不得依赖外部检索。"
           if "public_web" not in source_access
           else ""),
        f"## 交付语言\n\n{language}",
        "## 当前日期（运行时事实）\n\n"
        + effective_date
        + "\n\n委托中的‘当前’‘最新’‘截至目前’均以此日期为准。",
    ]
    if constraints:
        parts.append(
            "## 用户明确约束\n\n"
            + "\n".join(f"- {item}" for item in constraints)
        )
    if clarifications:
        exchange = "\n\n".join(
            f"Q{index}. {question.strip()}\nA{index}. {answer.strip()}"
            for index, (question, answer) in enumerate(clarifications, start=1)
        )
        parts.append(
            "## 你之前提出的澄清问题与用户的回答\n\n"
            + exchange
            + "\n\n这些回答与原始委托同等有效，不要再问已经得到答案的问题。"
        )
    if previous_contract.strip():
        parts.append("## 上一份候选\n\n" + previous_contract.strip())
    if revision_note.strip():
        parts.append(
            "## 用户要求的修改\n\n"
            + revision_note.strip()
            + "\n\n请提交一份完整替代候选，不要在旧正文后追加修订说明。"
        )
    return "\n\n".join(parts)


__all__ = [
    "ASK_SCOPE_QUESTION",
    "PROPOSE_CONTRACT",
    "SPEC",
    "SYSTEM_PROMPT",
    "architect_context_body",
    "make_validator",
]
