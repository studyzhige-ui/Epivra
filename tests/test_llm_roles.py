from __future__ import annotations

import json
import unittest
from collections.abc import Mapping, Sequence
from typing import Any

from deep_research_agent.llm_roles import (
    CuratorExecutor,
    EditorExecutor,
    PlannerExecutor,
    SupervisorExecutor,
    SynthesizerExecutor,
    ValidatorExecutor,
    WriterExecutor,
)
from deep_research_agent.model import ModelProtocolError, ModelReply, ToolSpec
from deep_research_agent.roles import (
    CuratorContext,
    EditorContext,
    PlannerContext,
    SupervisorContext,
    SynthesizerContext,
    ValidatorContext,
    WriterContext,
)
from deep_research_agent.state import (
    BodyRef,
    BranchHandoff,
    HydratedSource,
    ResearchContract,
    SourceDocument,
)


def hydrated_source(*, title: str, url: str, content: str) -> HydratedSource:
    source = SourceDocument.create(
        title=title,
        url=url,
        body_ref=BodyRef.from_content(content),
    )
    return HydratedSource(
        source_id=source.source_id,
        title=source.title,
        url=source.url,
        content=content,
        content_hash=source.content_hash,
        fetched_at=source.fetched_at,
        metadata=dict(source.metadata),
    )


class ScriptedModel:
    def __init__(self, values: Sequence[Mapping[str, Any]]) -> None:
        self._values = list(values)
        self.calls: list[dict[str, Any]] = []

    async def complete(
        self,
        messages: Sequence[Mapping[str, Any]],
        *,
        json_output: bool = False,
        tools: Sequence[ToolSpec] = (),
        tool_choice: str | None = None,
    ) -> ModelReply:
        self.calls.append(
            {
                "messages": tuple(messages),
                "json_output": json_output,
                "tools": tuple(tools),
                "tool_choice": tool_choice,
            }
        )
        if not self._values:
            raise AssertionError("scripted model ran out of replies")
        return ModelReply(content=json.dumps(self._values.pop(0), ensure_ascii=False))


class ToollessLlmRolesTest(unittest.IsolatedAsyncioTestCase):
    async def test_seven_roles_have_narrow_toolless_protocols(self) -> None:
        source = hydrated_source(
            title="Primary source",
            url="https://example.org/report",
            content="Opening. Exact primary evidence. Closing.",
        )
        contract = ResearchContract("回答问题并说明证据边界。", approved=True)
        model = ScriptedModel(
            [
                {
                    "status": "plan_ready",
                    "research_contract": "研究最新事实与重要反证。",
                    "approval_card": "研究目标：核验最新事实。",
                    "guide_refs": [],
                },
                {
                    "assessment": "来源发现已完成，进入策展。",
                    "actions": [
                        {
                            "target": "curator",
                            "instruction": "整理正式素材。",
                            "branch_id": "",
                        }
                    ],
                },
                {
                    "materials": [
                        {
                            "content": "主要来源给出了直接证据。",
                            "boundaries": "仅适用于该报告的明确范围。",
                            "anchors": [
                                {
                                    "source_id": source.source_id,
                                    "exact_quote": "Exact primary evidence.",
                                    "occurrence": 1,
                                }
                            ],
                        }
                    ],
                    "summary": "形成一条可写作素材。",
                    "blocking_issue": "",
                },
                {
                    "research_synthesis": "证据支持有限范围内的结论。",
                    "blocking_issue": "",
                },
                {
                    "draft": "结论受到直接证据支持。",
                    "material_blocked": "",
                },
                {"status": "pass", "findings": []},
                {
                    "status": "edited",
                    "edited_report": "结论受到直接证据支持。",
                    "resolution_notes": "仅改善表达。",
                    "substantive_change": False,
                    "closure_scope": "",
                },
            ]
        )

        plan = await PlannerExecutor(model)(PlannerContext(question="问题"))
        self.assertEqual(plan.contract.content, "研究最新事实与重要反证。")

        decision = await SupervisorExecutor(model)(
            SupervisorContext(
                contract=contract,
                stage="research_review",
                research_tasks=(),
                branch_handoffs=(),
                source_ids=(source.source_id,),
                journal_summary=(),
                material_ids=(),
                research_synthesis=None,
                draft_available=False,
                findings=(),
                edited_report_available=False,
                final_report_available=False,
                amendments=(),
            )
        )
        self.assertEqual(decision.actions[0].target, "curator")

        curated = await CuratorExecutor(model)(
            CuratorContext(
                contract=contract,
                guide_text="",
                branch_handoffs=(BranchHandoff("branch", "找到主要来源。"),),
                candidate_journal=(),
                source_corpus={source.source_id: source},
                existing_materials={},
            )
        )
        material = next(iter(curated.materials.values()))
        anchor = material.anchors[0]
        self.assertEqual(
            source.content[anchor.locator.start : anchor.locator.end],
            anchor.exact_quote,
        )

        synthesis = await SynthesizerExecutor(model)(
            SynthesizerContext(contract, "", curated.materials)
        )
        draft = await WriterExecutor(model)(
            WriterContext(contract, "", synthesis.synthesis, curated.materials)
        )
        validation = await ValidatorExecutor(model)(
            ValidatorContext(
                "draft: full report audit",
                contract,
                "",
                {source.source_id: source},
                curated.materials,
                synthesis.synthesis,
                draft.draft,
            )
        )
        edited = await EditorExecutor(model)(
            EditorContext(
                contract,
                "",
                synthesis.synthesis,
                curated.materials,
                draft.draft,
                validation.findings,
            )
        )
        self.assertEqual(edited.status, "edited")

        self.assertEqual(len(model.calls), 7)
        for call in model.calls:
            self.assertTrue(call["json_output"])
            self.assertEqual(call["tools"], ())
            self.assertIsNone(call["tool_choice"])

    async def test_rejects_schema_growth_and_unlocatable_quotes(self) -> None:
        extra = ScriptedModel(
            [
                {
                    "status": "needs_clarification",
                    "approval_card": "需要明确地区。",
                    "unexpected": "must fail",
                }
            ]
        )
        with self.assertRaises(ModelProtocolError):
            await PlannerExecutor(extra)(PlannerContext(question="问题"))

        source = hydrated_source(
            title="Source",
            url="https://example.org/source",
            content="Saved exact source text.",
        )
        bad_quote = ScriptedModel(
            [
                {
                    "materials": [
                        {
                            "content": "Unsupported material",
                            "boundaries": "No valid quote",
                            "anchors": [
                                {
                                    "source_id": source.source_id,
                                    "exact_quote": "Invented quote",
                                    "occurrence": 1,
                                }
                            ],
                        }
                    ],
                    "summary": "Should fail",
                    "blocking_issue": "",
                }
            ]
        )
        with self.assertRaises(ValueError):
            await CuratorExecutor(bad_quote)(
                CuratorContext(
                    contract=ResearchContract("Contract", approved=True),
                    guide_text="",
                    branch_handoffs=(),
                    candidate_journal=(),
                    source_corpus={source.source_id: source},
                    existing_materials={},
                )
            )


if __name__ == "__main__":
    unittest.main()
