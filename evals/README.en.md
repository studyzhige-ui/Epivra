# Research validation tools

**English** · [简体中文](README.md)

Synthetic cases here are diagnostic and regression tools, not a public benchmark score. Public research benchmarks have not yet been integrated. Report quality, role behavior, review reasoning, and engineering failures must be interpreted separately.

```powershell
# Engineering checks: no model or search calls
python -m unittest discover -s tests
python tools/check_architecture.py
ruff check src tests tools evals
# Optional deterministic frontend checks require Node.js; the app does not
node tests/web_reader.cjs
node tests/web_status.cjs
node tests/web_usage.cjs
```

GitHub Actions additionally runs the configured mypy checks and builds a wheel on its supported Python/OS matrix. The Python 3.13 base-install jobs also install the built wheel in a fresh environment outside the checkout, checking dependencies, import location, packaged assets, and CLI entry point. This checks the base wheel and resolved dependencies, not every dependency's minimum version or every extension.

## Online diagnostics

The commands below call model APIs and consume provider quota. Use a new run ID for a changed model, tool contract, fixture, or implementation. Successful recorded calls are replayed; do not resend old ledger operations. Private provider records remain in ignored local directories.

```powershell
# Small report review cases
python tools/run_review_eval.py --run-id review-version
# Positive/negative mechanism cases
python tools/run_review_eval.py --run-id mechanisms-version --mechanisms
# Selected mechanism cases
python tools/run_review_eval.py --run-id selected-version --mechanisms --only M02-positive M13-positive
# Complete small tasks using supplied materials
python tools/run_closed_loop_eval.py --case archive --run-id archive-version
python tools/run_closed_loop_eval.py --case decision --run-id decision-version
python tools/run_closed_loop_eval.py --case measurement --run-id measurement-version
```

`--assess-only` on closed-loop runs exports saved `trace.json`, `result.json`, and any published `report.md`. It does not automatically grade semantic quality. Test fixtures may auto-approve strategies; normal product use still requires user approval.

## Reuse saved reports and isolate roles

```powershell
python tools/run_review_eval.py --run-id report-version --report-db .epivra/prior-run/research.db
python tools/run_repair_eval.py --run-id repair-version --source-db .epivra/review-report-version/research.db
python tools/run_role_diagnostic.py --run-id delegation-version --trace .epivra/prior-run/trace.json --variant direct
python tools/run_role_diagnostic.py --run-id delegation-control --trace .epivra/prior-run/trace.json --variant delegated
```

Role diagnostics intentionally do not run the full research process; no publication is not a failure. Writer comparisons use `--variant writer-reference` / `writer-actual` plus `--reference evals/role_calibration.json`. Source identity, fixture fingerprints, and material consistency are checked. One run per condition cannot establish causality or success rates.

## What the fixtures establish

`mechanism_cases.py` supplies 36 short positive/negative reports across 18 mechanisms. They calibrate reviewing; they do not prove exploration, redirection, collaboration, or recovery occurred. `closed_loop_cases.json` supplies small complete tasks with four synthetic materials per task. `research_scenarios/` contains input corpora and separate assessment data; grading labels are not injected into the agent context.

`research_case.py` can generate 30 or 100 source files, including repeated origins and critical independent evidence. These are fixture sizes, not a product source limit. Automated coverage checks do not establish semantic correctness or long-document competence.

`tools/run_benchmark10.py` is a Windows batch diagnostic runner: cases run sequentially while retaining normal within-study concurrency. Supply your own JSONL file using `--queries path/to/cases.jsonl`; each line contains an integer `id` and a string `prompt`. Start with `python tools/run_benchmark10.py --run-id batch-version --queries path/to/cases.jsonl`; inspect saved status with `--run-id batch-version --status`. Starting consumes model/search quota and automatically approves generated strategies, so use explicitly authorized diagnostic cases only. Code and inputs are frozen into the run identity; do not silently change versions under the same run ID. The runner includes no private case list or public leaderboard score, and publication does not establish quality.

Assess decisive conclusions and evidence before stylistic preferences. A rejected report with incorrect rejection reasoning is not a successful review. Mark absent behavior as untested, not automatically passed or failed. Preserve disputed judgments for human review, and keep holdout tasks out of debugging. Raw model self-evaluation is not ground truth.

The [analysis fixture](analysis/README.md) documents the small public Iris dataset used for deterministic computation and artifact handoff checks.

## Small live checks in GitHub Actions

`Small live evaluation` reuses the existing Harness reviewer and four-material closed-loop tools. It does not implement another research loop. Only a committed change to `evals/live-request.json` on the designated development branch or `eval/**` triggers paid checks; ordinary code/document commits and PR offline validation do not. Manual workflow dispatch is also available. Provider secrets are injected only into the execution step, not dependency installation. `TAVILY_API_KEY` may contain a comma-separated pool of authorized keys.

Modes are `providers`, `review` (1–4 existing calibration cases), or `closed` (one existing small four-material case). `probe_providers` adds one tiny completion and a real search through each configured Tavily slot; probe usage is separate from research-ledger usage. Do not repeat successful provider probes unnecessarily.

Maintenance authorization as of 2026-09-19 permits ordinary small paid tests. Benchmark-10 and comparably expensive evaluations require renewed explicit owner approval; splitting a large batch must not bypass it. This entry point has no benchmark mode. Selection limits and the GitHub job deadline bound this diagnostic job, not normal product research calls, tokens, cost, or duration.

Paid attempts cannot be blindly rerun. Inspect prior evidence, then commit an explicit new request. A new request is not a continuation of the prior study and must not replay unknown operations. Ephemeral runners do not retain the research database; cross-runner operation recovery is not promised. Forced platform termination may leave incomplete artifacts and is not a pass.

