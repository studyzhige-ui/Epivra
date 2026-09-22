"""Explicit prerequisites for old serialization/version tests under the new contract.

This is test data, not an automatic readiness decision in the product. New
workflow tests exercise record_finding/prepare_writing through the real Harness.
"""

from epivra.research import ResearchLedger
from epivra.writing import WritingWorkspace


def basis_arguments(store, args, study="s"):
    """Explicit legacy-test data converted to owner assessments, never production."""
    ledger = ResearchLedger(store)
    current = {
        a.body["question"]: a for a in ledger.current(study, "question_assessment")
    }
    updates = []
    for row in args["coverage"]:
        limitation = "; ".join(
            [row.get("limitation", ""), *args.get("limitations", [])]
        ).strip("; ")
        findings = row["findings"]
        updates.append(
            {
                "question": row["question"],
                "answer_target": "Answer the original fixture question without extrapolation",
                "findings": findings,
                "checks": [],
                "remaining": [
                    {
                        "question": "Unanswered scope",
                        "disposition": "bounded" if findings else "blocked",
                        "reason": limitation,
                    }
                ]
                if limitation
                else [],
                "decision": "limited" if limitation else "ready",
                "reason": args["rationale"],
                **(
                    {"replaces": current[row["question"]].ref}
                    if row["question"] in current
                    else {}
                ),
            }
        )
    return {
        "updates": updates,
        "rationale": args["rationale"],
        **({"replaces": args["replaces"]} if args.get("replaces") else {}),
    }


def prepare_basis(store, work, study="s"):
    c = store.control(study)
    work = next(
        w
        for w in store.matching(study, "work", {"direction": c.direction})
        if w.body["role"] == "lead" and w.body.get("stage") == "research"
    )
    ledger = ResearchLedger(store)
    current = ledger.current_basis(study)
    sources = store.list(study, "source")
    expected = {s.ref for s in sources}
    if (
        current
        and expected.issubset(current.body["sources"])
        and not ledger.pending(study)
    ):
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
    args = basis_arguments(
        store,
        {
            "coverage": [
                {
                    "question": i,
                    "findings": [f.ref for f in findings],
                    "limitation": "Serialization fixture, no source claim assessed"
                    if not findings
                    else "",
                }
                for i, _ in enumerate(ledger.questions(study))
            ],
            "rationale": "This fixture checks serialization and version contracts, not truth.",
            "replaces": current.ref if current else None,
        },
        study,
    )
    args["updates"][0]["checks"] = [
        {
            "angle": "Explicit serialization fixture input",
            "refs": [item.ref],
            "effect": "changed",
            "reason": "Account for this known fixture delivery, not a model quality judgment",
        }
        for item in ledger.pending(study)
    ]
    return ledger.prepare_writing(study, work.ref, c.epoch, **args)


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
