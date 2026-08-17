import unittest

from deep_research_agent.citations import (
    CitationClosureError,
    CitationRenderer,
    citation_marker_signature,
    render_citations,
)
from deep_research_agent.state import (
    ArtifactValidationError,
    BodyRef,
    CuratedMaterial,
    HydratedSource,
    SourceAnchor,
    SourceDocument,
    TextLocator,
    locate_quote,
    make_material_id,
    make_source_id,
    merge_source_corpus,
    validate_anchor,
    validate_anchors,
)


def make_source(name: str, content: str | None = None) -> SourceDocument:
    body = content or f"Exact evidence from {name}."
    return SourceDocument.create(
        title=f"Source {name}",
        url=f"https://example.test/{name}",
        body_ref=BodyRef.from_content(body),
        metadata={"provider": "fixture"},
    )


def make_hydrated_source(name: str, content: str | None = None) -> HydratedSource:
    body = content or f"Exact evidence from {name}."
    source = make_source(name, body)
    return HydratedSource(
        source_id=source.source_id,
        title=source.title,
        url=source.url,
        content=body,
        content_hash=source.content_hash,
        fetched_at=source.fetched_at,
        metadata=dict(source.metadata),
    )


class CitationRendererTest(unittest.TestCase):
    def test_curated_material_cannot_exist_without_a_source_anchor(self) -> None:
        with self.assertRaisesRegex(ArtifactValidationError, "SourceAnchor"):
            CuratedMaterial.create(
                content="Unsupported formal material.",
                boundaries="No source boundary exists.",
                anchors=(),
            )

    def test_numbers_by_first_appearance_reuses_and_collapses_multiple_sources(
        self,
    ) -> None:
        source_a = make_source("a")
        source_b = make_source("b")
        source_c = make_source("c")
        unused = make_source("unused")
        corpus = {
            source.source_id: source
            for source in (source_a, source_b, source_c, unused)
        }
        draft = (
            f"First [[cite:{source_b.source_id}]]. "
            f"Reuse [[cite:{source_b.source_id}]]. "
            f"Combined [[cite:{source_a.source_id}, {source_c.source_id}]]. "
            f"Adjacent [[cite:{source_a.source_id}]] [[cite:{source_b.source_id}]]."
        )

        result = render_citations(draft, corpus)

        self.assertIn("First [1].", result.markdown)
        self.assertIn("Reuse [1].", result.markdown)
        self.assertIn("Combined [2, 3].", result.markdown)
        self.assertIn("Adjacent [1, 2].", result.markdown)
        self.assertEqual(
            result.cited_source_ids,
            (source_b.source_id, source_a.source_id, source_c.source_id),
        )
        self.assertEqual(result.numbering[source_b.source_id], 1)
        self.assertEqual(result.numbering[source_a.source_id], 2)
        self.assertEqual(result.numbering[source_c.source_id], 3)
        self.assertIn("[1] Source b.", result.markdown)
        self.assertIn("[2] Source a.", result.markdown)
        self.assertIn("[3] Source c.", result.markdown)
        self.assertNotIn("Source unused", result.markdown)
        self.assertNotIn("[[cite:", result.markdown)

    def test_unknown_source_breaks_citation_closure(self) -> None:
        with self.assertRaisesRegex(CitationClosureError, "unknown source"):
            render_citations("Unsupported [[cite:src_missing]].", {})

    def test_malformed_marker_is_rejected(self) -> None:
        with self.assertRaisesRegex(CitationClosureError, "malformed"):
            render_citations("Broken [[cite:]].", {})
        with self.assertRaisesRegex(CitationClosureError, "malformed"):
            render_citations("Broken [[ CITE:src_a]].", {})

    def test_handwritten_numbers_and_reference_sections_are_rejected(self) -> None:
        with self.assertRaisesRegex(CitationClosureError, "numeric citations"):
            render_citations("A hand-written claim [1].", {})
        with self.assertRaisesRegex(CitationClosureError, "references section"):
            render_citations("Report\n\n## References\n\n[1] source", {})

    def test_source_corpus_key_must_match_artifact(self) -> None:
        source = make_source("actual")
        with self.assertRaisesRegex(CitationClosureError, "does not match"):
            render_citations("Mismatch [[cite:src_alias]].", {"src_alias": source})

    def test_report_without_citations_does_not_gain_a_reference_section(self) -> None:
        result = CitationRenderer().render("A report with no external facts.", {})

        self.assertEqual(result.markdown, "A report with no external facts.")
        self.assertEqual(result.cited_source_ids, ())
        self.assertEqual(result.numbering, {})


