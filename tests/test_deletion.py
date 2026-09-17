"""Deletion uses temporary studies, never user data or paid providers."""

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from epivra.domain import Conflict
from epivra.host import Host
from epivra.workspace import Workspace


class DeletionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.host = Host(Path(self.temp.name))
        self.c = self.host.store.create("s", "Delete me", {})
        self.other = self.host.store.create("other", "Keep me", {})

    async def asyncTearDown(self):
        self.host.store.close()
        self.temp.cleanup()

    async def delete(self, **changes):
        return await self.host.dispatch(
            dict(
                action="delete",
                study="s",
                token=self.host.token,
                expected=changes.get("expected", self.c.ref),
                confirmed=changes.get("confirmed", True),
            )
        )

    async def test_confirmation_and_stale_control_do_not_cancel(self):
        with self.assertRaises(ValueError):
            await self.delete(confirmed=False)
        with self.assertRaises(Conflict):
            await self.delete(expected="stale")
        self.assertFalse(self.host.store.control("s").cancelled)

    async def test_deletes_all_owned_records_but_preserves_other_study_and_original(
        self,
    ):
        source = Path(self.temp.name) / "original.txt"
        source.write_text("original")
        work = self.host.store.work("s", self.c.ref, "lead", "Work")
        self.host.store.admit("s", work.ref, 0, "paid", {"tool": "example"})
        self.host.store.put("s", "source", {"text": "copy"})
        self.host.store.usage_records("s")
        self.assertEqual({"deleted": True}, await self.delete())
        for table in ("artifacts", "operations", "commands"):
            self.assertEqual(
                0,
                self.host.store.db.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE study=?", ("s",)
                ).fetchone()[0],
            )
        self.assertEqual(self.other, self.host.store.control("other"))
        self.assertEqual("original", source.read_text())
        self.assertNotIn("s", self.host.store._usage_cache)
        self.assertEqual({"deleted": True}, await self.delete())

    async def test_stops_inflight_import_and_agent_before_deleting(self):
        entered, stopped = asyncio.Event(), asyncio.Event()

        async def importing(*args):
            entered.set()
            try:
                await asyncio.Event().wait()
            finally:
                stopped.set()

        agent = Mock(close=AsyncMock())
        client = Mock(close=AsyncMock())
        # Register agent after import enters, to avoid its mocked running task.
        with patch("epivra.host.Workspace.upload_async", side_effect=importing):
            task = asyncio.create_task(
                self.host.dispatch(
                    dict(
                        token=self.host.token,
                        action="upload",
                        study="s",
                        expected=self.c.ref,
                        name="a.txt",
                        data="YQ==",
                    )
                )
            )
            await entered.wait()
            self.host.services["s"] = agent
            self.host.clients["s"] = [client]
            await self.delete()
            self.assertTrue(stopped.is_set())
            self.assertTrue(task.cancelled())
            agent.close.assert_awaited_once()
            client.close.assert_awaited_once()

    async def test_cleanup_failure_retains_intent_and_retry_after_restart(self):
        with patch(
            "epivra.host.AnalysisRuntime.reconcile",
            new=AsyncMock(side_effect=OSError("offline")),
        ):
            self.assertFalse((await self.delete())["deleted"])
        self.assertTrue(self.host.store.control("s").cancelled)
        self.assertEqual(1, self.host.store.count("s", "delete_request"))
        with self.assertRaises(ValueError):
            await self.host.dispatch(
                dict(token=self.host.token, action="control", study="s")
            )
        self.host.store.close()
        self.host = Host(Path(self.temp.name))
        server = asyncio.create_task(self.host.serve())
        try:
            for _ in range(100):
                if "s" in self.host.deletions:
                    break
                await asyncio.sleep(0.01)
            self.assertEqual({"deleted": True}, await self.host.deletions["s"])
        finally:
            self.host.stopping.set()
            await server
            self.host = Host(Path(self.temp.name))

    async def test_cancelled_connection_always_closes_socket(self):
        entered = asyncio.Event()

        async def dispatch(request):
            entered.set()
            await asyncio.Event().wait()

        reader = Mock(readline=AsyncMock(return_value=b"{}\n"))
        writer = Mock(wait_closed=AsyncMock())
        with patch.object(self.host, "dispatch", side_effect=dispatch):
            task = asyncio.create_task(self.host.connection(reader, writer))
            await entered.wait()
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        writer.close.assert_called_once()

    async def test_analysis_container_cleanup_precedes_record_erasure(self):
        c = self.host.store.create(
            "analysis", "Analysis", {"analysis": {"output_mb": 1}}
        )
        work = self.host.store.work("analysis", c.ref, "lead", "Fixture")
        job = self.host.store.put(
            "analysis",
            "analysis_job",
            {"code": "print(1)", "inputs": {}, "purpose": "fixture"},
            (work.ref,),
        )
        folder = Workspace(self.host.store).stage_analysis(job, {})
        with patch("epivra.analysis.DockerSandbox.cleanup", new=AsyncMock()) as cleanup:
            result = await self.host.dispatch(
                dict(
                    token=self.host.token,
                    action="delete",
                    study="analysis",
                    expected=c.ref,
                    confirmed=True,
                )
            )
        self.assertTrue(result["deleted"])
        cleanup.assert_awaited_once_with(job.ref)
        self.assertFalse(folder.exists())
        self.assertEqual(self.other, self.host.store.control("other"))

    async def test_disconnected_delete_request_does_not_cancel_cleanup(self):
        entered, release = asyncio.Event(), asyncio.Event()

        async def cleanup(study):
            entered.set()
            await release.wait()

        with patch("epivra.host.AnalysisRuntime.reconcile", side_effect=cleanup):
            request = asyncio.create_task(self.delete())
            await entered.wait()
            request.cancel()
            await asyncio.gather(request, return_exceptions=True)
            release.set()
            self.assertEqual({"deleted": True}, await self.host.deletions["s"])


if __name__ == "__main__":
    unittest.main()
