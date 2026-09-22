"""Small local service: control is independent of model I/O."""

from __future__ import annotations

import asyncio
from typing import Any

from .adapters import ProviderFailure, rate_limit_delay
from .domain import Conflict, RecoveryExhausted, RepeatedFailure
from .harness import Harness
from .storage import Store
from .usage import summarize


class ResearchService:
    def __init__(self, store: Store, harness: Harness, concurrency: int = 4):
        if concurrency < 1:
            raise ValueError("concurrency must be positive")
        self.store, self.harness = store, harness
        self.concurrency = concurrency
        self.tasks: dict[str, asyncio.Task] = {}
        self.errors: dict[str, str] = {}
        self.work_errors: dict[str, str] = {}
        self.repeated_failures: set[str] = set()

    def start(self, study: str) -> None:
        running = self.tasks.get(study)
        if running and not running.done():
            return
        self.errors.pop(study, None)
        for work in self.store.list(study, "work"):
            self.work_errors.pop(work.ref, None)
            self.repeated_failures.discard(work.ref)
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
        active: dict[str, asyncio.Task] = {}
        delivered = set()
        epoch = self.store.control(study).epoch
        try:
            while True:
                c = self.store.control(study)
                if c.epoch != epoch:
                    raise Conflict("control changed while steps were active")
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
                        "lead",
                        "提出供用户批准的研究路线：研究哪些问题、查阅哪些资料、怎样覆盖问题，不提出假设或预定答案。",
                    )
                    if self.harness.finished(study, work.ref):
                        return
                else:
                    inputs = (c.plan,) if c.plan else ()
                    owners = self.store.matching(study, "work", {
                        "direction": c.direction, "role": "lead", "stage": "research"
                    })
                    root = owners[0] if owners else self.store.work(
                        study,
                        c.ref,
                        "lead",
                        "依据当前方向自主研究并交付经过核查的报告。",
                        inputs,
                    )
                    children = [
                        w
                        for w in self.store.list(study, "work")
                        if w.body["owner"] == root.ref
                    ]
                    for child in children:
                        if self._discard_cancelled_error(study, child.ref):
                            continue
                        if child.ref in self.repeated_failures:
                            try:
                                self.harness._check_repeated(study, child.ref, c.epoch)
                            except RepeatedFailure:
                                pass
                            else:
                                self.repeated_failures.discard(child.ref)
                                self.work_errors.pop(child.ref, None)
                    pending = [
                        w
                        for w in children
                        if not self.harness.finished(study, w.ref)
                        and w.ref not in self.work_errors
                    ]
                    for child in children:
                        for result in self.harness._steps(
                            study, "work_result", child.ref
                        ):
                            if result.ref in delivered:
                                continue
                            self.store.observation(
                                study,
                                root.ref,
                                c.epoch,
                                {
                                    "work_result": result.ref,
                                    "work": child.ref,
                                    "role": child.body["role"],
                                    "result": result.body,
                                },
                                (result.ref,),
                            )
                            delivered.add(result.ref)
                        if child.ref in self.work_errors:
                            self.store.observation(
                                study,
                                root.ref,
                                c.epoch,
                                {
                                    "work": child.ref,
                                    "blocked": self.work_errors[child.ref],
                                    "instruction": (
                                        "This work repeated identical failures without progress. Change its inputs or method; do not recreate the same failing task."
                                        if child.ref in self.repeated_failures
                                        else "Do not resubmit unknown paid work; assess dependency."
                                    ),
                                },
                                (child.ref,),
                            )
                    waits = self.harness._steps(study, "work_wait", root.ref, limit=1)
                    waiting = bool(
                        waits and any(w.ref in waits[-1].body["refs"] for w in pending)
                    )
                    questions = self.store.clarifications(
                        study, owner=root.ref, open_only=True
                    )
                    if questions and (
                        not waits or any(q.seq > waits[-1].seq for q in questions)
                    ):
                        waiting = False
                    ready = [
                        w for w in pending if not self.harness.waiting(study, w.ref)
                    ] + ([] if waiting else [root])

                    def last_step(w):
                        return self.store.step_sequence(study, w.ref)

                    ready.sort(key=last_step)
                    for w in ready:
                        if len(active) >= self.concurrency:
                            break
                        if w.ref not in active:
                            active[w.ref] = asyncio.create_task(
                                self._run_child(study, w.ref)
                                if w.body["owner"]
                                else self.harness.step(study, w.ref)
                            )
                    if not active:
                        return
                    done, _ = await asyncio.wait(
                        active.values(),
                        timeout=0.25,
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                    outcomes = []
                    for ref, task in tuple(active.items()):
                        if task in done:
                            del active[ref]
                            outcomes.append(task.exception())
                    for outcome in outcomes:
                        if outcome is not None:
                            raise outcome
                    continue
                await self.harness.step(study, work.ref)
                # Let control messages run even when every operation was replayed.
                await asyncio.sleep(0)
        except asyncio.CancelledError:
            for task in active.values():
                task.cancel()
            raise
        except Conflict:
            raise
        except Exception as exc:
            # Never include provider request bodies or credential-bearing errors.
            self.errors[study] = (
                str(exc)
                if isinstance(exc, (ProviderFailure, RecoveryExhausted))
                else type(exc).__name__
            )

        finally:
            # Control changes stop admission; already sent responses settle before
            # another epoch starts. Host shutdown cancels and retains unknowns.
            if active:
                await asyncio.gather(*active.values(), return_exceptions=True)

    def status(self, study: str) -> dict[str, Any]:
        c = self.store.control(study)
        works = self.store.list(study, "work")
        for work in works:
            if work.ref in self.work_errors or work.ref in self.repeated_failures:
                self._discard_cancelled_error(study, work.ref)
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
            "provider_queue": self.harness.scheduler.snapshot(),
            "usage": summarize(self.store.usage_records(study)),
            "analyses": [a.body for a in self.store.list(study, "analysis_result")],
            "clarifications": [
                {
                    "ref": q.ref,
                    "work": q.body["work"],
                    "owner": q.body["owner"],
                    "text": q.body["text"],
                    "refs": q.body["refs"],
                }
                for q in self.store.clarifications(study, open_only=True)
            ],
            "work_errors": {
                w.ref: self.work_errors[w.ref]
                for w in works
                if w.ref in self.work_errors
            },
        }

    def _discard_cancelled_error(self, study: str, work: str) -> bool:
        if not any(result.body.get("status") == "cancelled" for result in
                   self.store.matching(study, "work_result", {"producer": work})):
            return False
        # Cancellation ends scheduling responsibility, not the paid-call history.
        self.work_errors.pop(work, None)
        self.repeated_failures.discard(work)
        return True

    async def _run_child(self, study: str, work: str) -> None:
        try:
            await self.harness.step(study, work)
        except Exception as exc:
            if self._discard_cancelled_error(study, work):
                return
            if isinstance(exc, Conflict):
                raise
            if isinstance(exc, RepeatedFailure):
                self.repeated_failures.add(work)
            self.work_errors[work] = (
                str(exc)
                if isinstance(exc, (ProviderFailure, RecoveryExhausted))
                else type(exc).__name__
            )

    async def close(self) -> None:
        tasks = list(self.tasks.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


def online_service(
    store: Store,
    study: str,
    keys: dict[str, str],
    model_name: str | None = None,
    scheduler=None,
) -> tuple[ResearchService, list]:
    """Compose explicit providers without giving adapters access to Agent control."""
    from .harness import STRING, Tool, object_schema
    from .models import create_model
    from .web_providers import connect
    from .workspace import Workspace

    policy = store.get(study, store.control(study).direction).body["policy"]
    if model_name:
        policy = {**policy, "model": model_name}
    workspace = Workspace(store)
    searches = policy.get(
        "search_providers", ["tavily"] if policy.get("network") else []
    )
    readers = policy.get(
        "reader_providers", ["tavily"] if policy.get("network") else []
    )
    providers = {
        name: connect(name, keys) for name in dict.fromkeys([*searches, *readers])
    }
    model, model_api = create_model(policy, keys)

    def select(args, names):
        name = args.get("provider", names[0] if names else None)
        if name not in names:
            raise ValueError("provider is not enabled for this research")
        return providers[name]

    def schema(field, names):
        value = object_schema({field: STRING})
        value["properties"]["provider"] = {"type": "string", "enum": names}
        if field == "url":
            value["properties"]["force_refresh"] = {"type": "boolean"}
        elif "tavily" in names:
            value["properties"].update(
                {
                    "include_domains": {"type": "array", "items": STRING},
                    "exclude_domains": {"type": "array", "items": STRING},
                    "start_date": STRING,
                    "end_date": STRING,
                }
            )
        return value

    async def search(args):
        return await select(args, searches).search(args)

    async def extract(args):
        return await select(args, readers).extract(args)

    def reuse(args):
        if args.get("force_refresh"):
            return None
        for source in reversed(store.list(study, "source")):
            if (
                args["url"]
                in (source.body.get("origin"), source.body.get("requested_url"))
                and source.body.get("text", "").strip()
            ):
                return {
                    "reused": {
                        "sources": [workspace.web_source_info(source)],
                        "failures": [],
                    }
                }
        return None

    def observe(raw, acquisition, names, reading=False):
        if "reused" in raw:
            return raw["reused"]
        provider = providers[raw["provider"]]
        try:
            decoded = (
                provider.decode_extract(raw) if reading else provider.decode_search(raw)
            )
        except (ProviderFailure, ValueError, KeyError, TypeError):
            return {
                "error": "source_provider_failed",
                "provider": provider.resource,
                "http_status": raw.get("http_status"),
                "alternatives": [name for name in names if name != provider.resource],
                "instruction": "Try an available alternative or revise the query/URL; no evidence was obtained.",
            }
        return (
            workspace.web_snapshot(study, decoded, acquisition) if reading else decoded
        )

    tools = {}
    for name, names, field, invoke, reading in (
        ("web_search", searches, "query", search, False),
        ("fetch_web", readers, "url", extract, True),
    ):
        if not names:
            continue
        tools[name] = Tool(
            (
                "Find source URLs across the public web. Snippets are leads, not original evidence. "
                "Choose queries and authoritative sites for the evidence needed; switch when results add no information. "
                "Only tavily supports include_domains/exclude_domains and YYYY-MM-DD start_date/end_date "
                "(publication or update date); other providers reject these fields. "
                if not reading
                else "Read a public URL into a citable source; saved text is reused unless force_refresh. "
            )
            + "Choose provider only when needed; default: "
            + names[0],
            schema(field, names),
            invoke,
            identity="web-selection-v1:"
            + ":".join(providers[n].identity for n in names),
            permission="network",
            roles=("lead", "investigator", "synthesizer", "writer", "reviewer"),
            observe=lambda raw, acq, choices=names, read=reading: observe(
                raw, acq, choices, read
            ),
            check=(lambda args: select(args, readers).validate_extract(args))
            if reading
            else (lambda args: select(args, searches).validate_search(args)),
            parallel_safe=True,
            resource=names[0],
            resource_map={n: n for n in names},
            cooldown=lambda raw: providers[raw["provider"]].retry_delay(raw, 0),
            retry_delay=lambda raw, attempt: (
                0
                if raw.get("credential_retry")
                and raw.get("http_status") in {401, 432, 433}
                else None
            ),
            reuse=reuse if reading else None,
        )
    public_clients = []
    if policy.get("network") and policy.get("public_sources"):
        from .public_sources import (
            ORIGINS,
            PublicSource,
            request,
            spacing,
        )
        from .public_sources import (
            TOOLS as PUBLIC_TOOLS,
        )
        from .scheduling import Scheduler

        scheduler = scheduler or Scheduler(history=store.admissions())
        public = {name: PublicSource(name) for name in ORIGINS}
        public_clients = [p.api for p in public.values()]
        for name in public:
            # Product pacing (not an assertion that every API has a 1 RPS limit).
            resource = "public:" + name
            scheduler.limits[resource] = {
                **scheduler.limits.get(resource, {}),
                "concurrency": 1,
            }
            scheduler.constrain(resource, 1.0)

        async def public_invoke(args, *, name, tool_name):
            raw = await public[name].invoke(tool_name, args)
            scheduler.constrain("public:" + name, spacing(raw))
            return raw

        def public_observe(raw, acq, *, name):
            try:
                decoded = public[name].decode(raw)
            except (ProviderFailure, ValueError, KeyError, TypeError, SyntaxError):
                return {
                    "error": "public_source_failed",
                    "provider": name,
                    "http_status": raw.get("http_status"),
                    "instruction": "No usable evidence obtained; revise query or use another permitted source.",
                }
            snapshots = workspace.web_snapshot(study, decoded, acq)
            return {
                **{
                    k: v for k, v in decoded.items() if k not in {"sources", "failures"}
                },
                **snapshots,
            }

        for tool_name, (name, description, parameters) in PUBLIC_TOOLS.items():
            tools[tool_name] = Tool(
                description,
                parameters,
                lambda args, n=name, t=tool_name: public_invoke(
                    args, name=n, tool_name=t
                ),
                identity="public-source-v1",
                roles=("lead", "investigator", "synthesizer", "writer", "reviewer"),
                permission="network",
                check=lambda args, t=tool_name: request(t, args),
                observe=lambda raw, acq, n=name: public_observe(raw, acq, name=n),
                resource="public:" + name,
                parallel_safe=True,
                cooldown=lambda raw: rate_limit_delay(raw, 0) or spacing(raw),
            )
    mcp_connections = []
    if policy.get("mcp"):
        from .mcp_tools import connect_tools

        mcp_tools, mcp_connections = connect_tools(store, study, policy)
        tools.update(mcp_tools)
    harness = Harness(store, model, tools, scheduler=scheduler)
    return ResearchService(store, harness), [
        model_api,
        *mcp_connections,
        *public_clients,
        *(p.api for p in providers.values()),
    ]
