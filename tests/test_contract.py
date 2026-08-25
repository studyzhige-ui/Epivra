from __future__ import annotations

import json
import unittest

from deep_research_agent.contract import (
    QuestionModel,
    ResearchContract,
    ResearchQuestion,
    build_contract,
    build_question_model,
    parse_question_lines,
    require_question_label,
    section_title,
)
from deep_research_agent.sources import ArtifactValidationError

CONTRACT_BODY = """\
## 目的与用途

为医院母婴护理团队选择婴儿 RSV 预防路径提供依据。

## 问题模型

### Q1. 对本院人群，母源疫苗与单克隆抗体应如何组合使用？
### Q2. 两条路径在住院与重症终点上的效力证据强度如何？
### Q3. 给药时点与季节性如何影响可行性？

## 范围与定义

时点为 2026 年 8 月。

## 证据与分析方法

优先监管标签、ACIP 记录与关键试验原文。

## 交付与保证

决策简报，独立审查。

## 自适应边界与已知限制

查询与来源顺序由 Lead 自适应。
"""


class QuestionLabelTest(unittest.TestCase):
    def test_canonical_labels_are_accepted(self) -> None:
        for label in ("Q1", "Q7", "Q12"):
            with self.subTest(label=label):
                self.assertEqual(label, require_question_label(label))

    def test_non_canonical_labels_are_rejected(self) -> None:
        for label in ("q1", "Q0", "Q01", "Question 1", "Q", "", "Q1a"):
            with self.subTest(label=label):
                with self.assertRaises(ArtifactValidationError):
                    require_question_label(label)


class QuestionParsingTest(unittest.TestCase):
    def test_headings_and_terse_forms_are_both_recognised(self) -> None:
        body = (
            "### Q1. Primary question?\n"
            "Q2: Supporting question?\n"
            "- Q3、Third question?\n"
            "Some prose that mentions Q2 but is not a question line.\n"
        )
        self.assertEqual(
            (
                ("Q1", "Primary question?"),
                ("Q2", "Supporting question?"),
                ("Q3", "Third question?"),
            ),
            parse_question_lines(body),
        )

    def test_a_body_without_numbered_questions_is_rejected(self) -> None:
        with self.assertRaisesRegex(ArtifactValidationError, "numbered questions"):
            build_question_model("## 问题模型\n\n讨论一些主题。\n")

    def test_a_repeated_label_is_rejected(self) -> None:
        with self.assertRaisesRegex(ArtifactValidationError, "more than once"):
            build_question_model("Q1. First?\nQ1. Duplicate?\n")


