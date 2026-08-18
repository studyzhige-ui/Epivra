from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import aiosqlite

from deep_research_agent.agents.architect import (
    SPEC,
    architect_context_body,
    contract_from_action,
    make_validator,
)
from deep_research_agent.approval import (
    ApprovalBody,
    ApprovalError,
    approval_card,
    approved_contract,
    decision_for,
    record_decision,
)
from deep_research_agent.artifact_store import SqliteArtifactStore
from deep_research_agent.content_store import SqliteContentStore
from deep_research_agent.contract import (
    CommissionBody,
    ResearchContract,
    build_contract,
)
from deep_research_agent.packs import PackCatalog
from deep_research_agent.sources import ArtifactValidationError

CONTRACT = """\
## 目的与用途

为医院母婴护理团队选择婴儿 RSV 预防路径提供依据。不支持个体化临床处方。

## 问题模型

### Q1. 对本院人群，母源疫苗与单克隆抗体应如何组合使用？
### Q2. 两条路径在住院与重症终点上的证据强度如何？
### Q3. 给药时点与季节性如何影响可行性？

## 范围与定义

时点为 2026 年 8 月。默认假设：仅考虑已获批产品。

## 证据与分析方法

优先监管标签、ACIP 记录与关键试验原文；主动检索反证与撤稿。

## 交付与保证

决策简报，中文，独立审查。

## 自适应边界与已知限制

查询与来源顺序由 Lead 自适应；改变人群或时点需重新审批。
"""


def pack_text(kind: str, pack_id: str) -> str:
    from deep_research_agent.packs import PACK_SECTIONS

    sections = "\n\n".join(
        f"## {name}\n\nguidance" for name in PACK_SECTIONS[kind]
    )
    return (
        f"---\nid: {pack_id}\nkind: {kind}\nversion: 1.0.0\n"
        f"title: T\nsummary: \"s\"\n---\n\n# T\n\n{sections}\n"
    )


class CommissionTest(unittest.TestCase):
    def test_the_request_is_preserved_verbatim(self) -> None:
        """Byte-for-byte, so the artifact hash covers exactly what was written."""

        raw = "  比较两条路径。\n注意时点。  "
        body = CommissionBody(request=raw, source_access=("public_web",))

        self.assertEqual(raw, body.request)
        self.assertEqual(body, CommissionBody.decode(body.encode()))
        self.assertEqual(raw, CommissionBody.decode(body.encode()).request)

    def test_source_access_is_a_permission_not_advice(self) -> None:
        offline = CommissionBody(request="x", source_access=("local_only",))
        online = CommissionBody(request="x", source_access=("public_web",))

        self.assertFalse(offline.allows_external_search)
        self.assertTrue(online.allows_external_search)

    def test_a_commission_must_authorise_something(self) -> None:
        with self.assertRaisesRegex(ArtifactValidationError, "at least one source"):
            CommissionBody(request="x", source_access=())
        with self.assertRaisesRegex(ArtifactValidationError, "unknown source access"):
            CommissionBody(request="x", source_access=("dark_web",))  # type: ignore[arg-type]


class ArchitectValidationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.validate = make_validator()

    def test_a_complete_candidate_passes(self) -> None:
        self.assertIsNone(
            self.validate(
                "propose_contract",
                {"contract_markdown": CONTRACT, "question_supports": {"Q3": ["Q2"]}},
            )
        )

    def test_a_missing_block_names_the_six_titles(self) -> None:
        trimmed = CONTRACT.split("## 交付与保证")[0]
        error = self.validate("propose_contract", {"contract_markdown": trimmed})

        assert error is not None
        self.assertIn("交付与保证", error.problem)
        self.assertIn("自适应边界与已知限制", error.problem)
        self.assertIn("目的与用途", error.allowed)

    def test_an_incoherent_question_model_is_correctable(self) -> None:
        broken = CONTRACT.replace("### Q2.", "### Q5.")
        error = self.validate("propose_contract", {"contract_markdown": broken})

        assert error is not None
        self.assertIn("contiguous", error.problem)
        self.assertIn("Q1", error.allowed)

    def test_a_scope_question_needs_no_contract(self) -> None:
        self.assertIsNone(
            self.validate(
                "ask_scope_question",
                {
                    "question": "面向本院还是全国？",
                    "why_it_changes_the_plan": "两者会导致完全不同的证据范围与结论。",
                },
            )
        )

    def test_the_architect_may_only_propose_or_ask(self) -> None:
        self.assertEqual(
            {"propose_contract", "ask_scope_question"}, set(SPEC.terminal_tools)
        )
        # No search tool: orientation is a later phase, and the Architect must
        # never be able to start formal research.
        self.assertEqual(
            {"propose_contract", "ask_scope_question"},
            {tool.name for tool in SPEC.tools},
        )


