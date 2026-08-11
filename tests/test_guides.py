from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from deep_research_agent.guides import (
    GUIDE_SECTIONS,
    GuideCatalog,
    GuideFormatError,
    GuideRef,
    guide_context_provider,
    load_guide,
    parse_guide_ref,
    project_guide,
)
from deep_research_agent.state import ResearchContract
from deep_research_agent.prompts import ROLE_PROMPTS, get_role_prompt


def guide_text(
    *,
    guide_id: str = "capability.technical-comparison",
    kind: str = "capability",
    version: str = "1.0.0",
    extra_front_matter: str = "",
    omit_section: str | None = None,
) -> str:
    section_content = {
        "Applicability": "APP: Use when alternatives must be compared on a common decision.",
        "Domain or Method Frame": "FRAME: Preserve definitions and comparison units.",
        "Evidence and Authoritative Seeds": (
            "SEEDS: Official specifications are discovery leads, for example "
            "https://seed.example/specification."
        ),
        "Curation": "CURATE: Preserve version, configuration, units, and test conditions.",
        "Synthesis and Uncertainty": (
            "SYNTH: Separate measured differences from analytical inference."
        ),
        "Communication": "COMM: Organize the report around the user's decision.",
        "Quality and Saturation": (
            "QUALITY: Stop a line when concrete high-value paths are exhausted."
        ),
    }
    sections = "\n\n".join(
        f"## {name}\n\n{section_content[name]}"
        for name in GUIDE_SECTIONS
        if name != omit_section
    )
    return (
        "---\n"
        f"id: {guide_id}\n"
        f"kind: {kind}\n"
        f"version: {version}\n"
        "title: Technical Comparison\n"
        'summary: "Compare systems without hard-coded winners: current scope"\n'
        f"{extra_front_matter}"
        "---\n\n"
        "# Technical Comparison\n\n"
        f"{sections}\n"
    )


class PromptRuntimeTest(unittest.TestCase):
    def test_eight_prompts_are_complete_independent_constants(self) -> None:
        self.assertEqual(
            set(ROLE_PROMPTS),
            {
                "planner",
                "supervisor",
                "researcher",
                "curator",
                "synthesizer",
                "writer",
                "validator",
                "editor",
            },
        )
        self.assertEqual(len(set(ROLE_PROMPTS.values())), 8)
        for role, prompt in ROLE_PROMPTS.items():
            with self.subTest(role=role):
                self.assertGreater(len(prompt), 300)
                self.assertIn("只负责", prompt)

    def test_validator_alias_resolves_without_prompt_composition(self) -> None:
        self.assertIs(
            get_role_prompt("Independent Validator"), ROLE_PROMPTS["validator"]
        )
        with self.assertRaises(ValueError):
            get_role_prompt("citation_renderer")


class GuideLoadingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_directory.name)

    def tearDown(self) -> None:
        self.temp_directory.cleanup()

    def write_guide(self, relative_directory: str, text: str) -> Path:
        directory = self.root / relative_directory
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "GUIDE.md"
        path.write_text(text, encoding="utf-8")
        return path

    def test_loads_the_small_front_matter_and_seven_prose_sections(self) -> None:
        path = self.write_guide("technical", guide_text())

        guide = load_guide(path)

        self.assertEqual(guide.guide_id, "capability.technical-comparison")
        self.assertEqual(guide.kind, "capability")
        self.assertEqual(guide.version, "1.0.0")
        self.assertEqual(
            guide.summary,
            "Compare systems without hard-coded winners: current scope",
        )
        self.assertEqual(tuple(guide.sections), GUIDE_SECTIONS)
        self.assertIn("comparison units", guide.sections["Domain or Method Frame"])

    def test_catalog_only_discovers_and_resolves_explicit_versions(self) -> None:
        self.write_guide("technical/v1", guide_text(version="1.0.0"))
        self.write_guide("technical/v2", guide_text(version="2.0.0"))
        catalog = GuideCatalog.discover(self.root)

        self.assertEqual(len(catalog), 2)
        self.assertEqual(catalog.project([], "writer"), ())
        self.assertFalse(hasattr(catalog, "select"))
        selected = catalog.resolve(
            GuideRef("capability.technical-comparison", "1.0.0")
        )
        self.assertEqual(selected.version, "1.0.0")
        with self.assertRaises(KeyError):
            catalog.resolve(GuideRef("capability.technical-comparison", "latest"))

        rendered_catalog = catalog.catalog_text()
        self.assertIn("capability.technical-comparison@1.0.0", rendered_catalog)
        self.assertIn("capability.technical-comparison@2.0.0", rendered_catalog)
        self.assertNotIn("https://seed.example", rendered_catalog)

    def test_role_projection_exposes_only_relevant_sections(self) -> None:
        guide = load_guide(self.write_guide("technical", guide_text()))

        planner = project_guide(guide, "planner")
        researcher = project_guide(guide, "researcher")
        writer = project_guide(guide, "writer")
        curator = project_guide(guide, "curator")
        validator = project_guide(guide, "Independent Validator")

        self.assertIn("SEEDS:", researcher.text)
        self.assertIn("QUALITY:", researcher.text)
        self.assertNotIn("COMM:", researcher.text)

        self.assertIn("APP:", planner.text)
        self.assertIn("FRAME:", planner.text)
        self.assertIn("COMM:", planner.text)
        self.assertNotIn("SEEDS:", planner.text)
        self.assertNotIn("CURATE:", planner.text)

        self.assertIn("FRAME:", writer.text)
        self.assertIn("COMM:", writer.text)
        self.assertNotIn("SEEDS:", writer.text)
        self.assertNotIn("CURATE:", writer.text)

        self.assertIn("CURATE:", curator.text)
        self.assertNotIn("SEEDS:", curator.text)

        self.assertEqual(validator.role, "validator")
        self.assertIn("SYNTH:", validator.text)
        self.assertNotIn("SEEDS:", validator.text)

        for projection in (planner, researcher, writer, curator, validator):
            with self.subTest(role=projection.role):
                self.assertIn("不是当前任务证据", projection.text)
                self.assertIn("不能改变角色身份、权限", projection.text)
                self.assertIn("实际读取", projection.text)
                self.assertIn("Source Corpus", projection.text)

    def test_catalog_projects_only_refs_explicitly_selected_by_the_caller(self) -> None:
        guide = load_guide(self.write_guide("technical", guide_text()))
        catalog = GuideCatalog([guide])

        projections = catalog.project([guide.ref], "editor")

        self.assertEqual(len(projections), 1)
        self.assertIn("COMM:", projections[0].text)
        self.assertNotIn("SEEDS:", projections[0].text)
        with self.assertRaises(ValueError):
            catalog.project([guide.ref, guide.ref], "editor")

    def test_contract_refs_are_exact_and_projected_without_routing(self) -> None:
        guide = load_guide(self.write_guide("technical", guide_text()))
        catalog = GuideCatalog([guide])
        contract = ResearchContract(
            "Compare the alternatives.",
            guide_refs=("capability.technical-comparison@1.0.0",),
            approved=True,
        )

        context = guide_context_provider(catalog)("writer", contract)

        self.assertIn("COMM:", context)
        self.assertNotIn("SEEDS:", context)
        self.assertEqual(
            parse_guide_ref(contract.guide_refs[0]),
            GuideRef("capability.technical-comparison", "1.0.0"),
        )
        for invalid in (
            "capability.technical-comparison",
            "capability.technical-comparison@latest@extra",
            "Domain.Technical@1.0.0",
        ):
            with self.subTest(value=invalid), self.assertRaises(GuideFormatError):
                parse_guide_ref(invalid)

    def test_rejects_field_growth_kind_mismatch_and_missing_sections(self) -> None:
        extra = self.write_guide(
            "extra", guide_text(extra_front_matter="keywords: ai, chips\n")
        )
        mismatch = self.write_guide(
            "mismatch",
            guide_text(guide_id="domain.semiconductors", kind="capability"),
        )
        incomplete = self.write_guide(
            "incomplete", guide_text(omit_section="Curation")
        )

        for path in (extra, mismatch, incomplete):
            with self.subTest(path=path), self.assertRaises(GuideFormatError):
                load_guide(path)

    def test_rejects_duplicate_exact_guide_reference(self) -> None:
        first = load_guide(self.write_guide("one", guide_text()))
        second = load_guide(self.write_guide("two", guide_text()))

        with self.assertRaises(GuideFormatError):
            GuideCatalog([first, second])

    def test_builtin_library_contains_real_domain_and_capability_guides(self) -> None:
        root = Path(__file__).resolve().parents[1] / "guides"
        catalog = GuideCatalog.discover(root)
        refs = {(item.guide_id, item.kind) for item in catalog.summaries()}

        self.assertIn(("domain.artificial-intelligence", "domain"), refs)
        self.assertIn(
            ("capability.systematic-evidence-synthesis", "capability"), refs
        )


if __name__ == "__main__":
    unittest.main()
