# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0358
- Task ID: TASK-0369
- QA Owner: Codex
- Created: 2026-11-22
- Updated: 2026-11-22
- Outcome: Pass

## Acceptance Criteria Coverage

| Criterion | Evidence | Result |
| --- | --- | --- |
| Changed transactions advance the revision and publish after commit | The Dataset live tests read the committed marker during publish. Cases cover Studio create, insert, update, delete, batch, undo, CSV create and append, Connected mutations, stale definition saves and Formula backfill. Existing workflow and Agent tests verify their revision increments. | Pass on SQLite |
| No-op and recovery behavior | Tests cover duplicate-key and batch rollback, dry runs, receipt replay, no-op upserts and batches, two concurrent upserts, a failed publish, and reconnect. The populated migration test preserves rows. The existing Formula downgrade guard preserves the head schema when it rejects a downgrade. | Pass on SQLite |
| Authorization and delivery | Tests cover same-origin cookie auth, foreign origins including another port, URL and PAT rejection, membership loss, password revocation, bounded sends, queue coalescing and cleanup. An actual write in another process reaches a socket through a real Redis connection. | Pass locally |

## Checks Performed

- Dataset, exporter, history, envelope and layer regressions. 185 passed and 140 environment-dependent cases skipped.
- Focused authentication, Chat origin, PAT, migration and Dataset checks. 77 passed and 18 skipped.
- Concurrent upsert, socket authorization and Formula downgrade probes. Three passed and three PostgreSQL cases skipped.
- Redis and history socket suite. 19 passed and 10 environment-dependent cases skipped. The local Redis 5 server used RESP2.
- Public OpenAPI drift, Factory hygiene, artifact IDs and whitespace checks passed.

- [PR #429 CI](https://github.com/quinguyen1502/superstep/pull/429/checks) passed all 24 runnable checks for reviewed head `0d89c910`, including PostgreSQL 17, Redis 7, Factory verification and all Playwright shards.

## Gaps And Residual Risk

The local Docker service is unavailable. The migration, mutation and split-process suite ran against PostgreSQL 17 and Redis 7 in PR CI. The Studio consumer and its browser refresh behavior are tracked in the following task.

## QA Decision

Pass. Require successful checks on the final PR head before integration.
