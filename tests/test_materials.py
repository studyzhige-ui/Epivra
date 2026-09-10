from __future__ import annotations

import asyncio
import base64
import io
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from openpyxl import Workbook
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from deep_research_agent.domain import Call, NotAllowed, Reply
from deep_research_agent.harness import Harness
from deep_research_agent.host import Host, send
from deep_research_agent.materials import parse
from deep_research_agent.storage import Store
from deep_research_agent.workspace import Workspace


def pdf_bytes(encrypted=False):
    writer = PdfWriter()
    page = writer.add_blank_page(300, 200)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject(
                {NameObject("/F1"): writer._add_object(font)}
            )
        }
    )
    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 12 Tf 20 100 Td (Primary evidence) Tj ET")
    page[NameObject("/Contents")] = writer._add_object(stream)
    writer.add_blank_page(300, 200)
    if encrypted:
        writer.encrypt("fixture-password")
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def xlsx_bytes():
    book = Workbook()
    sheet = book.active
    sheet.title = "中文证据"
    sheet["B2"] = "限制条件"
    sheet["C2"] = "=SUM(1,2)"
    sheet["D2"] = 0.12
    sheet["D2"].number_format = "0%"
    hidden = book.create_sheet("反证")
    hidden.sheet_state = "hidden"
    hidden["A1"] = "negative finding"
    output = io.BytesIO()
    book.save(output)
    book.close()
    return output.getvalue()


class MaterialTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.root = Path(self.folder.name)
        self.store = Store(self.root / "state.db")
        self.c = self.store.create("s", "Research", {"local_roots": [str(self.root)]})
        self.workspace = Workspace(self.store)

    def tearDown(self):
        self.store.close()
        self.folder.cleanup()

    def test_pdf_text_and_missing_page_have_exact_locators(self):
        raw = pdf_bytes()
        source = self.workspace.upload("s", "evidence.pdf", raw)
        body = source.body
        first, second = body["segments"]
        self.assertEqual({"page": 1}, first["locator"])
        self.assertIn("Primary evidence", body["text"][first["start"] : first["end"]])
        self.assertEqual("needs_ocr_or_visual_review", second["status"])
        original = self.store.get("s", body["original_ref"])
        self.assertEqual(raw, base64.b64decode(original.body["data"]))
        self.assertIn(original.ref, source.parents)

    def test_xlsx_preserves_sparse_coordinates_formulas_and_hidden_evidence(self):
        body = parse("book.xlsx", xlsx_bytes())
        first = body["segments"][0]
        self.assertEqual(2, first["locator"]["row"])
        self.assertEqual("中文证据", first["locator"]["sheet"])
        cells = json.loads(body["text"][first["start"] : first["end"]])
        self.assertEqual("B2", cells[0]["cell"])
        self.assertEqual("限制条件", cells[0]["value"])
        self.assertEqual("=SUM(1,2)", cells[1]["value"])
        self.assertEqual("f", cells[1]["type"])
        self.assertEqual("0%", cells[2]["number_format"])
        self.assertEqual("hidden", body["segments"][1]["locator"]["visibility"])
        self.assertIn("negative finding", body["text"])

    def test_csv_embedded_newline_is_one_citable_row(self):
        body = parse("table.csv", 'name,value\r\n"A, B","多行\n内容"\r\n'.encode())
        self.assertEqual(2, len(body["segments"]))
        segment = body["segments"][1]
        self.assertEqual(
            ["A, B", "多行\n内容"],
            json.loads(body["text"][segment["start"] : segment["end"]]),
        )
        self.assertEqual({"row": 2}, segment["locator"])

    def test_encrypted_and_corrupt_materials_do_not_create_false_sources(self):
        for name, raw in [
            ("locked.pdf", pdf_bytes(True)),
            ("bad.xlsx", b"not xlsx"),
            ("bad.csv", b'"unterminated'),
        ]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.workspace.upload("s", name, raw)
        self.assertEqual([], self.store.list("s", "source"))
        self.assertEqual([], self.store.list("s", "material_bytes"))

    def test_save_failure_rolls_back_original_bytes_and_source(self):
        original = self.store._put

        def fail(study, kind, body, parents):
            if kind == "source":
                raise OSError("disk failure")
            return original(study, kind, body, parents)

        with (
            patch.object(self.store, "_put", side_effect=fail),
            self.assertRaises(OSError),
        ):
            self.workspace.upload("s", "file.txt", b"contents")
        self.assertEqual([], self.store.list("s", "material_bytes"))

    def test_snapshot_and_upload_replay_without_reparsing(self):
        path = self.root / "file.pdf"
        path.write_bytes(pdf_bytes())
        catalog = self.workspace.discover("s", str(self.root))
        first = self.workspace.snapshot("s", catalog.ref, path.name)
        path.write_bytes(b"changed")
        with patch(
            "deep_research_agent.workspace.parse", side_effect=AssertionError("reparse")
        ):
            self.assertEqual(
                first.ref, self.workspace.snapshot("s", catalog.ref, path.name).ref
            )
            self.assertEqual(
                first.ref, self.workspace.upload("s", path.name, pdf_bytes()).ref
            )


class MaterialAsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_async_snapshot_then_model_read_exposes_coverage_and_page_location(
        self,
    ):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            store = Store(root / "state.db")
            try:
                c = store.create("s", "Research", {"local_roots": [str(root)]})
                plan = store.put("s", "plan", {"text": "Plan"}, (c.direction,))
                c = store.command("s", "approve", c.ref, "approve", {"plan": plan.ref})
                work = store.work("s", c.ref, "researcher", "Read PDF")
                (root / "source.pdf").write_bytes(pdf_bytes())
                catalog = Workspace(store).discover("s", str(root))

                class Model:
                    identity = "fixture"

                    async def complete(self, request):
                        sources = store.list("s", "source")
                        call = (
                            Call(
                                "read_source",
                                {"ref": sources[0].ref, "offset": 0, "limit": 1000},
                            )
                            if sources
                            else Call(
                                "snapshot_local",
                                {"catalog": catalog.ref, "path": "source.pdf"},
                            )
                        )
                        return Reply("", (call,)).to_json()

                harness = Harness(store, Model())
                await harness.step("s", work.ref)
                await harness.step("s", work.ref)
                result = store.list("s", "observation")[-1].body["result"]
                self.assertEqual({"page": 1}, result["segments"][0]["locator"])
                self.assertEqual("partial_extraction", result["coverage"])
                source = store.list("s", "source")[0]
                with self.assertRaises(NotAllowed):
                    harness._builtin(
                        "s",
                        work,
                        c.epoch,
                        "fixture",
                        0,
                        Call("read_artifact", {"ref": source.body["original_ref"]}),
                    )
            finally:
                store.close()

    async def test_control_remains_responsive_and_changed_upload_is_not_adopted(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            host = Host(root)
            c = host.store.create("s", "Research", {})
            entered, release = threading.Event(), threading.Event()

            def slow(name, raw):
                entered.set()
                release.wait(3)
                return parse(name, raw)

            try:
                request = {
                    "token": host.token,
                    "action": "upload",
                    "study": "s",
                    "expected": c.ref,
                    "name": "input.txt",
                    "data": base64.b64encode(b"evidence").decode(),
                }
                with patch("deep_research_agent.workspace.parse", side_effect=slow):
                    task = asyncio.create_task(host.dispatch(request))
                    self.assertTrue(await asyncio.to_thread(entered.wait, 1))
                    host.store.command("s", "pause", c.ref, "pause")
                    release.set()
                    with self.assertRaisesRegex(ValueError, "control changed"):
                        await task
                self.assertEqual([], host.store.list("s", "source"))
            finally:
                release.set()
                host.store.close()

    async def test_upload_over_ipc_requires_pause_after_approval(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            host = Host(root)
            c = host.store.create("s", "Research", {})
            plan = host.store.put("s", "plan", {"text": "Plan"}, (c.direction,))
            c = host.store.command("s", "approve", c.ref, "approve", {"plan": plan.ref})
            c = host.store.command("s", "pause", c.ref, "pause")
            task = asyncio.create_task(host.serve())
            for _ in range(100):
                if (root / ".deep-research-agent/host.json").exists():
                    break
                await asyncio.sleep(0.01)
            try:
                request = {
                    "action": "upload",
                    "study": "s",
                    "expected": c.ref,
                    "name": "表格.xlsx",
                    "data": base64.b64encode(xlsx_bytes()).decode(),
                }
                result = await send(root, request)
                self.assertIn("source", result)
                self.assertEqual(result, await send(root, request))
                local = root / "上传.csv"
                local.write_text("name,value\n证据,42\n", encoding="utf-8")
                process = await asyncio.create_subprocess_exec(
                    sys.executable,
                    "-m",
                    "deep_research_agent.host",
                    "--root",
                    str(root),
                    "upload",
                    "s",
                    str(local),
                    "--expected",
                    c.ref,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                output, errors = await asyncio.wait_for(process.communicate(), 10)
                self.assertEqual(0, process.returncode, errors.decode(errors="replace"))
                self.assertIn("source", json.loads(output))
                self.assertTrue(host.store.control("s").paused)
                host.store.command("s", "resume", c.ref, "resume")
                rejected = await send(root, request)
                self.assertEqual("ValueError", rejected["error"])
            finally:
                await send(root, {"action": "shutdown"})
                await task
