"""The single consolidated report judge.

One judge with a multi-domain rubric, not a panel of specialists.  The public
guidance behind this project's evaluation design is explicit that a single judge
with one rubric produces more consistent verdicts than several narrow ones, and
the practical reason is visible in the alternative: five judges give five
partially-overlapping opinions that then need a meta-rule to combine, and that
meta-rule is where an average sneaks back in.

The judge sees the **whole evidence set**, not only what the report cited, for
the same reason the Reviewer does: selective omission is the most consequential
reporting failure and it is invisible from the report alone.

It is *not* a research role.  It never appears in a run, has no tools but its
verdict, and lives here rather than in the package's ``agents/`` alongside the
seven roles.  What it grades is the report; resource utilisation is reported
beside it and never folded in (`docs/ARCHITECTURE.md` §10.6).
"""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from deep_research_agent.agents import AgentSpec, ToolError, invoke_agent
from deep_research_agent.artifact_store import SqliteArtifactStore
from deep_research_agent.context import (
    RoleContext,
    latest_body,
    load_contract,
    load_evidence,
)
from deep_research_agent.model import ToolSpec
from deep_research_agent.operations import ExecutionIdentity, SqliteOperationLedger
from deep_research_agent.sources import ArtifactValidationError

_ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("eval_rubric", _ROOT / "evals" / "rubric.py")
assert _spec is not None and _spec.loader is not None
rubric = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("eval_rubric", rubric)
_spec.loader.exec_module(rubric)


SYSTEM_PROMPT = """\
你是 Report Judge。你对一份已发布的研究报告做**分层判定**，不打总分。

你会看到：研究合同、评分表、报告全文，以及**当前证据集的全部素材**（包括报告没有
引用的那些）。看得到未被引用的素材是有意的——选择性遗漏是最严重的报告缺陷，只读
报告是发现不了的。

判定规则：

- 五个**关键域**逐一判定通过或失败。任一失败即不可发布。
- 十个**非关键域**逐一判定。它们单项不阻断，累积会降级。
- **不要输出总分或平均分。** 一个致命缺陷不能被九个良好维度稀释。
- 每一项都要给一句具体理由，指向报告里的具体位置或具体主张。理由不能是
  「整体不错」这类无法核对的话。

尤其注意两件容易判错的事：

1. **低确定性不是缺陷。** 一份诚实说「现有证据不足以支撑该结论」并披露缺口的报告，
   可以是最高档。过度自信、隐瞒局限、伪造支撑才是失败。
2. **不要因为「也许还能再检索」而判失败。** 除非你能说出缺的是哪一条具体证据、
   以及它会如何改变结论。证据世界本身不完整，而报告已准确限定并披露，这不是缺陷。

用中文提交 submit_judgement。\
"""


def _domain_enum(domains: Sequence[Any]) -> list[str]:
    return [domain.key for domain in domains]


def _verdict_array(domains: Sequence[Any], label: str) -> Mapping[str, Any]:
    return {
        "type": "array",
        "description": f"{label}，每个域恰好一条。",
        "minItems": len(domains),
        "maxItems": len(domains),
        "items": {
            "type": "object",
            "properties": {
                "domain": {"type": "string", "enum": _domain_enum(domains)},
                "passed": {"type": "boolean"},
                "reason": {
                    "type": "string",
                    "minLength": 8,
                    "description": "指向报告具体位置或具体主张的一句理由。",
                },
            },
            "required": ["domain", "passed", "reason"],
            "additionalProperties": False,
        },
    }


SUBMIT_JUDGEMENT = ToolSpec(
    name="submit_judgement",
    description="提交分层判定。这是唯一的终结动作，不要输出总分。",
    parameters={
        "type": "object",
        "properties": {
            "critical": _verdict_array(rubric.CRITICAL, "五个关键域的判定"),
            "supporting": _verdict_array(rubric.SUPPORTING, "十个非关键域的判定"),
            "summary": {
                "type": "string",
                "minLength": 30,
                "description": "一段话说明这份报告最强与最弱的地方，不要复述评分表。",
            },
        },
        "required": ["critical", "supporting", "summary"],
        "additionalProperties": False,
    },
)

