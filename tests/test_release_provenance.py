"""Exercise the actual workflow publisher offline with tiny fake archives."""

import hashlib
import json
import os
import tempfile
import textwrap
import unittest
import zipfile
from contextlib import chdir
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


class ReleaseProvenanceTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.sha = "a" * 40
        self.version = "0.3.5"
        self.name = "Epivra-0.3.5-windows-x64"
        self.archive = self.root / "release" / (self.name + ".zip")
        self.archive.parent.mkdir()
        self.check = self.archive.with_name(self.archive.name + ".sha256")
        (self.root / "pyproject.toml").write_text('[project]\nversion="0.3.5"\n')
        self.write_archive()
        workflow = (Path(__file__).resolve().parents[1] / ".github/workflows/desktop-release.yml").read_text()
        step = workflow.split("      - name: Publish desktop release\n", 1)[1]
        self.publisher = textwrap.dedent(step.split("        run: |\n", 1)[1])
        self.commands = []

    def write_archive(self, **overrides):
        with zipfile.ZipFile(self.archive, "w") as bundle:
            bundle.writestr(self.name + "/BUILD.json", json.dumps({
                "version": self.version, "commit": self.sha, "dirty": False, **overrides}))
        self.check.write_text(hashlib.sha256(self.archive.read_bytes()).hexdigest() + "  " + self.archive.name + "\n")

    def assets(self):
        return [{"name": path.name, "state": "uploaded",
                 "digest": "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()}
                for path in (self.archive, self.check)]

    def run_publisher(self, *, tagged=None, existing=None, tag_ref="auto", errors=None):
        if tag_ref == "auto":
            tag_ref = {"object": {"type": "commit", "sha": tagged["sha"]}} if tagged is not None else None
        responses = {
            "git/ref/tags/v0.3.5": tag_ref,
            "commits/tags/v0.3.5": tagged,
            "releases/tags/v0.3.5": existing,
        }
        errors = errors or {}
        def command(args, **kwargs):
            self.commands.append(args)
            if args[:2] == ["gh", "api"]:
                endpoint = args[2].removeprefix("repos/fixture/epivra/")
                self.assertIn(endpoint, responses)
                value = responses[endpoint]
                # GitHub resolves a missing commit/tag name with 422, whereas an
                # absent exact Git ref uses 404. Do not hide that API distinction.
                error = errors.get(endpoint, "(HTTP 422)" if endpoint.startswith("commits/") else "(HTTP 404)")
                return SimpleNamespace(returncode=0 if value is not None and endpoint not in errors else 1,
                    stdout=json.dumps(value), stderr=error if value is None or endpoint in errors else "")
            self.assertEqual(args[:2], ["gh", "release"])
            self.assertNotIn("--clobber", args)
            return SimpleNamespace(returncode=0)

        with (
            chdir(self.root), patch("subprocess.run", side_effect=command),
            patch.dict(os.environ, {"GH_REPO": "fixture/epivra", "BUILD_SHA": self.sha}),
        ):
            exec(compile(self.publisher, "desktop-release-publisher", "exec"), {})

    def mutations(self):
        return [args for args in self.commands if args[:2] == ["gh", "release"]]

    def test_new_release_uses_verified_commit_and_both_assets(self):
        self.run_publisher()
        command = self.mutations()[0]
        self.assertEqual(command[:4], ["gh", "release", "create", "v0.3.5"])
        self.assertEqual(command[command.index("--target") + 1], self.sha)
        self.assertIn("release/" + self.archive.name, [part.replace("\\", "/") for part in command])
        self.assertIn("release/" + self.check.name, [part.replace("\\", "/") for part in command])

    def test_missing_tag_checks_exact_ref_without_commit_resolution(self):
        self.run_publisher()
        endpoints = [args[2] for args in self.commands if args[:2] == ["gh", "api"]]
        self.assertEqual(endpoints, ["repos/fixture/epivra/git/ref/tags/v0.3.5",
                                     "repos/fixture/epivra/releases/tags/v0.3.5"])
        self.assertEqual([args[2] for args in self.mutations()], ["create"])

    def test_existing_annotated_tag_is_resolved_to_its_commit(self):
        self.run_publisher(tag_ref={"object": {"type": "tag", "sha": "c" * 40}},
                           tagged={"sha": self.sha}, existing={"assets": self.assets()})
        self.assertEqual([args[2] for args in self.mutations()], ["edit"])
        self.assertIn(["gh", "api", "repos/fixture/epivra/commits/tags/v0.3.5"], self.commands)

    def test_existing_ref_with_unresolvable_commit_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError, "HTTP 422"):
            self.run_publisher(tag_ref={"object": {"type": "tag", "sha": "c" * 40}})
        self.assertEqual(self.mutations(), [])

    def test_non_absence_api_errors_fail_closed(self):
        for endpoint in ("git/ref/tags/v0.3.5", "releases/tags/v0.3.5"):
            for status in (403, 422, 500):
                self.commands.clear()
                with self.assertRaisesRegex(RuntimeError, f"HTTP {status}"):
                    self.run_publisher(errors={endpoint: f"(HTTP {status})"})
                self.assertEqual(self.mutations(), [])

    def test_existing_identical_assets_are_not_uploaded_again(self):
        self.run_publisher(tagged={"sha": self.sha}, existing={"assets": self.assets()})
        self.assertEqual([args[2] for args in self.mutations()], ["edit"])

    def test_partial_release_uploads_only_missing_asset(self):
        self.run_publisher(tagged={"sha": self.sha}, existing={"assets": self.assets()[:1]})
        self.assertEqual([args[2] for args in self.mutations()], ["upload", "edit"])
        command = self.mutations()[0]
        self.assertNotIn("release/" + self.archive.name, [part.replace("\\", "/") for part in command])

    def test_different_or_unverified_existing_asset_blocks_every_mutation(self):
        for digest in ("sha256:" + "0" * 64, None):
            self.commands.clear()
            assets = self.assets()
            assets[0]["digest"] = digest
            with self.assertRaisesRegex(AssertionError, "never overwrite"):
                self.run_publisher(tagged={"sha": self.sha}, existing={"assets": assets})
            self.assertEqual(self.mutations(), [])

    def test_existing_tag_must_bind_the_same_commit(self):
        with self.assertRaisesRegex(AssertionError, "different source"):
            self.run_publisher(tagged={"sha": "b" * 40})
        self.assertEqual(self.mutations(), [])

    def test_release_without_tag_is_not_repaired_by_guessing(self):
        with self.assertRaisesRegex(AssertionError, "no source tag"):
            self.run_publisher(existing={"assets": self.assets()})
        self.assertEqual(self.mutations(), [])

    def test_archive_provenance_is_checked_before_publication(self):
        for altered in ({"commit": "b" * 40}, {"dirty": True}, {"version": "0.3.4"}):
            self.write_archive(**altered)
            with self.assertRaisesRegex(AssertionError, "provenance mismatch"):
                self.run_publisher()
            self.assertEqual(self.mutations(), [])

    def test_bad_checksum_never_reaches_publication(self):
        self.check.write_text("0" * 64 + "  " + self.archive.name)
        with self.assertRaisesRegex(AssertionError, "checksum mismatch"):
            self.run_publisher()
        self.assertEqual(self.mutations(), [])
