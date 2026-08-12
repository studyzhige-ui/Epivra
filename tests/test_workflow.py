from __future__ import annotations

import unittest
from collections.abc import Callable
from dataclasses import replace

from langgraph.types import Command

from deep_research_agent.checkpoint import memory_checkpointer
from deep_research_agent.citations import CitationClosureError
from deep_research_agent.content_store import InMemoryContentStore, hydrate_source
from deep_research_agent.roles import (
    CuratorContext,
    CuratorOutput,
    EditorContext,
    EditorOutput,
    PlanOutput,
    PlannerContext,
    ResearcherContext,
    ResearcherOutput,
    RoleContractError,
    RoleExecutors,
    SupervisorAction,
    SupervisorContext,
    SupervisorDecision,
    SynthesizerContext,
    SynthesizerOutput,
    ValidatorContext,
    ValidatorOutput,
    WriterContext,
    WriterOutput,
    project_curator,
    project_supervisor,
    validate_supervisor_decision,
)
from deep_research_agent.state import (
    Amendment,
    BodyRef,
    BranchHandoff,
    CuratedMaterial,
    HydratedSource,
    JournalEntry,
    ResearchContract,
    ResearchSynthesis,
    SourceDocument,
    ValidationFinding,
    locate_quote,
)
from deep_research_agent.workflow import (
    build_research_graph,
    validate_supervisor_transition,
)


