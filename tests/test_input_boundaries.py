"""Offline regression tests for decoded HTTP bodies and local import capacity."""

import base64
import gzip
import os
import tempfile
import unittest
import zlib
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx

from epivra import direct_reader, materials
from epivra.adapters import JsonAPI, decoded_response
from epivra.domain import Call
from epivra.harness import Harness, Tool
from epivra.host import Host
from epivra.storage import Store
from epivra.workspace import Workspace


class WireStream(httpx.AsyncByteStream):
    def __init__(self, content):
        self.content = content
        self.closed = False

    async def __aiter__(self):
        for offset in range(0, len(self.content), 7):
            yield self.content[offset : offset + 7]

    async def aclose(self):
        self.closed = True


COMPRESS = {"identity": lambda raw: raw, "gzip": gzip.compress, "deflate": zlib.compress}


class HTTPInputTests(unittest.IsolatedAsyncioTestCase):
    async def test_plain_and_markdown_encodings_do_not_trigger_reader_fallback(self):
        """Run the actual reader, decoder and Harness fallback decision."""
        client_type = httpx.AsyncClient
        url = "https://example.com/source"
        target = httpx.URL(url)
        address = target.copy_with(host="93.184.216.34")
        encodings = {
            "utf-8": "中文 original source café 42\n",
            "gb18030": "中文 original source 42\n",
            "iso-8859-1": "Résumé café source 42\n",
            "utf-16": "中文 original source café 42\n",
        }
        with tempfile.TemporaryDirectory() as folder, closing(Store(Path(folder) / "research.db")) as store:
            reader = direct_reader.DirectReader()
            tool = Tool(
                "Read a source", {}, reader.extract, resource="http",
                observe=lambda raw, acquisition: reader.decode_extract(raw),
            )
            model = SimpleNamespace(context_tokens=4096, max_tokens=1024)
            harness = Harness(store, model, {"fetch_web": tool})
            for mime in ("text/plain", "text/markdown"):
                for compression, compress in COMPRESS.items():
                    for charset, text in encodings.items():
                        with self.subTest(mime=mime, compression=compression, charset=charset):
                            wire = compress(text.encode(charset))
                            stream = WireStream(wire)
                            requests, fallback_calls = [], []

                            def reply(request):
                                requests.append(request)
                                return httpx.Response(200, headers={
                                    "Content-Type": f"{mime}; charset={charset}",
                                    "Content-Encoding": compression,
                                    "Content-Length": str(len(wire)),
                                }, stream=stream)

                            def client(**kwargs):
                                return client_type(transport=httpx.MockTransport(reply), **kwargs)

                            async def external(study, work, epoch, step, index, call):
                                if call.arguments.get("provider") == "jina":
                                    fallback_calls.append(call)
                                    return {"value": {"requested_url": url, "error": "unexpected_fallback"}}
                                return {"value": await reader.extract(call.arguments)}

                            with (
                                patch.object(direct_reader.httpx, "AsyncClient", side_effect=client),
                                patch.object(direct_reader, "public_address", AsyncMock(return_value=(address, target))),
                                patch.object(harness, "_external", side_effect=external),
                            ):
                                result, _ = await harness._acquired(
                                    "study", "work", 0, "step", 0, Call("fetch_web", {"url": url})
                                )
                            self.assertEqual(fallback_calls, [])
                            self.assertEqual(result["failures"], [])
                            self.assertEqual(result["sources"][0]["text"], text.strip())
                            self.assertEqual(result["sources"][0]["requested_url"], url)
                            self.assertEqual(len(requests), 1)
                            self.assertEqual(requests[0].headers["host"], target.host)
                            self.assertTrue(stream.closed)

    async def test_compressed_html_still_uses_html_parser(self):
        client_type = httpx.AsyncClient
        url = "https://example.com/source"
        target = httpx.URL(url)
        wire = gzip.compress('<html><title>标题</title><main><h1>正文</h1></main></html>'.encode())
        stream = WireStream(wire)
        transport = httpx.MockTransport(lambda request: httpx.Response(200, headers={
            "content-type": "text/html; charset=utf-8", "content-encoding": "gzip",
        }, stream=stream))
        with (
            patch.object(direct_reader.httpx, "AsyncClient", side_effect=lambda **kw: client_type(transport=transport, **kw)),
            patch.object(direct_reader, "public_address", AsyncMock(return_value=(target, target))),
        ):
            result = await direct_reader.DirectReader().extract({"url": url})
        self.assertEqual(result["text"], "# 正文")
        self.assertEqual(result["title"], "标题")
        self.assertTrue(stream.closed)

    async def test_json_api_shares_decoded_response_boundary(self):
        for compression, compress in COMPRESS.items():
            with self.subTest(compression=compression):
                stream = WireStream(compress('{"text":"中文 café"}'.encode()))
                transport = httpx.MockTransport(lambda request: httpx.Response(200, headers={
                    "content-type": "application/json; charset=utf-8",
                    "content-encoding": compression,
                    "x-rate-limit-limit": "50",
                }, stream=stream))
                async with httpx.AsyncClient(transport=transport) as client:
                    api = JsonAPI("https://example.com", "", client)
                    result = await api.request("GET", "/source")
                self.assertEqual(result["data"], {"text": "中文 café"})
                self.assertEqual(result["rate_limits"], {"x-rate-limit-limit": "50"})
                self.assertTrue(stream.closed)

    def test_decoded_response_preserves_charset_status_and_safe_headers(self):
        raw = "café".encode("iso-8859-1")
        original = httpx.Response(429, headers={
            "content-type": "text/plain; charset=iso-8859-1",
            "content-encoding": "gzip", "content-length": "999",
            "retry-after": "10",
        })
        decoded = decoded_response(original, raw)
        self.assertEqual(decoded.status_code, 429)
        self.assertEqual(decoded.text, "café")
        self.assertNotIn("content-encoding", decoded.headers)
        self.assertEqual(decoded.headers["content-length"], str(len(raw)))
        self.assertEqual(decoded.headers["retry-after"], "10")
        self.assertEqual(original.headers["content-encoding"], "gzip")


class FileInputTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "material.txt"

    def test_empty_and_exact_limit_files_are_accepted(self):
        for raw in (b"", b"x" * 16):
            with self.subTest(length=len(raw)), patch.object(materials, "MAX_INPUT_BYTES", 16):
                self.path.write_bytes(raw)
                self.assertEqual(materials.read_file(self.path), raw)

    def test_sparse_oversize_file_is_rejected_before_opening_read_stream(self):
        with self.path.open("wb") as stream:
            stream.truncate(materials.MAX_INPUT_BYTES + 1)
        with patch.object(materials.os, "fdopen") as fdopen:
            with self.assertRaisesRegex(ValueError, "material exceeds input byte limit"):
                materials.read_file(self.path)
        fdopen.assert_not_called()

    def test_growth_after_fstat_is_bounded_to_limit_plus_one(self):
        self.path.write_bytes(b"small")
        fstat, fdopen = os.fstat, os.fdopen
        reads = []
        stat_calls = 0

        def grow_after_stat(descriptor):
            nonlocal stat_calls
            before = fstat(descriptor)
            stat_calls += 1
            if stat_calls == 1:
                with self.path.open("ab") as stream:
                    stream.write(b"x" * 1024)
            return before

        def tracked_open(*args, **kwargs):
            stream = fdopen(*args, **kwargs)
            original_read = stream.read

            def read(size=-1):
                reads.append(size)
                return original_read(size)

            stream.read = read
            return stream

        with (
            patch.object(materials, "MAX_INPUT_BYTES", 16),
            patch.object(materials.os, "fstat", side_effect=grow_after_stat),
            patch.object(materials.os, "fdopen", side_effect=tracked_open),
        ):
            with self.assertRaisesRegex(ValueError, "material exceeds input byte limit"):
                materials.read_file(self.path)
        self.assertEqual(reads, [17])

    def test_growth_after_read_is_rejected_by_final_handle_stat(self):
        self.path.write_bytes(b"small")
        fdopen = os.fdopen

        def growing_open(*args, **kwargs):
            stream = fdopen(*args, **kwargs)
            original_read = stream.read

            def read(size=-1):
                raw = original_read(size)
                with self.path.open("ab") as target:
                    target.write(b"x" * 32)
                return raw

            stream.read = read
            return stream

        with (
            patch.object(materials, "MAX_INPUT_BYTES", 16),
            patch.object(materials.os, "fdopen", side_effect=growing_open),
        ):
            with self.assertRaisesRegex(ValueError, "material exceeds input byte limit"):
                materials.read_file(self.path)

    def test_changed_file_under_limit_is_not_imported_as_a_mixed_snapshot(self):
        self.path.write_bytes(b"small")
        fstat = os.fstat
        calls = 0

        def grow_after_stat(descriptor):
            nonlocal calls
            before = fstat(descriptor)
            calls += 1
            if calls == 1:
                with self.path.open("ab") as stream:
                    stream.write(b"x")
            return before

        with patch.object(materials.os, "fstat", side_effect=grow_after_stat):
            with self.assertRaisesRegex(ValueError, "source changed while reading"):
                materials.read_file(self.path)

    def test_device_is_rejected_without_reading(self):
        with patch.object(materials.os, "fdopen") as fdopen:
            with self.assertRaisesRegex(ValueError, "selected path is not a file"):
                materials.read_file(Path(os.devnull))
        fdopen.assert_not_called()

    @unittest.skipUnless(hasattr(os, "mkfifo"), "POSIX FIFO support required")
    def test_fifo_is_rejected_without_waiting_for_a_writer(self):
        os.mkfifo(self.path)
        with self.assertRaisesRegex(ValueError, "selected path is not a file"):
            materials.read_file(self.path)


class HostImportTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.host = Host(self.root)
        self.addCleanup(self.host.store.close)
        control = self.host.store.create("study", "Test imports", {})
        self.request = {"token": self.host.token, "study": "study", "expected": control.ref}

    async def test_import_dispatch_rejects_sparse_file_before_read_or_parser(self):
        path = self.root / "oversized.txt"
        with path.open("wb") as stream:
            stream.truncate(materials.MAX_INPUT_BYTES + 1)
        with (
            patch.object(Path, "read_bytes", side_effect=AssertionError("unbounded read")),
            patch.object(materials.os, "fdopen") as fdopen,
            patch.object(Workspace, "upload_async", new_callable=AsyncMock) as upload,
        ):
            with self.assertRaisesRegex(ValueError, "material exceeds input byte limit"):
                await self.host.dispatch({**self.request, "action": "import_file", "path": str(path)})
        fdopen.assert_not_called()
        upload.assert_not_awaited()

    async def test_import_dispatch_preserves_filename_bytes_and_parser_result(self):
        path = self.root / "原文.md"
        raw = "# 中文材料\n\nRésumé café\n".encode()
        path.write_bytes(raw)
        with patch.object(Path, "read_bytes", side_effect=AssertionError("unbounded read")):
            result = await self.host.dispatch({**self.request, "action": "import_file", "path": str(path)})
        source = self.host.store.get("study", result["source"])
        self.assertEqual(source.body["origin"], path.name)
        self.assertEqual(source.body["text"], raw.decode())
        self.assertEqual(result["characters"], len(raw.decode()))
        self.assertEqual(Workspace(self.host.store).original("study", source.ref), raw)

    async def test_existing_base64_upload_api_does_not_read_local_file(self):
        raw = "上传材料".encode()
        with patch("epivra.host.read_file", side_effect=AssertionError("unexpected local read")):
            result = await self.host.dispatch({
                **self.request, "action": "upload", "name": "upload.txt",
                "data": base64.b64encode(raw).decode(),
            })
        self.assertEqual(self.host.store.get("study", result["source"]).body["text"], raw.decode())


if __name__ == "__main__":
    unittest.main()
