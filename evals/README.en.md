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
