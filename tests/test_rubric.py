"""Rubric tests, including the one that keeps the judge and the gate agreeing.

The tier logic is the reason this file exists.  A publication gate built on an
average is the failure AMSTAR 2 warns about, so the tests below assert that one
critical failure blocks no matter how good everything else is, and that a report
which honestly reports low certainty can still reach the top tier.
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

from deep_research_agent.agents.reviewer import SYSTEM_PROMPT as REVIEWER_PROMPT

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("eval_rubric", ROOT / "evals" / "rubric.py")
assert _spec is not None and _spec.loader is not None
rubric = importlib.util.module_from_spec(_spec)
sys.modules["eval_rubric"] = rubric
_spec.loader.exec_module(rubric)


def _all(passed: bool, domains) -> list[tuple[str, bool, str]]:  # noqa: ANN001
    return [(domain.key, passed, "测试理由") for domain in domains]


class StructureTest(unittest.TestCase):
    def test_five_critical_and_ten_supporting_domains(self) -> None:
        self.assertEqual(5, len(rubric.CRITICAL))
        self.assertEqual(10, len(rubric.SUPPORTING))

    def test_domain_keys_are_unique(self) -> None:
        keys = [domain.key for domain in rubric.DOMAINS]
        self.assertEqual(len(keys), len(set(keys)))

    def test_the_rubric_never_exposes_a_score_or_an_average(self) -> None:
        """The ported source had publish_minimum_average: 3.0; this must not."""

        verdict = rubric.build_verdict(
            _all(True, rubric.CRITICAL), _all(True, rubric.SUPPORTING)
        )
        for attribute in ("score", "average", "total", "points"):
            self.assertFalse(
                hasattr(verdict, attribute),
                f"a layered verdict must not expose {attribute!r}",
            )


class TierTest(unittest.TestCase):
    def test_one_critical_failure_blocks_however_good_the_rest_is(self) -> None:
        critical = _all(True, rubric.CRITICAL)
        critical[0] = (rubric.CRITICAL[0].key, False, "引用指向邻近但不同的主张")
        verdict = rubric.build_verdict(critical, _all(True, rubric.SUPPORTING))
        self.assertEqual("不可发布", verdict.tier)
        self.assertFalse(verdict.publishable)
        self.assertEqual(1, len(verdict.critical_failures))

    def test_a_clean_report_with_one_weakness_is_still_top_tier(self) -> None:
        supporting = _all(True, rubric.SUPPORTING)
        supporting[0] = (rubric.SUPPORTING[0].key, False, "检索范围写得笼统")
        verdict = rubric.build_verdict(_all(True, rubric.CRITICAL), supporting)
        self.assertEqual("可发布·高", verdict.tier)

    def test_more_than_one_weakness_degrades_but_does_not_block(self) -> None:
        supporting = _all(True, rubric.SUPPORTING)
        supporting[0] = (rubric.SUPPORTING[0].key, False, "检索范围笼统")
        supporting[1] = (rubric.SUPPORTING[1].key, False, "两类局限混写")
        verdict = rubric.build_verdict(_all(True, rubric.CRITICAL), supporting)
        self.assertEqual("可发布·中", verdict.tier)
        self.assertTrue(verdict.publishable)

    def test_nine_weaknesses_still_do_not_block(self) -> None:
        """Only critical domains block. Accumulated weakness degrades the tier."""

        supporting = [
            (domain.key, index >= 9, "测试理由")
            for index, domain in enumerate(rubric.SUPPORTING)
        ]
        verdict = rubric.build_verdict(_all(True, rubric.CRITICAL), supporting)
        self.assertEqual("可发布·中", verdict.tier)
        self.assertTrue(verdict.publishable)

    def test_an_honest_undetermined_conclusion_can_be_top_tier(self) -> None:
        """Low certainty is not a defect; over-confidence is.

        sparse-evidence concluded that the evidence could not support a local
        recommendation and published. That has to be able to score at the top,
        or the rubric would punish exactly the honesty 1e was built to reward.
        """

        verdict = rubric.build_verdict(
            _all(True, rubric.CRITICAL), _all(True, rubric.SUPPORTING)
        )
        self.assertEqual("可发布·高", verdict.tier)


class VerdictValidationTest(unittest.TestCase):
    def test_a_verdict_missing_a_domain_is_refused(self) -> None:
        with self.assertRaisesRegex(ValueError, "not judged"):
            rubric.build_verdict(
                _all(True, rubric.CRITICAL[:-1]), _all(True, rubric.SUPPORTING)
            )

    def test_a_domain_judged_twice_is_refused(self) -> None:
        doubled = _all(True, rubric.CRITICAL) + [
            (rubric.CRITICAL[0].key, False, "又判了一次")
        ]
        with self.assertRaisesRegex(ValueError, "more than once"):
            rubric.build_verdict(doubled, _all(True, rubric.SUPPORTING))

    def test_an_unknown_domain_is_refused(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown rubric domain"):
            rubric.DomainVerdict("coverage_score", True, "理由")

    def test_a_verdict_without_a_reason_is_refused(self) -> None:
        with self.assertRaisesRegex(ValueError, "needs a reason"):
            rubric.DomainVerdict("scope_fidelity", True, "   ")


class GateAgreementTest(unittest.TestCase):
    """The offline judge and the in-run gate must block on the same five things.

    The Reviewer's prompt already listed these as blocking conditions before the
    rubric existed; stating them twice invites the two to drift into disagreeing
    about what publication requires. This check is intentionally brittle -- a
    reworded prompt fails it, which forces someone to confirm they still match.
    """

    def test_every_critical_domain_is_a_reviewer_blocking_rule(self) -> None:
        for key, phrase in rubric.reviewer_rules():
            with self.subTest(domain=key):
                self.assertIn(
                    phrase,
                    REVIEWER_PROMPT,
                    f"critical domain {key!r} is not a Reviewer blocking rule",
                )

    def test_every_critical_domain_declares_such_a_rule(self) -> None:
        self.assertEqual(len(rubric.CRITICAL), len(rubric.reviewer_rules()))


class RenderTest(unittest.TestCase):
    def test_the_rendered_rubric_separates_the_two_groups(self) -> None:
        text = rubric.render_rubric()
        self.assertIn("关键域（任一失败 → 不可发布）", text)
        self.assertIn("非关键域（累积则降级，单项不阻断）", text)
        for domain in rubric.DOMAINS:
            self.assertIn(domain.title, text)

    def test_a_rendered_verdict_names_the_failures(self) -> None:
        critical = _all(True, rubric.CRITICAL)
        critical[1] = (rubric.CRITICAL[1].key, False, "把关联写成了因果")
        rendered = rubric.build_verdict(critical, _all(True, rubric.SUPPORTING)).render()
        self.assertIn("不可发布", rendered)
        self.assertIn("把关联写成了因果", rendered)


if __name__ == "__main__":
    unittest.main()
