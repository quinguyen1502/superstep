# Task

## Metadata

- Project: superstep
- Task ID: TASK-0333
- Title: Keep only identifiers in Dataset write receipts and expire them
- Status: backlog
- Owner: Thái Quí Nguyễn
- Created: 2026-11-13
- Updated: 2026-11-13
- Requirement IDs: REQ-0100
- Design IDs: DES-0007
- Architecture IDs: ARCH-0003
- Decision IDs: —
- Plan: PLAN-0018
- Phase: Fix
- Priority: P1
- Size: M

## Objective

Write receipts hold identifiers and outcome only, existing receipts lose their row copies, and old receipts are removed on a schedule.

## Scope

### In Scope

- Receipt `result` shape `{row_id, inserted, revision}` (and `deleted` for `delete_row`); replay rebuilds the response by reading the current row and applying the caller's current permission and projection. When the row is gone, replay returns the identifiers without `values`.
- Alembic data migration that rewrites existing receipts to the new shape on SQLite and PostgreSQL, in batches.
- Retention: `STUDIO_DATASET_RECEIPT_DAYS` (default 30) removed by the existing worker retention loop; index on `created` if needed.
- Receipts are not removed when a row is deleted, so a retried insert still replays instead of inserting again; the handbook states the retry window.

### Out Of Scope

- Standalone export receipt tables (TASK-0343).
- Changing receipt identity or fingerprint rules.

## Inputs

- `repositories/dataset_rows.py` receipt writes and replays; `models/dataset_receipt.py`; worker retention loop.

## Related Artifacts

- Requirements: [REQ-0100](../../artifacts/REQ-0100-dataset-phase1-fixes.md), [REQ-0097](../../artifacts/REQ-0097-datasets.md), [REQ-0099](../../artifacts/REQ-0099-dataset-writes.md)
- Design: [DES-0007](../../artifacts/DES-0007-datasets.md)
- Architecture: [ARCH-0003](../../artifacts/ARCH-0003-datasets.md)
- Plan: [PLAN-0018](../../artifacts/PLAN-0018-dataset-phase1-fixes.md)

## Dependencies

- TASK-0332 merged (replay uses its permission-aware result function).

## Acceptance Criteria

- After migration no receipt contains a cell value; a test scans every receipt.
- Replay returns the same `row.id` and `inserted` as the first call; values come from the current row and respect the caller's read permission.
- A retried insert after the row was deleted does not create a new row within the retention window.
- Receipts older than the retention window are removed; newer ones replay.

## Tests

- Migration up/down on SQLite and PostgreSQL with seeded old-shape receipts.
- Replay after update, after delete, and after the caller loses read.
- Retention loop test with a fake clock.

## Validation Plan

- Targeted backend tests (`pytest`) on SQLite and PostgreSQL, `tests/test_layers.py` and `tests/test_api_envelope.py`; where the frontend is touched, `npm run lint`, `npm run build`, `npm test`, locale parity and the matching Playwright spec.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts on the task's own PR; all required CI green before merge.

## Open Questions

- Retention default: 30 days (recommended) or tie to run history retention.

## Activity Log

- 2026-11-13: Created by planning on branch `factory/plan-dataset-fixes-phase3`. No implementation. Stays in backlog until the owner accepts REQ-0100 and PLAN-0018.

## Handoff Notes

- Use branch `factory/task-0333-dataset-receipt-minimization` from `develop` when implementation begins.
