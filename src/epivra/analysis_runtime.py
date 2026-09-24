"""Local analysis lifecycle: admission, results, cancellation and reconciliation."""

import asyncio

from .analysis import DockerSandbox
from .domain import Conflict, NotAllowed
from .native_analysis import NativeSandbox
from .scheduling import Scheduler
from .storage import Store
from .workspace import Workspace


class AnalysisRuntime:
    def __init__(self, store: Store, scheduler=None, sandbox=None, native=None):
        self.store = store
        self.workspace = Workspace(store)
        self.scheduler = scheduler or Scheduler()
        self.sandbox = sandbox or DockerSandbox()
        self.native = native or NativeSandbox(store.path.parent)

    async def run(self, study, work, epoch, step, index, args):
        self.store.require_work(study, work.ref, epoch)
        config = (
            self.store.get(study, work.body["direction"]).body["policy"].get("analysis")
        )
        if not config or not self.store.control(study).approved:
            raise NotAllowed("analysis is not enabled for this work")
        sandbox = self.native if config.get("backend") == "native" else self.sandbox
        generation = self.store.work_generation(study, work.ref)
        inputs = {item["name"]: item["ref"] for item in args["inputs"]}
        if len(inputs) != len(args["inputs"]):
            raise ValueError("duplicate input names")
        previous = [
            a
            for a in self.store.list(study, "analysis_job")
            if a.body["step"] == step and a.body["index"] == index
        ]
        fresh = not previous
        files = (
            self.workspace.analysis_inputs(
                study, inputs, config["input_mb"] * 1024 * 1024
            )
            if fresh
            else None
        )
        job = (
            previous[0]
            if previous
            else self.store.put(
                study,
                "analysis_job",
                {
                    **args,
                    "inputs": inputs,
                    "step": step,
                    "index": index,
                    "image": config["image"],
                    "backend": config.get("backend", "docker"),
                },
                (work.ref, step, *inputs.values()),
            )
        )
        existing = [
            a
            for a in self.store.list(study, "analysis_result")
            if a.body["job"] == job.ref
        ]
        if existing:
            return existing[0].body
        if files is None:
            files = self.workspace.analysis_inputs(
                study, inputs, config["input_mb"] * 1024 * 1024
            )
        folder = self.workspace.stage_analysis(job, files)

        def guard():
            self.store.require_work(study, work.ref, epoch)
            if self.store.work_interrupted(study, work.ref) or generation != self.store.work_generation(study, work.ref):
                raise NotAllowed("analysis interrupted by its owner")

        try:
            async with self.scheduler.slot("analysis", guard):
                result = await sandbox.run(job.ref, folder, config, fresh, guard)
            saved = self.workspace.save_analysis(
                study, job, result, config["output_mb"] * 1024 * 1024
            )
        except (asyncio.CancelledError, Conflict, NotAllowed):
            # Cancellation is a known local outcome; preserve it before reaping.
            self.workspace.save_analysis(
                study,
                job,
                {
                    "status": "cancelled",
                    "log": "Analysis interrupted by user control",
                    "files": [],
                },
                config["output_mb"] * 1024 * 1024,
            )
            await asyncio.shield(self.cleanup(study, job))
            raise
        except (ValueError, KeyError, TypeError, OSError, TimeoutError) as exc:
            try:
                await sandbox.cleanup(job.ref)
            except (ValueError, OSError, TimeoutError) as cleanup_error:
                raise RuntimeError(
                    "Local analysis requires sandbox recovery; execution retained for reconciliation"
                ) from cleanup_error
            saved = self.workspace.save_analysis(
                study,
                job,
                {
                    "status": "failed",
                    "log": f"Analysis execution/collection failed: {exc}",
                    "files": [],
                },
                config["output_mb"] * 1024 * 1024,
            )
        try:
            await self.cleanup(study, job)
        except (ValueError, OSError, TimeoutError) as exc:
            guard()
            return {**saved.body, "cleanup_pending": str(exc)}
        guard()
        return saved.body

    async def cleanup(self, study, job):
        sandbox = self.native if job.body.get("backend") == "native" else self.sandbox
        await sandbox.cleanup(job.ref)
        self.workspace.clear_analysis_staging(job)
        self.store.put(study, "analysis_cleanup", {"job": job.ref}, (job.ref,))

    async def reconcile(self, study):
        c = self.store.control(study)
        cleaned = {a.body["job"] for a in self.store.list(study, "analysis_cleanup")}
        results = {a.body["job"] for a in self.store.list(study, "analysis_result")}
        for job in self.store.list(study, "analysis_job"):
            if job.ref in cleaned:
                continue
            sandbox = self.native if job.body.get("backend") == "native" else self.sandbox
            work = next(
                a
                for ref in job.parents
                if (a := self.store.get(study, ref)).kind == "work"
            )
            config = self.store.get(study, work.body["direction"]).body["policy"][
                "analysis"
            ]
            if job.ref in results:
                await self.cleanup(study, job)
            elif c.paused or c.cancelled or work.body["direction"] != c.direction:
                await sandbox.cleanup(job.ref)
                self.workspace.save_analysis(
                    study,
                    job,
                    {
                        "status": "cancelled",
                        "log": "Inactive local job recovered after interruption",
                        "files": [],
                    },
                    config["output_mb"] * 1024 * 1024,
                )
                self.workspace.clear_analysis_staging(job)
                self.store.put(study, "analysis_cleanup", {"job": job.ref}, (job.ref,))
            elif job.body.get("backend") == "native":
                # Host-owned native workers die on host loss; a lost local result
                # is recorded explicitly rather than rerunning arbitrary code.
                await sandbox.cleanup(job.ref)
                self.workspace.save_analysis(study, job, {
                    "status": "interrupted", "log": "Native execution interrupted by host restart; no automatic rerun.",
                    "files": []}, config["output_mb"] * 1024 * 1024)
                await self.cleanup(study, job)
            else:
                info = await sandbox.inspect("dr-analysis-" + job.ref)
                if info and info["State"]["Status"] == "exited":
                    try:
                        result = await sandbox.run(
                            job.ref,
                            self.store.path.parent / "analysis" / job.ref,
                            config,
                            False,
                            lambda: None,
                        )
                        self.workspace.save_analysis(
                            study, job, result, config["output_mb"] * 1024 * 1024
                        )
                    except (
                        ValueError,
                        KeyError,
                        TypeError,
                        OSError,
                        TimeoutError,
                    ) as exc:
                        await sandbox.cleanup(job.ref)
                        self.workspace.save_analysis(
                            study,
                            job,
                            {
                                "status": "failed",
                                "log": f"Local result recovery failed: {exc}",
                                "files": [],
                            },
                            config["output_mb"] * 1024 * 1024,
                        )
                    await self.cleanup(study, job)
