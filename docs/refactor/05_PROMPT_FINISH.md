# Cross-provider prompt and revision finishing pass

Base: `cf7691941e4986e872b31c8b6d79b0b6da8e2114`.
Scope: the five approved finishing items, not a new Agent framework or model-specific tuning.

## Implemented contracts

1. **Evidence and manuscript revision.** `record_finding(replaces=...)` changes one canonical judgment, including its conditions and limits. Replacement receipts explicitly state the dependent follow-up. The host already invalidates changed writing bases/conflicts; the shared instruction now makes the author correct the active evidence, not only the prose. `patch_draft(base=..., basis=<new>, edits=[])` can rebind an unchanged manuscript to a different valid basis, without retranscribing text or inventing a cosmetic edit. Same basis, stale base, invalid sources and missing basis fail. Any new version requires its own independent final review. This does not automatically detect an incorrect unmodified finding.
2. **Editorial decisions.** One common rubric distinguishes semantic defects and real user requirements from optional style. Reviewers group a common cause across affected locations and make their reason, defects and comments consistent. Short paired examples illustrate supported qualifications vs unsupported strengthening; they are not topic gates. No keyword classifier or host truth score is introduced.
3. **Useful delegation and focused context.** Selection considers independence, context isolation, specialist value, sequential dependence and shared writes. It neither requires helpers for everything nor prefers doing everything alone. The owner can work on nonoverlapping tasks while helpers run; waits are event-driven. Investigator, conflict verifier and check-mode editor no longer automatically inherit every finding from the current writing basis or the first global findings page. Assigned artifacts and own observations remain available; global directories retain truthful counts and unchanged pagination through explicit read_context. Full final editors and manuscript writers still receive the whole bound writing basis. This is focused default loading, not a security isolation or a claim of statistically independent judgment.
4. **Batch editing.** One patch can contain all known nonoverlapping edits against one base. Exact small anchors are for matching, not limits on change size. Independent reads can be grouped; dependent steps and shared version writes remain ordered. No old review is reused on a new report. No word, call or production time limit is added.
5. **One shared policy.** `prompts.py` defines each tool once. Planning uses a separate route-only instruction matched to actual pre-approval tools. Approved owners use the continuous-research policy. No model/provider name selects an alternative prompt, examples, thresholds or severity rubric. No second user question or research hypothesis is introduced.

## Source principles and exclusions

- Codex snapshot `5c5308fc9a9ee789049d646ef11e5400384b9c6f`: multi-agent coordination/waiting and precise patching contracts. Its orchestrator-only mode and coding-specific advice are not transplanted into research.
- Provided Claude Code snapshot `58231dcce408f805c645cfbc352d2876b517223b`: `tools/AgentTool/prompt.ts` for explaining task context, qualitative delegation value and completion notifications; `tools/FileEditTool/prompt.ts` for unique exact anchors and preserving existing content. Fork/cache claims and product-specific confirmation policies are not asserted for Epivra.
- Anthropic public prompting guidance: explicit instructions, motivation, distinct data/instruction boundaries and diverse examples. No model-specific sections or competing-hypothesis research recipe adopted.
  https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices
- OpenAI prompting guidance: clear goals/context/output boundaries and actual verification. No per-provider tuning or model replacement is in scope.
  https://developers.openai.com/api/docs/guides/prompt-engineering

## Verification boundaries

`tests/test_prompt_finish.py` checks unchanged-text rebind, exact version review, stale input/no-op rejection, idempotent replay, atomic rollback, durable reopen, source-to-finding-to-conflict-to-basis-to-batch propagation, cosmetic changes, focused helper inputs with complete lookup, full final-editor inputs, phase/tool alignment, provider-independent instruction selection, and one-definition tool contracts. These are deterministic engineering checks, not proof of model reasoning quality.

An old R1 experiment patch test now uses its own frozen old paragraph; its driver still rejects today's changed prompt instead of silently replaying an old paid trial. The product assertions are retained.

Local targeted validation: 90 tests passed; compile and architecture checks passed. Editable installation without fetching dependencies succeeded. Local full dependency installation was unavailable; use the repository's Windows self-hosted runner for dependency-complete checks. Record its exact run, outcome and evidence separately. No all-provider live certification follows from shared prompt selection.

The package remains `continuous-research-v2`; the added basis-only patch mode is additive. In-flight native sessions are bound to their original request/tool identities, so do not hot-swap live work or rewrite persisted runtime identities. Stop cleanly before updating and create a new study for new-prompt acceptance.
