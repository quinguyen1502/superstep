# Review

## Metadata

- Project: superstep
- Review ID: REV-0316
- Task ID: TASK-0332
- Reviewer: implementation review
- Created: 2026-11-13
- Updated: 2026-11-13
- Outcome: approved for QA

## Review Scope

Diff for identifier-only write results against REQ-0100, DEC-0099 (Option A, accepted), PLAN-0018, ARCH-0003, DES-0007, and the TASK-0332 acceptance criteria. The Studio row API, `delete_row`, `allow_delete`, and the public-entry matrix of DEC-0098 were checked to stay unchanged.

## Reference Artifacts

- REQ-0100-dataset-phase1-fixes.md
- DEC-0099-dataset-write-only-results.md
- PLAN-0018-dataset-phase1-fixes.md
- ARCH-0003-datasets.md
- DES-0007-datasets.md

## Findings

### Blocking

- None.

### Non-Blocking

- The branch stacks on TASK-0327 (PR #383) and merges the planning branch of PR #388 instead of starting from `develop` after #383 merges, as the task handoff said. This lets one change cover the Agent write path while #383 is still open. Retarget to `develop` once #383 merges.
- `fields` may now be empty for Insert row and Upsert row in the node binding, the connected API body, and both standalone export runtimes. An empty list asks for identifiers only. Without this, a write-only caller would always fail, because every binding had to name at least one field. Find rows, Get row, Delete row, and Agent tools still need at least one field.
- Standalone exports gained only the empty-field case so an exported write-only node keeps running. The Agent-without-Find rule and the no-op revision rule for standalone runtimes stay with TASK-0343.
- `DATASET_GRANT_DENIED` keeps its workflow-oriented message when a write-only token asks for fields. TASK-0337 owns error wording and the new token scope code, so `docs/api-errors.md` is unchanged here.

## Standards And Architecture Alignment

- One shared decision in `services/dataset_rows.py` (`_write_projection` and `_write_result`) serves the Dataset node, the Agent tool, connected tokens, dry-run, and receipt replay. Public entries reach it through the same runtime path, so TASK-0328 inherits it without its own code.
- Read permission comes from `dataset_access.can_read` on the grant or token. A request that would reveal values is re-checked under the writer lock against the stored grant or token, so a concurrent downgrade fails closed before any write.
- A no-op write skips the revision bump, the `updated` change, the key rewrite, and the row-update audit event. It still checks the requested revision and still stores its receipt.
- Receipts still hold the full row (TASK-0333). Replay strips values for a write-only caller and refuses a field request from a caller that lost read access.

## Design Alignment

- The node Data tab hides Fields to return for a write-only grant, explains the identifier-only result, and offers Return identifiers only when a saved node still asks for fields. Choosing Insert or Upsert on a write-only grant starts with no returned fields.
- The Access dialog explains Write under both permission pickers. The Agent tool settings explain the result shape when Find rows is off. English and Vietnamese keys match.

## Validation Review

- Security regressions in `tests/test_dataset_write_only.py` reproduce the review probe for the node, the token API, the Agent tool without Find, an Agent with Find on a write grant, dry-run, and replay, and assert the stored secret never appears in responses, run events, or model messages.
- No-op, concurrent no-op and update, and the lock re-check have their own tests. Existing runtime and receipt tests were updated where they relied on the leak.

## Assumptions

- An Agent tool binding is recognised by `filter_ops`, which only the trusted Agent expansion sets. A node that adds it can only lose values, never gain them.

## Required Follow-Up

- TASK-0328 must take this change before it merges (PLAN-0018). TASK-0333 removes values from stored receipts. TASK-0343 brings the remaining rules to standalone exports.

## Review Decision

Approved for QA. No blocking findings.
