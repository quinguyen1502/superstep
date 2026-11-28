# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0363
- Task ID: TASK-0374
- QA Owner: Codex
- Created: 2026-11-28
- Updated: 2026-11-28
- Outcome: passed local acceptance and reviewed-head CI

## Acceptance Coverage

- Real Python and TypeScript exports run identical Formula cases through Connected and standalone bindings on SQLite and PostgreSQL 17. The shared conformance cases passed in the server compiler and generated TypeScript interpreter. Deno type-checked the generated project.
- Runtime Agent reads return the typed calculated projection and respect configured filters, including rows with missing operands. Dataset node tests verify the read-only write mapping, dry run, and recalculation on a permitted write. A connected definition change rejects an older export with a binding mismatch.
- Formula snapshots are recalculated from inputs. Existing rows survive repeated setup, and a write receipt replays without another write. Auto-number and Unicode inputs, division-by-zero diagnostics, no-op revisions, write-only identifiers, and aggregates are covered across runtimes.
- Both generated runtimes add the nullable diagnostic column to older standalone databases under their existing setup lock. Tests verify idempotence and preserve rows, revisions and receipts. The operator guide records the setup and rollback steps.
- Public OpenAPI and AsyncAPI drift, backend layer rules, API envelopes, Factory hygiene and artifact IDs passed.

## Results

- Broad Python 3.12 run covering Dataset, exports and backend contracts: 421 passed, two Redis cases skipped. Both skipped cases passed separately with Redis 7, including writes from another process.
- Repeated the nine targeted generated evaluator, project and migration cases on the final diff after reserving the Python helper names. All passed.

## Gaps And Follow-Up

- [PR #435](https://github.com/quinguyen1502/superstep/pull/435/checks) passed 24 checks on reviewed head `84d9a65b`. Require the same result on the final state-only head before merge. Formula authoring remains opt-in. Relation work remains tracked separately in the approved plan.

## QA Decision

Local acceptance and reviewed-head CI passed. Owner approved integration, gated by CI on the final head.
