# Development execution and recovery


Read `.github/development-state.json` and this document before continuing an interrupted development task. Verify the live branch head; old chat claims and blob receipts are not proof of a published commit.

- Work only on `improve/epivra-optimization`; leave `main` and Draft PR #4 unmerged. Do not start another product phase while repairing development execution.
- Use one complete local worktree tied to an audited commit. Inspect the diff and run available local checks before writing. Preflight dependencies; never repeat an unavailable install silently or label partial checks as a full pass.
- Checkpoint one cohesive change at a time. Store ordinary source files, not an opaque compressed mega-patch. Upload blobs/tree, create a commit with the observed parent, then update the branch with `force=false`. Read the branch back. A blob alone is not an implemented feature.
- If a write result is lost, reconcile current head, tree and changed-file hashes before any retry. A stale branch requires reconciliation, not force push. Preserve uncommitted work in an explicit patch/archive with hashes before a session ends; container persistence is not guaranteed.
- Validation uses `tools/dev_check.py`. Keep stdout short and full per-gate logs in artifacts. Read a completed result once; do not busy-poll a running job. Pending means pending; never promise unscheduled background work.
- Never blindly rerun unknown paid operations. No paid research is part of development execution repair. Benchmark-10 or comparable large batches still require separate approval.
- Keep research product rules: route, not hypothesis or predetermined answer; one initial approval and no post-approval user questions; complete research owner with optional helpers; no default report length limit. Runtime safety boundaries are not disabled by autonomous operation.


This is tooling for the developer/assistant, not a new Epivra Agent workflow. It does not alter roles, prompts, research budgets, or report length.

## Established facts and unresolved causes

The upstream baseline for this repair is `046ab4a80a8251c651f7bd39987e9a9b262d958a`, tree `e3ae270777c1b2b3653feb6e9d0d27c6b2bd8773`. Its previous change only extended the committed-source snapshot workflow. The prior large blob `820e2d2962f74096af448b4aa0f429ab7515a5c2` is NOT a validated source commit on this branch. Do not apply it automatically.

The downloaded snapshot ZIP SHA-256 is `6c0b194cddb89d0504ba9b2881fd59f6b918b2e05b1128551ae03bf01fa625d4`; source.tar SHA-256 is `6a3d2c078f54ee3a7ece21aa2925653727689a9ebc16e97cb2a8ea4e589c84cd`. All 272 file blobs and the entire Git tree were verified before local editing. A local mirror commit is not the upstream commit; record both accurately.

Observed execution problems: long chains of sequential remote reads/writes, repeated busy polling, oversized encoded patch transfers without a published checkpoint, and recovery depending on chat history. These are controllable reliability risks, NOT proven causes of ChatGPT's internal `Thinking failed` errors. There is no platform traceback proving a context overflow, timeout or payload fault.

The current conversation container has Python 3.13.5 and Git, but lacked questionary/MCP/Ruff/mypy/build. An attempted isolated install failed on DNS resolution. Streaming exec/PTY was also unavailable. Stop retrying these paths; perform stdlib/local checks here and use the authorized Windows runner for dependency-complete validation. Neither limitation implies GitHub is read-only.

## Stable workflow

1. Read the live optimization head and recovery state. Check unresolved CI/write identities before any work. Never replay an unattached blob by memory.
2. Restore a full, hash-verified worktree; make one cohesive change. Save an explicit patch, changed-file hashes and base SHA outside the worktree as a portable recovery artifact.
3. `python tools/dev_check.py preflight --profile full` lists missing dependencies without installing or calling a provider. In a constrained container, use `--profile smoke` for the tooling's own tests, not as product acceptance.
4. `python tools/dev_check.py run --profile full --output <fresh-evidence-directory>` records the source digest, local Git head, Python/platform, each command, timestamps, return code and log hash. A fresh output path is mandatory. Credentials with common key/token/secret/password names (including numbered names) are removed from child environments. This is not an OS network sandbox or a guarantee against hardcoded secrets in test code.
5. `python tools/dev_check.py inspect --output <evidence-directory>` verifies input and log hashes and the complete expected gate list. Changed input, missing dependencies, timeout, incomplete execution or one failed gate cannot count as success. A hard kill may leave `running`; that means unfinished, not implicitly safe to resume.
6. Publish normal Git blobs/tree/commit, then a non-force ref update after checking the live head. Re-read head after the write. Stop on divergence or ambiguous results. Do not describe an uploaded blob as committed code.
7. CI executes the same driver, uploads per-gate evidence even on ordinary failure and removes only its own temporary environment. Use exact commit/run/attempt IDs. Do not submit an unrelated commit to trigger repeated CI. Do not fetch logs every few seconds while a job runs. If the session ends, record pending and inspect that original run on resume.

The driver terminates its process tree on a handled timeout/interruption. It cannot guarantee cleanup after power loss, forced host termination or artifact-service failure. The source checkpoint and run identity remain the recovery anchors; a local path alone is not durable across sessions.

## Completion boundary

Do not promise to fix platform internals or prevent every future interruption. Completed repair means a verified development checkpoint, tested failure/timeout/staleness handling, and a real remote read/write/validation path. Product development resumes only from that known state. Keep platform diagnosis unresolved absent logs.

Official reference: GitHub non-force ref updates are fast-forward-only (`https://docs.github.com/en/rest/git/refs`). OpenAI's troubleshooting guide lists several possible failure sources and diagnostic steps; it does not identify this conversation's cause (`https://help.openai.com/en/articles/7996703-troubleshooting-chatgpt-error-messages`).
