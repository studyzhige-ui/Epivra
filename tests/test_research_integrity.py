"""Offline negative integrity gates and legacy schema migration."""

import io
import json
import sqlite3
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path

from epivra.calculation import calculate
from epivra.citations import render, validate
from epivra.context import assemble, fit_read_result
from epivra.domain import (
    Artifact,
    OwnershipError,
    UnknownOutcome,
    encode,
    identity,
)
from epivra.evidence import chunks
from epivra.harness import Harness
from epivra.materials import parse
from epivra.research import ResearchLedger
from epivra.storage import Store
from epivra.usage import counters
from epivra.workspace import Workspace
from epivra.writing import WritingWorkspace, apply_edits


def fails(fn, types=(ValueError, RuntimeError)):
    try:
        fn()
    except types:
        return
    raise AssertionError("Expected rejection")


async def main():
    count = 0
    with tempfile.TemporaryDirectory() as d, ExitStack() as stack:
        s = Store(Path(d) / "main.db")
        stack.callback(s.close)
        c = s.create("S", "Question", {})
        fails(lambda: Store(s.path), (OwnershipError,))
        count += 1
        p = s.put("S", "plan", {"brief": {"questions": ["Q"]}}, (c.direction,))
        c = s.command("S", "approve", c.ref, "approve", {"plan": p.ref})
        root = s.work("S", c.ref, "lead", "root")
        ledger = ResearchLedger(s)
        w = WritingWorkspace(s)
        src = Workspace(s).upload("S", "x.txt", b"original alpha beta")
        f = ledger.record_finding(
            "S",
            root.ref,
            c.epoch,
            statement="Alpha",
            status="inference",
            support=[src.ref],
        )
        fails(
            lambda: ledger.record_finding(
                "S",
                root.ref,
                c.epoch,
                statement="Alpha fact",
                status="source_statement",
                support=[src.ref],
                replaces=f.ref,
                reason="Only relabel",
            )
        )
        count += 1
        row = {
            "question": 0,
            "answer_target": "Q",
            "findings": [f.ref],
            "checks": [],
            "remaining": [],
            "decision": "ready",
            "reason": "bounded answer",
        }
        b = ledger.prepare_writing("S", root.ref, c.epoch, updates=[row], rationale="ready")
        step = s.put("S", "step", {"request": {}}, (root.ref,))
        r = w.save(
            "S",
            root.ref,
            c.epoch,
            step.ref,
            0,
            text="😀 Result [[cite:" + src.ref + "]]",
            evidence=[src.ref],
        )
        report = s.get("S", r["ref"])
        fails(
            lambda: w.save(
                "S",
                root.ref,
                c.epoch,
                step.ref,
                1,
                text="replacement",
                evidence=[src.ref],
            )
        )
        count += 1
        fails(lambda: apply_edits("a a", [{"old": "a", "new": "b"}]))
        fails(
            lambda: apply_edits(
                "abc", [{"old": "ab", "new": "x"}, {"old": "bc", "new": "y"}]
            )
        )
        count += 2
        changed = ledger.record_finding(
            "S",
            root.ref,
            c.epoch,
            statement="Beta correction",
            status="observation",
            support=[src.ref],
            replaces=f.ref,
            reason="Correct the statement",
        )
        fails(lambda: ledger.require_basis("S", b.ref))
        fails(lambda: w.require_publishable("S", report))
        count += 2
        # Current assessment compare-and-swap and stale/current conflict binding.
        fails(
            lambda: ledger.assess_questions(
                "S", root.ref, c.epoch, updates=[{**row, "findings": [changed.ref]}]
            )
        )
        count += 1
        # Whole cited report binds original exact bytes, including Unicode spans.
        rendered = render(
            "😀A [[cite:" + src.ref + "]] `[[cite:" + src.ref + "]]`",
            [src.ref],
            lambda ref: s.get("S", ref),
        )
        validate({**rendered, "evidence": [src.ref]}, lambda ref: s.get("S", ref))
        assert len(rendered["citation_marks"]) == 1
        fails(
            lambda: validate(
                {
                    **rendered,
                    "text": rendered["text"] + "tampered",
                    "evidence": [src.ref],
                },
                lambda ref: s.get("S", ref),
            )
        )
        fails(
            lambda: render(
                "[[cite:" + "a" * 64 + "]]", [src.ref], lambda ref: s.get("S", ref)
            )
        )
        count += 2
        assert all(
            x
            not in Harness(
                s,
                type(
                    "M",
                    (),
                    {"identity": "m", "context_tokens": 1000000, "max_tokens": 1024},
                )(),
            )._schema("investigator", {"_approved": True})
            for x in ["publish_report", "draft_report", "assess_questions"]
        )
        count += 1
        # Unknown identical request cannot be admitted under another work/key/credential.
        rec = {
            "request": "same-request",
            "scope": "scope1",
            "binding": "m",
            "conditions": {},
        }
        s.admit(
            "S",
            root.ref,
            c.epoch,
            "op",
            {"x": 1},
            admission={"recovery": rec, "at": 1, "resource": "model", "tokens": 1},
        )
        child = s.work("S", c.ref, "investigator", "child", owner=root.ref)
        fails(
            lambda: s.admit(
                "S",
                child.ref,
                c.epoch,
                "alias",
                {"x": 1},
                admission={
                    "recovery": {**rec, "scope": "scope2"},
                    "at": 2,
                    "resource": "model",
                    "tokens": 1,
                },
            ),
            (UnknownOutcome,),
        )
        count += 1
        # Original operation succeeds once, then cannot be overwritten.
        s.settle("op", {"http_status": 200, "data": {"answer": 1}})
        fails(lambda: s.settle("op", {"http_status": 200, "data": {"answer": 2}}))
        count += 1
        assert (
            counters(
                {
                    "data": {
                        "usage": {
                            "prompt_tokens": -1,
                            "completion_tokens": False,
                            "total_tokens": float("nan"),
                        }
                    }
                }
            )["total_tokens"]
            is None
        )
        count += 1
        # Context envelopes stay bounded and retain retrieval handles.
        artifact = Artifact(
            "x", "S", "source", {"text": "A" * 2600 + "\n\nB" * 1000}, (), 1
        )
        pieces = chunks(artifact)
        assert all(artifact.body["text"][p["start"] : p["end"]] for p in pieces)
        a = assemble(
            {"inputs": []},
            [
                Artifact(str(i), "S", "note", {"text": "x" * 200}, (), i)
                for i in range(20)
            ],
            None,
            600,
        )
        assert len(encode(a)) <= 600 and a["omitted_count"] > 0
        result = fit_read_result(
            lambda n: {"text": "😀" * n, "next_offset": n}, 200, 100
        )
        assert len(encode(result)) <= 100 and result["next_offset"] > 0
        count += 2
        # Parser/arithmetical boundaries and legitimate non-ASCII CSV/XLSX path.
        assert parse("x.csv", "列,值\nA,1\n".encode())["segments"][1]["locator"] == {
            "row": 2
        }
        from openpyxl import Workbook

        book = Workbook()
        sheet = book.active
        sheet["A1"] = "=1+1"
        buf = io.BytesIO()
        book.save(buf)
        assert "=1+1" in parse("x.xlsx", buf.getvalue())["text"]
        for expr in ["__import__('os')", "1/0", "2**100000", "9" * 2001]:
            fails(lambda: calculate(expr))
        assert calculate("0.1+0.2")["exact"] == "3/10"
        count += 6
        s.close()
        # Real legacy 2001 schema: constructor migrates additively and preserves rows.
        old = Path(d) / "legacy.db"
        db = sqlite3.connect(old)
        db.executescript(
            "CREATE TABLE artifacts(seq INTEGER PRIMARY KEY AUTOINCREMENT,ref TEXT UNIQUE,study TEXT,kind TEXT,body TEXT,parents TEXT); CREATE TABLE operations(id TEXT PRIMARY KEY,study TEXT,work TEXT,direction TEXT,epoch INTEGER,request TEXT,status TEXT,result TEXT); CREATE TABLE commands(study TEXT,command_id TEXT,request TEXT,receipt TEXT,PRIMARY KEY(study,command_id)); PRAGMA user_version=2001;"
        )
        body = {"old": "evidence"}
        ref = identity("L", "note", body, ())
        db.execute(
            "INSERT INTO artifacts(ref,study,kind,body,parents) VALUES(?,?,?,?,?)",
            (ref, "L", "note", encode(body), "[]"),
        )
        db.commit()
        db.close()
        oldstore = Store(old)
        stack.callback(oldstore.close)
        assert oldstore.get("L", ref).body == body
        assert oldstore.db.execute("PRAGMA user_version").fetchone()[0] == 2004
        assert {"request_step", "admission"} <= {
            x[1] for x in oldstore.db.execute("PRAGMA table_info(operations)")
        }
        oldstore.close()
        count += 1
        print(
            json.dumps(
                {
                    "negative_boundary_checks": count,
                    "areas": [
                        "ownership lock",
                        "finding status preservation",
                        "assessment/basis version invalidation",
                        "manuscript CAS",
                        "exact patch rejection",
                        "citation identity and Unicode",
                        "role grants",
                        "unknown cross-key/work nonreplay",
                        "immutable settlement",
                        "usage sanitization",
                        "bounded context",
                        "CSV/XLSX/arithmetic",
                        "root symlink rejection",
                        "2001 migration",
                    ],
                    "result": "PASS",
                    "provider_calls": 0,
                }
            )
        )


class ResearchIntegrityTests(unittest.IsolatedAsyncioTestCase):
    async def test_negative_integrity_and_legacy_migration(self):
        await main()

    @unittest.skipIf(
        __import__("os").name == "nt",
        "POSIX symlink fixture; native Windows reparse boundary is separate",
    )
    def test_approved_root_does_not_follow_symlink(self):
        with tempfile.TemporaryDirectory() as d, ExitStack() as stack:
            s = Store(Path(d) / "main.db")
            stack.callback(s.close)
            folder = Path(d) / "root"
            folder.mkdir()
            outside = Path(d) / "outside.txt"
            outside.write_text("secret")
            (folder / "escape.txt").symlink_to(outside)
            s.create("F", "files", {"local_roots": [str(folder)]})
            catalog = Workspace(s).discover("F", str(folder))
            assert catalog.body["entries"][0]["status"] == "unavailable"
            fails(lambda: Workspace(s).snapshot("F", catalog.ref, "escape.txt"))
