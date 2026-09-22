"""Local worker artifacts commit only while their admission remains current."""
import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from epivra.domain import Call, Conflict, NotAllowed, Reply
from epivra.harness import Harness
from epivra.materials import parse
from epivra.storage import Store
from epivra.workspace import Workspace


class Model:
    context_tokens = 49024
    max_tokens = 1024
    identity = "local-fence-fixture"

    def __init__(self, call):
        self.call = call

    async def complete(self, request):
        return Reply("", (self.call,)).to_json()


class LocalCommitFenceTests(unittest.IsolatedAsyncioTestCase):
    async def test_late_worker_discovery_and_parse_cannot_commit(self):
        for tool in ("discover_local", "snapshot_local"):
            for interruption in ("cancel_work", "pause", "steer"):
                with self.subTest(tool=tool, interruption=interruption):
                    with tempfile.TemporaryDirectory() as folder:
                        root = Path(folder)
                        (root / "input.txt").write_text("Original evidence", encoding="utf-8")
                        store = Store(root / "state.db")
                        task = None
                        release = asyncio.Event()
                        try:
                            c = store.create("s", "Research", {"local_roots": [str(root)]})
                            plan = store.put("s", "plan", {"text": "Read"}, (c.direction,))
                            c = store.command("s", "approve", c.ref, "approve", {"plan": plan.ref})
                            lead = store.work("s", c.ref, "lead", "Coordinate")
                            child = store.work("s", c.ref, "investigator", "Read local sources", owner=lead.ref)
                            workspace = Workspace(store)
                            catalog = workspace.discover("s", str(root)) if tool == "snapshot_local" else None
                            args = {"root": str(root)} if catalog is None else {"catalog": catalog.ref, "path": "input.txt"}
                            harness = Harness(store, Model(Call(tool, args)))
                            entered = asyncio.Event()
                            async def delayed_parse(study, name, raw):
                                entered.set()
                                await release.wait()
                                return parse(name, raw)
                            async def delayed_scan(function, *args):
                                result = function(*args)
                                entered.set()
                                await release.wait()
                                return result
                            method = "_parse" if tool == "snapshot_local" else "_io"
                            delayed = delayed_parse if tool == "snapshot_local" else delayed_scan
                            before = {kind: len(store.list("s", kind)) for kind in ("catalog", "source", "material_bytes")}
                            with patch.object(harness.workspace, method, side_effect=delayed):
                                task = asyncio.create_task(harness.step("s", child.ref))
                                await asyncio.wait_for(entered.wait(), 5)
                                if interruption == "cancel_work":
                                    store.cancel_work("s", lead.ref, child.ref, c.epoch, "No longer needed")
                                else:
                                    store.command("s", "interrupt", c.ref, interruption,
                                                  {"request": "New scope"} if interruption == "steer" else {})
                                release.set()
                                with self.assertRaises((Conflict, NotAllowed)):
                                    await task
                            self.assertEqual(before, {kind: len(store.list("s", kind)) for kind in before})
                            self.assertEqual([], store.list("s", "observation"))
                        finally:
                            release.set()
                            if task is not None and not task.done():
                                await asyncio.gather(task, return_exceptions=True)
                            store.close()

    async def test_user_import_keeps_its_independent_authority(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "input.txt").write_text("User evidence", encoding="utf-8")
            store = Store(root / "state.db")
            try:
                store.create("s", "Research", {"local_roots": [str(root)]})
                workspace = Workspace(store)
                catalog = await workspace.discover_async("s", str(root))
                source = await workspace.snapshot_async("s", catalog.ref, "input.txt")
                self.assertEqual("User evidence", source.body["text"])
                self.assertEqual(1, len(store.list("s", "material_bytes")))
            finally:
                store.close()
