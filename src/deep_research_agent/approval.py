"""The approval gate: a receipt binds one exact Contract, and nothing else.

Approval is where a user commits money and attention, so its integrity rule is
narrow and absolute: a receipt names the exact Contract artifact it approved,
and research may only start when that artifact is *still* the current head.
Revising a Contract produces a new artifact, which silently orphans the old
receipt -- there is no state to update and no window in which a stale approval
can authorise research on a body the user never read.

That property is why the receipt carries the Contract as its parent rather than
a copy of its text: artifact identity already includes the body hash, so
"approved this exact Contract" and "approved this hash" are the same statement.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from .artifact_store import SqliteArtifactStore
from .contract import ResearchContract
from .sources import ArtifactValidationError

#: What a user may do with a candidate.  Deliberately three: anything else --
#: "approve with changes", "approve the scope but not the method" -- would leave
#: ambiguity about what was actually authorised.
ApprovalDecision = Literal["approved", "revision_requested", "cancelled"]

DECISIONS: tuple[ApprovalDecision, ...] = (
    "approved",
    "revision_requested",
    "cancelled",
)


class ApprovalError(RuntimeError):
    """Research cannot start from the approval state as recorded."""


@dataclass(frozen=True, slots=True)
class ApprovalBody:
    """One user decision on one exact Contract candidate."""

    decision: ApprovalDecision
    note: str = ""

    def __post_init__(self) -> None:
        if self.decision not in DECISIONS:
            raise ArtifactValidationError(
                f"decision must be one of {list(DECISIONS)}, got {self.decision!r}"
            )
        if not isinstance(self.note, str):
            raise ArtifactValidationError("approval note must be a string")
        if self.decision == "revision_requested" and not self.note.strip():
            raise ArtifactValidationError(
                "a revision request must say what to change"
            )

    def encode(self) -> str:
        return json.dumps(
            {"decision": self.decision, "note": self.note},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    @classmethod
    def decode(cls, body: str) -> ApprovalBody:
        value = json.loads(body)
        return cls(
            decision=str(value["decision"]),  # type: ignore[arg-type]
            note=str(value.get("note", "")),
        )


def approval_card(contract: ResearchContract) -> str:
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
    return (
        "# 研究方案待您批准\n\n"
        f"{contract.body_markdown.strip()}\n\n"
        "---\n\n"
        f"## 问题结构\n\n{questions}\n\n"
        f"## 能力包\n\n{packs}\n\n"
        "## 可选操作\n\n"
        "- `批准并开始研究`\n"
        "- `提出修改`（会生成一份完整的新方案，旧批准自动失效）\n"
        "- `取消`\n"
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
            # A receipt exists, but for an older candidate: the user approved a
            # body that has since been replaced, so it authorises nothing here.
            raise ApprovalError(
                "the current Contract candidate is not approved; an approval "
                "exists for a superseded candidate and does not carry over"
            )
        raise ApprovalError("the Contract candidate is awaiting user approval")
    if decision.decision == "cancelled":
        raise ApprovalError("the user cancelled this research task")
    if decision.decision == "revision_requested":
        raise ApprovalError(
            "the user requested a revision; a new Contract candidate is needed"
        )

    return head, ResearchContract.decode(await store.body(head))


async def decision_for(
    store: SqliteArtifactStore, contract_ref: str
) -> ApprovalBody | None:
    """The recorded decision on one candidate, or None if undecided."""

    view = await store.active_view()
    for ref in view.active("approval_receipt"):
        envelope = await store.get(ref)
        if contract_ref in envelope.parent_refs:
            return ApprovalBody.decode(await store.body(ref))
    return None


def render_decisions(decisions: Mapping[str, ApprovalBody]) -> str:
    """Compact audit rendering used by status output."""

    return "\n".join(
        f"{ref}: {body.decision}" + (f" — {body.note}" if body.note else "")
        for ref, body in sorted(decisions.items())
    )


__all__ = [
    "DECISIONS",
    "ApprovalBody",
    "ApprovalDecision",
    "ApprovalError",
    "approval_card",
    "approved_contract",
    "decision_for",
    "record_decision",
    "render_decisions",
]
