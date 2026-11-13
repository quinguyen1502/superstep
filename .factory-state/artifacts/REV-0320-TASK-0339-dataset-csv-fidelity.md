# Review

## Metadata

- Project: superstep
- Review ID: REV-0320
- Task ID: TASK-0339
- Reviewer: implementation review
- Created: 2026-11-14
- Updated: 2026-11-14
- Outcome: approved for QA

## Review Scope

Diff for CSV type inference, the formula guard round trip, and required revisions on Studio deletes against REQ-0100, PLAN-0018, and the TASK-0339 acceptance criteria. Reviewed `services/dataset_csv.py`, the delete routes, the CSV dialog, handbook, and changelog.

## Reference Artifacts

- REQ-0100-dataset-phase1-fixes.md
- PLAN-0018-dataset-phase1-fixes.md
- DES-0007-datasets.md
- ARCH-0003-datasets.md
- docs/backend-architecture.md

## Findings

### Blocking

- None.

### Non-Blocking

- The task lists `=`, `+`, `-`, `@`, tab, and carriage return for the guard. Import removes the guard exactly when export adds it, which also covers full-width signs, spaces before a formula sign, and line feed. This keeps the round trip lossless; a value that already starts with an apostrophe before a formula sign gets a second apostrophe on export.
- A hand-written CSV cell like `'=x` is read as `=x`, the same as a spreadsheet shows it.
- Column DELETE also requires `revision`. The task names row and dataset DELETE; the objective says Studio deletes always check the revision, and the Studio already sends it for all three.
- Inference only changes suggestions. Importing into an existing Number column still reads `007` as 7.

## Standards And Architecture Alignment

- `_guarded` is the one rule for export and import. Inference treats any guarded value as text, so `'-5` stays text.
- Delete routes use a required `revision` query parameter; a missing one fails request validation (422 `VALIDATION_ERROR`), a stale one keeps `DATASET_ROW_CONFLICT` or `DATASET_SCHEMA_CONFLICT`.
- Public routes, workflow `delete_row`, and the public OpenAPI file are unchanged.

## Design Alignment

- The new-dataset schema step in the CSV dialog explains in English and Vietnamese why codes are read as text and how to change it. The preview shows values without the guard.

## Test Coverage Review

- `tests/test_dataset_csv.py` covers export then import with `00123`, `+84901234567`, `=SUM(A1)`, `-5`, a value that already starts with the guard, an apostrophe inside text, and a 16-digit value; inference for codes, phone numbers, and long digit runs next to real numbers; import into a Number column; and missing and stale revisions on row, column, and dataset DELETE.
- Playwright `e2e/dataset-csv.spec.ts` covers the hint, a preview without the guard, changing an inferred Text column to Number, and an exported file that matches the source.

## Risk Review

- PAT scripts that delete without `revision` now get 422. The changelog states it.

## Required Fixes

- None.

## Approval Decision

Approved for QA.
