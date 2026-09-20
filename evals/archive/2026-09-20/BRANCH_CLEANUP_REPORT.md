# Branch cleanup report — 2026-09-20

## Final state

Branch cleanup is complete. The repository now has exactly two long-lived branches:

- `main` — stable baseline, unchanged at `51d039dfc6ffdb88fb5768f1add72535029c2bd7`.
- `improve/epivra-optimization` — the single optimization development line.

PR #2 and PR #3 were closed without merge because their heads are fully contained by the unified optimization line. PR #4 remains open as Draft and is the only optimization review/evidence entry. PR #1 remains closed/merged historical record.

## Archived before deletion

Two experimental branches contained unique negative/partial evidence, so their results were copied into the unified branch before deletion:

- `evals/archive/2026-09-20/objective-led-research.md`
- `evals/archive/2026-09-20/review-decision.md`

The Objective-led Lead experiment reached publication in 654.533 seconds and reduced calls/tokens on that one task, but failed independent quality review. The reviewer-decision experiment improved one negative control and preserved the qualified positive control, but still accepted the real SQLite report despite independently confirmed evidence-strength defects. Neither experimental prompt is part of the unified production baseline.

## Deleted branches

1. `chore/archive-public-evidence-20260919`
2. `chore/prepare-read-contracts-20260919`
3. `chore/prepare-read-type-20260919`
4. `chore/prepare-report-receipt-20260919`
5. `chore/secret-smoke-20260919`
6. `chore/verify-audit-provenance-20260919`
7. `codex/research-runtime-hardening`
8. `experiment/objective-led-research-20260920`
9. `experiment/review-decision-20260920`
10. `improve/live-validation-20260919`
11. `improve/read-contracts-20260919`
12. `stage/agent-capabilities-20260920`
13. `stage/read-delivery-20260920`

## Safety behavior

Cleanup was performed with an explicit allow-list and exact expected head SHAs. The workflow first verified **all** 13 refs and verified PR #2/#3 were already closed; deletion began only after the full verification phase passed.

The first cleanup run (`35502898188`) stopped before deleting any branch because one expected SHA had a one-character transcription mismatch. After correcting the audit manifest, run `35503050646` completed successfully and deleted all 13 approved branches. This was a safety check working as intended rather than a partial cleanup.

The one-off cleanup workflow is removed in the same finalization commit as this report, so it cannot be re-run accidentally.

## Rule going forward

Normal optimization work continues only on `improve/epivra-optimization`. Temporary experiment branches may be created only when isolation is necessary; at experiment end, a successful generalizable change is integrated into the unified line, while a failed experiment keeps only the evidence/result archive and the temporary branch is deleted.
