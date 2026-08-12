from __future__ import annotations

import json
import unittest
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from deep_research_agent.llm_roles import (
    CuratorExecutor,
    EditorExecutor,
    SupervisorExecutor,
    SynthesizerExecutor,
    ValidatorExecutor,
    WriterExecutor,
)
from deep_research_agent.model import ModelProtocolError, ModelReply, ToolSpec
from deep_research_agent.roles import (
    CuratorContext,
    EditorContext,
    SupervisorContext,
    SynthesizerContext,
    ValidatorContext,
    WriterContext,
)
from deep_research_agent.state import (
    BodyRef,
    CuratedMaterial,
    HydratedSource,
    ResearchContract,
    ResearchSynthesis,
    SourceDocument,
    ValidationFinding,
    locate_quote,
)


LIMIT = 6_000


class InspectingModel:
    def __init__(
        self, responder: Callable[[Mapping[str, Any], str], Mapping[str, Any]]
    ) -> None:
        self._responder = responder
        self.contexts: list[Mapping[str, Any]] = []
        self.payload_sizes: list[int] = []

    async def complete(
        self,
        messages: Sequence[Mapping[str, Any]],
        *,
        json_output: bool = False,
        tools: Sequence[ToolSpec] = (),
        tool_choice: str | None = None,
    ) -> ModelReply:
        self.payload_sizes.append(
            len(json.dumps(messages, ensure_ascii=False, separators=(",", ":")))
        )
        user = str(messages[1]["content"])
        context_text = user.split("\n\n", 1)[1].rsplit(
            "\n\n只返回 JSON 对象，不要代码围栏。JSON 形状：\n", 1
        )[0]
        context = json.loads(context_text)
        self.contexts.append(context)
        value = self._responder(context, str(messages[0]["content"]))
        return ModelReply(content=json.dumps(value, ensure_ascii=False))


def _seen(context: Mapping[str, Any], sentinels: Sequence[str]) -> list[str]:
    serialized = json.dumps(context, ensure_ascii=False, separators=(",", ":"))
    return [sentinel for sentinel in sentinels if sentinel in serialized]


def _source_and_materials(
    sentinels: Sequence[str], *, filler: int = 2_800
) -> tuple[HydratedSource, dict[str, CuratedMaterial]]:
    quote = "stable exact quote"
    body = quote + "\n" + ("x" * filler).join(sentinels)
    document = SourceDocument.create(
        title="Capacity source",
        url="https://example.org/capacity",
        body_ref=BodyRef.from_content(body),
    )
    source = HydratedSource(
        source_id=document.source_id,
        title=document.title,
        url=document.url,
        content=body,
        content_hash=document.content_hash,
        fetched_at=document.fetched_at,
        metadata=dict(document.metadata),
    )
    anchor = locate_quote(source, quote)
    materials = {
        material.material_id: material
        for material in (
            CuratedMaterial.create(
                content=("m" * filler) + sentinel,
                boundaries="bounded test material",
                anchors=(anchor,),
            )
            for sentinel in sentinels
        )
    }
    return source, materials


