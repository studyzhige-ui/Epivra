# Source references and acceptance map

This refactor is a Python implementation of the approved research semantics using
mechanisms inspected in the following pinned references. It does not claim to copy
the complete Rust/TypeScript runtime or reproduce every feature of either product.
No reference repository files or third-party source license headers are removed.

## Pinned engineering references

- Codex `5c5308fc9a9ee789049d646ef11e5400384b9c6f`:
  `codex-rs/core/src/tools/handlers/multi_agents.rs`, `multi_agents/wait.rs`:
  optional collaboration, inherited execution policy, completion-driven waiting.
  `tools/handlers/plan.rs`: separate planning interface from actual execution.
  `tools/handlers/apply_patch.rs`: model-selected edits with deterministic apply
  feedback. Epivra uses exact substitutions plus immutable base-CAS, not a literal
  port of Codex's multi-file patch parser or its full tool surface.
- User-provided Claude Code snapshot `58231dcce408f805c645cfbc352d2876b517223b`:
  `QueryEngine.ts`, `tools/AgentTool/agentToolUtils.ts`, `tools/AgentTool/prompt.ts`:
  persistent loop, explicit effective tools, delegated question/context and real
  completion notifications instead of fabricated sub-agent results.
  `tools/FileEditTool/FileEditTool.ts`: read/change-state checks before edits.
  Epivra does not copy `behavior: ask`: after research approval, errors return to
  the owner, not to a second user-approval prompt. The supplied snapshot is not
  asserted to be the current closed-source product.
- `eval/benchmark-10/gemini-17.md`, `gemini-19.md`, `gemini-02.md`:
  user-facing research routes enumerate inquiries/material collection/comparison,
  not predetermined answers. GPT archives are retained as actually captured;
  missing standalone approval plans are not reverse-engineered from reports.

Primary upstreams:
https://github.com/openai/codex/tree/5c5308fc9a9ee789049d646ef11e5400384b9c6f
https://github.com/studyzhige-ui/claude-code-source-private/tree/58231dcce408f805c645cfbc352d2876b517223b

## User handbook mechanism map

Basis: `studyzhige-ui/ai-application-interview-handbook`,
`curriculum/09-agent/README.md` (24 chapter headings as read during refactor).
The map is an inspection guide, **not** a declaration that all interviews/features
are automatically passed. Source paths and tests are concrete entry points.

| Chapters | Mechanism and inspection/test entry |
|---|---|
| 01 System / 02 Autonomy | `application.py`, `harness.py`; continuous_owner/research_workspace tests: owner directly researches/authors, helpers optional, no fixed stage chain |
| 03 Loop/scopes | `storage.py` work/step/operation, `ResearchService`; execution/runtime_lifecycle tests |
| 04 Tool contract / 05 Registry | BUILTINS, Tool roles/permissions, validation; argument_checks/harness_boundaries tests; new research tools have model-visible parameter limits and semantic error feedback |
| 06 Execution/failure | admitted/invoked/settled operation ledger; provider_recovery/execution tests; ambiguous external calls not blindly repeated |
| 07 Concurrency/cancel | `scheduling.py`, `application.py`, `analysis_runtime.py`; application/usage_scheduling/analysis tests; shared document uses transactional base-CAS |
| 08 Planning/control | route approval in Store, owner-only tool surface before/after approval; continuous_owner tests; no default research budget or hypotheses |
| 09 Context/cache | `context.py`, adapters actual wire delivery; read_delivery/context_accounting tests; canonical evidence and draft refs paginated |
| 10 Compaction | memory projection/old source refill; long_runtime/context_pages tests; same study question/permissions remain mandatory |
| 11 Memory | work memory revisions and original material, not claimed universal lifelong learning; long_runtime/role_handoffs tests |
| 12 Persistence / 13 Resume | Store transactions/process lock/version identity, source snapshots; execution/request_storage/research_workspace tests; incompatible old runtime not silently resumed |
| 14 Permissions / 15 Injection | no source instruction authority, allowlisted tools/paths/network, private protocol boundary; public_sources/workspace/harness_boundaries tests; no post-approval user questions is not permission bypass |
| 16 MCP | existing mcp_client/mcp_tools/mcp_server; mcp tests and optional extra; preserved rather than replaced by bespoke protocol |
| 17 Skills/hooks/extensions | explicit Tool extension registry exists; no fabricated parity with all coding-agent hook/plugin features; arbitrary plugin marketplace is not needed for this product slice |
| 18 Routing/provider | provider-native adapters, versioned settings, visible failures; models/native_models/provider_recovery tests; no hidden quality downgrade on failure |
| 19 Multi-Agent/A2A | optional internal helpers, exact handoff originals, completion waits; application/role_handoffs tests; no claim of external A2A interoperability or recursive agent swarms |
| 20 Trace/replay | diagnostics/operation timing, private vs public exports, exact artifact versions; read_redundancy/operation_timing tests; replay structural operations, never unknown external actions |
| 21 Evaluation | closed/open cases, scripted contract tests and paid evidence separately; no Benchmark-10 without separate approval; no success labels overriding final facts |
| 22 Coding delivery | immutable manuscript plus exact edits adapted from coding-agent mechanisms; research_workspace tests; Epivra is not marketed as a general coding IDE |
| 23 Production runtime | process lock/SQLite atomicity, cancellation, public UI/CLI/MCP and wheel checks; web_integration/dev_check tests; not a distributed SaaS reliability certification |
| 24 Framework choices | keep existing small Python runtime, no forced LangGraph migration or new backend framework; document concrete safety and capability tradeoffs |

Python coverage additionally follows `curriculum/01-python`: mutable ownership and
copy semantics (immutable Artifact + copies), iterators and bounded paging,
exceptions/context-manager cleanup, JSON semantic validation, thread/process/
coroutine separation, locks/transactions, subprocess cancellation and restart.
The implementation uses asynchronous I/O for provider requests; CPU/external
analysis stays in existing isolated execution. Tests and typing are mechanisms,
not a promise of mastery of every hypothetical Python question.
