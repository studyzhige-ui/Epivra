"""Offline paired profile of equivalent context assembly; never calls a provider.

Run from a checkout with Epivra installed:
  python tools/profile_context_assembly.py --output context-profile.json

Results describe these fixtures on this machine, not end-to-end research speed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import statistics
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from epivra import context
from epivra import harness as harness_module
from epivra.adapters import DeepSeek
from epivra.domain import Artifact, encode, identity
from epivra.storage import Store
from evals import context_assembly_reference as reference

BASE_COMMIT = "cc0d68d89981aa0730d1bf6fbbdd9bf511ede777"


def paired(functions, repetitions):
    """Compare canonical output first; alternate order, keep every timing sample."""
    originals = {arm: encode(function()) for arm, function in functions.items()}
    if len(set(originals.values())) != 1:
        raise AssertionError("different model input: not a performance-only comparison")
    samples = {arm: [] for arm in functions}
    for function in functions.values():
        function()  # Untimed warmup on both arms.
    for repetition in range(repetitions):
        arms = list(functions)
        if repetition % 2:
            arms.reverse()
        for arm in arms:
            cpu_start, wall_start = time.process_time_ns(), time.perf_counter_ns()
            result = functions[arm]()
            elapsed, cpu = time.perf_counter_ns() - wall_start, time.process_time_ns() - cpu_start
            if encode(result) != originals[arm]:
                raise AssertionError("stateful output changed across repetitions")
            samples[arm].append({"wall_ns": elapsed, "process_cpu_ns": cpu})
    peaks = {}
    for arm, function in functions.items():
        tracemalloc.start()
        function()
        _, peaks[arm] = tracemalloc.get_traced_memory()
        tracemalloc.stop()
    value = next(iter(originals.values()))
    return {
        "canonical_outputs_equal": True,
        "output_sha256": hashlib.sha256(value.encode()).hexdigest(),
        "output_characters": len(value),
        "samples": samples,
        "median_wall_ms": {arm: statistics.median(x["wall_ns"] for x in rows) / 1e6 for arm, rows in samples.items()},
        "median_process_cpu_ms": {arm: statistics.median(x["process_cpu_ns"] for x in rows) / 1e6 for arm, rows in samples.items()},
        "peak_traced_bytes_untimed": peaks,
    }


def fixture(count, body_length, capacity):
    base = {
        "direction": {"request": "Compare the evidence, its conditions and counterevidence; preserve the user's writing requirements."},
        "task": "Use original evidence. " * 180,
        "tools": {"read": {"description": "Read exact references; do not infer permissions."}},
    }
    candidates = []
    for index in range(count):
        body = {"text": ("材料 😀 \\\"\n" * (body_length // 8 + 1))[:body_length], "sequence": index}
        if index % 11 == 0:
            body["text"] *= 8
        kind = "clarification_answer" if index % 13 == 0 else "note"
        candidates.append(Artifact(identity(index, body), "profile", kind, body, (), index))
    direct = [a.ref for a in candidates[::7]]
    base["inputs"] = [{"ref": ref} for ref in direct]
    return base, candidates, None, capacity


def encode_work(module, args):
    calls, characters = 0, 0

    def measured(value):
        nonlocal calls, characters
        result = encode(value)
        calls += 1
        characters += len(result)
        return result

    with patch.object(module, "encode", measured):
        module.assemble(*args)
    return {"encode_calls": calls, "encoded_characters": characters}


class NoNetwork:
    account = "offline-context-profile"

    async def post(self, *args, **kwargs):
        raise AssertionError("profiling must never call a provider")


def run(repetitions):
    root = Path(__file__).resolve().parents[1]
    result = {
        "baseline_commit": BASE_COMMIT,
        "scope": "offline local assembly only; no model calls or provider waiting; no research quality claim",
        "python": sys.version,
        "platform": platform.platform(),
        "repetitions": repetitions,
        "provider_calls": 0,
        "source_sha256": {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in (
            "src/epivra/context.py", "src/epivra/harness.py", "src/epivra/domain.py",
            "evals/context_assembly_reference.py", "tools/profile_context_assembly.py",
        )},
        "cases": [],
    }
    for name, count, body_length, capacity in (
        ("small", 16, 256, 48000),
        ("window-pressure", 128, 1024, 48000),
        ("growth-stress", 512, 1024, 96000),
    ):
        args = fixture(count, body_length, capacity)
        functions = {"baseline": lambda: reference.assemble(*args), "candidate": lambda: context.assemble(*args)}
        result["cases"].append({
            "name": name, "candidate_count": count, "context_capacity": capacity,
            "fixture_hash": identity(args[0], [a.__dict__ for a in args[1]], args[2], args[3]),
            **paired(functions, repetitions),
            "serialization_work": {arm: encode_work(module, args) for arm, module in (("baseline", reference), ("candidate", context))},
        })
    with tempfile.TemporaryDirectory() as folder:
        store = Store(Path(folder) / "profile.db")
        try:
            control = store.create("profile", "Compare evidence and limitations; no writing length requirement.", {"as_of_date": "2026-09-19"})
            plan = store.put("profile", "plan", {"text": "Investigate the question"}, (control.direction,))
            control = store.command("profile", "approve", control.ref, "approve", {"plan": plan.ref})
            lead = store.work("profile", control.ref, "lead", "Coordinate")
            investigator = store.work("profile", control.ref, "investigator", "Investigate", (), lead.ref)
            inputs = [store.put("profile", "note", {"text": ("Finding with a condition " * 42) + str(i)}, (investigator.ref,)) for i in range(64)]
            finding = store.put("profile", "work_result", {
                "text": "Evidence supports a conditional conclusion.", "refs": [x.ref for x in inputs], "producer": investigator.ref,
            }, (investigator.ref, control.direction, *(x.ref for x in inputs)))
            writer = store.work("profile", control.ref, "writer", "Write the supported findings", (finding.ref, *(x.ref for x in inputs)), lead.ref)
            for index in range(64):
                store.observation("profile", writer.ref, control.epoch, {"tool": "read_artifact", "result": {"text": "Original evidence " * 65, "item": index}}, ())
            harness = harness_module.Harness(store, DeepSeek(NoNetwork(), context_tokens=1000000, max_tokens=65536))

            def request_with(function):
                with patch.object(harness_module, "assemble", function):
                    return harness._request("profile", writer)

            result["cases"].append({
                "name": "harness-request-with-native-prepare",
                "scope": "same Store/schema/authority/prepare/page implementation in both arms; only assemble substituted",
                "note_inputs": 64, "observations": 64,
                **paired({"baseline": lambda: request_with(reference.assemble), "candidate": lambda: request_with(context.assemble)}, repetitions),
            })
        finally:
            store.close()
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=9)
    args = parser.parse_args()
    if args.repetitions < 1:
        parser.error("repetitions must be positive")
    if args.output.exists():
        parser.error("refuse to overwrite prior measurements")
    result = run(args.repetitions)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for case in result["cases"]:
        print(case["name"], case["median_wall_ms"])
