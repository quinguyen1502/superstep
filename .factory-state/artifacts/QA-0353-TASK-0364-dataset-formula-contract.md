# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0353
- Task ID: TASK-0364
- QA Owner: Codex
- Created: 2026-11-21
- Updated: 2026-11-21
- Outcome: Pass

## Validation Scope

Verified the bounded Python Formula contract and existing Dataset behavior. Exercised storage and Relation concurrency in disposable SQLite and PostgreSQL 17 databases with the application's existing Dataset writer lock.

## Acceptance Criteria Coverage

| Criterion | Evidence | Result |
| --- | --- | --- |
| Typed evaluation and syntax | Shared contract fixture and `test_dataset_formula.py` exercise types, arithmetic, comparisons, text, IF, malformed syntax and input/output bounds | Pass |
| Deterministic dependencies, nulls and diagnostics | Reverse-order dependencies, cycles, missing cells, lazy IF, overflow, division by zero and stale stored values have executable cases | Pass |
| Storage feasibility | Evaluated and backfilled two dependent formulas in bounded 500-row pages under one transaction. Verified numeric JSON sorting, persisted row and schema revisions, and restoration of original values and revisions after an explicit rollback | Pass for prototype |
| Concurrent Relation integrity | Racing a link against target deletion rejected the delete when linking committed first and rejected the link when deletion committed first, on both engines | Pass for prototype |
| Dataset and layer regression coverage | Formula, Dataset schema, rows, batch, CSV, aggregates, filter groups, summaries, API envelope and layer suite with SQLite and PostgreSQL enabled | 128 passed |

## Performance Evidence

Two arithmetic formulas on short rows in disposable local databases. The transaction time includes existing writer-lock acquisition, paged ORM reads and writes, the row-size check, revision changes and commit. The sorted read used the materialized numeric output to sort and return 50 rows.

| Engine | Rows | Evaluation only | Backfill transaction | Sorted page |
| --- | ---: | ---: | ---: | ---: |
| SQLite | 10,000 | 0.046 s | 0.584 s | 0.019 s |
| SQLite | 25,000 | 0.110 s | 1.504 s | 0.055 s |
| PostgreSQL 17 | 10,000 | 0.044 s | 0.991 s | 0.010 s |
| PostgreSQL 17 | 25,000 | 0.109 s | 2.338 s | 0.019 s |

These values provide a local feasibility baseline. Production migration tests still need representative row widths, diagnostic metadata, writer contention and many-formula worst cases.

## Gaps And Residual Risk

- The prototype did not change the application migration history. The actual migration, connected grants, mixed old-client behavior and rollback operations remain in subsequent tasks.
- The contract includes test vectors for TypeScript. TypeScript parity and UI behavior are separate milestones.

## QA Outcome

Pass for review of the contract, evaluator and storage feasibility.
