# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0354
- Task ID: TASK-0365
- QA Owner: Codex
- Created: 2026-11-21
- Updated: 2026-11-21
- Outcome: Pass

## Validation Scope

Tested SQLite and disposable PostgreSQL 17 with actual application migrations, retained legacy rows and real Dataset service calls.

## Acceptance Criteria Coverage

| Criterion | Evidence | Result |
| --- | --- | --- |
| Additive upgrade and guarded downgrade | The migration test takes a populated Dataset through the preceding revision and back. Active formulas block downgrade. Archiving the formula enables the downgrade and leaves the source data intact | Pass |
| Consistent mutations and rollback | Tests cover single writes, upsert, batch append and undo, CSV mapping and import, auto-number, receipt replay, workflow writes and simulated writes. A concurrent formula definition edit and row write leave a coherent result. A backfill error after a flushed page rolls back the schema and rows | Pass |
| Typed read behavior and permissions | Tests cover sorting, filtering, summaries, projected diagnostics, calculation error recovery, Viewer access, denied unrelated users, write-only tokens and legacy connected contracts. Direct computed writes and deletion of dependencies are refused | Pass |
| Rollout and export compatibility | Off by default. Existing formulas still recalculate when the flag is off. Ordinary API/export regression tests pass and project export rejects formulas until standalone writers support them | Pass |
| Backend and locale regression | 176 tests passed and two environment-specific tests skipped with SQLite and PostgreSQL enabled. All five frontend locale checks passed | Pass |

## Performance Evidence

Measured both schema add operations through the actual service, with 156-byte notes in each row. The second Formula depends on the first and produces a division-by-zero diagnostic for one in sixteen rows. Times include lock acquisition, paged persistence, revision updates and commit.

| Engine | Rows | First Formula | Dependent Formula | Sorted page of 50 |
| --- | ---: | ---: | ---: | ---: |
| SQLite | 10,000 | 0.593 s | 0.708 s | 0.024 s |
| SQLite | 25,000 | 1.490 s | 1.765 s | 0.063 s |
| PostgreSQL 17 | 10,000 | 0.895 s | 1.690 s | 0.011 s |
| PostgreSQL 17 | 25,000 | 2.429 s | 4.183 s | 0.020 s |

The 25,000-row runs each persisted and verified 1,563 diagnostics. These local timings characterize two representative formulas and are not a bound for arbitrary expression mixes.

## Gaps And Residual Risk

The Studio and standalone export slices, end-to-end accessibility, and worst-case release measurements remain future acceptance work. No production database was migrated.

## QA Outcome

Pass for review of the Formula persistence slice.