class PackSelectionTest(unittest.TestCase):
    def setUp(self) -> None:
        self._directory = tempfile.TemporaryDirectory()
        root = Path(self._directory.name)
        for kind, pack_id in (
            ("domain", "domain.medicine"),
            ("genre", "genre.decision-brief"),
        ):
            path = root / pack_id / "PACK.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(pack_text(kind, pack_id), encoding="utf-8")
        self.catalog = PackCatalog.discover(root)

    def tearDown(self) -> None:
        self._directory.cleanup()

    def test_choosing_no_pack_is_valid_with_or_without_a_catalog(self) -> None:
        for validate in (make_validator(), make_validator(self.catalog)):
            with self.subTest(catalog=validate is not None):
                self.assertIsNone(
                    validate("propose_contract", {"contract_markdown": CONTRACT})
                )

    def test_a_valid_selection_is_accepted(self) -> None:
        self.assertIsNone(
            make_validator(self.catalog)(
                "propose_contract",
                {
                    "contract_markdown": CONTRACT,
                    "pack_refs": ["domain.medicine@1.0.0", "genre.decision-brief@1.0.0"],
                },
            )
        )

    def test_an_unknown_pack_is_answered_with_the_menu(self) -> None:
        error = make_validator(self.catalog)(
            "propose_contract",
            {"contract_markdown": CONTRACT, "pack_refs": ["domain.astrology@1.0.0"]},
        )

        assert error is not None
        self.assertIn("domain.medicine@1.0.0", error.allowed)
        self.assertIn("不选任何包是合法选择", error.allowed)

    def test_selecting_a_pack_with_none_installed_is_refused(self) -> None:
        error = make_validator()(
            "propose_contract",
            {"contract_markdown": CONTRACT, "pack_refs": ["domain.medicine@1.0.0"]},
        )

        assert error is not None
        self.assertIn("留空 pack_refs", error.allowed)


class ContextTest(unittest.TestCase):
    def test_an_offline_commission_says_so_explicitly(self) -> None:
        body = architect_context_body(
            "比较两条路径。", source_access=["local_only"], language="zh"
        )
        self.assertIn("不得依赖外部检索", body)

        online = architect_context_body(
            "比较两条路径。", source_access=["public_web"], language="zh"
        )
        self.assertNotIn("不得依赖外部检索", online)

    def test_the_original_request_is_marked_unrewritable(self) -> None:
        body = architect_context_body(
            "原始委托正文。", source_access=["public_web"], language="zh"
        )
        self.assertIn("不可改写", body)
        self.assertIn("原始委托正文。", body)

    def test_a_revision_demands_a_complete_replacement(self) -> None:
        body = architect_context_body(
            "请求",
            source_access=["public_web"],
            language="zh",
            previous_contract=CONTRACT,
            revision_note="把地域限定到华东。",
        )
        self.assertIn("华东", body)
        self.assertIn("完整替代候选", body)
        self.assertIn("不要在旧正文后追加", body)

    def test_the_pack_menu_is_passed_through_and_optional(self) -> None:
        self.assertIn(
            "未安装能力包",
            architect_context_body("x", source_access=["public_web"], language="zh"),
        )