class QuestionModelTest(unittest.TestCase):
    def test_flat_supporting_questions_default_to_supporting_the_primary(self) -> None:
        model = build_question_model("Q1. Primary?\nQ2. Second?\nQ3. Third?\n")

        self.assertEqual(("Q1", "Q2", "Q3"), model.labels)
        self.assertEqual("Q1", model.primary.label)
        self.assertEqual(("Q1",), model.get("Q2").supports)

    def test_layered_support_structure_is_preserved(self) -> None:
        model = build_question_model(
            "Q1. Primary?\nQ2. Second?\nQ3. Third?\n",
            supports={"Q2": ("Q1",), "Q3": ("Q2",)},
        )

        self.assertEqual(("Q2",), model.get("Q3").supports)

    def test_exactly_one_primary_question_labelled_q1(self) -> None:
        with self.assertRaisesRegex(ArtifactValidationError, "exactly one primary"):
            QuestionModel(
                questions=(
                    ResearchQuestion(label="Q1", text="First?", role="primary"),
                    ResearchQuestion(label="Q2", text="Second?", role="primary"),
                )
            )
        with self.assertRaisesRegex(ArtifactValidationError, "labelled Q1"):
            QuestionModel(
                questions=(
                    ResearchQuestion(label="Q1", text="First?", role="supporting",
                                     supports=("Q2",)),
                    ResearchQuestion(label="Q2", text="Second?", role="primary"),
                )
            )

    def test_labels_must_be_contiguous_from_q1(self) -> None:
        with self.assertRaisesRegex(ArtifactValidationError, "contiguous"):
            QuestionModel(
                questions=(
                    ResearchQuestion(label="Q1", text="First?", role="primary"),
                    ResearchQuestion(
                        label="Q4", text="Fourth?", role="supporting", supports=("Q1",)
                    ),
                )
            )

    def test_a_supporting_question_must_declare_its_role(self) -> None:
        with self.assertRaisesRegex(ArtifactValidationError, "which question it supports"):
            ResearchQuestion(label="Q2", text="Orphan topic?", role="supporting")

    def test_the_primary_question_must_not_declare_supports(self) -> None:
        with self.assertRaisesRegex(ArtifactValidationError, "must not declare supports"):
            ResearchQuestion(
                label="Q1", text="Primary?", role="primary", supports=("Q2",)
            )

    def test_support_must_transitively_reach_the_primary_question(self) -> None:
        with self.assertRaisesRegex(ArtifactValidationError, "transitively support Q1"):
            QuestionModel(
                questions=(
                    ResearchQuestion(label="Q1", text="Primary?", role="primary"),
                    ResearchQuestion(
                        label="Q2", text="Second?", role="supporting", supports=("Q3",)
                    ),
                    ResearchQuestion(
                        label="Q3", text="Third?", role="supporting", supports=("Q2",)
                    ),
                )
            )

    def test_support_of_an_undefined_question_is_rejected(self) -> None:
        with self.assertRaisesRegex(ArtifactValidationError, "unknown questions"):
            build_question_model(
                "Q1. Primary?\nQ2. Second?\n", supports={"Q2": ("Q9",)}
            )

    def test_supports_mapping_cannot_name_absent_questions(self) -> None:
        with self.assertRaisesRegex(ArtifactValidationError, "absent from the body"):
            build_question_model("Q1. Primary?\n", supports={"Q5": ("Q1",)})


class ContractResolutionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = build_contract(CONTRACT_BODY)

    def test_contract_exposes_the_labels_a_role_may_select(self) -> None:
        self.assertEqual(("Q1", "Q2", "Q3"), self.contract.labels)

    def test_resolution_returns_questions_in_canonical_order(self) -> None:
        resolved = self.contract.resolve(("Q3", "Q1"))

        self.assertEqual(("Q1", "Q3"), tuple(q.label for q in resolved))
        self.assertIn("母源疫苗", resolved[0].text)

    def test_an_unknown_label_is_rejected_with_the_available_set(self) -> None:
        with self.assertRaises(ArtifactValidationError) as caught:
            self.contract.resolve(("Q9",))

        message = str(caught.exception)
        self.assertIn("Q9", message)
        self.assertIn("Q1, Q2, Q3", message)

    def test_duplicate_and_empty_selections_are_rejected(self) -> None:
        with self.assertRaisesRegex(ArtifactValidationError, "duplicate"):
            self.contract.resolve(("Q2", "Q2"))
        with self.assertRaisesRegex(ArtifactValidationError, "at least one"):
            self.contract.resolve(())

    def test_pack_refs_must_be_unique(self) -> None:
        with self.assertRaisesRegex(ArtifactValidationError, "duplicates"):
            build_contract(CONTRACT_BODY, pack_refs=("a@1", "a@1"))

    def test_section_titles_cover_the_six_blocks(self) -> None:
        self.assertEqual("问题模型", section_title("question_model"))
        with self.assertRaises(ArtifactValidationError):
            section_title("coverage_matrix")


