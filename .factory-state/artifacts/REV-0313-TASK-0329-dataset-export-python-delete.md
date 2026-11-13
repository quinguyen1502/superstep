# Review

## Metadata

- Project: superstep
- Review ID: REV-0313
- Task ID: TASK-0329
- Reviewer: implementation review
- Created: 2026-11-13
- Updated: 2026-11-13
- Outcome: approved for QA

## Review Scope

Diff for Python export Delete row and Agent writes against REQ-0099, DEC-0098, ARCH-0003, and the TASK-0329 acceptance criteria. The TypeScript runtime, snapshots, and handbook were checked to stay unchanged.

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

- The shared "Superstep API" section of `docs/dataset-export.md` also changed. It listed four operations and did not mention delete permission, and connected Delete row is part of this task. The edit adds `delete_row`, its arguments and result, and the delete-allowed token. The TypeScript section is unchanged.
- The exported offline mock model now fills enum parameters and Dataset write values, like the Studio mock from TASK-0327. Without it the generated project could not run an Agent write offline.

## Standards And Architecture Alignment

- Standalone `delete_row` takes the same writer lock as insert and upsert, checks the receipt before the row, removes the row and its unique keys, and stores `{row_id, deleted}`. A missing row raises `DATASET_ROW_NOT_FOUND` inside the transaction, so no receipt is stored and a later delete with that identity can still succeed.
- The delete fingerprint covers the operation, the fields, and the normalized target. A different target with the same identity returns `DATASET_RECEIPT_CONFLICT`.
- Delete arguments are exactly `{row_id}` or `{key, value}`, and the key must be unique, as in Studio.
- `dataset_agent` accepts the operations, write fields, and key saved on the tool, and rejects anything else before any storage access. The generated tool node takes `config` only when a write tool exists and derives one operation ID per model call.
- `DatasetExport.prepare` lists the Agent tool's operations in the manifest, checks that its write fields exist, and checks that its upsert key is unique.

## Design Alignment

- No UI change.

## Validation Review

- New tests run the generated single-file project against SQLite: a graph that deletes locally and reads through the Superstep API, run twice, receipt replay and conflict, the missed-delete rule, a concurrent delete race, an Agent upsert graph, direct Agent insert and Find calls, and connected Delete row rejected without `allow_delete` and accepted with it.
- Existing standalone and project export tests still pass.

## Assumptions

- The LangGraph checkpoint namespace identifies one tool-node execution, as the Dataset node already assumes for its operation ID.

## Required Follow-Up

- TASK-0330 mirrors the runtime in TypeScript.

## Review Decision

Approved for QA. No blocking findings.
