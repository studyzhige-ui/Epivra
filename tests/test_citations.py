from __future__ import annotations

import unittest

from deep_research_agent.citations import (
    CitationClosureError,
    build_handles,
    citation_syntax_problem,
    extract_handles,
    render_citations,
)
from deep_research_agent.sources import (
    ArtifactValidationError,
    BodyRef,
    MaterialBody,
    SourceAnchor,
    SourceSnapshotBody,
    canonical_url,
    locate_quote,
    validate_anchor,
)

SOURCE_A = "src_00000000000000000000000a"
SOURCE_B = "src_00000000000000000000000b"
MATERIAL_A = "mat_00000000000000000000000a"
MATERIAL_B = "mat_00000000000000000000000b"


def snapshot(name: str, text: str = "Exact evidence body.") -> SourceSnapshotBody:
    return SourceSnapshotBody(
        url=f"https://example.test/{name}",
        title=f"Source {name}",
        text_ref=BodyRef.from_content(text),
        fetched_at="2026-08-17",
    )


def anchor(source_ref: str, text: str, quote: str) -> SourceAnchor:
    return SourceAnchor(
        source_ref=source_ref, exact_quote=quote, locator=locate_quote(text, quote)
    )


def material(source_ref: str, text: str, quote: str) -> MaterialBody:
    return MaterialBody.create(
        content=f"A curated statement supported by {quote!r}.",
        boundaries="Applies only to the population the source studied.",
        anchors=(anchor(source_ref, text, quote),),
    )


class AnchorTest(unittest.TestCase):
    def test_a_quote_must_be_locatable_in_the_saved_text(self) -> None:
        text = "Repeated evidence. Repeated evidence."

        located = locate_quote(text, "Repeated evidence.")

        self.assertEqual(0, located.start)
        self.assertEqual(18, located.end)
        with self.assertRaisesRegex(ArtifactValidationError, "not present"):
            locate_quote(text, "Absent claim.")

    def test_an_anchor_pointing_at_the_wrong_offset_is_rejected(self) -> None:
        text = "Before exact evidence after."
        valid = anchor(SOURCE_A, text, "exact evidence")
        validate_anchor(valid, text)

        drifted = SourceAnchor(
            source_ref=SOURCE_A,
            exact_quote="exact evidence",
            locator=locate_quote(text, "Before"),
        )
        with self.assertRaisesRegex(ArtifactValidationError, "does not match"):
            validate_anchor(drifted, text)

    def test_an_anchor_beyond_the_saved_text_is_rejected(self) -> None:
        stale = anchor(SOURCE_A, "A longer original body here.", "original body")
        with self.assertRaisesRegex(ArtifactValidationError, "exceeds"):
            validate_anchor(stale, "A shorter body.")


class MaterialBodyTest(unittest.TestCase):
    def test_material_cannot_exist_without_an_anchor(self) -> None:
        with self.assertRaisesRegex(ArtifactValidationError, "SourceAnchor"):
            MaterialBody.create(
                content="Unsupported formal material.",
                boundaries="No source boundary exists.",
                anchors=(),
            )

    def test_boundaries_are_mandatory(self) -> None:
        text = "Exact evidence body."
        with self.assertRaisesRegex(ArtifactValidationError, "boundaries"):
            MaterialBody.create(
                content="A claim.",
                boundaries="   ",
                anchors=(anchor(SOURCE_A, text, "Exact evidence"),),
            )

    def test_anchor_order_does_not_change_the_canonical_body(self) -> None:
        text = "First fact. Second fact."
        forward = MaterialBody.create(
            content="Two facts.",
            boundaries="Both from one source.",
            anchors=(
                anchor(SOURCE_A, text, "First fact."),
                anchor(SOURCE_A, text, "Second fact."),
            ),
        )
        reversed_order = MaterialBody.create(
            content="Two facts.",
            boundaries="Both from one source.",
            anchors=(
                anchor(SOURCE_A, text, "Second fact."),
                anchor(SOURCE_A, text, "First fact."),
            ),
        )

        self.assertEqual(forward.encode(), reversed_order.encode())

    def test_parent_lineage_is_derived_from_the_anchors(self) -> None:
        text = "Exact evidence body."
        body = MaterialBody.create(
            content="Supported by two sources.",
            boundaries="Conflicting estimates retained.",
            anchors=(
                anchor(SOURCE_B, text, "Exact evidence"),
                anchor(SOURCE_A, text, "evidence body"),
            ),
        )

        self.assertEqual((SOURCE_A, SOURCE_B), body.source_refs)

    def test_bodies_round_trip_through_their_canonical_encoding(self) -> None:
        text = "Exact evidence body."
        body = material(SOURCE_A, text, "Exact evidence")

        self.assertEqual(body, MaterialBody.decode(body.encode()))


