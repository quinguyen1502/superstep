# Task

## Metadata

- Project: superstep
- Task ID: TASK-0369
- Title: Publish authorized Dataset invalidations after writes
- Status: backlog
- Owner: Thái Quí Nguyễn
- Created: 2026-11-22
- Updated: 2026-11-22
- Requirement IDs: REQ-0103
- Design IDs: DES-0009
- Architecture IDs: ARCH-0005

## Objective

Let authorized Studio sessions detect committed data and schema changes across API and worker processes.

## Scope

Add a Dataset-scoped authenticated WebSocket and a cheap persisted data revision using the existing notification hub patterns. Inventory every writer, including CSV, batch and undo, workflow and Agent, connected API, admin schema edits and Formula backfills. Expose the revision through an authorized lightweight HTTP read for resync.

## Inputs

- Workflow history socket, Redis and in-memory notification hubs, Dataset repositories, row writer transaction and row/schema revisions, and Formula persistence.

## Related Artifacts

- [Requirement](../../artifacts/REQ-0103-dataset-integrations-and-live-sharing.md)
- [Design](../../artifacts/DES-0009-dataset-integrations-and-live-sharing.md)
- [Architecture](../../artifacts/ARCH-0005-dataset-integrations-and-live-sharing.md)
- [Decision](../../decisions/DEC-0103-dataset-integration-and-sharing-boundaries.md)
- [Delivery plan](../../artifacts/PLAN-0021-dataset-integrations-and-live-sharing.md)

## Expected Outputs

Additive migration, committed revision marker and post-commit notification, authorization and resync endpoint, and mutation coverage matrix.

## Implementation Notes

Advance once per committed changed transaction, separately from row and schema revisions. Push a bounded invalidation after commit with no row values. Recheck session and Dataset visibility on handshake, push and heartbeat. A failure to publish must not lose a committed mutation or prevent clients from detecting it later.

## Constraints

- Follow the existing backend layers, permission checks, API envelope and error catalog. Use EN/VI locale parity, shared UI components and theme tokens where applicable.
- Review and QA precede approval to merge into develop. Recheck shared Dataset schema and export changes from PLAN-0020 at task start.

## Dependencies

- [TASK-0368](../backlog/TASK-0368-dataset-python-typescript-sdk.md). Start after this dependency integrates, or document an approved stack.

## Acceptance Criteria

- A real create, update, delete, CSV import, batch/undo or workflow/Agent/Connected write produces one observable invalidation for a changed transaction. A Formula backfill or schema edit is coherent with the resulting schema and rows.
- A rollback, dry run, receipt replay and no-op upsert do not emit a data change. The persisted marker remains available after a missed push, process restart or reconnect.
- An unauthorized or revoked session receives no invalidation. Redis fan-out works across processes and local single-process mode works without Redis.

## Validation Plan

Exercise the writer matrix and upgrade from the previous migration on SQLite and PostgreSQL. Exercise split API/worker with Redis and test subscriber access removal, reconnect, rollback and slow-client cleanup. Run the applicable repository and Factory checks and record review and QA evidence on the task PR.

## Assumptions

Use the v1 scope of REQ-0103 and the proposed interfaces in ARCH-0005.

## Open Questions

Confirm the predecessor contract and integration before promoting to todo.

## Activity Log

- 2026-11-22: Planned from the owner-approved scope and sequence.

## Handoff Notes

Use a dedicated task branch from current develop when implementation is requested. This plan does not authorize a release or merge.
