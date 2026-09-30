"""Named stream enumeration closes handles and never treats errors as clean."""

import ctypes
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from epivra.native_analysis import measured
from epivra.sandbox_windows import StreamData, reject_named_streams


class StreamEnumerationTests(unittest.TestCase):
    def enumerate(self, names, first_error=38, next_error=38):
        started = bool(names)
        names = iter(names)
        closed = []
        error = [first_error]

        def fill(pointer):
            name = next(names, None)
            if name is None:
                return False
            ctypes.cast(pointer, ctypes.POINTER(StreamData)).contents.name = name
            return True

        def first(path, level, pointer, flags):
            return 42 if fill(pointer) else ctypes.c_void_p(-1).value

        def following(handle, pointer):
            error[0] = next_error
            return fill(pointer)

        functions = {"FindFirstStreamW": first, "FindNextStreamW": following,
                     "FindClose": lambda handle: closed.append(handle)}
        with (
            patch("epivra.sandbox_windows.api", side_effect=lambda dll, name, *args: functions[name]),
            patch.object(ctypes, "get_last_error", side_effect=lambda: error[0], create=True),
            patch.object(ctypes, "WinError", side_effect=lambda code: OSError(code, "test Windows failure"), create=True),
        ):
            try:
                reject_named_streams(Path("fixture"))
            finally:
                self.assertEqual(closed, [42] if started else [])

    def test_unnamed_file_and_empty_directory_are_allowed(self):
        self.enumerate(["::$DATA"])
        self.enumerate([])
        self.enumerate([], first_error=87)

    def test_file_and_directory_named_streams_are_rejected(self):
        for names in (["::$DATA", ":hidden:$DATA"], [":hidden:$DATA"]):
            with self.subTest(names=names), self.assertRaisesRegex(ValueError, "alternate data stream"):
                self.enumerate(names)

    def test_enumeration_failure_does_not_pass_as_no_streams(self):
        with self.assertRaises(OSError):
            self.enumerate([], first_error=5)
        with self.assertRaises(OSError):
            self.enumerate(["::$DATA"], next_error=5)


@unittest.skipUnless(os.name == "nt", "Requires actual Windows named streams")
class WindowsStreamTests(unittest.TestCase):
    def test_small_actual_file_and_directory_streams(self):
        for directory in (False, True):
            with self.subTest(directory=directory), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                target = root if directory else root / "file"
                if not directory:
                    target.write_bytes(b"")
                Path(str(target) + ":epivra-test").write_bytes(b"small probe")
                with self.assertRaisesRegex(ValueError, "alternate data stream"):
                    measured(root, 1024)