SPEC = AgentSpec(
    role="judge",
    system_prompt=SYSTEM_PROMPT,
    tools=(SUBMIT_JUDGEMENT,),
    terminal_tools=frozenset({"submit_judgement"}),
)


def _triples(raw: Any) -> list[tuple[str, bool, str]]:
    return [
        (
            str(item.get("domain", "")),
            bool(item.get("passed", False)),
            str(item.get("reason", "")),
        )
        for item in (raw or ())
        if isinstance(item, Mapping)
    ]


def make_validator():  # noqa: ANN201 - matches the runner's TerminalValidator
    """Turn a malformed judgement into a correction rather than a crash.

    The rubric refuses a verdict that omits or repeats a domain, so an incomplete
    judgement comes back to the judge naming exactly what is missing.
    """

    def validate(name: str, arguments: Mapping[str, Any]) -> ToolError | None:
        try:
            rubric.build_verdict(
                _triples(arguments.get("critical")),
                _triples(arguments.get("supporting")),
            )
        except (ValueError, ArtifactValidationError) as error:
            return ToolError(
                action=name,
                problem=str(error),
                allowed=(
                    "关键域："
                    + "、".join(_domain_enum(rubric.CRITICAL))
                    + "；非关键域："
                    + "、".join(_domain_enum(rubric.SUPPORTING))
                ),
            )
        return None

    return validate


@dataclass(frozen=True, slots=True)
class Judgement:
    """A verdict bound to the exact report artifact it was made about."""

    report_ref: str
    verdict: Any
    summary: str

    def render(self) -> str:
        return f"{self.verdict.render()}\n\n小结：{self.summary}"


def judge_context(
    contract: Any, evidence: Any, report: str, *, report_ref: str
) -> RoleContext:
    """Everything the judge needs and nothing that would bias it.

    The Reviewer's own verdict is deliberately withheld: the judge exists partly
    to check whether the gate was right, and showing it the answer first would
    turn an independent judgement into agreement.
    """

    body = "\n".join(
        [
            f"## 研究合同\n\n{contract.body_markdown.strip()}\n",
            f"## 评分表\n\n{rubric.render_rubric()}\n",
            (
                "## 当前证据集全集（含报告未引用的素材）\n\n"
                f"素材数：{len(evidence.materials)}\n\n"
                f"{evidence.render(with_handles=True)}\n"
            ),
            f"## 待判定报告\n\n{report.strip()}\n",
        ]
    )
    return RoleContext(
        role="judge",
        purpose="对一份已发布报告做分层判定",
        body=body,
        input_refs=(report_ref, *evidence.material_refs),
    )


async def judge_report(
    store: SqliteArtifactStore,
    ledger: SqliteOperationLedger,
    *,
    model: Any,
    execution: ExecutionIdentity,
) -> Judgement:
    """Judge the published report a database holds.

    Routed through the operation ledger like any other paid call, so re-running
    the judge on an unchanged report replays instead of paying again -- and
    editing the judge's prompt correctly counts as different work.
    """

    contract = await load_contract(store)
    evidence = await load_evidence(store)
    published = await latest_body(store, "publication_receipt")
    if published is None:
        raise ArtifactValidationError("this task has no published report to judge")
    report_ref, report = published

    action = await invoke_agent(
        SPEC,
        judge_context(contract, evidence, report, report_ref=report_ref),
        model=model,
        ledger=ledger,
        task_id=store.task_id,
        execution=execution,
        validate=make_validator(),
    )
    return Judgement(
        report_ref=report_ref,
        verdict=rubric.build_verdict(
            _triples(action.arguments.get("critical")),
            _triples(action.arguments.get("supporting")),
        ),
        summary=str(action.arguments.get("summary", "")),
    )


__all__ = [
    "SPEC",
    "SUBMIT_JUDGEMENT",
    "SYSTEM_PROMPT",
    "Judgement",
    "judge_context",
    "judge_report",
    "make_validator",
    "rubric",
]
