# Review

## Metadata

- Project: superstep
- Review ID: REV-0314
- Task ID: TASK-0330
- Reviewer: implementation review
- Created: 2026-11-13
- Updated: 2026-11-13
- Outcome: approved for QA

## Review Scope

Diff for TypeScript export Delete row and Agent writes against REQ-0099, DEC-0098, ARCH-0003, and the TASK-0330 acceptance criteria. The Python runtime, snapshots, and handbook were checked to stay unchanged.

## Reference Artifacts

- REQ-0099-dataset-writes.md
- DEC-0098-dataset-delete-and-public.md
- ARCH-0003-datasets.md
- PLAN-0017-dataset-writes.md
- docs/dataset-export.md

## Findings

### Blocking

- None.

### Non-Blocking

- `datasetAgent` is now exported from the generated module, next to `datasetCall`. The probe tests call it directly, and a deployment can reuse it.
- The exported TypeScript mock model now fills enum parameters and Dataset write values, like the Studio and Python mocks.

## Standards And Architecture Alignment

- `datasetDelete` runs inside the write transaction that takes the writer lock. It checks the receipt before the row, removes the row and its unique keys, and stores `{deleted, row_id}`. A missing row fails before the receipt insert, so no receipt is stored.
- The fingerprint has the same shape as the Python runtime: operation, fields, and the normalized `{key, row_id, value}` target.
- `datasetAgent` checks operations, write fields, the upsert key, and nested values before any storage or network access.
- Manifest entries come from the shared `DatasetExport.prepare` change in TASK-0329.
- Only the TypeScript section of `docs/dataset-export.md` changed.

## Design Alignment

- No UI change.

## Validation Review

- New Deno tests run the generated module against SQLite: a graph that deletes locally and reads through the Superstep API, run twice; replay, conflict, the missed-delete rule, invalid targets, and a two-process delete race; an Agent upsert graph with connected delete denied without `allow_delete` and allowed with it; and direct `datasetAgent` insert, replay, conflict, rejected arguments, and Find rows.
- `deno check` passed on the generated Agent-write module.

## Assumptions

- None.

## Required Follow-Up

- None.

## Review Decision

Approved for QA. No blocking findings.