class SourceSnapshotBodyTest(unittest.TestCase):
    def test_url_identity_drops_fragments_and_lowercases_the_host(self) -> None:
        body = SourceSnapshotBody(
            url="HTTPS://EXAMPLE.TEST/report#section-two",
            title="Report",
            text_ref=BodyRef.from_content("body"),
        )
        self.assertEqual("https://example.test/report", body.url)

    def test_unsafe_urls_are_refused(self) -> None:
        for url in (
            "file:///etc/passwd",
            "http://127.0.0.1/private",
            "https://user:password@example.test/report",
            "https://example.test/report?access_token=secret",
            "https://example.test/report?X-Amz-Signature=signed",
        ):
            with self.subTest(url=url), self.assertRaises(ArtifactValidationError):
                canonical_url(url)

    def test_bodies_round_trip_through_their_canonical_encoding(self) -> None:
        body = snapshot("a")
        self.assertEqual(body, SourceSnapshotBody.decode(body.encode()))


class HandleIssuanceTest(unittest.TestCase):
    def test_one_handle_is_issued_per_material_anchor_pair(self) -> None:
        text = "First fact. Second fact."
        materials = {
            MATERIAL_A: MaterialBody.create(
                content="Two facts.",
                boundaries="Both from one source.",
                anchors=(
                    anchor(SOURCE_A, text, "First fact."),
                    anchor(SOURCE_A, text, "Second fact."),
                ),
            ),
            MATERIAL_B: material(SOURCE_B, text, "Second fact."),
        }
        sources = {SOURCE_A: snapshot("a", text), SOURCE_B: snapshot("b", text)}

        handles = build_handles(materials, sources)

        self.assertEqual(("h1", "h2", "h3"), tuple(h.handle for h in handles))
        self.assertEqual(MATERIAL_A, handles[0].material_ref)
        self.assertEqual(MATERIAL_B, handles[2].material_ref)

    def test_issuance_is_stable_regardless_of_mapping_order(self) -> None:
        text = "Exact evidence body."
        sources = {SOURCE_A: snapshot("a", text), SOURCE_B: snapshot("b", text)}
        forward = build_handles(
            {
                MATERIAL_A: material(SOURCE_A, text, "Exact evidence"),
                MATERIAL_B: material(SOURCE_B, text, "evidence body"),
            },
            sources,
        )
        reverse = build_handles(
            {
                MATERIAL_B: material(SOURCE_B, text, "evidence body"),
                MATERIAL_A: material(SOURCE_A, text, "Exact evidence"),
            },
            sources,
        )

        self.assertEqual(
            [(h.handle, h.material_ref) for h in forward],
            [(h.handle, h.material_ref) for h in reverse],
        )

    def test_a_material_anchoring_an_unknown_source_fails_closed(self) -> None:
        text = "Exact evidence body."
        with self.assertRaisesRegex(CitationClosureError, "unknown source"):
            build_handles(
                {MATERIAL_A: material(SOURCE_A, text, "Exact evidence")}, {}
            )


