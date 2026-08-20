"""Source access is a permission the Trust Plane enforces, not prose.

``source_access`` used to travel to the Investigator only as a sentence in its
context ("允许使用：public_web"). Nothing checked it. Under ``local_only`` -- the
mode whose entire purpose is that the topic never reaches a search vendor -- the
branch could still have searched Tavily and fetched any URL.

The two source families also have different threat models, which is why they get
separate validators: a web URL must not reach a private address, a local path must
not escape the granted corpus. One validator doing both would weaken each.
"""

from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

from deep_research_agent.contract import CommissionBody
from deep_research_agent.providers._http import SourceReadError
from deep_research_agent.providers.local import LocalCorpusReader
from deep_research_agent.sources import (
    ArtifactValidationError,
    BodyRef,
    SourceSnapshotBody,
    canonical_local_ref,
    is_local_source,
    source_locator,
)
from deep_research_agent.wave import SourcePermission


class PermissionDerivationTest(unittest.TestCase):
    def test_public_web_grants_network_only(self) -> None:
        permission = SourcePermission.of(("public_web",))
        self.assertTrue(permission.network)
        self.assertFalse(permission.local)

    def test_user_files_adds_the_corpus_without_removing_the_web(self) -> None:
        permission = SourcePermission.of(("public_web", "user_files"))
        self.assertTrue(permission.network)
        self.assertTrue(permission.local)

    def test_local_only_forbids_the_network(self) -> None:
        permission = SourcePermission.of(("local_only",))
        self.assertFalse(permission.network)
        self.assertTrue(permission.local)

    def test_local_only_cannot_be_combined_with_the_web(self) -> None:
        """A contradiction on the one artifact no model may rewrite."""

        with self.assertRaisesRegex(ArtifactValidationError, "cannot be combined"):
            CommissionBody(
                request="Study X.", source_access=("local_only", "public_web")
            )

    def test_the_commission_reports_both_capabilities(self) -> None:
        commission = CommissionBody(
            request="Study X.", source_access=("user_files",)
        )
        self.assertFalse(commission.allows_external_search)
        self.assertTrue(commission.allows_local_corpus)


class LocalIdentityTest(unittest.TestCase):
    """Identity stays corpus-relative; an absolute path would leak the layout."""

    def test_a_relative_reference_is_canonicalised(self) -> None:
        self.assertEqual(
            "local:reports/q3.pdf", canonical_local_ref("local:./reports/q3.pdf")
        )
        self.assertEqual(
            "local:reports/q3.pdf", canonical_local_ref("reports\\q3.pdf")
        )

    def test_traversal_is_refused(self) -> None:
        with self.assertRaisesRegex(ArtifactValidationError, "climb out"):
            canonical_local_ref("local:../../etc/passwd")

    def test_an_absolute_path_is_refused_rather_than_reinterpreted(self) -> None:
        """Stripping the slash would accept a reference nobody wrote."""

        with self.assertRaisesRegex(ArtifactValidationError, "not absolute"):
            canonical_local_ref("local:/etc/passwd")

    def test_a_drive_letter_is_refused(self) -> None:
        with self.assertRaisesRegex(ArtifactValidationError, "relative"):
            canonical_local_ref("local:C:/Users/secret.txt")

    def test_the_locator_dispatches_by_scheme(self) -> None:
        self.assertEqual("local:a/b.md", source_locator("local:a/b.md"))
        self.assertEqual("https://example.org/x", source_locator("https://example.org/x"))
        self.assertTrue(is_local_source("local:a/b.md"))
        self.assertFalse(is_local_source("https://example.org/x"))

    def test_web_guards_are_not_reachable_through_the_local_path(self) -> None:
        """A private address must not become readable by dressing it as local."""

        for value in ("http://127.0.0.1/x", "http://localhost/x", "file:///etc/passwd"):
            with self.subTest(value=value):
                with self.assertRaises(ArtifactValidationError):
                    source_locator(value)

    def test_a_snapshot_accepts_a_local_source(self) -> None:
        body = SourceSnapshotBody(
            url="local:notes/a.md",
            title="a.md",
            text_ref=BodyRef("0" * 64, 12),
        )
        self.assertEqual("local:notes/a.md", body.url)


class LocalReaderTest(unittest.TestCase):
    def setUp(self) -> None:
        self._directory = tempfile.TemporaryDirectory()
        self.root = Path(self._directory.name) / "corpus"
        (self.root / "sub").mkdir(parents=True)
        (self.root / "notes.md").write_text("# Notes\n\nA finding.\n", encoding="utf-8")
        (self.root / "sub" / "data.csv").write_text("a,b\n1,2\n", encoding="utf-8")
        (self.root / "image.png").write_bytes(b"\x89PNG\r\n")
        self.outside = Path(self._directory.name) / "secret.txt"
        self.outside.write_text("do not read me", encoding="utf-8")
        self.reader = LocalCorpusReader(root=self.root)

    def tearDown(self) -> None:
        self._directory.cleanup()

    def test_a_granted_file_is_read_with_a_relative_identity(self) -> None:
        result = asyncio.run(self.reader.read("local:notes.md"))
        self.assertEqual("local:notes.md", result.url)
        self.assertIn("A finding.", result.content)

    def test_the_listing_offers_only_readable_files(self) -> None:
        listing = self.reader.listing()
        self.assertIn("local:notes.md", listing)
        self.assertIn("local:sub/data.csv", listing)
        self.assertNotIn("local:image.png", listing)

    def test_a_binary_type_is_refused_by_name_not_decoded_hopefully(self) -> None:
        (self.root / "blob.bin").write_bytes(b"\x00\x01\x02")
        with self.assertRaisesRegex(SourceReadError, "not readable as text"):
            asyncio.run(self.reader.read("local:blob.bin"))

    def test_traversal_cannot_reach_outside_the_root(self) -> None:
        with self.assertRaises(ArtifactValidationError):
            asyncio.run(self.reader.read("local:../secret.txt"))

    def test_a_symlink_out_of_the_corpus_is_refused(self) -> None:
        """Containment is checked on the resolved path, so links cannot escape."""

        link = self.root / "escape.md"
        try:
            link.symlink_to(self.outside)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable on this platform")
        with self.assertRaisesRegex(SourceReadError, "outside the granted corpus"):
            asyncio.run(self.reader.read("local:escape.md"))

    def test_a_missing_file_is_an_operational_failure(self) -> None:
        with self.assertRaisesRegex(SourceReadError, "does not exist"):
            asyncio.run(self.reader.read("local:absent.md"))

    def test_an_empty_file_is_refused(self) -> None:
        (self.root / "empty.md").write_text("", encoding="utf-8")
        with self.assertRaisesRegex(SourceReadError, "empty"):
            asyncio.run(self.reader.read("local:empty.md"))

    def test_a_root_that_is_not_a_directory_is_refused(self) -> None:
        with self.assertRaisesRegex(ValueError, "not a directory"):
            LocalCorpusReader(root=self.root / "notes.md")


if __name__ == "__main__":
    unittest.main()
