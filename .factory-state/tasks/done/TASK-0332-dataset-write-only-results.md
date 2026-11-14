# Task

## Metadata

- Project: superstep
- Task ID: TASK-0332
- Title: Stop write-only Dataset callers from reading row values
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-13
- Updated: 2026-11-14
- Requirement IDs: REQ-0100
- Design IDs: DES-0007
- Architecture IDs: ARCH-0003
- Decision IDs: DEC-0099
- Plan: PLAN-0018
- Phase: Fix
- Priority: P0
- Size: M

## Objective

A caller with write but not read permission gets identifiers only from insert, upsert, dry-run, and replay, and a no-op write leaves the row revision unchanged.

## Scope

### In Scope

- One shared result function in `services/dataset_rows.py` that strips `values` when the principal lacks read (DEC-0099 Option A, accepted). It is used by the Dataset node, the Agent tool, public entries, connected tokens, and the dry-run branch.
- A requested field projection from a write-only caller returns `DATASET_GRANT_DENIED` before any write.
- Agent tools configured without Find receive `{row: {id, revision}, inserted}` even when the grant is `read_write`, so the model only sees values through Find.
- No-op detection: when the built values equal the stored values, skip the revision bump, `updated`, key rewrite, and `dataset.row_update` audit; still store and replay the receipt.
- Access dialog and Dataset node: explain that Write returns identifiers only; hide the output field picker for write-only grants; en/vi strings.
- `docs/dataset-export.md` and the handbook note on the response shape and the residual existence signal of `inserted`.

### Out Of Scope

- Receipt storage shape (TASK-0333) and standalone export runtimes (TASK-0343).
- Changing the `allow_delete` capability or the public-entry matrix of DEC-0098.

## Inputs

- `services/dataset_access.py` `_allows`, `DatasetPrincipal`; `services/dataset_rows.py` upsert and dry-run branches; `repositories/dataset_rows.py` `save`.
- Review probe: a write-only token got 401 on `find_rows` and 200 with 9 values on `upsert_row`.
- TASK-0327 Agent write tool and TASK-0328 public-entry runtime once merged.

## Related Artifacts

- Requirements: [REQ-0100](../../artifacts/REQ-0100-dataset-phase1-fixes.md), [REQ-0097](../../artifacts/REQ-0097-datasets.md), [REQ-0099](../../artifacts/REQ-0099-dataset-writes.md)
- Design: [DES-0007](../../artifacts/DES-0007-datasets.md)
- Architecture: [ARCH-0003](../../artifacts/ARCH-0003-datasets.md)
- Plan: [PLAN-0018](../../artifacts/PLAN-0018-dataset-phase1-fixes.md)

## Dependencies

- DEC-0099 Option A accepted by the owner on 2026-11-13.
- Branch from `develop` after PR #383 (TASK-0327) merges, so the Agent write path is covered in the same change. Must merge before the TASK-0328 PR; TASK-0328 then rebases onto it.

## Acceptance Criteria

- A `write` grant and a `write` token never receive a cell value from insert, upsert, dry-run, or a replayed receipt; the response has `row.id`, `row.revision`, and `inserted` only.
- A write-only caller that asks for fields gets `DATASET_GRANT_DENIED` and nothing is written.
- An Agent tool with Insert and Upsert but without Find returns identifiers only to the model, and the trace shows the outcome and count.
- Upserting identical values twice leaves `revision` and `updated` unchanged and records one audit event.
- `read_write` callers and Studio users keep today's full response.

## Tests

- Security regression: write-only grant, write-only token, Agent without Find, public-entry write (when TASK-0328 is merged) on SQLite and PostgreSQL.
- Dry-run and receipt replay for a write-only caller.
- No-op upsert revision and audit tests; concurrent no-op and real update under the writer lock.
- Playwright: Access dialog note and the node output picker for a write-only grant.

## Validation Plan

- Targeted backend tests (`pytest`) on SQLite and PostgreSQL, `tests/test_layers.py` and `tests/test_api_envelope.py`; where the frontend is touched, `npm run lint`, `npm run build`, `npm test`, locale parity and the matching Playwright spec.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts on the task's own PR; all required CI green before merge.

## Open Questions

- None.

## Activity Log

- 2026-11-13: Created by planning on branch `factory/plan-dataset-fixes-phase3`. No implementation. Stays in backlog until the owner accepts REQ-0100 and PLAN-0018.
- 2026-11-13: Updated after the owner's answers on PR #388 (22:33 Asia/Saigon): DEC-0099 Option A accepted.
- 2026-11-13: Owner accepted REQ-0100 and PLAN-0018 (22:34 Asia/Saigon); moved to todo as the first task of the plan. Not started.

- 2026-11-13: Implemented on `factory/task-0332-dataset-write-only-results`, stacked on `factory/task-0327-dataset-agent-write` (PR #383) with the planning branch of PR #388 merged in. Review REV-0316. QA QA-0316. Moved to review.

## Related Artifacts (Review)

- Review: [REV-0316](../../artifacts/REV-0316-TASK-0332-dataset-write-only-results.md)
- QA: [QA-0316](../../artifacts/QA-0316-TASK-0332-dataset-write-only-results.md)

## Integration

- Merged into develop via PR #389 at `10cc53f2`. The lifecycle was reconciled on 2026-11-14.

## Handoff Notes

- PR into `factory/task-0327-dataset-agent-write`; retarget to `develop` after #383 merges. Do not merge until the owner asks and required CI is green.
- Insert row and Upsert row accept `fields: []` (identifiers only) in the node binding, the connected API, and the standalone runtimes.
- TASK-0328 must merge this change before it merges itself. TASK-0333 removes values from receipts; TASK-0343 ports the Agent-without-Find and no-op rules to standalone exports.
