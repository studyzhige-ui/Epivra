"""Research fixtures stay complete, frozen and isolated from hidden assessment."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from epivra.domain import identity
from tools.run_closed_loop_eval import load_case, prepare_corpus

ROOT = Path(__file__).resolve().parents[1]


class ResearchScenarioTests(unittest.TestCase):
    def test_authorized_originals_are_complete_and_assessment_is_excluded(self):
        case = load_case(ROOT, "service_planning")
        self.assertEqual(len(case["sources"]), 9)
        self.assertTrue(all("synthetic" in text for text in case["sources"]))
        self.assertGreater(sum(map(len, case["sources"])), 8000)
        with tempfile.TemporaryDirectory() as temporary:
            corpus = Path(temporary) / "corpus"
            prepare_corpus(corpus, case)
            self.assertEqual(
                {p.name for p in corpus.iterdir()}, set(case["material_names"])
            )
            for name, text in zip(case["material_names"], case["sources"], strict=True):
                self.assertEqual((corpus / name).read_text(encoding="utf-8"), text)
            self.assertFalse((corpus / "assessment.md").exists())
            self.assertFalse(any(case["assessment"] in s for s in case["sources"]))
            prepare_corpus(corpus, case)
            drifted = corpus / case["material_names"][0]
            drifted.write_text("changed", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "corpus changed"):
                prepare_corpus(corpus, case)
            self.assertEqual(drifted.read_text(encoding="utf-8"), "changed")

    def test_fingerprint_covers_originals_and_hidden_assessment(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scenario = root / "evals/research_scenarios/service_planning"
            shutil.copytree(
                ROOT / "evals/research_scenarios/service_planning", scenario
            )
            before = load_case(root, "service_planning")
            assessment = scenario / "assessment.md"
            assessment.write_text(
                before["assessment"] + "\nEvaluation revision.", encoding="utf-8"
            )
            revised = load_case(root, "service_planning")
            self.assertNotEqual(identity(before), identity(revised))
            self.assertEqual(before["sources"], revised["sources"])
            source = scenario / "corpus" / before["material_names"][0]
            source.write_text(before["sources"][0] + "\nNew fact.", encoding="utf-8")
            self.assertNotEqual(
                identity(revised), identity(load_case(root, "service_planning"))
            )

    def test_assessment_cannot_become_an_authorized_material(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scenario = root / "evals/research_scenarios/service_planning"
            shutil.copytree(
                ROOT / "evals/research_scenarios/service_planning", scenario
            )
            config_path = scenario / "task.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["materials"].append("assessment.md")
            config_path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "separate"):
                load_case(root, "service_planning")

    def test_legacy_cases_keep_their_original_identity_and_filenames(self):
        cases = json.loads(
            (ROOT / "evals/closed_loop_cases.json").read_text(encoding="utf-8")
        )
        for original in cases:
            with self.subTest(case=original["id"]):
                loaded = load_case(ROOT, original["id"])
                self.assertEqual(loaded, original)
                self.assertEqual(identity(loaded), identity(original))
                with tempfile.TemporaryDirectory() as temporary:
                    corpus = Path(temporary)
                    prepare_corpus(corpus, loaded)
                    self.assertEqual(
                        {p.name for p in corpus.iterdir()},
                        {f"material-{i}.txt" for i in range(len(original["sources"]))},
                    )
