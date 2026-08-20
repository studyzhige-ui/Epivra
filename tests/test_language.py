"""The deliverable's language is the user's choice, carried end to end.

This exists because the field was decorative. ``CommissionBody.language`` and the
Architect's "## 交付语言" section both existed, while four role prompts carried
"write in Chinese" as fixed text -- a direct contradiction in which the prompt
won. Non-Chinese output was not untested, it was impossible.

The other half is where translation happens. Anchors must stay verbatim in the
source language, so somebody has to cross languages; it is the Curator, the only
role whose stated job is judging whether a paraphrase is faithful to its source,
and whose output keeps the original quote beside it for checking.
"""

from __future__ import annotations

import unittest

from deep_research_agent.agents import analyst, architect, author, curator, reviewer
from deep_research_agent.context import (
    analyst_context,
    author_context,
    curator_context,
    reviewer_context,
)
from deep_research_agent.contract import CommissionBody, build_contract
from deep_research_agent.sources import BodyRef, SourceSnapshotBody

BODY = (
    "## 问题模型\n\n"
    "### Q1. Does classroom air cleaning reduce respiratory infection spread?\n"
)

#: Every role that emits prose a human or a later role reads.
PROSE_PROMPTS = {
    "architect": architect.SYSTEM_PROMPT,
    "curator": curator.SYSTEM_PROMPT,
    "analyst": analyst.SYSTEM_PROMPT,
    "author": author.SYSTEM_PROMPT,
    "reviewer": reviewer.SYSTEM_PROMPT,
}


def _contract(language: str):  # noqa: ANN202
    return build_contract(BODY, language=language)


class ContractLanguageTest(unittest.TestCase):
    def test_the_contract_carries_the_language_structurally(self) -> None:
        self.assertEqual("en", _contract("en").language)

    def test_the_language_survives_a_round_trip(self) -> None:
        contract = _contract("ja")
        from deep_research_agent.contract import ResearchContract

        self.assertEqual("ja", ResearchContract.decode(contract.encode()).language)

    def test_a_contract_written_before_the_field_existed_reads_as_chinese(self) -> None:
        """Every such Contract was a Chinese deliverable, so that is honest."""

        from deep_research_agent.contract import ResearchContract

        legacy = '{"markdown": %s, "packs": [], "supports": {}}' % (
            __import__("json").dumps(BODY, ensure_ascii=False)
        )
        self.assertEqual("zh", ResearchContract.decode(legacy).language)

    def test_an_empty_language_is_refused(self) -> None:
        from deep_research_agent.sources import ArtifactValidationError

        with self.assertRaisesRegex(ArtifactValidationError, "contract language"):
            build_contract(BODY, language="  ")

    def test_the_architect_takes_the_language_from_the_commission(self) -> None:
        """It is the user's choice, not a research judgment the Architect makes."""

        commission = CommissionBody(request="Study X.", source_access=("public_web",), language="en")
        contract = architect.contract_from_action(
            {"contract_markdown": BODY}, language=commission.language
        )
        self.assertEqual("en", contract.language)


class PromptLanguageTest(unittest.TestCase):
    def test_no_prompt_fixes_the_output_language(self) -> None:
        """The regression that made the language field decorative."""

        for role, prompt in PROSE_PROMPTS.items():
            with self.subTest(role=role):
                self.assertNotIn("用中文", prompt)

    def test_every_prose_role_is_pointed_at_the_delivery_language(self) -> None:
        for role, prompt in PROSE_PROMPTS.items():
            with self.subTest(role=role):
                self.assertIn("交付语言", prompt)

    def test_the_curator_owns_the_single_translation(self) -> None:
        prompt = PROSE_PROMPTS["curator"]
        self.assertIn("exact_quote", prompt)
        self.assertIn("绝不翻译", prompt)

    def test_the_author_is_told_not_to_translate_quotes(self) -> None:
        self.assertIn("不要翻译引文", PROSE_PROMPTS["author"])


class ContextLanguageTest(unittest.TestCase):
    """Each prose role must be able to see the language without being told twice."""

    class _Evidence:
        evidence_set_id = "evs_test"
        materials = ()
        material_refs = ()
        handles = ()
        sources: dict[str, object] = {}

        def render(self, *, with_handles: bool) -> str:
            return "（当前证据集为空）"

        def source_summary(self) -> str:
            return "（尚无来源）"

    def test_the_language_reaches_analyst_author_reviewer_and_curator(self) -> None:
        contract = _contract("en")
        evidence = self._Evidence()
        candidates = {
            "src_1": SourceSnapshotBody(
                url="https://example.org/a",
                title="A trial",
                text_ref=BodyRef("0" * 64, 10),
            )
        }
        contexts = {
            "analyst": analyst_context(contract, evidence),
            "author": author_context(contract, evidence, "综合", "brief"),
            "reviewer": reviewer_context(contract, evidence, "综合", "报告"),
            "curator": curator_context(contract, assignment="a", candidates=candidates),
        }
        for role, context in contexts.items():
            with self.subTest(role=role):
                self.assertIn("## 交付语言", context.body)
                self.assertIn("en", context.body)

    def test_the_language_section_forbids_translating_anchors(self) -> None:
        body = analyst_context(_contract("en"), self._Evidence()).body
        self.assertIn("锚点引文保持原语言", body)


if __name__ == "__main__":
    unittest.main()
