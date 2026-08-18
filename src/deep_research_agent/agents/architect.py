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

Pack selection is a semantic judgment recorded in the Contract.  Choosing
nothing is a first-class answer: the system must reach a publishable report with
no packs, so packs are an improvement rather than a prerequisite.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ..contract import CONTRACT_SECTIONS, build_contract, section_title
from ..model import ToolSpec
from ..packs import PackCatalog, PackFormatError, validate_selection
from ..sources import ArtifactValidationError
from . import AgentSpec, ToolError

SYSTEM_PROMPT = """\
你是 Research Architect。你的唯一职责是把用户的原始研究委托转化为一份可审批的
Research Contract。

先弄清三件事：用户真正要理解或决定什么、谁会使用这份报告、什么范围与推断边界会
改变答案。

Contract 必须覆盖六个区块，每个用同名标题：

## 目的与用途
研究为何进行、由谁使用、支持什么判断，以及明确**不**支持什么用途。

## 问题模型
编号问题。`Q1` 是核心问题——报告最终必须回答它。`Q2` 起是支撑问题，每个都要能
说明它如何支撑 Q1。写成 `Q1. 问题正文` 这样的行（也可用 `### Q1. ...` 标题）。
不能解释自己作用的"主题"不要写进来。

## 范围与定义
对象、地域、时间点、关键术语、纳入与排除边界。把不确定项写成**醒目的默认假设**，
而不是留白。

## 证据与分析方法
来源策略、选择原则、如何主动寻找反证、如何处理冲突与不可比性、允许的推断强度。

## 交付与保证
受众、语言、输出形式、引用要求、独立审查。篇幅由体裁与证据密度决定，不预设字数。

## 自适应边界与已知限制
Research Lead 可以自行调整什么（查询、来源顺序、并行度），以及什么变化必须重新
获得用户批准（用途、Q1、关键对象/地域/时间、纳排标准、必需交付）。还要写明已知
的可行性限制。

硬性要求：

- **委托的前提可能不成立，这时你的职责是重写问题，不是继承它。** 委托可能预设了
  结论（"请论证 X 能降低 Y"）、要求证据给不出的精确度（"给出一个明确的排名"）、
  或把关联当成因果。遇到这种委托，Q1 要写成证据有可能回答的问题，并在「目的与用途」
  中写明你改写了什么、为什么改。把异议记进「已知限制」却让原问题继续当 Q1，等于让
  整份研究去服务一个你已经判断不成立的前提——报告最后必须回答 Q1，Q1 错了，后面每
  个角色都在为它工作。
- 只在**缺少答案会产生两个根本不同的研究任务**时才提问。其余不确定性写成默认假设。
  用户面对一串低价值问题的体验，比面对一个可以一键修正的清晰假设更差。关于用户自身
  情况的空白（行业、规模、现有系统、团队）几乎总是默认假设——用户在审批卡上一眼就
  能改。提问也不能用来回避委托本身的问题：那要靠上一条改写，不是靠反问用户。
- 不要写具体查询词、URL、固定来源数、固定 Wave 数、预期结论或最终文章目录。
- 不要承诺已经找到结论。你还没有做任何研究。
- 不要替用户批准。
- 能力包按需选择，**不选任何包是完全合法的默认**。包只在你判断这个领域/探究方式/
  体裁确实需要额外方法提示时才选，每类最多一个。

用中文撰写 Contract。\
"""

PROPOSE_CONTRACT = ToolSpec(
    name="propose_contract",
    description=(
        "提交一份完整的 Research Contract 候选，交给用户审批。"
        "这是终结动作之一。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "contract_markdown": {
                "type": "string",
                "minLength": 400,
                "description": "覆盖六个区块的完整 Contract，含编号问题 Q1..Qn。",
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
            "pack_refs": {
                "type": "array",
                "description": (
                    "可选。选中的能力包，形如 domain.medicine@1.0.0，每类最多一个。"
                    "留空表示不使用能力包，这是合法且常见的选择。"
                ),
                "items": {"type": "string"},
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


def make_validator(catalog: PackCatalog | None = None):
    """Validate a Contract candidate's mechanical shape, not its quality.

    Everything checked here is something the Architect can see and fix from the
    error alone: the six blocks are present, the question model is coherent, the
    selected packs exist.  Whether the prose is *good* is the user's judgment at
    the approval card, and later the Protocol Assurer's -- not a schema's.
    """

    def validate(name: str, arguments: Mapping[str, Any]) -> ToolError | None:
        if name == "ask_scope_question":
            return None

        markdown = str(arguments.get("contract_markdown", ""))
        supports = {
            str(label): tuple(str(item) for item in targets)
            for label, targets in dict(arguments.get("question_supports", {})).items()
        }
        refs = tuple(str(item) for item in arguments.get("pack_refs", ()) or ())

        try:
            contract = build_contract(markdown, supports=supports, pack_refs=refs)
        except ArtifactValidationError as error:
            return ToolError(
                action=name,
                problem=str(error),
                allowed="Q1 为核心问题，Q2 起须说明支撑关系，编号必须从 Q1 连续",
            )

        missing = contract.missing_sections()
        if missing:
            titles = "、".join(section_title(section) for section in missing)
            return ToolError(
                action=name,
                problem=f"缺少必需区块：{titles}",
                allowed="六个区块各用同名标题：" + "、".join(
                    section_title(section) for section in CONTRACT_SECTIONS
                ),
            )

        if refs:
            if catalog is None:
                return ToolError(
                    action=name,
                    problem="本次运行没有安装任何能力包，不能选择包引用",
                    allowed="留空 pack_refs",
                )
            try:
                validate_selection(catalog, refs)
            except (PackFormatError, KeyError) as error:
                return ToolError(
                    action=name,
                    problem=str(error).strip("'"),
                    allowed=catalog.offer(),
                )
        return None

    return validate


def architect_context_body(
    request: str,
    *,
    source_access: Sequence[str],
    language: str,
    constraints: Sequence[str] = (),
    pack_menu: str = "",
    revision_note: str = "",
    previous_contract: str = "",
) -> str:
    """Compose the Architect's context from the Commission and the pack menu.

    A revision passes the previous candidate and the user's note, because the
    Architect must produce a *complete replacement* Contract rather than append
    an amendment -- an approval binds one exact body, so patching a prior one
    would leave nothing coherent to approve.
    """

    parts = [
        "## 用户原始委托（不可改写）\n\n" + request.strip(),
        "## 来源授权\n\n"
        + "、".join(source_access)
        + ("\n\n没有授权公开网络检索，方案不得依赖外部检索。"
           if "public_web" not in source_access
           else ""),
        f"## 交付语言\n\n{language}",
    ]
    if constraints:
        parts.append(
            "## 用户明确约束\n\n"
            + "\n".join(f"- {item}" for item in constraints)
        )
    parts.append(
        "## 可选能力包\n\n" + (pack_menu or "（未安装能力包，本次不使用包）")
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
