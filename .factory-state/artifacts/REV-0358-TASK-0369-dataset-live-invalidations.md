# Review

## Metadata

- Project: superstep
- Review ID: REV-0358
- Task ID: TASK-0369
- Reviewer: Codex
- Created: 2026-11-22
- Updated: 2026-11-22
- Outcome: Approved for merge

## Review Scope

Reviewed the Dataset writer matrix, metadata migration, read authorization, HTTP revision endpoint, WebSocket lifetime, and post-commit fan-out against develop at `d3493d36`.

## References

- [Task](../tasks/done/TASK-0369-dataset-live-invalidations.md)
- [Requirement](REQ-0103-dataset-integrations-and-live-sharing.md)
- [Architecture](ARCH-0005-dataset-integrations-and-live-sharing.md)
- [Backend contract and writer matrix](../../docs/backend-architecture.md#dataset-realtime)

## Findings

### Blocking

- No blocking findings in the final source diff.

### Non-Blocking

- During rolling deployment, API and worker processes need migration 0073 and the new writer implementation before relying on the marker across processes.
- Authorization loss from a cascaded team or user removal is observed on the next wakeup or heartbeat. Explicit Dataset deletion publishes a wakeup after commit.

## Standards And Architecture Alignment

Repositories advance the persisted marker with the existing writer lock. A schema change preserves the marker from the locked row when merging a detached definition. Services signal after commit. Row values, identities, and Formula diagnostics remain on the existing authorized read routes.

The WebSocket uses the Studio session cookie and the origin matcher also used by public Chat. It revalidates the session and current Dataset membership before pushes and heartbeats. Redis acknowledgement precedes the initial revision read. The memory hub uses a bounded queue for these sockets, and both transports bound send time and clean up subscriptions.

## Validation Review

The first migration pass exposed SQLite legacy DDL behavior during a downgrade past the Formula guard. Migration 0073 now begins a transaction before dropping its column on SQLite so a rejected downgrade preserves the marker and the Formula rows. The previous downgrade test and the new populated Dataset migration test cover that behavior.

## Review Decision

The owner approved merging PR #429 into develop on 2026-11-22. The Studio grid consumer is planned separately and will use the documented socket and resync endpoint.
