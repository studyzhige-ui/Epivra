"""Offline full research journey through the real persistent domain and Harness."""

import io
import json
import tempfile
import unittest
import zipfile
from contextlib import ExitStack
from pathlib import Path

from epivra.domain import Call, Conflict, NotAllowed, Reply
from epivra.harness import Harness
from epivra.presentation import progress, published_report, work_detail
from epivra.report_export import markdown_report, word_report
from epivra.research import ResearchLedger
from epivra.storage import Store
from epivra.workspace import Workspace
from epivra.writing import WritingWorkspace


class Model:
    identity = "offline-audit-model"
    context_tokens = 1000000
    max_tokens = 4096

    def __init__(self):
        self.calls = []
        self.requests = []

    async def complete(self, request):
        self.requests.append(request)
        return Reply("", tuple(Call(n, a) for n, a in self.calls)).to_json()


class ResearchJourneyTests(unittest.IsolatedAsyncioTestCase):
    async def test_complete_local_research_journey(self):
        with tempfile.TemporaryDirectory() as d, ExitStack() as stack:
            path = Path(d) / "state/research.db"
            s = Store(path)
            stack.callback(s.close)
            m = Model()
            h = Harness(s, m)
            ws = Workspace(s)
            c = s.create(
                "S",
                "Does the source establish that water freezes at 0 C?",
                {"network": False, "evidence_provider": "bm25"},
            )
            source = await ws.upload_async(
                "S",
                c.ref,
                "source.txt",
                b"At normal atmospheric pressure, pure water freezes at 0 C. This is conditional, not universal.",
            )
            route = s.work("S", c.ref, "lead", "plan")

            async def turn(w, calls):
                m.calls = calls
                result = await h.step("S", w.ref)
                obs = [
                    x.body
                    for x in s.related(
                        "S",
                        "observation",
                        s.related("S", "step", w.ref, first_parent=True)[-1].ref,
                    )
                ]
                bad = [
                    o
                    for o in obs
                    if o.get("error")
                    or isinstance(o.get("result"), dict)
                    and o["result"].get("error")
                ]
                if bad:
                    raise AssertionError(bad)
                return result

            assert "read_source" not in h._request("S", route)["tools"]
            await turn(
                route,
                [
                    (
                        "propose_plan",
                        {
                            "text": "Check conditions in the supplied source.",
                            "brief": {
                                "subject": "water freezing",
                                "given_context": [],
                                "questions": ["What does the source establish?"],
                                "material_scope": {
                                    "mode": "case_materials",
                                    "basis": "User supplied one original file",
                                },
                            },
                        },
                    )
                ],
            )
            plan = s.list("S", "plan")[-1]
            c = s.command("S", "approve", c.ref, "approve", {"plan": plan.ref})
            root = s.work("S", c.ref, "lead", "research", (plan.ref,))
            await turn(
                root,
                [
                    (
                        "delegate_work",
                        {
                            "role": "investigator",
                            "task": "Check the source and its limits",
                            "refs": [source.ref],
                        },
                    )
                ],
            )
            child = s.matching("S", "work", {"role": "investigator"})[-1]
            await turn(
                child,
                [
                    (
                        "request_clarification",
                        {
                            "text": "Should I preserve pressure condition?",
                            "refs": [source.ref],
                        },
                    )
                ],
            )
            q = s.list("S", "clarification")[-1]
            assert h.waiting("S", child.ref)
            await turn(
                root,
                [
                    (
                        "answer_clarification",
                        {
                            "question": q.ref,
                            "text": "Yes, retain all material conditions.",
                            "refs": [source.ref],
                        },
                    )
                ],
            )
            assert not h.waiting("S", child.ref)
            await turn(
                child,
                [
                    ("read_source", {"ref": source.ref}),
                    ("calculate", {"expression": "(1+2)^3"}),
                ],
            )
            obs = s.matching("S", "observation", {"tool": "read_source"})[-1]
            selection = obs.body["result"]["selections"][0]["selection"]
            await turn(
                child,
                [
                    (
                        "record_evidence",
                        {
                            "selection": selection,
                            "text": "The source establishes a conditional freezing point.",
                            "limits": "Normal atmospheric pressure",
                        },
                    )
                ],
            )
            note = s.matching("S", "note", {"producer": child.ref})[-1]
            await turn(
                child,
                [
                    (
                        "record_finding",
                        {
                            "statement": "At normal atmospheric pressure pure water freezes at 0 C",
                            "status": "source_statement",
                            "support": [note.ref],
                            "conditions": ["normal atmospheric pressure", "pure water"],
                            "limits": [],
                        },
                    )
                ],
            )
            finding = s.list("S", "finding")[-1]
            await turn(
                child,
                [
                    (
                        "finish_work",
                        {
                            "text": "Conditional result supported.",
                            "refs": [finding.ref, source.ref],
                        },
                    )
                ],
            )
            result = s.matching("S", "work_result", {"producer": child.ref})[-1]
            await turn(
                root,
                [
                    (
                        "prepare_writing",
                        {
                            "rationale": "The single original question is answered within the supplied-source scope.",
                            "updates": [
                                {
                                    "question": 0,
                                    "answer_target": "Report conditions rather than universalize",
                                    "findings": [finding.ref],
                                    "checks": [
                                        {
                                            "angle": "Investigator returned the original conditional claim",
                                            "refs": [result.ref, source.ref],
                                            "effect": "changed",
                                            "reason": "Retained the pressure and purity conditions",
                                        }
                                    ],
                                    "remaining": [],
                                    "decision": "ready",
                                    "reason": "Original source directly supports the bounded answer",
                                }
                            ],
                        },
                    )
                ],
            )
            basis = s.list("S", "writing_basis")[-1]
            await turn(
                root,
                [
                    (
                        "delegate_work",
                        {
                            "role": "writer",
                            "task": "Write one concise conditional answer",
                            "refs": [basis.ref, source.ref],
                        },
                    )
                ],
            )
            writer = s.matching("S", "work", {"role": "writer"})[-1]
            await turn(
                writer,
                [
                    (
                        "draft_report",
                        {
                            "text": "# Result 😀\n\nPure water freezes at 0 C at normal atmospheric pressure. [[cite:"
                            + note.ref
                            + "]]",
                            "evidence": [source.ref],
                        },
                    )
                ],
            )
            report = s.list("S", "report")[-1]
            try:
                WritingWorkspace(s)._allowed("S", root.ref, c.epoch)
            except NotAllowed:
                pass
            else:
                raise AssertionError("root stole writer ownership")
            await turn(
                writer,
                [
                    (
                        "finish_work",
                        {
                            "text": "Saved the answer with its material conditions.",
                            "refs": [report.ref],
                        },
                    )
                ],
            )
            assert s.writing_author("S") == root.ref
            await turn(
                root,
                [
                    (
                        "delegate_work",
                        {
                            "role": "reviewer",
                            "task": "Independently check this exact report",
                            "refs": [report.ref],
                        },
                    )
                ],
            )
            reviewer = s.matching("S", "work", {"role": "reviewer"})[-1]
            try:
                s.require_report_delivery("S", reviewer.ref, report.ref)
            except ValueError:
                pass
            else:
                raise AssertionError("undelivered reviewer could accept")
            await turn(reviewer, [("read_report", {})])
            await turn(
                reviewer,
                [
                    (
                        "submit_review",
                        {
                            "reason": "Checked the exact complete report and citation; all material conditions retained.",
                            "defects": [],
                        },
                    )
                ],
            )
            review = s.list("S", "review")[-1]
            await turn(
                root, [("publish_report", {"report": report.ref, "review": review.ref})]
            )
            published = published_report(s, "S", report.ref)
            assert "😀" in published["text"]
            assert published["citation_marks"]
            assert "\\[1]" in markdown_report(published)
            b = word_report(published)
            z = zipfile.ZipFile(io.BytesIO(b))
            assert b"0 C" in z.read("word/document.xml")
            assert progress(s, "S")["manuscript"]["state"] == "published"
            assert work_detail(s, "S", child.ref)["entries"]
            try:
                ResearchLedger(s).record_finding(
                    "S",
                    root.ref,
                    c.epoch,
                    statement="new",
                    status="observation",
                    support=[source.ref],
                )
            except NotAllowed:
                pass
            else:
                raise AssertionError("published evidence mutable")
            paid_count = len(s.admissions())
            s.close()
            s = Store(path)
            stack.callback(s.close)
            assert published_report(s, "S")["ref"] == report.ref
            assert len(s.admissions()) == paid_count
            imported = Store(Path(d) / "imported/research.db")
            stack.callback(imported.close)
            assert imported.import_completed(path, "S")["imported"]
            assert imported.import_completed(path, "S")["already_imported"]
            assert published_report(imported, "S")["text"] == published["text"]
            imported.close()
            c = s.command(
                "S", "steer", c.ref, "steer", {"request": "A distinct new question"}
            )
            assert published_report(s, "S") == {"report": None}
            try:
                published_report(s, "S", report.ref)
            except Conflict:
                pass
            else:
                raise AssertionError("old report still current")
            s.close()
            print(
                json.dumps(
                    {
                        "journey": "route -> approval -> investigator clarification -> original reading -> exact evidence -> findings -> assessment/basis -> exclusive writer -> independent exact review -> publication -> DOCX/Markdown -> restart -> idempotent archive import -> steer invalidation",
                        "model_turns": paid_count,
                        "result": "PASS",
                        "network_calls": 0,
                    }
                )
            )
