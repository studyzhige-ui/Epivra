"""Offline execution transport limits and extraction coverage invariants."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from epivra import analysis, document_parser, native_analysis


class Additional(unittest.IsolatedAsyncioTestCase):
    async def test_docker_adapter_output_cap(self):
        with patch.object(analysis, "docker_executable", return_value=sys.executable):
            with self.assertRaisesRegex(ValueError, "output limit"):
                await analysis.docker(
                    "-c", 'import sys;sys.stdout.write("x"*5000)', cap=1000
                )

    async def test_docker_adapter_timeout(self):
        with patch.object(analysis, "docker_executable", return_value=sys.executable):
            with self.assertRaises(TimeoutError):
                await analysis.docker("-c", "import time;time.sleep(5)", timeout=0.05)

    async def test_docker_adapter_no_credentials(self):
        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "fake"}),
            patch.object(analysis, "docker_executable", return_value=sys.executable),
        ):
            output = await analysis.docker(
                "-c",
                'import os;assert "OPENAI_API_KEY" not in os.environ;print("clean")',
            )
        self.assertEqual(output.strip(), b"clean")

    @unittest.skipIf(sys.platform == "win32", "Checks the unsupported-platform guard")
    async def test_native_rejects_unsupported_platform(self):
        with tempfile.TemporaryDirectory() as p:
            with self.assertRaisesRegex(ValueError, "Windows x64"):
                await native_analysis.NativeSandbox(p).run(
                    "a" * 64, Path(p), analysis.DEFAULTS, True, lambda: None
                )

    def test_located_document_never_hides_partial_extraction(self):
        loc = SimpleNamespace(
            page_no=1, bbox=SimpleNamespace(model_dump=lambda **kw: {"l": 1, "r": 2})
        )
        items = [
            (
                SimpleNamespace(
                    label="text", text="text", self_ref="#/text/0", prov=[loc]
                ),
                0,
            ),
            (
                SimpleNamespace(
                    label="picture", text="", self_ref="#/picture/0", prov=[]
                ),
                0,
            ),
        ]
        doc = SimpleNamespace(
            pages={1: None, 2: None}, iterate_items=lambda: iter(items)
        )
        result = document_parser.located_document(
            doc, "partial_success", "test", [object()]
        )
        self.assertEqual(result["coverage"], "partial_extraction")
        self.assertEqual(result["text"], "text\n\n")
        self.assertEqual(len(result["issues"]), 3)
        self.assertTrue(
            all(result["text"][s["start"] : s["end"]] for s in result["segments"])
        )