class QuestionTextTest(unittest.TestCase):
    """A question has to survive being read on its own.

    Roles are handed ``contract.resolve(labels)`` and nothing else, so the text
    on the Q-line is the entire question as far as every later role is
    concerned.  A live Contract wrote ``### Q1. 核心问题`` as a heading with the
    real question in the prose underneath; the parser took the heading, and the
    run stayed healthy-looking while Q1 was the literal string "核心问题".
    """

    def test_a_bare_section_label_is_not_a_question(self) -> None:
        for label in ("核心问题", "现行制度边界", "行为定性", "通用义务与云场景角色"):
            with self.subTest(label=label):
                with self.assertRaisesRegex(
                    ArtifactValidationError, "section label rather than a question"
                ):
                    build_question_model(f"Q1. {label}\n")

    def test_a_short_question_survives_if_it_is_punctuated_as_one(self) -> None:
        model = build_question_model("Q1. 哪些法规现行有效？\n")
        self.assertEqual("哪些法规现行有效？", model.primary.text)

    def test_a_long_clause_survives_without_a_question_mark(self) -> None:
        body = (
            "Q1. 已获批的老年 RSV 疫苗对 65 岁以上人群的效力证据达到何种强度，"
            "以监管审评为基线。\n"
        )
        self.assertIn("何种强度", build_question_model(body).primary.text)


class LegacyContractTest(unittest.TestCase):
    """Create is strict; decode admits what a committed Contract cannot fix.

    This check was added *after* real runs, and artifacts are immutable, so
    enforcing it on the way in as well as out stranded a study that had already
    been planned, approved and part-way completed: it raised on decode, which meant
    `advance()`, `approval_card()` and everything else refused to touch it.  One
    task in the calibration corpus is in exactly that state.

    §2.3.1 draws the line at whether the artifact could still satisfy the check.
    Structure it needs to be usable at all stays enforced in both directions.
    """

    BODY = "## 问题模型\n\n### Q1. 核心问题\n### Q2. 支撑问题\n"

    def _committed(self) -> str:
        """The body as it sits in a real database: encoded before the check existed."""

        return json.dumps(
            {"markdown": self.BODY, "supports": {}, "packs": [], "language": "zh"},
            ensure_ascii=False,
            sort_keys=True,
        )

    def test_a_committed_contract_can_still_be_read(self) -> None:
        contract = ResearchContract.decode(self._committed())
        self.assertEqual("核心问题", contract.question_model.primary.text)
        self.assertEqual(("Q1", "Q2"), contract.labels)

    def test_what_it_was_admitted_despite_is_recorded(self) -> None:
        """Admitted, not hidden -- a reader must be able to tell the difference."""

        contract = ResearchContract.decode(self._committed())
        self.assertTrue(contract.legacy_degraded)
        self.assertIn("section label rather than a question", contract.legacy_degraded[0])

    def test_a_contract_this_version_produced_is_not_marked(self) -> None:
        good = build_contract("## 问题模型\n\n### Q1. 两条路径的证据强度如何？\n")
        self.assertEqual((), ResearchContract.decode(good.encode()).legacy_degraded)

    def test_the_same_body_is_still_refused_on_the_way_in(self) -> None:
        """Leniency is one-directional, or the check would be worthless."""

        with self.assertRaisesRegex(
            ArtifactValidationError, "section label rather than a question"
        ):
            build_contract(self.BODY)

    def test_the_degradation_record_stays_out_of_the_body(self) -> None:
        """It is an observation made while reading, not part of what was approved.

        In the body it would change the artifact's identity, so re-encoding a
        legacy Contract would silently fork it.
        """

        decoded = ResearchContract.decode(self._committed())
        self.assertTrue(decoded.legacy_degraded)
        self.assertNotIn("legacy_degraded", decoded.encode())
        self.assertNotIn("degraded", decoded.encode())

    def test_mechanical_structure_is_never_relaxed(self) -> None:
        """Leniency covers judgement, not the structure roles depend on."""

        for markdown, expected in (
            ("## 问题模型\n\n### Q2. 只有支撑问题，没有核心问题？\n", "primary question"),
            ("## 问题模型\n\n没有任何编号问题。\n", "numbered questions"),
        ):
            with self.subTest(markdown=markdown):
                body = json.dumps(
                    {"markdown": markdown, "supports": {}, "packs": []},
                    ensure_ascii=False,
                )
                with self.assertRaises(ArtifactValidationError) as raised:
                    ResearchContract.decode(body)
                self.assertIn(expected, str(raised.exception))


if __name__ == "__main__":
    unittest.main()
