import asyncio
import gzip
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from epivra.adapters import IncompleteStream, JsonAPI
from epivra.diagnostics import windows
from epivra.domain import Call, RecoveryExhausted, Reply, bounded_json, encode
from epivra.harness import BUILTINS, Harness, validate
from epivra.materials import parse_isolated
from epivra.review import public_inputs, units
from epivra.storage import Store
from epivra.web_providers import TavilyKeyPool
from epivra.workspace import Workspace


class Stream(httpx.AsyncByteStream):
    def __init__(self, blocks, delay=0):
        self.blocks, self.delay, self.closed = blocks, delay, False

    async def __aiter__(self):
        for block in self.blocks:
            await asyncio.sleep(self.delay)
            yield block

    async def aclose(self):
        self.closed = True


class NetworkBoundaries(unittest.IsolatedAsyncioTestCase):
    async def test_key_pool_preserves_configured_response_limits(self):
        stream = Stream([b"x" * 100])
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda _: httpx.Response(200, stream=stream))
        ) as client:
            api = TavilyKeyPool(
                "https://fixture", "fixture-key", client, max_response_bytes=10
            )
            with self.assertRaises(IncompleteStream):
                await api.post("/search", {})
        self.assertTrue(stream.closed)

    async def test_gzip_success_and_rejection_are_decoded_once(self):
        for status, body in [
            (200, {"ok": True}),
            (429, {"error": {"code": "insufficient_quota"}}),
        ]:
            async with httpx.AsyncClient(
                transport=httpx.MockTransport(
                    lambda _: httpx.Response(
                        status,
                        content=gzip.compress(json.dumps(body).encode()),
                        headers={"Content-Encoding": "gzip"},
                    )
                )
            ) as client:
                value = await JsonAPI("https://fixture", "", client).post("/", {})
                self.assertEqual(status, value["http_status"])
                self.assertEqual(
                    body, value["data"]
                ) if status == 200 else self.assertEqual("quota", value["error_kind"])

    async def test_slow_drip_total_deadline_closes_stream(self):
        stream = Stream([b" "] * 1000, 0.01)
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda _: httpx.Response(200, stream=stream))
        ) as client:
            api = JsonAPI("https://fixture", "", client, deadline=0.04)
            with self.assertRaises(TimeoutError):
                await api.post("/", {})
        self.assertTrue(stream.closed)

    async def test_response_and_single_sse_line_are_bounded(self):
        for streaming in (False, True):
            stream = Stream([b"data:" + b"x" * 100])
            async with httpx.AsyncClient(
                transport=httpx.MockTransport(
                    lambda _: httpx.Response(200, stream=stream)
                )
            ) as client:
                api = JsonAPI(
                    "https://fixture",
                    "",
                    client,
                    max_response_bytes=1000 if streaming else 10,
                    max_event_bytes=10,
                )
                with self.assertRaises(IncompleteStream):
                    await (api.chat_stream("/", {}) if streaming else api.post("/", {}))
            self.assertTrue(stream.closed)


class Model:
    identity = "audit-fixture"
    calls = ()

    async def complete(self, request):
        return Reply("", self.calls).to_json()


