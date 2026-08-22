"""The approval gate: a receipt binds one exact Plan, and nothing else.

Approval is where a user commits money and attention, so its integrity rule is
narrow and absolute: a receipt names the exact Contract artifact it decided on,
and research may only start when that artifact is *still* the current head.

A task's plan is allowed to iterate before research begins.  The user reads a
candidate and either approves it or says what to change; saying what to change
produces a *new* Contract artifact rather than editing the old one, which
silently orphans the earlier receipt -- there is no state to update and no window
in which a stale approval can authorise research on a body the user never read.

That property is why the receipt carries the Contract as its parent rather than
a copy of its text: artifact identity already includes the body hash, so
"approved this exact Contract" and "approved this hash" are the same statement.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal

from .artifact_store import SqliteArtifactStore
from .contract import ResearchContract
from .sources import ArtifactValidationError

#: What a user may decide about a candidate.  Deliberately two: approving it, or
#: saying what to change.  Anything else -- "approve with changes", "approve the
#: scope but not the method" -- would leave ambiguity about what was authorised.
#: Abandoning a study is not a decision about a plan; it is
#: :meth:`~deep_research_agent.service.ResearchService.delete_research`.
ApprovalDecision = Literal["approved", "revision_requested"]

DECISIONS: tuple[ApprovalDecision, ...] = ("approved", "revision_requested")


class ApprovalError(RuntimeError):
    """Research cannot start from the approval state as recorded."""


class StalePlanError(ApprovalError):
    """A decision was made about a plan that is no longer the current one.

    The case this exists for: a user reads Plan v1, a revision produces Plan v2,
    and the reply to the old screen arrives afterwards.  Applying it to v2 would
    approve, or send back, a plan the user never saw.
    """


class StaleClarificationError(ApprovalError):
    """An answer arrived for a question that is no longer the open one.

    The same hazard as :class:`StalePlanError`, one step earlier: an answer to
    "are you choosing or explaining" must not be recorded against "which markets
    matter" just because that is what the Architect is asking now.
    """


@dataclass(frozen=True, slots=True)
class ApprovalBody:
    """One user decision on one exact Contract candidate.

    ``revision_note`` is the user's instruction to the Architect -- what to
    change about *this* candidate -- not a comment on an approval.  It is
    required when a revision is requested and meaningless otherwise, which is why
    it carries that name rather than a generic one.
    """

    decision: ApprovalDecision
    revision_note: str = ""

    def __post_init__(self) -> None:
        if self.decision not in DECISIONS:
            raise ArtifactValidationError(
                f"decision must be one of {list(DECISIONS)}, got {self.decision!r}"
            )
        if not isinstance(self.revision_note, str):
            raise ArtifactValidationError("revision note must be a string")
        if self.decision == "revision_requested" and not self.revision_note.strip():
            raise ArtifactValidationError(
                "a revision request must say what to change"
            )

    def encode(self) -> str:
        return json.dumps(
            {"decision": self.decision, "revision_note": self.revision_note},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    @classmethod
    def decode(cls, body: str) -> ApprovalBody:
        value = json.loads(body)
        return cls(
            decision=str(value["decision"]),  # type: ignore[arg-type]
            revision_note=str(value.get("revision_note", "")),
        )


def approval_card(contract: ResearchContract, *, version: int = 0) -> str:
    """The user-facing projection of a candidate.

    The card shows the Contract prose the approval will bind, the question model
    made explicit so the user can see what will and will not be answered, and
    the boundary between what the Lead may adapt and what needs re-approval.
    It shows no queries, no node names, and no model reasoning.
    """

    questions = "\n".join(
        f"- **{question.label}**（{'核心' if question.role == 'primary' else '支撑 ' + '、'.join(question.supports)}）"
        f" {question.text}"
        for question in sorted(
            contract.question_model.questions,
            key=lambda item: contract.labels.index(item.label),
        )
    )
    packs = (
        "、".join(contract.pack_refs) if contract.pack_refs else "（未使用能力包）"
    )
    heading = "# 研究方案待您批准" + (f"（第 {version} 版）" if version > 1 else "")
    return (
        f"{heading}\n\n"
        f"{contract.body_markdown.strip()}\n\n"
        "---\n\n"
        f"## 问题结构\n\n{questions}\n\n"
        f"## 能力包\n\n{packs}\n\n"
        "## 可选操作\n\n"
        "- `批准并开始研究`\n"
        "- `提出修改`（说明要改什么，会生成完整的新一版方案，旧批准自动失效）\n"
    )


async def record_decision(
    store: SqliteArtifactStore,
    contract_ref: str,
    body: ApprovalBody,
    *,
    provenance: object = None,
) -> str:
    """Commit a decision bound to one exact Contract artifact."""

    await store.get(contract_ref)
    envelope = await store.put(
        kind="approval_receipt",
        body=body.encode(),
        parent_refs=(contract_ref,),
        provenance=provenance,  # type: ignore[arg-type]
    )
    return envelope.artifact_id


async def approved_contract(
    store: SqliteArtifactStore,
) -> tuple[str, ResearchContract]:
    """Return the current Contract only if it is approved, else refuse.

    Every caller that is about to spend money on research goes through here.
    The checks are ordered so the error names the actual situation: no Contract
    at all, a Contract with no decision, a decision that was not approval, or an
    approval that belongs to a superseded candidate.
    """

    view = await store.active_view()
    head = view.head("research_contract")
    if head is None:
        raise ApprovalError("no Contract candidate exists for this task")

    decisions: dict[str, ApprovalBody] = {}
    for ref in view.active("approval_receipt"):
        envelope = await store.get(ref)
        for parent in envelope.parent_refs:
            decisions[parent] = ApprovalBody.decode(await store.body(ref))

    decision = decisions.get(head)
    if decision is None:
        if decisions:
            # A receipt exists, but for an older candidate: the user decided on a
            # body that has since been replaced, so it authorises nothing here.
            raise ApprovalError(
                "the current Contract candidate is not approved; a decision "
                "exists for a superseded candidate and does not carry over"
            )
        raise ApprovalError("the Contract candidate is awaiting user approval")
    if decision.decision == "revision_requested":
        raise ApprovalError(
            "the user requested a revision; a new Contract candidate is needed"
        )

    return head, ResearchContract.decode(await store.body(head))


async def decision_receipt(
    store: SqliteArtifactStore, contract_ref: str
) -> tuple[str, ApprovalBody] | None:
    """The receipt deciding one candidate, as ``(receipt_ref, body)``.

    The reference matters as much as the body: a revised Contract carries the
    receipt among its parents, which is what records *which* request produced it.
    """

    view = await store.active_view()
    for ref in view.active("approval_receipt"):
        envelope = await store.get(ref)
        if contract_ref in envelope.parent_refs:
            return ref, ApprovalBody.decode(await store.body(ref))
    return None


async def decision_for(
    store: SqliteArtifactStore, contract_ref: str
) -> ApprovalBody | None:
    """The recorded decision on one candidate, or None if undecided."""

    found = await decision_receipt(store, contract_ref)
    return None if found is None else found[1]


__all__ = [
    "DECISIONS",
    "ApprovalBody",
    "ApprovalDecision",
    "ApprovalError",
    "StaleClarificationError",
    "StalePlanError",
    "approval_card",
    "approved_contract",
    "decision_for",
    "decision_receipt",
    "record_decision",
]