class ApprovalFixture(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._directory = tempfile.TemporaryDirectory()
        path = Path(self._directory.name) / "task.sqlite3"
        self._connection = await aiosqlite.connect(path)
        content = SqliteContentStore(self._connection)
        await content.setup()
        self.store = SqliteArtifactStore(self._connection, content, task_id="t1")
        await self.store.setup()

    async def asyncTearDown(self) -> None:
        await self._connection.close()
        self._directory.cleanup()

    async def commit_contract(self, markdown: str = CONTRACT) -> str:
        contract = build_contract(markdown, supports={"Q3": ("Q2",)})
        envelope = await self.store.put(
            kind="research_contract", body=contract.encode()
        )
        return envelope.artifact_id


class ApprovalTest(ApprovalFixture):
    async def test_an_approved_contract_is_returned_with_its_ref(self) -> None:
        ref = await self.commit_contract()
        await record_decision(self.store, ref, ApprovalBody(decision="approved"))

        approved_ref, contract = await approved_contract(self.store)

        self.assertEqual(ref, approved_ref)
        self.assertEqual(("Q1", "Q2", "Q3"), contract.labels)
        self.assertEqual(("Q2",), contract.question_model.get("Q3").supports)

    async def test_research_cannot_start_before_a_decision(self) -> None:
        await self.commit_contract()
        with self.assertRaisesRegex(ApprovalError, "awaiting user approval"):
            await approved_contract(self.store)

    async def test_no_contract_at_all_is_a_distinct_error(self) -> None:
        with self.assertRaisesRegex(ApprovalError, "no Contract candidate"):
            await approved_contract(self.store)

    async def test_a_revision_request_blocks_research(self) -> None:
        ref = await self.commit_contract()
        await record_decision(
            self.store,
            ref,
            ApprovalBody(decision="revision_requested", note="缩小地域"),
        )
        with self.assertRaisesRegex(ApprovalError, "requested a revision"):
            await approved_contract(self.store)

    async def test_cancellation_blocks_research(self) -> None:
        ref = await self.commit_contract()
        await record_decision(self.store, ref, ApprovalBody(decision="cancelled"))
        with self.assertRaisesRegex(ApprovalError, "cancelled"):
            await approved_contract(self.store)

    async def test_an_approval_never_carries_over_to_a_revised_contract(self) -> None:
        """The invariant: approving one body authorises only that body."""

        first = await self.commit_contract()
        await record_decision(self.store, first, ApprovalBody(decision="approved"))
        await approved_contract(self.store)  # currently fine

        revised = await self.commit_contract(
            CONTRACT.replace("时点为 2026 年 8 月。", "时点为 2026 年 9 月。")
        )
        self.assertNotEqual(first, revised)

        with self.assertRaisesRegex(ApprovalError, "superseded candidate"):
            await approved_contract(self.store)

        # The old receipt is still readable for audit; it simply authorises nothing.
        self.assertEqual(
            "approved", (await decision_for(self.store, first)).decision  # type: ignore[union-attr]
        )
        self.assertIsNone(await decision_for(self.store, revised))

    async def test_a_receipt_binds_the_contract_as_its_parent(self) -> None:
        ref = await self.commit_contract()
        receipt = await record_decision(
            self.store, ref, ApprovalBody(decision="approved")
        )

        envelope = await self.store.get(receipt)
        self.assertEqual((ref,), envelope.parent_refs)
        self.assertTrue(receipt.startswith("apr_"))

    async def test_a_revision_request_must_say_what_to_change(self) -> None:
        with self.assertRaisesRegex(ArtifactValidationError, "what to change"):
            ApprovalBody(decision="revision_requested", note="  ")

    async def test_an_unknown_decision_is_refused(self) -> None:
        for value in ("approve", "partially_approved", ""):
            with self.subTest(value=value):
                with self.assertRaises(ArtifactValidationError):
                    ApprovalBody(decision=value)  # type: ignore[arg-type]


class ApprovalCardTest(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = build_contract(CONTRACT, supports={"Q3": ("Q2",)})

    def test_the_card_shows_the_question_structure_and_pack_choice(self) -> None:
        card = approval_card(self.contract)

        self.assertIn("核心", card)
        self.assertIn("支撑 Q2", card)
        self.assertIn("（未使用能力包）", card)
        self.assertIn("批准并开始研究", card)
        self.assertIn("旧批准自动失效", card)

    def test_the_card_carries_the_exact_prose_the_approval_binds(self) -> None:
        card = approval_card(self.contract)
        for title in ("目的与用途", "证据与分析方法", "自适应边界与已知限制"):
            self.assertIn(title, card)

    def test_a_selected_pack_is_shown_to_the_user(self) -> None:
        contract = ResearchContract.decode(
            build_contract(
                CONTRACT, pack_refs=("domain.medicine@1.0.0",)
            ).encode()
        )
        self.assertIn("domain.medicine@1.0.0", approval_card(contract))


class ActionTranslationTest(unittest.TestCase):
    """One reader of the tool schema, because a second one drifted.

    ``question_supports`` is declared as an object keyed by question label.  The
    stress runner grew its own copy that read a list of ``{"label": ...}``
    objects instead, and because the field is optional the divergence stayed
    invisible for seven fixtures -- the eighth was the first Contract to declare
    a question hierarchy, and it crashed the run.
    """

    def test_the_declared_object_shape_builds_a_layered_model(self) -> None:
        contract = contract_from_action(
            {"contract_markdown": CONTRACT, "question_supports": {"Q3": ["Q2"]}}
        )
        self.assertEqual(("Q2",), contract.question_model.resolve(("Q3",))[0].supports)

    def test_an_omitted_mapping_defaults_every_question_to_the_primary(self) -> None:
        contract = contract_from_action({"contract_markdown": CONTRACT})
        for question in contract.question_model.questions:
            if question.role == "supporting":
                self.assertEqual(("Q1",), question.supports)

    def test_a_wrong_shape_is_a_correction_rather_than_a_crash(self) -> None:
        arguments = {
            "contract_markdown": CONTRACT,
            "question_supports": [{"label": "Q3", "supports": ["Q2"]}],
        }
        with self.assertRaisesRegex(ArtifactValidationError, "must be an object"):
            contract_from_action(arguments)
        # And the Architect sees it as something it can fix in one turn.
        error = make_validator(None)("propose_contract", arguments)
        self.assertIsNotNone(error)
        self.assertIn("question_supports", error.problem)


if __name__ == "__main__":
    unittest.main()
