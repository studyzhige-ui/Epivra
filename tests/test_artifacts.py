from __future__ import annotations

import unittest

from deep_research_agent.artifacts import (
    ArtifactDisposition,
    ArtifactEnvelope,
    Provenance,
    evidence_set_id,
    kind_of,
    lineage_closure,
    make_artifact_id,
    normalize_parent_refs,
    project_active_view,
    require_artifact_id,
    require_evidence_set_id,
)
from deep_research_agent.state import ArtifactValidationError, BodyRef


def body(text: str) -> BodyRef:
    return BodyRef.from_content(text)


def artifact(
    kind: str, text: str, parents: tuple[str, ...] = ()
) -> ArtifactEnvelope:
    return ArtifactEnvelope.create(kind=kind, body_ref=body(text), parent_refs=parents)


class ArtifactIdentityTest(unittest.TestCase):
    def test_identity_is_stable_for_the_same_kind_body_and_lineage(self) -> None:
        first = artifact("material", "Exact curated excerpt.")
        second = artifact("material", "Exact curated excerpt.")

        self.assertEqual(first.artifact_id, second.artifact_id)
        self.assertEqual("mat", first.artifact_id.split("_")[0])
        self.assertEqual("material", kind_of(first.artifact_id))

    def test_same_body_with_different_lineage_stays_distinct(self) -> None:
        source_a = artifact("source_snapshot", "Source A body.")
        source_b = artifact("source_snapshot", "Source B body.")

        from_a = artifact("material", "Identical wording.", (source_a.artifact_id,))
        from_b = artifact("material", "Identical wording.", (source_b.artifact_id,))

        self.assertEqual(from_a.body_ref, from_b.body_ref)
        self.assertNotEqual(from_a.artifact_id, from_b.artifact_id)

    def test_same_body_and_kind_across_kinds_stays_distinct(self) -> None:
        shared = "A body that two kinds could both carry."
        self.assertNotEqual(
            make_artifact_id("synthesis", body(shared)),
            make_artifact_id("report", body(shared)),
        )

    def test_provenance_does_not_participate_in_identity(self) -> None:
        reference = body("One synthesis body.")
        bare = ArtifactEnvelope.create(kind="synthesis", body_ref=reference)
        attributed = ArtifactEnvelope.create(
            kind="synthesis",
            body_ref=reference,
            provenance=Provenance(
                produced_at="2026-08-17T12:00:00Z",
                producer="analyst",
                operation_ref="op-1",
                model_id="test-model",
            ),
        )

        self.assertEqual(bare.artifact_id, attributed.artifact_id)
        self.assertEqual("analyst", attributed.provenance.producer)

    def test_parent_order_and_duplicates_do_not_change_identity(self) -> None:
        first = artifact("source_snapshot", "First source.").artifact_id
        second = artifact("source_snapshot", "Second source.").artifact_id

        forward = artifact("material", "Two anchors.", (first, second))
        reversed_with_duplicate = artifact(
            "material", "Two anchors.", (second, first, second)
        )

        self.assertEqual(forward.artifact_id, reversed_with_duplicate.artifact_id)
        self.assertEqual((min(first, second), max(first, second)), forward.parent_refs)

    def test_unsupported_kind_and_malformed_refs_are_rejected(self) -> None:
        with self.assertRaises(ArtifactValidationError):
            make_artifact_id("coverage_score", body("x"))
        with self.assertRaises(ArtifactValidationError):
            require_artifact_id("mat_not_a_digest")
        with self.assertRaises(ArtifactValidationError):
            normalize_parent_refs(("branch-1",))

    def test_envelope_rejects_a_forged_identity(self) -> None:
        genuine = artifact("report", "Report body.")
        with self.assertRaisesRegex(ArtifactValidationError, "artifact_id"):
            ArtifactEnvelope(
                artifact_id=genuine.artifact_id,
                kind="report",
                body_ref=body("A different report body."),
            )

    def test_envelope_requires_canonical_parent_ordering(self) -> None:
        first = artifact("source_snapshot", "First source.").artifact_id
        second = artifact("source_snapshot", "Second source.").artifact_id
        unsorted = tuple(sorted((first, second), reverse=True))

        with self.assertRaisesRegex(ArtifactValidationError, "sorted"):
            ArtifactEnvelope(
                artifact_id=make_artifact_id("material", body("m"), unsorted),
                kind="material",
                body_ref=body("m"),
                parent_refs=unsorted,
            )


class DispositionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.target = artifact("material", "Superseded excerpt.").artifact_id
        self.replacement = artifact("material", "Corrected excerpt.").artifact_id

    def test_superseded_requires_a_distinct_replacement(self) -> None:
        disposition = ArtifactDisposition(
            target_ref=self.target,
            status="superseded",
            reason="A more reliable version of the same source was published.",
            replacement_ref=self.replacement,
        )
        self.assertEqual(self.replacement, disposition.replacement_ref)

        with self.assertRaisesRegex(ArtifactValidationError, "replacement_ref"):
            ArtifactDisposition(
                target_ref=self.target,
                status="superseded",
                reason="Missing successor.",
            )
        with self.assertRaisesRegex(ArtifactValidationError, "differ"):
            ArtifactDisposition(
                target_ref=self.target,
                status="superseded",
                reason="Self replacement.",
                replacement_ref=self.target,
            )

    def test_retractions_must_not_name_a_replacement(self) -> None:
        for status in ("withdrawn", "quarantined"):
            with self.subTest(status=status):
                ArtifactDisposition(
                    target_ref=self.target,
                    status=status,
                    reason="Recorded for audit.",
                )
                with self.assertRaisesRegex(ArtifactValidationError, "replacement"):
                    ArtifactDisposition(
                        target_ref=self.target,
                        status=status,
                        reason="Recorded for audit.",
                        replacement_ref=self.replacement,
                    )

    def test_status_outside_the_closed_set_is_rejected(self) -> None:
        for status in ("qualified", "rejected", "approved", "L0"):
            with self.subTest(status=status):
                with self.assertRaises(ArtifactValidationError):
                    ArtifactDisposition(
                        target_ref=self.target,
                        status=status,
                        reason="Not a supported status.",
                    )

    def test_reason_is_mandatory(self) -> None:
        with self.assertRaisesRegex(ArtifactValidationError, "reason"):
            ArtifactDisposition(
                target_ref=self.target, status="withdrawn", reason="   "
            )


class ActiveViewTest(unittest.TestCase):
    def test_singleton_head_is_the_newest_active_artifact(self) -> None:
        first = artifact("synthesis", "First synthesis.")
        second = artifact("synthesis", "Second synthesis.")

        view = project_active_view((first, second))

        self.assertEqual(second.artifact_id, view.head("synthesis"))
        self.assertEqual(
            (first.artifact_id, second.artifact_id), view.active("synthesis")
        )

    def test_disposed_artifacts_leave_the_active_view_but_stay_known(self) -> None:
        original = artifact("material", "Original excerpt.")
        corrected = artifact("material", "Corrected excerpt.")
        disposition = ArtifactDisposition(
            target_ref=original.artifact_id,
            status="superseded",
            reason="Publisher issued a correction.",
            replacement_ref=corrected.artifact_id,
        )

        view = project_active_view((original, corrected), (disposition,))

        self.assertEqual((corrected.artifact_id,), view.active("material"))

    def test_head_is_none_before_a_kind_exists(self) -> None:
        view = project_active_view(())
        self.assertIsNone(view.head("report"))
        self.assertEqual((), view.active("material"))

    def test_collection_kinds_reject_head_access(self) -> None:
        view = project_active_view(())
        with self.assertRaisesRegex(ArtifactValidationError, "accumulates"):
            view.head("material")

    def test_disposition_for_an_unknown_target_fails_closed(self) -> None:
        stray = ArtifactDisposition(
            target_ref=artifact("material", "Absent.").artifact_id,
            status="withdrawn",
            reason="Target was never committed here.",
        )
        with self.assertRaisesRegex(ArtifactValidationError, "unknown artifact"):
            project_active_view((), (stray,))


class EvidenceSetTest(unittest.TestCase):
    def test_identity_ignores_order_and_duplicates(self) -> None:
        first = artifact("material", "First material.").artifact_id
        second = artifact("material", "Second material.").artifact_id

        self.assertEqual(
            evidence_set_id((first, second)),
            evidence_set_id((second, first, first)),
        )
        require_evidence_set_id(evidence_set_id((first, second)))

    def test_adding_material_changes_the_set_identity(self) -> None:
        first = artifact("material", "First material.").artifact_id
        second = artifact("material", "Second material.").artifact_id

        self.assertNotEqual(evidence_set_id((first,)), evidence_set_id((first, second)))

    def test_only_material_artifacts_form_an_evidence_set(self) -> None:
        source = artifact("source_snapshot", "A source body.").artifact_id
        with self.assertRaisesRegex(ArtifactValidationError, "not a Material"):
            evidence_set_id((source,))

    def test_active_view_exposes_the_current_evidence_set(self) -> None:
        kept = artifact("material", "Kept material.")
        dropped = artifact("material", "Dropped material.")
        view = project_active_view(
            (kept, dropped),
            (
                ArtifactDisposition(
                    target_ref=dropped.artifact_id,
                    status="withdrawn",
                    reason="Curator retracted an over-broad paraphrase.",
                ),
            ),
        )

        self.assertEqual(
            evidence_set_id((kept.artifact_id,)), view.evidence_set_id()
        )


class LineageTest(unittest.TestCase):
    def test_closure_walks_every_ancestor(self) -> None:
        source = artifact("source_snapshot", "Source body.")
        material = artifact("material", "Excerpt.", (source.artifact_id,))
        synthesis = artifact("synthesis", "Analysis.", (material.artifact_id,))
        report = artifact("report", "Report.", (synthesis.artifact_id,))
        index = {
            item.artifact_id: item
            for item in (source, material, synthesis, report)
        }

        closure = lineage_closure(report.artifact_id, index)

        self.assertEqual(set(index), set(closure))

    def test_closure_fails_closed_on_a_dangling_parent(self) -> None:
        orphan_parent = artifact("synthesis", "Absent synthesis.").artifact_id
        report = artifact("report", "Report.", (orphan_parent,))

        with self.assertRaisesRegex(ArtifactValidationError, "unknown artifact"):
            lineage_closure(report.artifact_id, {report.artifact_id: report})


if __name__ == "__main__":
    unittest.main()
