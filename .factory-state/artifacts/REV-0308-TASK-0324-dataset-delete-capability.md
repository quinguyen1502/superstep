# Review

## Metadata

- Project: superstep
- Review ID: REV-0308
- Task ID: TASK-0324
- Reviewer: implementation review
- Created: 2026-11-13
- Updated: 2026-11-13
- Outcome: approved for QA

## Review Scope

Diff for the delete capability on Dataset workflow grants and API tokens. Compared with REQ-0099, DEC-0098, and the TASK-0324 acceptance criteria. `delete_row`, Agent writes, public entry, and export runtimes were checked to remain unchanged.

## Reference Artifacts

- REQ-0099-dataset-writes.md
- DEC-0098-dataset-delete-and-public.md
- DES-0007-datasets.md
- PLAN-0017-dataset-writes.md
- docs/backend-architecture.md
- docs/ui-conventions.md

## Findings

### Blocking

- None.

### Non-Blocking

- Local pytest skipped the PostgreSQL parameter because no test database URL was set. The migration uses the same additive boolean on both dialects. CI still needs to run the Postgres job.
- Saving a grant still replaces `created`. That behavior predates this task.

## Standards And Architecture Alignment

- The flag is a boolean beside the existing permission check constraint. Read, write, and read-and-write values are unchanged.
- Routers pass the schema field to the service. The service writes the model through the repository. No new error code.
- The Studio row-delete route remains a plain DELETE. Revoke still uses typed confirmation.

## Design Alignment

- The Access dialog adds one unchecked checkbox for grants and one for tokens, using the shared Checkbox and theme tokens.
- English and Vietnamese keys match. The Vietnamese string uses the glossary spelling `xoá`.
- Both controls are keyboard reachable. The Playwright spec focuses each checkbox and toggles it with Space.

## Validation Review

- Targeted access, migration, layer, envelope, connected, runtime, and receipt tests passed on SQLite.
- Locale parity passed. Frontend lint passed with existing warnings. The Dataset access Playwright spec passed in system Chrome.

## Assumptions

- A missing `allow_delete` field means false, so older clients do not enable deletion.

## Required Follow-Up

- None for this task. TASK-0325 consumes the flag when it adds `delete_row`.

## Review Decision

Approved for QA. No blocking findings.
