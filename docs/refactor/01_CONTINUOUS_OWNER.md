# Continuous research owner — first executable refactor batch

Base: `08e54a544db587a3a12f8c8c8849a9bef7d02e30`. Development remains on
`improve/epivra-optimization`; no main merge or release.

## Implemented contracts

The persisted role name `lead` now means the complete research owner. After the
initial route approval it can read original sources, record exact evidence,
perform explicitly authorized web/public-source/local analysis work, and save
reports. Investigator, conflict-verification (`synthesizer`) and writer helpers
are optional specializations: they may start from direct materials, rather than
being required to receive another role's `work_result`. Delegation, internal
questions, cancellation and completion notifications continue through the existing
runtime. This batch does not add recursive/nested helper creation.

`draft_report` atomically saves `report` + `draft_saved`, not `work_result`.
Saving does not end the owner or helper. The current draft ref is included in the
model request and survives reopening the database. A revision names the exact
current `base`; stale base writes and stale accepted-version publications fail.
An explicitly handed-off report may be used as the first revision base of a new
helper; unrelated reports cannot. The owner continues through independent editor
feedback. Helpers finish explicitly with the current report ref; the existing
owner notification receives its report and metrics without copying the full text.

Publication still needs a different reviewer work, actual report delivery, an
accepted final verdict, exact report identity, valid citations and current user
direction. No author self-acceptance, comment-to-acceptance conversion, or old
review transfer is introduced. Saving a draft never marks it delivered in the UI.

Approval is once per study: replaying the identical approval command is idempotent;
a second approval command is rejected. User-initiated steering retains existing
authority, fences old work and never grants new external permissions. The owner
cannot ask the user through a clarification tool; helper questions stay internal.
Reading originals and using external tools remain unavailable before approval.
Private execution/material bytes remain unreadable research inputs.

The approval route and role instructions now explicitly prohibit research
hypotheses and predetermined answers. They describe problems and research routes,
not a role pipeline. Conflict verification is targeted, and the editor checks
faithfulness, consistency and real user requirements. These are prompt contracts,
not a claim that every model response already obeys them.

## Migration boundary

New studies use `continuous-research-v1`. Older `research-mainline-v2` studies stay
readable as audit history and cannot silently resume under changed completion
semantics. Their provider operations are not replayed. Starting new studies is the
supported route; automatic migration of in-flight work is NOT implemented.

No default word count, provider model change, total study budget or deadline was
added. Authorized analysis retains its pre-existing sandbox limits. Test timeouts
apply only to deterministic offline tests, not user research.

## Engineering references and adaptation

These are behavior references, not a claim to have copied whole Rust/TypeScript
products into Python. No new third-party source was vendored in this batch.

- Codex `5c5308fc9a9ee789049d646ef11e5400384b9c6f`,
  `codex-rs/core/src/tools/handlers/multi_agents.rs`: child agents inherit effective
  provider, permission, sandbox and working context before role-specific settings.
  Epivra uses the existing direction policy and explicit tool grants; role
  specialization no longer acts as a prerequisite chain.
- Codex at the same revision, `multi_agents/wait.rs`: wait on real child status,
  do not fabricate completion. Existing Epivra wait/notification mechanics remain.
- Provided Claude Code snapshot `58231dcce408f805c645cfbc352d2876b517223b`,
  `tools/AgentTool/prompt.ts`: investigations receive a question and adequate
  context, not an invented answer; actual notifications establish completion.
- The same snapshot, `tools/AgentTool/agentToolUtils.ts`: explicit tool/permission
  filtering is separate from specialized agent purpose. Epivra's network,
  filesystem, analysis and private-artifact guards are retained.
- Local product examples: `eval/benchmark-10/gemini-17.md` and `gemini-19.md` initial
  approval sections. Questions and material directions are route content, not
  hypotheses. GPT records that have no separate visible approval are not filled
  in from their final answers.

## Tests and handbook acceptance links

New `test_continuous_owner.py` exercises direct owner research, independent exact
version review, repeated saves, stale versions, atomic failures, persisted draft
recovery, approval idempotency, scope/private boundaries and an entire mocked
ResearchService loop (plan -> approval -> owner investigation -> draft -> editor
feedback -> same-owner correction -> new editor -> publication). Its test model
is deliberately scripted; it proves execution contracts, not LLM quality.

`test_analysis.py` now additionally invokes authorized analysis from the owner,
with the same sandbox lineage and cleanup as a helper. Existing tests for
cancellation, unknown requests, prompt injection, citations, current-direction
fencing and private records remain. Old assertions that deliberately required
obsolete role barriers have been changed to test the new contract, not skipped.
Near-capacity stress fixtures derive their task size from the actual tool schema,
retaining the same context ceilings, navigation load and accepted-memory checks.

Handbook `curriculum/09-agent` review targets: chapters 02/03 (autonomy and scopes),
04/06/07 (tool contracts, results, cancellation), 08/09/10 (route, context,
continuation), 12/13 (state, recovery), 14/15 (authorization and containment),
19 (helpers), 20/21 (evidence and tests), 22 (persistent authoring). Python targets:
object identity/copying, exceptions/context managers, async cancellation, and
transactions. This is an acceptance map, not a claim every chapter has passed.

## Validation and remaining work

Local source uses the entire hash-verified worktree. An offline editable install
made isolated parser subprocess imports work. Local full discovery after fixes:
465 discovered, 456 passed, 7 skipped, 2 import errors because questionary is not
installed here. This is NOT a green full run. The authorized Windows runner must
validate with full dependencies, Ruff, configured mypy and a built wheel before
source promotion. No paid model or Tavily calls in this batch.

The first slice is a persistent authoring lifecycle, not yet diff editing:
`draft_report` still receives a complete replacement text. The shared evidence
basis/readiness model, patch-based writing workspace, formal conflict-resolution
records, semantic review/revision handling and real end-to-end quality/cost
validation remain. Evidence sufficiency is currently a prompt obligation, not a
programmatically verified guarantee. No speedup or release readiness is claimed.