class RenderTest(unittest.TestCase):
    def setUp(self) -> None:
        text = "Exact evidence body."
        self.materials = {
            MATERIAL_A: material(SOURCE_A, text, "Exact evidence"),
            MATERIAL_B: material(SOURCE_B, text, "evidence body"),
        }
        self.sources = {SOURCE_A: snapshot("a", text), SOURCE_B: snapshot("b", text)}
        self.handles = build_handles(self.materials, self.sources)

    def test_numbering_follows_first_appearance_and_reuses_repeats(self) -> None:
        draft = (
            "First claim [[cite:h2]].\n"
            "Second claim [[cite:h1]].\n"
            "Repeat of the first [[cite:h2]].\n"
        )

        result = render_citations(draft, self.handles)

        self.assertIn("First claim [1].", result.markdown)
        self.assertIn("Second claim [2].", result.markdown)
        self.assertIn("Repeat of the first [1].", result.markdown)
        self.assertEqual(
            ("1. Source b (2026-08-17). https://example.test/b",
             "2. Source a (2026-08-17). https://example.test/a"),
            result.references,
        )

    def test_the_reference_section_is_generated_not_authored(self) -> None:
        result = render_citations("A claim [[cite:h1]].", self.handles)

        self.assertIn("## 参考资料", result.markdown)
        self.assertNotIn("[[cite:", result.markdown)
        self.assertEqual((MATERIAL_A,), result.used_material_refs)

    def test_uncited_evidence_is_not_listed_in_references(self) -> None:
        result = render_citations("Only one source [[cite:h1]].", self.handles)

        self.assertIn("https://example.test/a", result.markdown)
        self.assertNotIn("https://example.test/b", result.markdown)

    def test_extraction_preserves_first_appearance_order(self) -> None:
        self.assertEqual(
            ("h2", "h1"),
            extract_handles("b [[cite:h2]] a [[cite:h1]] b again [[cite:h2]]"),
        )

    def test_an_unknown_handle_fails_closed(self) -> None:
        with self.assertRaisesRegex(CitationClosureError, "does not exist"):
            render_citations("Unsupported [[cite:h99]].", self.handles)

    def test_a_handle_outside_the_evidence_set_fails_closed(self) -> None:
        with self.assertRaisesRegex(CitationClosureError, "not in the current"):
            render_citations(
                "Withdrawn evidence [[cite:h2]].",
                self.handles,
                evidence_set=(MATERIAL_A,),
            )

    def test_hand_written_numbers_and_reference_sections_are_rejected(self) -> None:
        with self.assertRaisesRegex(CitationClosureError, "手写的数字引用"):
            render_citations("A claim [1]. [[cite:h1]]", self.handles)
        with self.assertRaisesRegex(CitationClosureError, "参考资料小节"):
            render_citations(
                "A claim [[cite:h1]].\n\n## References\n\nsomething", self.handles
            )

    def test_a_malformed_marker_is_rejected(self) -> None:
        with self.assertRaisesRegex(CitationClosureError, "格式错误的引用标记"):
            render_citations("Broken [[cite:]]. [[cite:h1]]", self.handles)
        with self.assertRaisesRegex(CitationClosureError, "格式错误的引用标记"):
            render_citations("Broken [[ CITE:h1]]. [[cite:h1]]", self.handles)

    def test_a_report_citing_nothing_cannot_be_published(self) -> None:
        with self.assertRaisesRegex(CitationClosureError, "cites no evidence"):
            render_citations("A report with no grounded facts.", self.handles)

    def test_rendering_is_byte_stable_for_the_same_input(self) -> None:
        draft = "First [[cite:h2]] then [[cite:h1]]."
        self.assertEqual(
            render_citations(draft, self.handles).markdown,
            render_citations(draft, self.handles).markdown,
        )


if __name__ == "__main__":
    unittest.main()


