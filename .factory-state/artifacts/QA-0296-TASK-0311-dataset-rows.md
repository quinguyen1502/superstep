# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0296
- Task ID: TASK-0311
- QA Owner: Codex
- Created: 2026-11-12
- Updated: 2026-11-12
- Outcome: Pass for task acceptance

## Acceptance Coverage

- Scoped CRUD, typed defaults and nulls, numeric ordering, text filtering, field projection, pagination and error codes passed on SQLite and PostgreSQL 17.
- The concurrency case produced one insert and one update with the same row ID. Cross-type numeric equality correctly reserved the same unique key. Stale cell edits and deletes were rejected.
- A required column cannot be added when rows exist. Adding an optional column leaves existing cells null and applies defaults on new rows. Archived values are absent from queries, and dataset deletion clears its rows and unique keys.
- Dataset, migration, layer and API envelope suites reported 24 passing tests with disposable PostgreSQL 17 enabled.

## Measured Workload

- A fixture with 25,000 rows, three fields and one unique key ran 30 timed repository calls per query after five warmups.
- SQLite p95 was 4.28 ms for an indexed unique lookup and 40.86 ms for the first 50 rows filtered by status and sorted by score.
- PostgreSQL 17 p95 was 2.51 ms for the lookup and 8.76 ms for the filtered page.
- Implemented limits are 25,000 rows per dataset, 64 KiB per serialized row, 100 rows and 1 MiB of row payload per query page, and at most 12 filters. These are operational bounds. The fixture measures only the narrow shape described above.

## Gaps And Residual Risk

- The task is stacked on the schema PR. GitHub required checks and owner approval gate integration.
- Grid, CSV, Agent tools and workflow-node writes are later tasks. The API implements concurrent upsert; run-originated durable operation receipts follow in the runtime task.