Only explicitly projected and redacted domain artifacts, sources, public review reasons, usage, and actual-input receipts are uploaded. No `.env`, research database, HTTP headers, or native private model protocol bodies leave the runner. Receipts can be joined with original artifacts but are not full native transcripts. This entry point is for existing synthetic corpora, not unreviewed uploads of sensitive real materials.

`execution_pass` means the selected path completed. Reviewer `decision_gate` only compares existing labels. `semantic_acceptance` remains pending independent review. Missing results, errors, unknown operations, or label mismatches cause a nonzero exit, even when an underlying script exits normally. Investigate mismatches against the task, corpus, draft, scope, and reason: a good next research action need not be an acceptable final report. Do not hide disputed labels by weakening production prompts or silently relabeling cases.

## General research-quality rubric and change policy

The following is an **Epivra evaluation convention**, not a production prompt or an official DeepResearch Bench score. Criteria are general, but judgments must be anchored to the task and original evidence.

| Dimension | What to examine |
|---|---|
| Task and coverage | The core question, purpose, and explicit requirements are answered; convenient tangents do not displace important branches |
| Facts and numbers | Entities, dates, values, units, and calculations match evidence; observations, attributed statements, and inferences remain distinct |
| Evidence support | Cited passages support the actual claims and can be located; republications are not independent corroboration; inaccessible is not the same as unsupported |
| Analysis and synthesis | Methods fit the question, comparisons use compatible definitions, and inferences follow from evidence rather than stacked summaries |
| Conditions and calibration | Counterevidence, applicability limits, and revisions change conclusions when appropriate; sufficient evidence still receives a definite useful answer |
| Usability and presentation | Answers and evidence are easy to find at the requested level of detail; no bonus for verbosity, fixed sections, word count, or citation count |

Use optional per-dimension anchors 0–4: 0 invalidates the core result; 1 has major defects; 2 is partly usable but needs substantive revision; 3 meets the task with at most minor issues; 4 additionally provides evidence-backed high-value analysis. Use `not_evaluated` for unexamined or unresolved items, not a score. Attach report/source locations and the practical consequence of each judgment. Scores are calibratable conventions, not proofs; no default aggregate hides decisive errors.

Track decisive errors separately: false key facts, fabricated support, unsupported causal or extrapolated conclusions, obsolete premises still driving recommendations, or unwarranted refusal despite sufficient evidence. Explain how the problem changes the answer; do not promote every stylistic difference to a blocker. Formatting cannot offset a substantive error. Wrong review reasons, false rejections, and report errors are separate observations. Automated grades require independent human calibration; AI review is not human acceptance.

**Engineering fixes** may address reproducible protocol, cancellation, recovery, capacity, or security defects, with ordinary-path and negative regression tests. **Kernel, role, and prompt changes** need more than one disappointing report: trace public inputs, tools, handoffs, outputs, and review reasons; propose a mechanism independent of case names; compare controlled configurations across contexts and opposite-direction controls, and retain tasks unused during tuning. One improvement is not a stable gain. Without generalization evidence, keep the diagnosis rather than adding topic branches, mandatory critics, or repeated prohibitions.

Prefer primary official documentation before prompt changes, recording the precise principle, applicability, and validation. Official advice motivates a design; it does not establish effectiveness on Epivra's configured model. Product boundaries and existing contracts take precedence over another project's feature list.

## Primary references and limits

- [OpenAI evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices): separate objectives, data, metrics, and comparisons; calibrate with human judgments and check position/verbosity bias.
- [OpenAI prompt engineering](https://developers.openai.com/api/docs/guides/prompt-engineering): clear instructions, context, and testable iteration; verify model-specific behavior.
- [Anthropic success criteria and evaluations](https://platform.claude.com/docs/en/test-and-evaluate/develop-tests): specific, measurable, purpose-relevant criteria; recognize ambiguous evaluation cases.
- [Google prompt design strategies](https://ai.google.dev/gemini-api/docs/prompting-strategies): clear context/examples; excessive examples can overfit responses. Do not embed single-task answers into general prompts.
- [DeepResearch Bench, pinned revision](https://github.com/Ayanami0730/deep_research_bench/blob/469cce54ea7f6a63c163d3d9fec879cf289ec484/README.md): RACE evaluates comprehensiveness, insight/depth, instruction-following, and readability with task-adaptive criteria. FACT separately verifies support and measures citation accuracy/effective citations. Supported-citation counts do not establish analytical quality; reference reports are not unquestionable truth. Do not label custom results official scores or combine incompatible judges/versions.
- [Codex tool-runtime snapshot](https://github.com/openai/codex/blob/e269f2164cbb9f499e4f22301c393500e2a831f3/codex-rs/core/src/tools/parallel.rs): preserve invocation context and execution records; not a reason to migrate language/framework.
- [User-supplied Claude tool-result snapshot](https://github.com/studyzhige-ui/claude-code-source-private/blob/58231dcce408f805c645cfbc352d2876b517223b/utils/toolResultStorage.ts): bounded readers must not loop through persisted-output handles; this snapshot is not the entire current official product.
- [DeerFlow](https://github.com/bytedance/deer-flow): the inspected mainline is the rewritten 2.0 general harness; the original research framework is on `main-1.x`. Record branch/commit when borrowing a mechanism, not fixed report sections, mandatory lengths, or domain-specific style templates.

References checked 2026-09-19. Engineering checks, model behavior, semantic report quality, official benchmarks, and release claims remain separate evidence layers.
