# Decision Record

## Metadata

- Project: superstep
- Decision ID: DEC-0098
- Status: Accepted for planning
- Owner: Thái Quí Nguyễn
- Created: 2026-11-13
- Updated: 2026-11-13
- Related Requirements: REQ-0099
- Related Architecture: ARCH-0003
- Related Tasks: TASK-0324, TASK-0325, TASK-0326, TASK-0327, TASK-0328, TASK-0329, TASK-0330, TASK-0331

## Context

REQ-0097 grants are `read`, `write`, or `read_write`, and a public run is rejected before the grant is checked. REQ-0099 adds workflow row delete, Agent insert and upsert, and Dataset use from public entries. Delete must not be implied by write, and public entries must still be unable to delete.

## Decision

- Store delete as `allow_delete`, a boolean defaulting to false, beside the existing permission on `dataset_workflow_grants` and `dataset_api_tokens`. Keep the permission check constraint unchanged. An additive migration follows `0066_dataset_receipts`.
- `delete_row` accepts either `row_id` or one unique `key` plus its `value`, and no other arguments. The key must name a unique column.
- A missing row raises `DATASET_ROW_NOT_FOUND` and does not store a receipt. A completed delete replays its receipt. A different payload for that identity raises `DATASET_RECEIPT_CONFLICT`.
- Demo mode rejects every Dataset operation. A public run may find, get, insert, and upsert when the saved workflow grant allows that operation. `delete_row` on a public run raises `DATASET_GRANT_DENIED` even when `allow_delete` is true. Unsaved workflows stay denied.
- An Agent tool may enable `find_rows`, `insert_row`, and `upsert_row`. It cannot enable `delete_row`.
- Reuse the existing Dataset error codes for these denials and conflicts.

## Rationale

A separate boolean preserves current grants and tokens without a new permission combination. The public rule follows the run sources already classified as public, including Studio chat, while keeping delete off those entries as REQ-0099 requires.

## Alternatives Considered

- Option: Add `delete` to the permission enum.
  - Benefits: One field carries the whole grant.
  - Tradeoffs: Existing rows and every `read` / `write` / `read_write` check need a new combination for delete.
  - Reason Not Chosen: REQ-0099 keeps read and write unchanged and treats delete as an extra capability.
- Option: Allow public delete when `allow_delete` is set.
  - Benefits: One grant means the same operations on every entry.
  - Tradeoffs: A public client could remove rows.
  - Reason Not Chosen: The owner kept delete off public entries.

## Impacts

- ARCH-0003's blanket public denial no longer applies to Find, Get, Insert, and Upsert under REQ-0099. Delete and demo mode stay denied.
- Studio Access, the Dataset node, Agent tool settings, connected tokens, and both export runtimes must honor `allow_delete` and the operation matrix.

## Risks

- A public run that can upsert can still change rows. The grant, field list, receipt, and audit boundary remain the controls.
- Export tasks that land after the Studio operation must not leave a documented standalone `delete_row` that the generated runtime cannot run. The acceptance task closes that gap.
