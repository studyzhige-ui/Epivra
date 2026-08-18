"""The matrix must actually vary what it claims to vary.

A stress matrix whose fixtures all lean the same way tests one thing eight
times.  These checks are cheap and they catch the failure that matters: a
fixture set quietly shaped toward whatever the system already does well.
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "eval_fixtures", ROOT / "evals" / "fixtures.py"
)
assert _spec is not None and _spec.loader is not None
fixtures = importlib.util.module_from_spec(_spec)
sys.modules["eval_fixtures"] = fixtures
_spec.loader.exec_module(fixtures)


class MatrixTest(unittest.TestCase):
    def test_fixture_ids_are_unique(self) -> None:
        ids = [f.fixture_id for f in fixtures.FIXTURES]
        self.assertEqual(len(ids), len(set(ids)))

    def test_the_matrix_spans_several_domains_and_genres(self) -> None:
        domains = {f.domain for f in fixtures.FIXTURES}
        genres = {f.genre for f in fixtures.FIXTURES}

        self.assertGreaterEqual(len(domains), 5)
        self.assertGreaterEqual(len(genres), 4)

    def test_no_single_domain_dominates(self) -> None:
        counts = Counter(f.domain for f in fixtures.FIXTURES)
        self.assertLessEqual(
            counts.most_common(1)[0][1], len(fixtures.FIXTURES) // 2
        )

    def test_genre_varies_within_one_domain(self) -> None:
        """Isolating genre requires two fixtures that differ only in genre."""

        by_domain: dict[str, set[str]] = {}
        for fixture in fixtures.FIXTURES:
            by_domain.setdefault(fixture.domain, set()).add(fixture.genre)
        self.assertTrue(
            any(len(genres) > 1 for genres in by_domain.values()),
            "no domain carries two genres, so genre cannot be isolated",
        )

    def test_every_fixture_states_both_success_and_failure(self) -> None:
        for fixture in fixtures.FIXTURES:
            with self.subTest(fixture=fixture.fixture_id):
                self.assertTrue(fixture.stresses.strip())
                self.assertGreaterEqual(len(fixture.honest_behaviour), 2)
                self.assertGreaterEqual(len(fixture.failure_looks_like), 2)

    def test_the_tempting_answer_is_wrong_in_several_fixtures(self) -> None:
        """The matrix must contain cases where compliance is the failure."""

        adversarial = {
            "incomparable-benchmarks",  # user demands a ranking
            "improper-causality",       # user demands a causal argument
            "sparse-evidence",          # user wants a recommendation
        }
        self.assertTrue(adversarial <= set(fixtures.FIXTURES_BY_ID))

    def test_unknown_ids_list_what_exists(self) -> None:
        with self.assertRaises(KeyError) as caught:
            fixtures.get("nonexistent")
        self.assertIn("sparse-evidence", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