class RuntimeBoundaries(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = Path(self.folder.name) / "state.db"
        self.store = Store(self.path)
        c = self.store.create("s", "Find a supported answer", {})
        p = self.store.put("s", "plan", {"text": "Investigate"}, (c.direction,))
        self.c = self.store.command("s", "approve", c.ref, "approve", {"plan": p.ref})
        self.lead = self.store.work("s", self.c.ref, "lead", "Coordinate")
        self.model = Model()
        self.harness = Harness(self.store, self.model)

    async def asyncTearDown(self):
        self.store.close()
        self.folder.cleanup()

    async def execute(self, work, name, args):
        self.model.calls = (Call(name, args),)
        await self.harness.step("s", work.ref)
        return self.harness._steps("s", "observation", work.ref)[-1].body["result"]

    async def test_retry_exhaustion_survives_restart_and_explicit_resume_recovers(self):
        class Rejected(Model):
            count = 0
            retry_delay = staticmethod(
                lambda raw, n: 0 if raw.get("http_status") == 429 else None
            )

            async def complete(inner, request):
                inner.count += 1
                return (
                    {"http_status": 429}
                    if inner.count <= 6
                    else Reply("done", ()).to_json()
                )

        model = Rejected()
        with self.assertRaises(RecoveryExhausted):
            await Harness(self.store, model).step("s", self.lead.ref)
        self.assertEqual(6, model.count)
        self.store.close()
        self.store = Store(self.path)
        with self.assertRaises(RecoveryExhausted):
            await Harness(self.store, model).step("s", self.lead.ref)
        self.assertEqual(6, model.count)
        self.store.command("s", "resume", self.c.ref, "resume")
        await Harness(self.store, model).step("s", self.lead.ref)
        self.assertEqual(7, model.count)
        self.assertFalse(self.store.unsettled("s"))

    async def test_long_report_must_reach_next_model_request_before_acceptance(self):
        text = "数据及条件" * 10000 + "最后限制不可省略"
        report = self.store.put(
            "s", "report", {"text": text, "evidence": []}, (self.c.direction,)
        )
        reviewer = self.store.work(
            "s", self.c.ref, "reviewer", "Check all", (report.ref,), self.lead.ref
        )
        denied = await self.execute(
            reviewer, "submit_review", {"reason": "claimed read", "defects": []}
        )
        self.assertIn("has not reached", denied["error"])
        offset, seen = 0, []
        while offset is not None:
            result = await self.execute(
                reviewer, "read_report", {"offset": offset, "limit": 100000}
            )
            self.assertLess(len(encode(result)), 12000)
            seen.extend(x["text"] for x in result["units"])
            following = result["next_offset"]
            self.assertTrue(following is None or following > offset)
            offset = following
        self.assertEqual(text, "".join(seen))
        accepted = await self.execute(
            reviewer, "submit_review", {"reason": "checked original", "defects": []}
        )
        self.assertIn("ref", accepted)

    async def test_revision_reaches_writer_and_memory_after_reopen(self):
        inv = self.store.work(
            "s", self.c.ref, "investigator", "Investigate", (), self.lead.ref
        )
        old = await self.execute(
            inv, "finish_work", {"text": "Effect grew 20%", "refs": []}
        )
        writer = self.store.work(
            "s", self.c.ref, "writer", "Write", (old["ref"],), self.lead.ref
        )
        correction = self.store.work(
            "s",
            self.c.ref,
            "investigator",
            "Check metric",
            (old["ref"],),
            self.lead.ref,
        )
        new = await self.execute(
            correction,
            "finish_work",
            {
                "text": "Registration grew 20%; effects were not measured.",
                "refs": [],
                "supersedes": [old["ref"]],
                "findings": [
                    {
                        "statement": "Registration grew 20%",
                        "status": "observation",
                        "support": [],
                        "conditions": ["registration metric"],
                        "not_supported": ["effectiveness growth"],
                    }
                ],
            },
        )
        self.assertIn("ref", new)
        self.store.close()
        self.store = Store(self.path)
        self.harness = Harness(self.store, self.model)
        request = self.harness._request("s", writer)
        self.assertEqual(new["ref"], request["input_revisions"][old["ref"]])
        self.assertIn(new["ref"], self.harness._handoff_inputs("s", writer))
        self.assertIn("Registration grew", encode(request["context"]))
        synth_work = self.store.work(
            "s", self.c.ref, "synthesizer", "Synthesize", (old["ref"],), self.lead.ref
        )
        synthesis = self.store.put(
            "s",
            "work_result",
            {"text": "Derived recommendation", "producer": synth_work.ref},
            (synth_work.ref, self.c.direction, old["ref"]),
        )
        indirect = self.store.work(
            "s", self.c.ref, "writer", "Use synthesis", (synthesis.ref,), self.lead.ref
        )
        indirect_request = self.harness._request("s", indirect)
        self.assertEqual(new["ref"], indirect_request["input_revisions"][old["ref"]])
        self.assertIn(synthesis.ref, self.harness._handoff_inputs("s", indirect))
        self.assertIn(new["ref"], self.harness._handoff_inputs("s", indirect))
        remember = self.store.work(
            "s",
            self.c.ref,
            "investigator",
            "Continue remembered research",
            (),
            self.lead.ref,
        )
        await self.execute(
            remember,
            "save_memory",
            {"text": "Use derived recommendation", "refs": [synthesis.ref]},
        )
        self.assertEqual(
            new["ref"],
            self.harness._request("s", remember)["input_revisions"][old["ref"]],
        )

    async def test_late_premise_revision_requires_a_new_final_review(self):
        inv = self.store.work(
            "s", self.c.ref, "investigator", "Investigate", (), self.lead.ref
        )
        old = await self.execute(
            inv, "finish_work", {"text": "Tentative finding", "refs": []}
        )
        writer = self.store.work(
            "s", self.c.ref, "writer", "Write", (old["ref"],), self.lead.ref
        )
        result = await self.execute(
            writer, "draft_report", {"text": "Tentative answer", "evidence": []}
        )
        report = self.store.get("s", result["ref"])
        check = self.store.work(
            "s",
            self.c.ref,
            "reviewer",
            "Check manuscript form",
            (report.ref,),
            self.lead.ref,
            review_mode="check",
        )
        checked = await self.execute(
            check,
            "finish_work",
            {
                "text": "Manuscript contains tentative answer",
                "refs": [report.ref],
                "findings": [
                    {
                        "statement": "The manuscript states a tentative answer",
                        "status": "observation",
                        "support": [report.ref],
                    }
                ],
            },
        )
        self.assertIn("ref", checked)
        reviewer = self.store.work(
            "s", self.c.ref, "reviewer", "Review", (report.ref,), self.lead.ref
        )
        accepted = await self.execute(
            reviewer, "submit_review", {"reason": "Checked exact draft", "defects": []}
        )
        correction = self.store.work(
            "s",
            self.c.ref,
            "investigator",
            "Correct premise",
            (old["ref"],),
            self.lead.ref,
        )
        await self.execute(
            correction,
            "finish_work",
            {"text": "Premise changed", "refs": [], "supersedes": [old["ref"]]},
        )
        with self.assertRaisesRegex(ValueError, "premise changed after review"):
            self.store.publish(
                "s", self.lead.ref, self.c.epoch, report.ref, accepted["ref"]
            )

    def test_actual_wire_not_normalized_context_and_no_private_reasoning_in_projection(
        self,
    ):
        report = self.store.put("s", "report", {"text": "Original", "evidence": []})
        reviewer = self.store.work(
            "s", self.c.ref, "reviewer", "Check", (report.ref,), self.lead.ref
        )
        context = [{"ref": report.ref, "kind": "report", "body": report.body}]

        def record(label, payload, status=200):
            request = {"context": context, "wire": {"payload": payload}}
            step = self.store.put("s", "step", {"request": request}, (reviewer.ref,))
            self.store.admit(
                "s", reviewer.ref, self.c.epoch, label, request, request_step=step.ref
            )
            self.store.settle(label, {"http_status": status})

        record(
            "omitted",
            {
                "messages": [
                    {
                        "role": "assistant",
                        "content": encode({"context": context}),
                        "reasoning_content": "PRIVATE",
                    }
                ]
            },
        )
        with self.assertRaises(ValueError):
            self.store.require_report_delivery("s", reviewer.ref, report.ref)
        record(
            "rejected",
            {"messages": [{"role": "user", "content": encode({"context": context})}]},
            429,
        )
        with self.assertRaises(ValueError):
            self.store.require_report_delivery("s", reviewer.ref, report.ref)
        record(
            "delivered",
            {
                "contents": [
                    {"role": "user", "parts": [{"text": encode({"context": context})}]}
                ]
            },
        )
        self.store.require_report_delivery("s", reviewer.ref, report.ref)
        self.assertNotIn("PRIVATE", encode(list(windows(self.store, "s"))))

    def test_automatic_sqlite_rollback_preserves_original_error(self):
        self.store.db.execute(
            "CREATE TRIGGER full_disk BEFORE INSERT ON artifacts BEGIN SELECT RAISE(ROLLBACK, 'disk full fixture'); END"
        )
        with self.assertRaisesRegex(Exception, "disk full fixture"):
            with self.store.transaction():
                self.store._put("s", "note", {"text": "never committed"})
        self.assertEqual([], self.store.list("s", "note"))
        self.assertFalse(self.store.db.in_transaction)


class ParserLifecycle(unittest.IsolatedAsyncioTestCase):
    async def test_io_error_during_cancellation_does_not_replace_cancel(self):
        ready, release = threading.Event(), threading.Event()

        def fail():
            ready.set()
            release.wait(2)
            raise ValueError("late I/O error")

        task = asyncio.create_task(Workspace._io(fail))
        while not ready.is_set():
            await asyncio.sleep(0.001)
        task.cancel()
        await asyncio.sleep(0)
        release.set()
        with self.assertRaises(asyncio.CancelledError):
            await task
        with self.assertRaisesRegex(ValueError, "late I/O error"):
            await Workspace._io(fail)

    async def test_output_flood_is_bounded_and_child_reaped(self):
        spawn = asyncio.create_subprocess_exec
        children = []

        async def flood(*args, **kwargs):
            child = await spawn(
                sys.executable,
                "-c",
                "import sys; sys.stdout.buffer.write(b'x'*2000000)",
                **kwargs,
            )
            children.append(child)
            return child

        with (
            patch("epivra.materials.asyncio.create_subprocess_exec", flood),
            patch("epivra.materials.MAX_OUTPUT_BYTES", 100),
        ):
            with self.assertRaisesRegex(ValueError, "output byte limit"):
                await asyncio.wait_for(parse_isolated("x.txt", b"input"), 5)
        self.assertIsNotNone(children[0].returncode)

    async def test_repeated_cancel_during_output_reaps_child(self):
        spawn = asyncio.create_subprocess_exec
        ready = asyncio.Event()
        children = []

        async def flood(*args, **kwargs):
            child = await spawn(
                sys.executable,
                "-c",
                "import sys,time; sys.stdout.buffer.write(b'x'*2000000); sys.stdout.flush(); time.sleep(30)",
                **kwargs,
            )
            children.append(child)
            ready.set()
            return child

        with patch("epivra.materials.asyncio.create_subprocess_exec", flood):
            task = asyncio.create_task(parse_isolated("x.txt", b"input"))
            await ready.wait()
            await asyncio.sleep(0.05)
            task.cancel()
            await asyncio.sleep(0)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await asyncio.wait_for(task, 5)
        self.assertIsNotNone(children[0].returncode)


class InputBoundaries(unittest.TestCase):
    def test_finding_contract_distinguishes_reference_from_evidence_prose(self):
        value = {
            "text": "supported conclusion",
            "refs": [],
            "findings": [
                {
                    "statement": "observed outcome",
                    "status": "observation",
                    "support": ["source says the outcome improved"],
                }
            ],
        }
        with self.assertRaisesRegex(
            ValueError, r"arguments.findings\[0\].support\[0\].*exact artifact ref"
        ):
            validate(value, BUILTINS["finish_work"][1])
        value["findings"][0]["support"] = ["a" * 64]
        validate(value, BUILTINS["finish_work"][1])

    def test_json_depth_and_nonfinite_numbers(self):
        nested = []
        for _ in range(100):
            nested = [nested]
        with self.assertRaises(ValueError):
            bounded_json(nested)
        with self.assertRaises(ValueError):
            bounded_json({"value": float("nan")})

    def test_native_tool_results_and_rebuild_projection(self):
        receipt = {
            "observation_ref": "x",
            "result": {"report": "r", "units": units("tail")},
        }
        for payload in [
            {"messages": [{"role": "tool", "content": encode(receipt)}]},
            {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "tool_result", "content": encode(receipt)}
                        ],
                    }
                ]
            },
            {
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"functionResponse": {"response": receipt}}],
                    }
                ]
            },
        ]:
            self.assertEqual(
                [receipt], list(public_inputs({"wire": {"payload": payload}}))
            )

    def test_source_lookup_does_not_decode_unrelated_originals(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder) / "state.db")
            try:
                store.create("s", "Task", {})
                for i in range(120):
                    store.put("s", "source", {"sha256": str(i), "text": "large" * 1000})
                with patch.object(store, "_artifact", wraps=store._artifact) as decode:
                    result = store.matching("s", "source", {"sha256": "119"}, limit=1)
                self.assertEqual(1, decode.call_count)
                self.assertEqual("119", result[0].body["sha256"])
            finally:
                store.close()
