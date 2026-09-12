import asyncio
import base64
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from deep_research_agent.analysis import DEFAULTS, DockerSandbox, filename
from deep_research_agent.domain import Call, Conflict, Reply
from deep_research_agent.harness import Harness
from deep_research_agent.storage import Store
from deep_research_agent.workspace import Workspace


class Model:
    identity = "analysis-fixture"
    call = None

    async def complete(self, request):
        return Reply("", (self.call,)).to_json()


class AnalysisTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.folder.name) / "state.db")
        c = self.store.create("s", "Analyze supplied data", {"analysis": DEFAULTS})
        plan = self.store.put(
            "s", "plan", {"text": "descriptive analysis"}, (c.direction,)
        )
        self.c = self.store.command(
            "s", "approve", c.ref, "approve", {"plan": plan.ref}
        )
        self.lead = self.store.work("s", self.c.ref, "lead", "Coordinate")
        self.work = self.store.work(
            "s", self.c.ref, "investigator", "Analyze", (), self.lead.ref
        )
        self.source = Workspace(self.store).upload("s", "input.csv", b"x\n1\n3\n")
        self.model = Model()
        self.sandbox = AsyncMock()
        self.sandbox.run.return_value = {
            "status": "succeeded",
            "exit_code": 0,
            "log": "mean=2",
            "files": [
                {"name": "summary.csv", "data": base64.b64encode(b"mean\n2\n").decode()}
            ],
        }
        self.harness = Harness(self.store, self.model, sandbox=self.sandbox)
        self.args = {
            "purpose": "Compute mean",
            "code": "print(2)",
            "inputs": [{"name": "data.csv", "ref": self.source.ref}],
        }

    async def asyncTearDown(self):
        self.store.close()
        self.folder.cleanup()

    async def execute(self):
        self.model.call = Call("run_analysis", self.args)
        await self.harness.step("s", self.work.ref)
        return self.store.list("s", "analysis_result")[-1]

    async def test_actual_tool_source_lineage_and_replay_without_running_again(self):
        result = await self.execute()
        job = self.store.get("s", result.body["job"])
        output = self.store.get("s", result.body["files"][0]["ref"])
        self.assertEqual("computed_not_reviewed", output.body["coverage"])
        self.assertIn(self.source.ref, output.parents)
        self.assertIn(job.ref, output.parents)
        self.assertEqual(b"mean\n2\n", self.harness.workspace.original("s", output.ref))
        replay = await self.harness._analysis(
            "s", self.work, self.c.epoch, job.body["step"], 0, self.args
        )
        self.assertEqual(result.body, replay)
        self.assertEqual(1, self.sandbox.run.await_count)
        self.assertFalse((self.store.path.parent / "analysis" / job.ref).exists())
        self.model.call = Call(
            "finish_work",
            {
                "text": "Mean is 2; descriptive only.",
                "refs": [self.source.ref, output.ref],
            },
        )
        await self.harness.step("s", self.work.ref)
        handoff = self.store.list("s", "work_result")[-1]
        writer = self.store.work(
            "s",
            self.c.ref,
            "writer",
            "Use the computed table",
            (handoff.ref,),
            self.lead.ref,
        )
        self.model.call = Call(
            "read_source", {"ref": output.ref, "offset": 0, "limit": 1000}
        )
        await self.harness.step("s", writer.ref)
        observation = self.store.list("s", "observation")[-1].body["result"]
        self.assertEqual("mean\n2\n", observation["text"])
        self.assertEqual(job.ref, observation["analysis"])

    async def test_pause_during_analysis_records_cancel_and_reaps(self):
        async def paused(job, folder, config, fresh, guard):
            self.store.command("s", "pause", self.c.ref, "pause")
            guard()

        self.sandbox.run.side_effect = paused
        with self.assertRaises(Conflict):
            await self.execute()
        self.assertEqual(
            "cancelled", self.store.list("s", "analysis_result")[0].body["status"]
        )
        self.sandbox.cleanup.assert_awaited_once()

    async def test_task_cancellation_reaps_and_preserves_local_outcome(self):
        self.sandbox.run.side_effect = asyncio.CancelledError()
        with self.assertRaises(asyncio.CancelledError):
            await self.execute()
        self.assertEqual(
            "cancelled", self.store.list("s", "analysis_result")[0].body["status"]
        )
        self.sandbox.cleanup.assert_awaited_once()

    async def test_inputs_and_outputs_cannot_escape_or_cross_studies(self):
        for name in ("../secret", "/absolute", "a\\b", "a:stream", "CON", "a/../../b"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                filename(name)
        self.store.create("other", "Other study", {})
        other = Workspace(self.store).upload("other", "private.txt", b"private")
        with self.assertRaises((ValueError, KeyError)):
            self.harness.workspace.analysis_inputs("s", {"x.txt": other.ref}, 100)
        self.assertNotIn(
            "run_analysis", self.harness._schema("lead", {"analysis": DEFAULTS})
        )
        self.assertNotIn("run_analysis", self.harness._schema("investigator", {}))
        self.sandbox.run.return_value["files"][0]["data"] = "invalid-base64"
        result = await self.harness._analysis(
            "s", self.work, self.c.epoch, self.source.ref, 0, self.args
        )
        self.assertEqual("failed", result["status"])
        self.assertEqual([], result["files"])
        self.assertTrue(self.store.list("s", "analysis_cleanup"))

    async def test_docker_failure_is_reported_and_cleaned(self):
        self.sandbox.run.side_effect = ValueError("Docker logs unavailable")
        result = await self.execute()
        self.assertEqual("failed", result.body["status"])
        self.assertTrue(self.store.list("s", "analysis_cleanup"))
        job = self.store.get("s", result.body["job"])
        self.assertFalse((self.store.path.parent / "analysis" / job.ref).exists())

    async def test_cleanup_failure_does_not_hide_committed_result(self):
        self.sandbox.cleanup.side_effect = ValueError("Docker disconnected")
        result = await self.execute()
        self.assertEqual("succeeded", result.body["status"])
        self.assertIn(
            "cleanup_pending", self.store.list("s", "observation")[-1].body["result"]
        )
        self.sandbox.cleanup.side_effect = None
        await self.harness.analysis.reconcile("s")
        self.assertEqual(1, len(self.store.list("s", "analysis_result")))
        self.assertTrue(self.store.list("s", "analysis_cleanup"))

    async def test_inactive_old_direction_reclaims_job_and_preserves_completed_result(
        self,
    ):
        result = await self.execute()
        job = self.store.get("s", result.body["job"])
        self.store.command(
            "s", "steer", self.c.ref, "steer", {"request": "New question"}
        )
        await self.harness.analysis.reconcile("s")
        self.assertEqual(result.ref, self.store.list("s", "analysis_result")[0].ref)
        self.assertEqual(job.ref, result.body["job"])

    async def test_input_path_collision_and_nonportable_output_are_explicit(self):
        with self.assertRaisesRegex(ValueError, "conflict"):
            self.harness.workspace.analysis_inputs(
                "s", {"data": self.source.ref, "data/file.csv": self.source.ref}, 1000
            )
        self.sandbox.run.return_value["files"].append(
            {"name": "../outside", "data": ""}
        )
        result = await self.execute()
        self.assertEqual(1, len(result.body["files"]))
        self.assertTrue(self.store.get("s", result.body["log"]).body["issues"])

    async def test_restart_reconciles_paused_and_committed_jobs(self):
        job = self.store.put(
            "s",
            "analysis_job",
            {
                **self.args,
                "inputs": {"data.csv": self.source.ref},
                "step": self.source.ref,
                "index": 0,
            },
            (self.work.ref,),
        )
        folder = self.harness.workspace.stage_analysis(job, {"data.csv": b"x\n1\n"})
        self.store.command("s", "pause", self.c.ref, "pause")
        await self.harness.analysis.reconcile("s")
        self.assertEqual(
            "cancelled", self.store.list("s", "analysis_result")[0].body["status"]
        )
        self.assertFalse(folder.exists())
        calls = self.sandbox.cleanup.await_count
        await self.harness.analysis.reconcile("s")
        self.assertEqual(calls, self.sandbox.cleanup.await_count)

    async def test_restart_reclaims_unfinished_job_from_old_direction(self):
        job = self.store.put(
            "s",
            "analysis_job",
            {
                **self.args,
                "inputs": {"data.csv": self.source.ref},
                "step": self.source.ref,
                "index": 0,
            },
            (self.work.ref, self.source.ref),
        )
        folder = self.harness.workspace.stage_analysis(job, {"data.csv": b"x\n1\n"})
        self.store.command(
            "s",
            "steer",
            self.c.ref,
            "steer",
            {"request": "A different research question"},
        )
        await self.harness.analysis.reconcile("s")
        self.assertEqual(
            "cancelled", self.store.list("s", "analysis_result")[0].body["status"]
        )
        self.assertFalse(folder.exists())
        self.sandbox.run.assert_not_called()

    async def test_missing_local_container_is_not_rerun(self):
        sandbox = DockerSandbox()
        with (
            patch.object(sandbox, "inspect", AsyncMock(return_value=None)),
            patch("deep_research_agent.analysis.docker", AsyncMock()) as command,
        ):
            result = await sandbox.run(
                "fixture", self.folder.name, DEFAULTS, False, lambda: None
            )
            self.assertEqual("interrupted", result["status"])
            command.assert_not_called()

    async def test_container_launch_contract_has_no_writable_host_mount(self):
        args = DockerSandbox().command("name", "job", self.folder.name, DEFAULTS)
        self.assertEqual("none", args[args.index("--network") + 1])
        self.assertIn("--read-only", args)
        self.assertIn("no-new-privileges", args)
        self.assertIn("--cap-drop", args)
        self.assertEqual("65534:65534", args[args.index("--user") + 1])
        self.assertEqual(1, args.count("--mount"))
        self.assertTrue(args[args.index("--mount") + 1].endswith(",readonly"))
        self.assertNotIn("--privileged", args)
        self.assertNotIn("--env", args)
