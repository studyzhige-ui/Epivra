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

    def run_publisher(self, *, tagged=None, existing=None):
        def command(args, **kwargs):
            self.commands.append(args)
            if args[:2] == ["gh", "api"]:
                value = tagged if "/commits/" in args[2] else existing
                return SimpleNamespace(returncode=0 if value is not None else 1,
                    stdout=json.dumps(value), stderr="(HTTP 404)" if value is None else "")
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
