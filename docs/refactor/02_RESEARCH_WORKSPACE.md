# Continuous research: evidence, conflicts and authoring

Implementation contract for `continuous-research-v2`. This is an Agent runtime,
not a host-selected investigation→synthesis→writing workflow. The owner decides
research actions; immutable records make those decisions inspectable and safe.

## Product rules

The initial plan is a research route: questions, supplied context and material
scope. It must not propose hypotheses, preselect explanations or dictate an
answer. The user approves once. The approved owner has no user-clarification tool
and cannot request a second approval. Helpers may bring internal questions to the
owner. The user may still initiate pause, cancellation or steering. Permissions
are never elevated by approval or inherited from untrusted source text.

The historical role key `lead` denotes the full research owner, not a dispatch-only
manager. Research helpers can read originals, record findings and author the
shared draft without an investigator-result prerequisite. `synthesizer` denotes
optional, scoped conflict investigation. `reviewer` is the independent editor:
check faithful use of the evidence, conditions, consistency and user requirements;
return concrete research issues to the owner rather than ask the user or redo all
research. Only the owner spawns helpers, avoiding unbounded recursive delegation.

## Canonical research ledger

`record_finding` stores a versioned judgment with exact original source/note
references, declared status, conditions and limitations. A completion note is no
longer a second structured `findings` database. `finish_work` references canonical
records; the original evidence is accessible directly without a chain of rewritten
summaries. Source statements, observations, inferences and forecasts remain
separate; no hypothesis/assumption status is introduced.

Replacing a finding requires the current reference and an explanation. Restating
an inference against the same support cannot promote it to a source statement.
This is a provenance constraint, **not** a proof that a model's first claim or new
support is semantically correct. Exact support can be a full source or a note
whose quote/offset are verified against its source. Plans, reviews, other studies
and narrative summaries are not direct evidence.

`record_conflict` records a concrete question and affected current findings.
Investigation can establish different scope/version, transcription error, no
conflict, genuine disagreement, or insufficient material. Outcomes other than
`open` require original evidence and an explanation. We do not force agreement.
A closed conflict becomes stale when one of its findings changes.

`prepare_writing` records the Agent's readiness assessment: cover every original
approved question, bind the selected findings, explain remaining limitations and
why available further investigation is not needed now. Questions with insufficient
material require explicit limitations, not invented answers. It cannot ignore an
open/stale conflict. There is no scalar saturation score, fixed source quota, fixed
research-round budget or report-length requirement. Readiness remains an Agent
judgment, never a host truth certificate.

A basis records all findings it considered. New/replaced findings or conflicts
invalidate that basis. A newly fetched raw page alone is not declared a semantic
change; the Agent must assess it. The runtime does not silently hide changed
knowledge while allowing an older "ready" basis to authorize publication.

## Persistent authoring

`draft_report` saves the first complete author Markdown with citation markers and
its current writing-basis version. It does not finish the author work.
`read_draft` reads exact author text in bounded pages, not generated citation
numbers. `patch_draft(base, edits)` applies simultaneous unique exact substitutions
against the named shared head. Missing, ambiguous, no-op and overlapping edits
fail before persistence. There is no fuzzy replacement or report-length cap.

The owner and explicitly assigned writing helpers share one manuscript per user
direction. Helpers cannot overwrite an unassigned author's work. A stale base
loses the compare-and-swap race rather than overwriting later edits. Report and
`draft_saved` receipt are atomic; request/step identities make partial-step replay
idempotent without regenerating or duplicating a document. Unchanged Unicode,
line endings and citations are copied exactly. Whole rewriting remains available
when the Agent decides it is necessary; small changes use patches.

A basis change requires reassessment and an explicit patch/full revision bound to
the new basis. Editing all semantically affected passages remains the Agent's job;
a successful textual patch is not proof of semantic completeness. Original and
updated handoff inputs, clarification answers and report dependencies stay in the
version lineage so late premise changes remain discoverable.

Publication requires the current shared draft, its current nonstale evidence basis,
intact citation rendering, a different work's final editor result for that exact
version, and actual report delivery before the decision. An accepted old report
cannot authorize a new revision. A published direction is immutable; only an
explicit user-initiated direction change starts new research. The editor cannot
alter evidence or patch the manuscript it independently judges.

## Runtime and migration

The existing operation ledger, provider adapters, concurrency, cancellation,
unknown-operation settlement, context compaction, source delivery and permissions
remain in use. Research/authoring updates run in the same Store transactions and
process-lock boundary. Each update has an idempotent step identity. There is no
new backend service, vector store, queue or framework dependency.

New directions carry `runtime=continuous-research-v2`. Old saved studies remain
readable/exportable for audit but cannot be silently resumed under a different
contract. Never convert their records by modifying immutable source identities or
resend unknown paid operations. Start a new study for new execution; keep the old
study intact.

The public progress view shows canonical finding/conflict counts, readiness/stale
state and a persistent draft distinct from a publication. Detail views expose only
known public fields, never private steps/provider protocol. Role labels in CLI/Web
use research owner/conflict verification/editorial review.

## Validation and limits

`tests/test_research_workspace.py` exercises the complete ResearchService through
one route approval, original reading, finding/basis, drafting, independent edit
rejection, local patch, new-version acceptance and publication. It does not script
these turns in the product. Additional tests cover exact provenance, fake source
rejection, supersession, investigated disagreements, question coverage, basis
invalidation, stale-author races, patch failure rollback, partial-step replay,
restart and user steering.

Legacy serialization/lineage tests explicitly prepare the new preconditions using
`tests/research_fixture.py`. These fixtures do not auto-certify production research.
Old duplicate `finish_work.findings` assertions are replaced by canonical evidence
contract checks; safety and actual-delivery assertions remain.

Offline passing proves mechanism contracts, not broad research quality or speed.
Real-model smoke and complete-task evidence are reported separately. A small
successful task is not Benchmark-10 performance or release certification.