class AdjacentCitationTest(RenderTest):
    def test_repeated_and_neighbouring_citations_merge_into_one_bracket(self) -> None:
        draft = (
            "Three handles, one source [[cite:h1]][[cite:h1]][[cite:h1]].\n"
            "Two distinct sources [[cite:h1]][[cite:h2]].\n"
        )

        result = render_citations(draft, self.handles)

        self.assertIn("one source [1].", result.markdown)
        self.assertIn("distinct sources [1, 2].", result.markdown)
        self.assertNotIn("[1][1]", result.markdown)

    def test_citations_separated_by_prose_are_left_alone(self) -> None:
        result = render_citations(
            "First claim [[cite:h1]] and then a second one [[cite:h2]].", self.handles
        )

        self.assertIn("First claim [1] and then a second one [2].", result.markdown)


class ReferenceFormatTest(RenderTest):
    def test_a_capture_timestamp_is_shown_as_a_date(self) -> None:
        precise = SourceSnapshotBody(
            url="https://example.test/a",
            title="Source a",
            text_ref=BodyRef.from_content("Exact evidence body."),
            fetched_at="2026-08-12T10:26:46.585733+00:00",
        )
        handles = build_handles(
            {MATERIAL_A: self.materials[MATERIAL_A]}, {SOURCE_A: precise}
        )

        result = render_citations("A claim [[cite:h1]].", handles)

        self.assertIn("(2026-08-12)", result.markdown)
        self.assertNotIn("10:26:46", result.markdown)


class SyntaxCorrectionTest(unittest.TestCase):
    """The correctable check and the fail-closed check must be one rule.

    Publication resolves every marker or refuses to publish, which is right: a
    marker a reader cannot follow is worse than no report.  But a live
    genre-shift run reached that refusal with a report already written,
    reviewed and approved, and lost all of it -- the Author's submission
    validator only looked for *well-formed* handles, so a malformed marker was
    invisible to it and sailed through.

    Both call sites now read the same function, so the guarantee at publication
    stays a last resort instead of becoming a second, slightly different rule.
    """

    FAULTS = {
        "spaced opener": "结论 [[ cite:h1]] 继续。",
        "unclosed marker": "结论 [[cite:h1] 继续。",
        "two handles in one marker": "结论 [[cite:h1, h2]] 继续。",
        "hand-written number": "结论 [[cite:h1]] 另一处 [1] 继续。",
        "self-written references": "结论 [[cite:h1]]\n\n## 参考资料\n\n1. x\n",
    }

    def test_every_fault_is_described_before_publication(self) -> None:
        for label, markdown in self.FAULTS.items():
            with self.subTest(fault=label):
                self.assertNotEqual("", citation_syntax_problem(markdown))

    def test_a_malformed_marker_is_located_not_just_announced(self) -> None:
        """A fault the role cannot find is a fault it cannot fix.

        The first Author told only that "there is a malformed marker" corrected
        nothing and lost the run on its second attempt -- the report was 40,000
        characters with about a hundred markers in it.
        """

        long_body = "正文段落。" * 200
        problem = citation_syntax_problem(
            f"{long_body} 结论 [[cite:h1]] 另一处 [[cite:h2, h3]] 收尾 [[cite:h4]]"
        )
        self.assertIn("[[cite:h2, h3]]", problem)
        self.assertNotIn("[[cite:h1]]", problem)

    def test_a_clean_report_reports_no_problem(self) -> None:
        self.assertEqual(
            "", citation_syntax_problem("结论 [[cite:h1]] 与 [[cite:h2]]。")
        )

    def test_publication_refuses_exactly_what_the_validator_describes(self) -> None:
        for label, markdown in self.FAULTS.items():
            with self.subTest(fault=label):
                with self.assertRaises(CitationClosureError):
                    render_citations(markdown, ())


if __name__ == "__main__":
    unittest.main()