class OfflineRoles:
    def __init__(
        self,
        supervisor: Callable[[SupervisorContext, "OfflineRoles"], SupervisorDecision]
        | None = None,
        *,
        substantive_edit: bool = False,
        evidence_insufficient: bool = False,
        validation_findings_on_full: bool = False,
        clarify_first: bool = False,
    ) -> None:
        self.supervisor_policy = supervisor or self._normal_supervisor
        self.substantive_edit = substantive_edit
        self.evidence_insufficient = evidence_insufficient
        self.validation_findings_on_full = validation_findings_on_full
        self.clarify_first = clarify_first
        self.full_finding_emitted = False
        self.planner_calls = 0
        self.researcher_contexts: list[ResearcherContext] = []
        self.curator_contexts: list[CuratorContext] = []
        self.writer_contexts: list[WriterContext] = []
        self.validator_contexts: list[ValidatorContext] = []
        self.editor_contexts: list[EditorContext] = []
        self.content_store = InMemoryContentStore()

    def executors(self) -> RoleExecutors:
        owner = self

        class FreshValidator:
            async def __call__(self, context: ValidatorContext) -> ValidatorOutput:
                return await owner.validator(context)

        return RoleExecutors(
            planner=self.planner,
            supervisor=self.supervisor,
            researcher=self.researcher,
            curator=self.curator,
            synthesizer=self.synthesizer,
            writer=self.writer,
            validator_factory=FreshValidator,
            editor=self.editor,
        )

    async def planner(self, context: PlannerContext) -> PlanOutput:
        self.planner_calls += 1
        if self.clarify_first and self.planner_calls == 1:
            return PlanOutput(
                approval_card="研究对象是产品还是整个市场？",
                status="needs_clarification",
            )
        suffix = f" Revision {self.planner_calls}." if self.planner_calls > 1 else ""
        return PlanOutput(
            contract=ResearchContract(
                "研究问题、范围、Deep 深度、方法、完成条件。" + suffix
            ),
            approval_card="# 研究计划\n\n将围绕两个独立方面完成深度研究。",
        )

    @staticmethod
    def _normal_supervisor(
        context: SupervisorContext, _roles: "OfflineRoles"
    ) -> SupervisorDecision:
        if context.stage == "approved":
            return SupervisorDecision(
                "两个方面相互独立，可以并行。",
                (
                    SupervisorAction("researcher", "研究方面 A", "branch-a"),
                    SupervisorAction("researcher", "研究方面 B", "branch-b"),
                ),
            )
        if context.stage == "evidence_review":
            return SupervisorDecision(
                "来源已经整理，证据阶段通过。",
                (SupervisorAction("synthesizer", "综合正式素材"),),
            )
        if context.stage == "analysis_review":
            return SupervisorDecision(
                "分析阶段通过。", (SupervisorAction("writer", "撰写报告"),)
            )
        if context.stage == "edited_substantive":
            return SupervisorDecision(
                "实质编辑需要窄范围闭合验证。",
                (SupervisorAction("validator", "核验编辑影响的段落"),),
            )
        if context.stage in {"edited_style_only", "closure_passed"}:
            return SupervisorDecision(
                "发布门通过。",
                (SupervisorAction("citation_renderer", "编译引用"),),
            )
        raise AssertionError(f"unexpected supervisor stage: {context.stage}")

    async def supervisor(self, context: SupervisorContext) -> SupervisorDecision:
        return self.supervisor_policy(context, self)

    async def researcher(self, context: ResearcherContext) -> ResearcherOutput:
        self.researcher_contexts.append(context)
        branch = context.task.branch_id
        content = f"{branch} 的权威来源正文：可核验事实。"
        body_ref = await self.content_store.put(content)
        source = SourceDocument.create(
            title=f"{branch} source",
            url=f"https://example.test/{branch}",
            body_ref=body_ref,
        )
        anchor = locate_quote(
            await hydrate_source(source, self.content_store), "可核验事实"
        )
        return ResearcherOutput(
            sources={source.source_id: source},
            journal=(
                JournalEntry(
                    kind="finding",
                    content=f"{branch} 找到候选事实。",
                    anchors=(anchor,),
                    branch_id=branch,
                ),
            ),
            handoff=BranchHandoff(branch, f"{branch} 候选来源已筛选。"),
        )

    async def curator(self, context: CuratorContext) -> CuratorOutput:
        self.curator_contexts.append(context)
        materials: dict[str, CuratedMaterial] = {}
        for source in context.source_corpus.values():
            anchor = locate_quote(source, "可核验事实")
            material = CuratedMaterial.create(
                content=f"{source.title} 支持一项可核验事实。",
                boundaries="仅适用于本示例来源所述范围。",
                anchors=(anchor,),
            )
            materials[material.material_id] = material
        return CuratorOutput(materials, "候选内容均已回查原文并完成策展。")

    async def synthesizer(self, context: SynthesizerContext) -> SynthesizerOutput:
        ids = ", ".join(context.materials)
        if self.evidence_insufficient:
            text = f"当前证据不足以形成确定结论；已处理材料：{ids}。"
        else:
            text = f"两个方面共同支持有限结论；材料：{ids}。"
        return SynthesizerOutput(ResearchSynthesis(text))

    async def writer(self, context: WriterContext) -> WriterOutput:
        self.writer_contexts.append(context)
        source_ids = []
        for material in context.materials.values():
            source_ids.extend(anchor.source_id for anchor in material.anchors)
        conclusion = (
            "当前证据不足以确定"
            if self.evidence_insufficient
            else "现有证据支持有限结论"
        )
        marker = "[[cite:" + ",".join(dict.fromkeys(source_ids)) + "]]"
        return WriterOutput(f"# 报告\n\n{conclusion}。{marker}\n")

    async def validator(self, context: ValidatorContext) -> ValidatorOutput:
        self.validator_contexts.append(context)
        if (
            self.validation_findings_on_full
            and context.scope.startswith("draft")
            and not self.full_finding_emitted
        ):
            self.full_finding_emitted = True
            return ValidatorOutput(
                "findings",
                (
                    ValidationFinding(
                        issue="结论需要恢复正式素材中的限定。",
                        location="首段",
                        severity_reason="会扩大结论",
                    ),
                ),
            )
        return ValidatorOutput("pass")

    async def editor(self, context: EditorContext) -> EditorOutput:
        self.editor_contexts.append(context)
        return EditorOutput(
            status="edited",
            edited_report=context.draft.replace("# 报告", "# 深度研究报告"),
            resolution_notes="完成最终编辑。",
            substantive_change=self.substantive_edit,
            closure_scope="首段结论及相邻引用"
            if self.substantive_edit
            else "",
        )


