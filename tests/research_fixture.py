"""Explicit prerequisites for old serialization/version tests under the new contract.

This is test data, not an automatic readiness decision in the product. New
workflow tests exercise record_finding/prepare_writing through the real Harness.
"""

from epivra.research import ResearchLedger
from epivra.writing import WritingWorkspace


def prepare_basis(store, work, study="s"):
    c = store.control(study)
    ledger = ResearchLedger(store)
    current = ledger.current_basis(study)
    sources = store.list(study, "source")
    expected = {s.ref for s in sources}
    if current and expected.issubset(current.body["sources"]):
        return current
    findings = ledger.current(study, "finding")
    accounted = {ref for f in findings for ref in f.body["sources"]}
    for source in sources:
        if source.ref not in accounted:
            findings.append(
                ledger.record_finding(
                    study,
                    work.ref,
                    c.epoch,
                    statement="Serialization fixture's supplied record",
                    status="observation",
                    support=[source.ref],
                    limits=["Not an LLM quality assessment"],
                )
            )
    return ledger.prepare_writing(
        study,
        work.ref,
        c.epoch,
        findings=[f.ref for f in findings],
        coverage=[
            {
                "question": i,
                "findings": [f.ref for f in findings],
                "limitation": "Serialization fixture, no source claim assessed"
                if not findings
                else "",
            }
            for i, _ in enumerate(ledger.questions(study))
        ],
        rationale="This test checks serialization and version contracts on explicitly supplied fixtures, not truth.",
        replaces=current.ref if current else None,
    )


def save_report(store, work, text, evidence=(), study="s"):
    basis = prepare_basis(store, work, study)
    c = store.control(study)
    step = store.put(study, "step", {"fixture": "authoring"}, (work.ref,))
    result = WritingWorkspace(store).save(
        study,
        work.ref,
        c.epoch,
        step.ref,
        0,
        text=text,
        evidence=list(evidence),
        basis=basis.ref,
    )
    return store.get(study, result["ref"])