class BoundedRoleContextTest(unittest.IsolatedAsyncioTestCase):
    def assert_bounded(self, model: InspectingModel) -> None:
        self.assertGreater(len(model.contexts), 1)
        self.assertTrue(model.payload_sizes)
        self.assertLessEqual(max(model.payload_sizes), LIMIT)

    async def test_curator_chunks_one_large_source_without_losing_sentinels(self) -> None:
        sentinels = ("CURATOR_SENTINEL_A", "CURATOR_SENTINEL_B", "CURATOR_SENTINEL_C")
        source, _ = _source_and_materials(sentinels, filler=3_200)
        observed: set[str] = set()
        old_material = CuratedMaterial.create(
            content="obsolete incorrect material",
            boundaries="must be removed",
            anchors=(locate_quote(source, sentinels[0]),),
        )

        def respond(context: Mapping[str, Any], _: str) -> Mapping[str, Any]:
            mode = str(context.get("execution_mode", ""))
            visible = _seen(context, sentinels)
            observed.update(visible)
            if "final global Curator decision" not in mode:
                return {
                    "observation": "candidate exact quotes "
                    + " ".join(visible or ["neutral"])
                }
            materials: list[dict[str, Any]] = []
            for sentinel in visible:
                materials.append(
                    {
                        "content": f"accepted {sentinel}",
                        "boundaries": "test boundary",
                        "anchors": [
                            {
                                "source_id": source.source_id,
                                "exact_quote": sentinel,
                                "occurrence": 1,
                            }
                        ],
                    }
                )
            return {
                "materials": materials,
                "summary": "final replacement library",
                "blocking_issue": "",
            }

        model = InspectingModel(respond)
        output = await CuratorExecutor(model, max_payload_chars=LIMIT)(
            CuratorContext(
                contract=ResearchContract("test contract", approved=True),
                guide_text="",
                branch_handoffs=(),
                candidate_journal=(),
                source_corpus={source.source_id: source},
                existing_materials={old_material.material_id: old_material},
            )
        )
        self.assertEqual(observed, set(sentinels))
        self.assertEqual(len(output.materials), len(sentinels))
        self.assertNotIn(old_material.material_id, output.materials)
        self.assert_bounded(model)

    async def test_synthesizer_hierarchically_processes_every_material(self) -> None:
        sentinels = ("SYNTH_SENTINEL_A", "SYNTH_SENTINEL_B", "SYNTH_SENTINEL_C")
        _, materials = _source_and_materials(sentinels)
        observed_material_ids: set[str] = set()
        local_blocked = False

        def respond(context: Mapping[str, Any], _: str) -> Mapping[str, Any]:
            nonlocal local_blocked
            serialized = json.dumps(context, ensure_ascii=False)
            observed_material_ids.update(
                material_id for material_id in materials if material_id in serialized
            )
            visible = _seen(context, sentinels)
            mode = str(context.get("execution_mode", ""))
            blocked = ""
            if "bounded material analysis batch" in mode:
                blocked = "temporary local gap"
                local_blocked = True
            return {
                "research_synthesis": "synthesis " + " ".join(visible or ["neutral"]),
                "blocking_issue": blocked,
            }

        model = InspectingModel(respond)
        output = await SynthesizerExecutor(model, max_payload_chars=LIMIT)(
            SynthesizerContext(
                ResearchContract("test contract", approved=True), "", materials
            )
        )
        self.assertEqual(observed_material_ids, set(materials))
        for sentinel in sentinels:
            self.assertIn(sentinel, output.synthesis.content)
        self.assertTrue(local_blocked)
        self.assertEqual(output.blocking_issue, "")
        self.assert_bounded(model)

    async def test_writer_hierarchically_preserves_material_and_citation_inputs(self) -> None:
        sentinels = ("WRITER_SENTINEL_A", "WRITER_SENTINEL_B", "WRITER_SENTINEL_C")
        source, materials = _source_and_materials(sentinels)
        observed_material_ids: set[str] = set()
        local_blocked = False

        def respond(context: Mapping[str, Any], _: str) -> Mapping[str, Any]:
            nonlocal local_blocked
            serialized = json.dumps(context, ensure_ascii=False)
            observed_material_ids.update(
                material_id for material_id in materials if material_id in serialized
            )
            visible = _seen(context, sentinels)
            cites = (
                f" [[cite:{source.source_id}]]" if source.source_id in serialized else ""
            )
            mode = str(context.get("execution_mode", ""))
            blocked = ""
            if "bounded composition batch" in mode:
                blocked = "temporary local writing gap"
                local_blocked = True
            return {
                "draft": "draft " + " ".join(visible or ["neutral"]) + cites,
                "material_blocked": blocked,
            }

        model = InspectingModel(respond)
        synthesis = ResearchSynthesis(" ".join(sentinels))
        output = await WriterExecutor(model, max_payload_chars=LIMIT)(
            WriterContext(
                ResearchContract("test contract", approved=True),
                "",
                synthesis,
                materials,
            )
        )
        self.assertEqual(observed_material_ids, set(materials))
        for sentinel in sentinels:
            self.assertIn(sentinel, output.draft)
        self.assertIn(f"[[cite:{source.source_id}]]", output.draft)
        self.assertTrue(local_blocked)
        self.assertEqual(output.material_blocked, "")
        self.assert_bounded(model)

    async def test_validator_makes_one_global_cross_artifact_judgment(self) -> None:
        sentinels = ("CHAIN_SOURCE_EXPECTED", "CHAIN_MATERIAL_OTHER", "CHAIN_REPORT_EXPECTED")
        source, materials = _source_and_materials(sentinels[:2], filler=3_100)
        material_id = next(iter(materials))
        observed: set[str] = set()

        def respond(context: Mapping[str, Any], _: str) -> Mapping[str, Any]:
            observed.update(_seen(context, sentinels))
            mode = str(context.get("execution_mode", ""))
            if "final global Validator judgment" not in mode:
                return {
                    "observation": "chain facts "
                    + " ".join(_seen(context, sentinels) or ["neutral"])
                }
            if all(sentinel in json.dumps(context, ensure_ascii=False) for sentinel in sentinels):
                return {
                    "status": "findings",
                    "findings": [
                        {
                            "issue": "cross-artifact meaning mismatch",
                            "location": "report segment",
                            "related_material_ids": [material_id],
                            "related_source_ids": [source.source_id],
                            "severity_reason": "accuracy",
                        }
                    ],
                }
            return {"status": "pass", "findings": []}

        model = InspectingModel(respond)
        output = await ValidatorExecutor(model, max_payload_chars=LIMIT)(
            ValidatorContext(
                "full audit",
                ResearchContract("test contract", approved=True),
                "",
                {source.source_id: source},
                materials,
                ResearchSynthesis("CHAIN_MATERIAL_OTHER" + ("s" * 7_000)),
                "CHAIN_REPORT_EXPECTED" + ("r" * 7_000),
            )
        )
        self.assertEqual(observed, set(sentinels))
        self.assertEqual(output.status, "findings")
        self.assertEqual(len(output.findings), 1)
        self.assert_bounded(model)

    async def test_editor_final_global_judgment_can_clear_or_keep_batch_escalation(
        self,
    ) -> None:
        sentinels = (
            "EDITOR_DRAFT_A",
            "EDITOR_SYNTHESIS_B",
            "EDITOR_MATERIAL_C",
            "EDITOR_FINDING_ESCALATE",
        )
        source, materials = _source_and_materials((sentinels[2],), filler=3_300)
        material_id = next(iter(materials))

        for final_status in ("edited", "needs_supervisor"):
            with self.subTest(final_status=final_status):
                saw_local_escalation = False
                saw_prior_escalation = False
                saw_prior_substantive_change = False

                def respond(
                    context: Mapping[str, Any], _: str
                ) -> Mapping[str, Any]:
                    nonlocal saw_local_escalation, saw_prior_escalation
                    nonlocal saw_prior_substantive_change
                    serialized = json.dumps(context, ensure_ascii=False)
                    visible = _seen(context, sentinels)
                    mode = str(context.get("execution_mode", ""))
                    is_final = "final global Editor judgment" in mode
                    is_local_escalation = (
                        "bounded edit batch" in mode
                        and sentinels[3] in serialized
                    )
                    saw_local_escalation = (
                        saw_local_escalation or is_local_escalation
                    )
                    if is_final:
                        saw_prior_escalation = bool(
                            context.get("prior_escalation_observed")
                        )
                        saw_prior_substantive_change = bool(
                            context.get("prior_substantive_change_observed")
                        )
                    cite = (
                        f" [[cite:{source.source_id}]]"
                        if source.source_id in serialized
                        else ""
                    )
                    return {
                        "status": (
                            final_status
                            if is_final
                            else (
                                "needs_supervisor"
                                if is_local_escalation
                                else "edited"
                            )
                        ),
                        "edited_report": "edited "
                        + " ".join(visible or ["neutral"])
                        + cite,
                        "resolution_notes": (
                            f"final decision: {final_status}"
                            if is_final
                            else (
                                "local escalation observation"
                                if is_local_escalation
                                else "working observation"
                            )
                        ),
                        "substantive_change": False
                        if is_final
                        else sentinels[0] in serialized,
                        "closure_scope": (
                            "final scope" if is_final else "working scope"
                        ),
                    }

                model = InspectingModel(respond)
                output = await EditorExecutor(model, max_payload_chars=LIMIT)(
                    EditorContext(
                        ResearchContract("test contract", approved=True),
                        "",
                        ResearchSynthesis(sentinels[1] + ("s" * 7_000)),
                        materials,
                        sentinels[0] + ("d" * 7_000),
                        (
                            ValidationFinding(
                                issue=sentinels[3] + ("f" * 4_000),
                                location="draft",
                                related_material_ids=(material_id,),
                                related_source_ids=(source.source_id,),
                            ),
                        ),
                    )
                )
                self.assertTrue(saw_local_escalation)
                self.assertTrue(saw_prior_escalation)
                self.assertTrue(saw_prior_substantive_change)
                self.assertEqual(output.status, final_status)
                self.assertFalse(output.substantive_change)
                self.assertEqual(
                    output.resolution_notes, f"final decision: {final_status}"
                )
                self.assertEqual(output.closure_scope, "final scope")
                for sentinel in sentinels:
                    self.assertIn(sentinel, output.edited_report)
                self.assertIn(f"[[cite:{source.source_id}]]", output.edited_report)
                self.assert_bounded(model)

    async def test_supervisor_reads_all_indexes_before_one_global_gate_action(self) -> None:
        sentinels = ("SOURCE_INDEX_A", "SOURCE_INDEX_B", "MATERIAL_INDEX_C")
        final_observation = ""

        def respond(context: Mapping[str, Any], _: str) -> Mapping[str, Any]:
            nonlocal final_observation
            mode = str(context.get("execution_mode", ""))
            visible = _seen(context, sentinels)
            if "final global Gate decision" in mode:
                final_observation = str(context.get("gate_observation", ""))
                return {
                    "assessment": "global Gate used " + " ".join(visible),
                    "actions": [
                        {
                            "target": "curator",
                            "instruction": "curate after global review",
                            "branch_id": "",
                            "relevant_source_ids": [],
                        }
                    ],
                }
            return {"observation": "observation " + " ".join(visible or ["neutral"])}

        model = InspectingModel(respond)
        context = SupervisorContext(
            contract=ResearchContract("test contract", approved=True),
            stage="research_review",
            research_tasks=(),
            branch_handoffs=(),
            source_ids=("src_a", "src_b"),
            journal_summary=(),
            material_ids=("mat_c",),
            research_synthesis=None,
            draft_available=False,
            findings=(),
            edited_report_available=False,
            final_report_available=False,
            amendments=(),
            source_index=tuple(sentinel + ("s" * 3_500) for sentinel in sentinels[:2]),
            material_index=(sentinels[2] + ("m" * 3_500),),
        )
        decision = await SupervisorExecutor(model, max_payload_chars=LIMIT)(context)
        for sentinel in sentinels:
            self.assertIn(sentinel, final_observation)
        self.assertEqual(decision.actions[0].target, "curator")
        self.assert_bounded(model)

    async def test_fixed_role_context_that_cannot_fit_fails_without_calling_model(
        self,
    ) -> None:
        model = InspectingModel(
            lambda _context, _prompt: {
                "research_synthesis": "must not run",
                "blocking_issue": "",
            }
        )
        with self.assertRaisesRegex(ModelProtocolError, "refusing to omit"):
            await SynthesizerExecutor(model, max_payload_chars=LIMIT)(
                SynthesizerContext(
                    ResearchContract("contract " + ("x" * 20_000), approved=True),
                    "",
                    {},
                )
            )
        self.assertEqual(model.contexts, [])


if __name__ == "__main__":
    unittest.main()