async def run_approved(roles: OfflineRoles, thread_id: str) -> dict:
    graph = build_research_graph(
        roles.executors(),
        content_store=roles.content_store,
        checkpointer=memory_checkpointer(),
    )
    config = {"configurable": {"thread_id": thread_id}}
    interrupted = await graph.ainvoke(
        {"task_id": thread_id, "question": "测试问题"}, config
    )
    if "__interrupt__" not in interrupted:
        raise AssertionError("expected plan approval interrupt")
    return await graph.ainvoke(Command(resume={"action": "approve"}), config)


class WorkflowTests(unittest.IsolatedAsyncioTestCase):
    def test_source_provenance_is_detached_at_read_only_role_boundary(self) -> None:
        content = "Exact source content."
        source = SourceDocument.create(
            title="Source",
            url="https://example.com/source",
            body_ref=BodyRef.from_content(content),
            metadata={"content_from": "provider-a"},
        )
        state = {
            "research_contract": ResearchContract("Research this question."),
            "source_corpus": {source.source_id: source},
        }

        hydrated = HydratedSource(
            source_id=source.source_id,
            title=source.title,
            url=source.url,
            content=content,
            content_hash=source.content_hash,
            fetched_at=source.fetched_at,
            metadata=dict(source.metadata),
        )
        curator_context = project_curator(
            state, source_corpus={source.source_id: hydrated}
        )
        projected = curator_context.source_corpus[source.source_id]
        projected.metadata["content_from"] = "tampered"  # type: ignore[index]

        self.assertEqual("provider-a", source.metadata["content_from"])

    async def test_invalid_guide_selection_fails_before_human_approval(self) -> None:
        async def planner(_context: PlannerContext) -> PlanOutput:
            return PlanOutput(
                contract=ResearchContract(
                    "Contract with unavailable Guide.",
                    guide_refs=("domain.missing@1.0.0",),
                ),
                approval_card="Invalid plan",
            )

        def guide_context(_role: str, contract: ResearchContract) -> str:
            if contract.guide_refs:
                raise KeyError(contract.guide_refs[0])
            return ""

        roles = OfflineRoles()
        executors = replace(roles.executors(), planner=planner)
        graph = build_research_graph(
            executors,
            content_store=roles.content_store,
            checkpointer=memory_checkpointer(),
            guide_context=guide_context,
        )

        with self.assertRaisesRegex(RoleContractError, "unavailable"):
            await graph.ainvoke(
                {"task_id": "bad-guide", "question": "test"},
                {"configurable": {"thread_id": "bad-guide"}},
            )

    def test_stage_invariants_reject_shortcuts_around_research_and_assurance(self) -> None:
        approved = {
            "stage": "approved",
            "research_contract": ResearchContract("contract", approved=True),
        }
        with self.assertRaises(RoleContractError):
            validate_supervisor_transition(
                approved,
                SupervisorDecision(
                    "skip", (SupervisorAction("synthesizer", "skip research"),)
                ),
            )

        edited = {
            "stage": "edited_substantive",
            "research_contract": ResearchContract("contract", approved=True),
            "edited_report": "report",
        }
        with self.assertRaisesRegex(RoleContractError, "publication assurance"):
            validate_supervisor_transition(
                edited,
                SupervisorDecision(
                    "skip closure",
                    (SupervisorAction("citation_renderer", "publish now"),),
                ),
            )

        writer_blocked = {
            "stage": "user_responded",
            "research_contract": ResearchContract("contract", approved=True),
            "draft": "blocked draft",
            "publication_gate_status": "material_blocked",
        }
        for forbidden_target in ("validator", "editor", "citation_renderer"):
            with self.subTest(forbidden_target=forbidden_target):
                with self.assertRaisesRegex(RoleContractError, "material block"):
                    validate_supervisor_transition(
                        writer_blocked,
                        SupervisorDecision(
                            "try to bypass the block",
                            (SupervisorAction(forbidden_target),),
                        ),
                    )

        pending_closure = {
            "stage": "edited_substantive",
            "research_contract": ResearchContract("contract", approved=True),
            "draft": "validated draft",
            "edited_report": "changed report",
            "publication_gate_status": "closure_validation_required",
            "closure_validation_scope": "changed conclusion",
        }
        with self.assertRaisesRegex(RoleContractError, "only to closure"):
            validate_supervisor_transition(
                pending_closure,
                SupervisorDecision(
                    "edit it again",
                    (SupervisorAction("editor", "avoid validation"),),
                ),
            )

        stale_stage = {
            **pending_closure,
            "stage": "edited_style_only",
            "publication_gate_status": "full_validation_passed",
        }
        with self.assertRaisesRegex(RoleContractError, "publication assurance"):
            validate_supervisor_transition(
                stale_stage,
                SupervisorDecision(
                    "stage name alone must not publish",
                    (SupervisorAction("citation_renderer"),),
                ),
            )

        with self.assertRaisesRegex(RoleContractError, "unknown source IDs"):
            validate_supervisor_transition(
                approved,
                SupervisorDecision(
                    "inspect a source that does not exist",
                    (
                        SupervisorAction(
                            "researcher",
                            "verify",
                            "verify",
                            ("src_missing",),
                        ),
                    ),
                ),
            )

        editor_escalation = {
            "stage": "editor_needs_supervisor",
            "research_contract": ResearchContract("contract", approved=True),
            "source_corpus": {"src_known": object()},
            "curated_material_library": {"mat_known": object()},
            "research_synthesis": ResearchSynthesis("synthesis"),
            "draft": "validated draft",
            "edited_report": "editor report with unresolved issue",
            "final_report": "stale compiled report",
            "publication_gate_status": "closed",
        }
        for forbidden_target in ("validator", "citation_renderer", "finish"):
            with self.subTest(editor_escalation_target=forbidden_target):
                with self.assertRaisesRegex(
                    RoleContractError, "requires Supervisor L0/L1/L2 resolution"
                ):
                    validate_supervisor_transition(
                        editor_escalation,
                        SupervisorDecision(
                            "attempt to bypass Supervisor classification",
                            (SupervisorAction(forbidden_target),),
                        ),
                    )

        for target, level in (
            ("synthesizer", "L0"),
            ("researcher", "L1"),
            ("planner", "L2"),
        ):
            action = (
                SupervisorAction("researcher", "verify gap", "verify-branch")
                if target == "researcher"
                else SupervisorAction(target)
            )
            without_amendment = SupervisorDecision("resolve escalation", (action,))
            with self.subTest(editor_escalation_requires=level):
                with self.assertRaisesRegex(RoleContractError, f"matching {level}"):
                    validate_supervisor_transition(
                        editor_escalation, without_amendment
                    )
                valid = SupervisorDecision(
                    "resolve escalation",
                    (action,),
                    Amendment(level, "upstream issue", "affected scope", ("report",)),
                )
                validate_supervisor_decision(valid)
                validate_supervisor_transition(editor_escalation, valid)

        clarification = SupervisorDecision(
            "clarify the unresolved requirement", (SupervisorAction("user"),)
        )
        validate_supervisor_decision(clarification)
        validate_supervisor_transition(editor_escalation, clarification)

    async def test_editor_escalation_clarification_returns_to_supervisor_gate(
        self,
    ) -> None:
        asked_user = False
        saw_answer_at_gate = False
        editor_calls = 0

        def supervisor(
            context: SupervisorContext, roles: OfflineRoles
        ) -> SupervisorDecision:
            nonlocal asked_user, saw_answer_at_gate
            if context.stage == "editor_needs_supervisor":
                if not asked_user:
                    asked_user = True
                    return SupervisorDecision(
                        "请确认报告范围是否保持不变。",
                        (SupervisorAction("user"),),
                    )
                saw_answer_at_gate = "范围保持不变" in context.stage_note
                return SupervisorDecision(
                    "用户已澄清；问题只需在正文内修正。",
                    (SupervisorAction("editor", "按已批准范围完成编辑"),),
                    Amendment(
                        "L0",
                        "正文问题可由现有成果解决",
                        "最终正文",
                        ("edited_report",),
                    ),
                )
            return roles._normal_supervisor(context, roles)

        roles = OfflineRoles(supervisor)

        async def editor(context: EditorContext) -> EditorOutput:
            nonlocal editor_calls
            editor_calls += 1
            if editor_calls == 1:
                return EditorOutput(
                    status="needs_supervisor",
                    edited_report=context.draft,
                    resolution_notes="范围意图需要用户澄清。",
                )
            return EditorOutput(
                status="edited",
                edited_report=context.draft.replace("# 报告", "# 深度研究报告"),
                resolution_notes="按澄清后的既有范围完成编辑。",
            )

        graph = build_research_graph(
            replace(roles.executors(), editor=editor),
            content_store=roles.content_store,
            checkpointer=memory_checkpointer(),
        )
        config = {"configurable": {"thread_id": "editor-user-clarification"}}
        approval = await graph.ainvoke(
            {"task_id": "editor-user-clarification", "question": "测试问题"},
            config,
        )
        self.assertIn("__interrupt__", approval)

        clarification = await graph.ainvoke(Command(resume="approve"), config)
        self.assertIn("__interrupt__", clarification)
        self.assertEqual("editor_awaiting_user", clarification["stage"])

        final = await graph.ainvoke(Command(resume="范围保持不变"), config)
        self.assertTrue(saw_answer_at_gate)
        self.assertEqual("finished", final["stage"])
        self.assertEqual(["L0"], [item.level for item in final["amendments"]])

        with self.assertRaisesRegex(RoleContractError, "L2 amendment"):
            validate_supervisor_decision(
                SupervisorDecision(
                    "ask the user without replanning",
                    (SupervisorAction("user", "change the scope"),),
                    Amendment("L2", "scope invalid", "contract", ("contract",)),
                )
            )

    async def test_human_approval_precedes_research_and_resumes_same_thread(self) -> None:
        roles = OfflineRoles()
        graph = build_research_graph(
            roles.executors(),
            content_store=roles.content_store,
            checkpointer=memory_checkpointer(),
        )
        config = {"configurable": {"thread_id": "approval"}}

        state = await graph.ainvoke(
            {"task_id": "approval", "question": "测试问题"}, config
        )

        self.assertIn("__interrupt__", state)
        self.assertEqual([], roles.researcher_contexts)
        self.assertFalse(state["research_contract"].approved)

        final = await graph.ainvoke(Command(resume="approve"), config)

        self.assertEqual("finished", final["stage"])
        self.assertTrue(final["research_contract"].approved)
        self.assertIn("## References", final["final_report"])

    async def test_parallel_researchers_receive_isolated_branch_context(self) -> None:
        roles = OfflineRoles()

        final = await run_approved(roles, "parallel")

        self.assertEqual({"branch-a", "branch-b"}, {
            item.task.branch_id for item in roles.researcher_contexts
        })
        for context in roles.researcher_contexts:
            self.assertEqual((), context.branch_journal)
            self.assertEqual({}, dict(context.relevant_sources))
        self.assertEqual(2, len(final["source_corpus"]))
        self.assertEqual(2, len(final["curated_material_library"]))
        self.assertEqual(1, len(roles.curator_contexts))
        supervisor = project_supervisor(final)
        self.assertEqual(2, len(supervisor.source_index))
        self.assertEqual(2, len(supervisor.material_index))
        self.assertTrue(all("url: https://" in item for item in supervisor.source_index))
        self.assertTrue(
            all("boundaries:" in item for item in supervisor.material_index)
        )
        for source in final["source_corpus"].values():
            body = await roles.content_store.get(source.body_ref)
            self.assertNotIn(body, "\n".join(supervisor.source_index))

    async def test_writer_and_editor_never_receive_source_corpus_or_journal(self) -> None:
        roles = OfflineRoles()

        await run_approved(roles, "projection")

        writer = roles.writer_contexts[0]
        editor = roles.editor_contexts[0]
        self.assertFalse(hasattr(writer, "source_corpus"))
        self.assertFalse(hasattr(writer, "research_journal"))
        self.assertFalse(hasattr(editor, "source_corpus"))
        self.assertFalse(hasattr(editor, "research_journal"))
        self.assertTrue(writer.materials)

    async def test_validator_uses_fresh_read_only_context(self) -> None:
        roles = OfflineRoles(substantive_edit=True)

        final = await run_approved(roles, "validator")

        self.assertEqual(2, len(roles.validator_contexts))
        self.assertTrue(roles.validator_contexts[0].scope.startswith("draft"))
        self.assertTrue(roles.validator_contexts[1].scope.startswith("closure"))
        self.assertIn("首段结论及相邻引用", roles.validator_contexts[1].scope)
        self.assertNotIn("实质编辑需要", roles.validator_contexts[1].scope)
        for context in roles.validator_contexts:
            self.assertFalse(hasattr(context, "messages"))
            self.assertFalse(hasattr(context, "search_trace"))
        assurance = final["assurance_log"]
        self.assertEqual(
            ["independent_validator", "editor", "independent_validator"],
            [event.actor for event in assurance],
        )
        self.assertTrue(assurance[0].scope.startswith("draft"))
        self.assertTrue(assurance[-1].scope.startswith("closure"))
        self.assertTrue(all(len(event.artifact_digest) == 64 for event in assurance))
        self.assertTrue(all(event.recorded_at for event in assurance))

    async def test_validation_findings_force_closure_even_if_editor_calls_edit_style_only(self) -> None:
        roles = OfflineRoles(validation_findings_on_full=True)

        final = await run_approved(roles, "forced-closure")

        self.assertEqual("finished", final["stage"])
        self.assertEqual(2, len(roles.validator_contexts))
        self.assertTrue(roles.validator_contexts[1].scope.startswith("closure"))

    async def test_citation_removal_or_move_cannot_publish_as_style_only(
        self,
    ) -> None:
        class ClosureObserved(RuntimeError):
            pass

        for mode in ("remove", "move"):
            with self.subTest(mode=mode):
                roles = OfflineRoles()

                async def editor(context: EditorContext) -> EditorOutput:
                    marker_start = context.draft.index("[[cite:")
                    marker_end = context.draft.index("]]", marker_start) + 2
                    marker = context.draft[marker_start:marker_end]
                    without_marker = (
                        context.draft[:marker_start]
                        + context.draft[marker_end:]
                    )
                    edited = (
                        without_marker
                        if mode == "remove"
                        else marker + "\n" + without_marker
                    )
                    return EditorOutput(
                        status="edited",
                        edited_report=edited,
                        resolution_notes="只调整样式。",
                        substantive_change=False,
                    )

                class GuardValidator:
                    async def __call__(
                        self, context: ValidatorContext
                    ) -> ValidatorOutput:
                        roles.validator_contexts.append(context)
                        if context.scope.startswith("closure"):
                            raise ClosureObserved
                        return ValidatorOutput("pass")

                executors = replace(
                    roles.executors(),
                    editor=editor,
                    validator_factory=GuardValidator,
                )
                graph = build_research_graph(
                    executors,
                    content_store=roles.content_store,
                    checkpointer=memory_checkpointer(),
                )
                thread_id = f"citation-{mode}"
                config = {"configurable": {"thread_id": thread_id}}
                interrupted = await graph.ainvoke(
                    {"task_id": thread_id, "question": "测试问题"}, config
                )
                self.assertIn("__interrupt__", interrupted)

                with self.assertRaises(ClosureObserved):
                    await graph.ainvoke(Command(resume="approve"), config)

                self.assertEqual(2, len(roles.validator_contexts))
                self.assertIn(
                    "citation markers and their claim associations",
                    roles.validator_contexts[-1].scope,
                )
                snapshot = await graph.aget_state(config)
                self.assertFalse(snapshot.values.get("final_report"))

    async def test_zero_citation_report_cannot_publish_even_after_validator_pass(
        self,
    ) -> None:
        roles = OfflineRoles()

        async def editor(context: EditorContext) -> EditorOutput:
            marker_start = context.draft.index("[[cite:")
            marker_end = context.draft.index("]]", marker_start) + 2
            return EditorOutput(
                status="edited",
                edited_report=(
                    context.draft[:marker_start] + context.draft[marker_end:]
                ),
                resolution_notes="错误地删除了全部引用。",
                substantive_change=False,
            )

        graph = build_research_graph(
            replace(roles.executors(), editor=editor),
            content_store=roles.content_store,
            checkpointer=memory_checkpointer(),
        )
        config = {"configurable": {"thread_id": "zero-citations"}}
        interrupted = await graph.ainvoke(
            {"task_id": "zero-citations", "question": "测试问题"}, config
        )
        self.assertIn("__interrupt__", interrupted)

        with self.assertRaisesRegex(CitationClosureError, "at least one"):
            await graph.ainvoke(Command(resume="approve"), config)

        self.assertEqual(2, len(roles.validator_contexts))

    async def test_evidence_insufficiency_still_completes_full_report(self) -> None:
        roles = OfflineRoles(evidence_insufficient=True)

        final = await run_approved(roles, "insufficient")

        self.assertEqual("finished", final["stage"])
        self.assertIn("当前证据不足以确定", final["final_report"])
        self.assertEqual(2, len(roles.validator_contexts))
        self.assertEqual(1, len(roles.editor_contexts))

    async def test_l0_repeats_synthesis_without_new_search(self) -> None:
        revisited = False

        def supervisor(
            context: SupervisorContext, roles: OfflineRoles
        ) -> SupervisorDecision:
            nonlocal revisited
            if context.stage == "analysis_review" and not revisited:
                revisited = True
                return SupervisorDecision(
                    "分析措辞需要基于现有材料修正。",
                    (SupervisorAction("synthesizer", "重新处理限定"),),
                    Amendment("L0", "分析扩大", "综合结论", ("synthesis", "draft")),
                )
            return roles._normal_supervisor(context, roles)

        roles = OfflineRoles(supervisor)

        final = await run_approved(roles, "l0")

        self.assertEqual("finished", final["stage"])
        self.assertEqual(2, len(roles.researcher_contexts))
        self.assertEqual(["L0"], [item.level for item in final["amendments"]])

    async def test_l1_reopens_only_named_research_branch(self) -> None:
        reopened = False

        def supervisor(
            context: SupervisorContext, roles: OfflineRoles
        ) -> SupervisorDecision:
            nonlocal reopened
            if context.stage == "analysis_review" and not reopened:
                reopened = True
                return SupervisorDecision(
                    "核心冲突仍缺外部证据。",
                    (
                        SupervisorAction(
                            "researcher",
                            "定向核验冲突",
                            "verify-only",
                            context.source_ids[:1],
                        ),
                    ),
                    Amendment(
                        "L1", "缺决定性外部证据", "冲突 A", ("materials", "synthesis")
                    ),
                )
            return roles._normal_supervisor(context, roles)

        roles = OfflineRoles(supervisor)

        final = await run_approved(roles, "l1")

        branches = [item.task.branch_id for item in roles.researcher_contexts]
        self.assertEqual(["branch-a", "branch-b", "verify-only"], branches)
        verification = roles.researcher_contexts[-1]
        self.assertEqual(
            set(verification.task.relevant_source_ids),
            set(verification.relevant_sources),
        )
        self.assertTrue(verification.relevant_sources)
        self.assertEqual(["L1"], [item.level for item in final["amendments"]])

    async def test_reopened_branch_inherits_sources_anchored_in_its_journal(
        self,
    ) -> None:
        reopened = False

        class ChangingHandoffRoles(OfflineRoles):
            def __init__(self, policy) -> None:  # type: ignore[no-untyped-def]
                super().__init__(policy)
                self.branch_runs: dict[str, int] = {}

            async def researcher(
                self, context: ResearcherContext
            ) -> ResearcherOutput:
                output = await super().researcher(context)
                branch = context.task.branch_id
                self.branch_runs[branch] = self.branch_runs.get(branch, 0) + 1
                return ResearcherOutput(
                    output.sources,
                    output.journal,
                    BranchHandoff(
                        branch,
                        f"{branch} handoff round {self.branch_runs[branch]}",
                    ),
                )

        def supervisor(
            context: SupervisorContext, roles: OfflineRoles
        ) -> SupervisorDecision:
            nonlocal reopened
            if context.stage == "analysis_review" and not reopened:
                reopened = True
                return SupervisorDecision(
                    "继续核验 branch-a 已有来源中的限定。",
                    (
                        SupervisorAction(
                            "researcher",
                            "回查本分支原文限定",
                            "branch-a",
                        ),
                    ),
                    Amendment(
                        "L1",
                        "需要回查已有原文",
                        "branch-a",
                        ("materials", "synthesis"),
                    ),
                )
            return roles._normal_supervisor(context, roles)

        roles = ChangingHandoffRoles(supervisor)

        final = await run_approved(roles, "l1-same-branch")

        branch_a_contexts = [
            context
            for context in roles.researcher_contexts
            if context.task.branch_id == "branch-a"
        ]
        self.assertEqual(2, len(branch_a_contexts))
        reopened_context = branch_a_contexts[-1]
        self.assertTrue(reopened_context.branch_journal)
        self.assertEqual(1, len(reopened_context.relevant_sources))
        source = next(iter(reopened_context.relevant_sources.values()))
        self.assertEqual("branch-a source", source.title)
        latest_handoffs = roles.curator_contexts[-1].branch_handoffs
        self.assertEqual(
            1,
            sum(item.branch_id == "branch-a" for item in latest_handoffs),
        )
        self.assertIn(
            "round 2",
            next(
                item.summary
                for item in latest_handoffs
                if item.branch_id == "branch-a"
            ),
        )
        self.assertEqual("finished", final["stage"])

    async def test_l2_returns_to_planner_and_requires_new_approval(self) -> None:
        reopened = False

        def supervisor(
            context: SupervisorContext, roles: OfflineRoles
        ) -> SupervisorDecision:
            nonlocal reopened
            if context.stage == "analysis_review" and not reopened:
                reopened = True
                return SupervisorDecision(
                    "核心范围需要修改。",
                    (SupervisorAction("planner", "修改研究范围"),),
                    Amendment("L2", "范围失效", "研究问题", ("contract", "all")),
                )
            return roles._normal_supervisor(context, roles)

        roles = OfflineRoles(supervisor)
        graph = build_research_graph(
            roles.executors(),
            content_store=roles.content_store,
            checkpointer=memory_checkpointer(),
        )
        config = {"configurable": {"thread_id": "l2"}}
        first = await graph.ainvoke(
            {"task_id": "l2", "question": "测试问题"}, config
        )
        self.assertIn("__interrupt__", first)
        first_contract_content = first["research_contract"].content

        second = await graph.ainvoke(Command(resume="approve"), config)

        self.assertIn("__interrupt__", second)
        self.assertEqual(2, roles.planner_calls)
        self.assertFalse(second["research_contract"].approved)
        self.assertNotEqual(first_contract_content, second["research_contract"].content)
        self.assertEqual({}, second.get("source_corpus", {}))
        self.assertEqual([], second.get("research_journal", []))
        self.assertEqual([], second.get("branch_handoffs", []))


if __name__ == "__main__":
    unittest.main()
