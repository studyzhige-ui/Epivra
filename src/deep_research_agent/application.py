"""Small local service: control is independent of model I/O."""

from __future__ import annotations

import asyncio
from typing import Any

from .domain import Conflict
from .harness import Harness
from .storage import Store


class ResearchService:
    def __init__(self, store: Store, harness: Harness, concurrency: int = 4):
        if concurrency < 1:
            raise ValueError("concurrency must be positive")
        self.store, self.harness = store, harness
        self.concurrency = concurrency
        self.tasks: dict[str, asyncio.Task] = {}
        self.errors: dict[str, str] = {}
        self.work_errors: dict[str, str] = {}

    def start(self, study: str) -> None:
        running = self.tasks.get(study)
        if running and not running.done():
            return
        self.errors.pop(study, None)
        for work in self.store.list(study, "work"):
            self.work_errors.pop(work.ref, None)
        self.tasks[study] = asyncio.create_task(self.run(study))

    async def run(self, study: str) -> None:
        while True:
            control_ref = self.store.control(study).ref
            try:
                await self._drive(study)
                return
            except Conflict:
                c = self.store.control(study)
                if c.paused or c.cancelled:
                    return
                if c.ref == control_ref:
                    self.errors[study] = "Conflict"
                    return
                await asyncio.sleep(0)

    async def _drive(self, study: str) -> None:
        try:
            while True:
                c = self.store.control(study)
                if c.paused or c.cancelled:
                    return
                publications = [
                    a
                    for a in self.store.list(study, "publication")
                    if c.direction in a.parents
                ]
                if publications:
                    return
                if not c.approved:
                    work = self.store.work(
                        study,
                        c.ref,
                        "planner",
                        "提出初始研究策略并提交审批。",
                    )
                    if self.harness.finished(study, work.ref):
                        return
                else:
                    inputs = (c.plan,) if c.plan else ()
                    root = self.store.work(
                        study,
                        c.ref,
                        "researcher",
                        "依据当前方向自主研究并交付经过核查的报告。",
                        inputs,
                    )
                    children = [
                        w
                        for w in self.store.list(study, "work")
                        if w.body["owner"] == root.ref
                        and w.body["role"] == "investigator"
                    ]
                    pending = [
                        w
                        for w in children
                        if not self.harness.finished(study, w.ref)
                        and w.ref not in self.work_errors
                    ]
                    if pending:
                        pending.sort(
                            key=lambda w: len(self.harness._steps(study, "step", w.ref))
                        )
                        outcomes = await asyncio.gather(
                            *(
                                self._investigate(study, w.ref)
                                for w in pending[: self.concurrency]
                            ),
                            return_exceptions=True,
                        )
                        for outcome in outcomes:
                            if isinstance(outcome, BaseException):
                                raise outcome
                        continue
                    for child in children:
                        for result in self.harness._steps(
                            study, "work_result", child.ref
                        ):
                            self.store.observation(
                                study,
                                root.ref,
                                c.epoch,
                                {
                                    "investigation_result": result.ref,
                                    "work": child.ref,
                                    "result": result.body,
                                },
                                (result.ref,),
                            )
                        if child.ref in self.work_errors:
                            self.store.observation(
                                study,
                                root.ref,
                                c.epoch,
                                {
                                    "work": child.ref,
                                    "blocked": self.work_errors[child.ref],
                                    "instruction": "Do not resubmit unknown paid work; assess dependency.",
                                },
                                (child.ref,),
                            )
                    # A report proposal requests an independent work context;
                    # the scheduler does not choose when research should write.
                    reports = [
                        a
                        for a in self.store.list(study, "report")
                        if root.ref in a.parents and c.direction in a.parents
                    ]
                    work = root
                    for report in reports:
                        reviews = [
                            a
                            for a in self.store.list(study, "review")
                            if report.ref in a.parents
                        ]
                        if reviews:
                            for review in reviews:
                                self.store.observation(
                                    study,
                                    root.ref,
                                    c.epoch,
                                    {
                                        "review_available": review.ref,
                                        "report": report.ref,
                                        "decision": review.body,
                                    },
                                    (review.ref,),
                                )
                            continue
                        work = self.store.work(
                            study,
                            c.ref,
                            "reviewer",
                            "核查指定报告及原始证据，提交具体核查结论。",
                            (report.ref,),
                            root.ref,
                        )
                        break
                await self.harness.step(study, work.ref)
                # Let control messages run even when every operation was replayed.
                await asyncio.sleep(0)
        except Conflict:
            raise
        except Exception as exc:
            # Never include provider request bodies or credential-bearing errors.
            self.errors[study] = type(exc).__name__

    def status(self, study: str) -> dict[str, Any]:
        c = self.store.control(study)
        return {
            "control": c.ref,
            "epoch": c.epoch,
            "direction": c.direction,
            "approved": c.approved,
            "paused": c.paused,
            "cancelled": c.cancelled,
            "plans": [
                {"ref": a.ref, "body": a.body} for a in self.store.list(study, "plan")
            ],
            "reports": [
                {"ref": a.ref, "body": a.body}
                for a in self.store.list(study, "publication")
            ],
            "running": bool(study in self.tasks and not self.tasks[study].done()),
            "error": self.errors.get(study),
            "unsettled_operations": self.store.unsettled(study),
            "work_errors": {
                w.ref: self.work_errors[w.ref]
                for w in self.store.list(study, "work")
                if w.ref in self.work_errors
            },
        }

    async def _investigate(self, study: str, work: str) -> None:
        try:
            await self.harness.step(study, work)
        except Conflict:
            raise
        except Exception as exc:
            self.work_errors[work] = type(exc).__name__

    async def close(self) -> None:
        tasks = list(self.tasks.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