class ArtifactTrustBoundaryTest(unittest.TestCase):
    def test_source_rejects_non_web_private_credential_and_signed_urls(self) -> None:
        unsafe = (
            "file:///etc/passwd",
            "http://127.0.0.1/private",
            "https://user:password@example.test/report",
            "https://example.test/report?access_token=secret",
            "https://example.test/report?X-Amz-Signature=signed",
        )
        for url in unsafe:
            with self.subTest(url=url), self.assertRaises(ArtifactValidationError):
                SourceDocument.create(
                    title="unsafe", url=url, body_ref=BodyRef.from_content("body")
                )

    def test_source_ids_are_deterministic_for_an_exact_source_version(self) -> None:
        content = "An exact source body."
        first = SourceDocument.create(
            title="First title",
            url="HTTPS://EXAMPLE.TEST/report#section-one",
            body_ref=BodyRef.from_content(content),
        )
        second = SourceDocument.create(
            title="A changed display title",
            url="https://example.test/report#section-two",
            body_ref=BodyRef.from_content(content),
            metadata={"provider": "another"},
        )

        self.assertEqual(first.source_id, second.source_id)
        self.assertEqual(first.url, "https://example.test/report")
        self.assertEqual(
            first.source_id,
            make_source_id(
                "https://example.test/report", BodyRef.from_content(content).content_hash
            ),
        )
        self.assertNotEqual(
            first.source_id,
            make_source_id(
                "https://example.test/report",
                BodyRef.from_content(content + " Updated").content_hash,
            ),
        )

    def test_quote_locator_must_select_exact_saved_text(self) -> None:
        source = make_hydrated_source(
            "quotes", "Repeated evidence. Repeated evidence."
        )
        anchor = locate_quote(source, "Repeated evidence.", occurrence=2)

        validate_anchor(anchor, source)
        self.assertEqual(anchor.locator, TextLocator(start=19, end=37))

        invalid = SourceAnchor(
            source_id=source.source_id,
            exact_quote=anchor.exact_quote,
            locator=TextLocator(start=1, end=19),
        )
        with self.assertRaisesRegex(ArtifactValidationError, "does not match"):
            validate_anchor(invalid, source)

    def test_anchor_collection_rejects_unknown_sources(self) -> None:
        source = make_hydrated_source("known")
        anchor = locate_quote(source, "Exact evidence")

        with self.assertRaisesRegex(ArtifactValidationError, "unknown source"):
            validate_anchors((anchor,), {})

    def test_material_id_is_stable_regardless_of_anchor_input_order(self) -> None:
        source_a = make_hydrated_source("material-a")
        source_b = make_hydrated_source("material-b")
        anchor_a = locate_quote(source_a, "Exact evidence")
        anchor_b = locate_quote(source_b, "Exact evidence")

        first = CuratedMaterial.create(
            content="Both sources report the same bounded observation.",
            boundaries="Applies only to the fixture context.",
            anchors=(anchor_b, anchor_a),
        )
        second = CuratedMaterial.create(
            content=first.content,
            boundaries=first.boundaries,
            anchors=(anchor_a, anchor_b),
        )

        self.assertEqual(first, second)
        self.assertEqual(
            first.material_id,
            make_material_id(first.content, first.boundaries, first.anchors),
        )

    def test_source_reducer_merges_parallel_metadata_for_one_exact_source(self) -> None:
        source = make_source("merge")
        duplicate = SourceDocument(
            source_id=source.source_id,
            title="A richer display title",
            url=source.url,
            body_ref=source.body_ref,
            fetched_at="2026-08-11T12:00:00Z",
            metadata={"provider": "another", "language": "en"},
        )

        self.assertEqual(
            merge_source_corpus({}, {source.source_id: source}),
            {source.source_id: source},
        )
        merged = merge_source_corpus(
            {source.source_id: source},
            {duplicate.source_id: duplicate},
        )[source.source_id]
        reversed_merge = merge_source_corpus(
            {duplicate.source_id: duplicate},
            {source.source_id: source},
        )[source.source_id]

        self.assertEqual(merged, reversed_merge)
        self.assertEqual("A richer display title", merged.title)
        self.assertEqual("another | fixture", merged.metadata["provider"])
        self.assertEqual("en", merged.metadata["language"])

        third = SourceDocument(
            source_id=source.source_id,
            title="Third display title",
            url=source.url,
            body_ref=source.body_ref,
            fetched_at="2026-08-11T13:00:00Z",
            metadata={"provider": "third"},
        )
        left = merge_source_corpus(
            {source.source_id: merged},
            {third.source_id: third},
        )[source.source_id]
        right_branch = merge_source_corpus(
            {duplicate.source_id: duplicate},
            {third.source_id: third},
        )
        right = merge_source_corpus(
            {source.source_id: source},
            right_branch,
        )[source.source_id]
        replayed = merge_source_corpus(
            {left.source_id: left},
            {source.source_id: source},
        )[source.source_id]

        self.assertEqual(left, right)
        self.assertEqual(left, replayed)
        self.assertEqual("another | fixture | third", left.metadata["provider"])

    def test_citation_signature_detects_marker_removal_and_reassociation(self) -> None:
        marker = "[[cite:src_fixture]]"
        original = f"First claim.{marker}\n\nSecond claim."
        removed = "First claim.\n\nSecond claim."
        moved = f"First claim.\n\nSecond claim.{marker}"

        self.assertNotEqual(
            citation_marker_signature(original),
            citation_marker_signature(removed),
        )
        self.assertNotEqual(
            citation_marker_signature(original),
            citation_marker_signature(moved),
        )


if __name__ == "__main__":
    unittest.main()
