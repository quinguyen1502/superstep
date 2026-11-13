# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0303
- Task ID: TASK-0318
- QA Owner: Codex
- Created: 2026-11-13
- Updated: 2026-11-13
- Outcome: Pass for scoped checks

## Acceptance Criteria Coverage

- Ran the exported Python project and TypeScript project on Node 22 and LangGraph.js 1.7 against the real Superstep Dataset API through a localhost fixture. Both inserted, upserted, found, and retrieved rows, preserving false and zero values. The Agent used the configured projection.
- A gateway returned 503 after the initial insert committed. Both runtimes retried the exact body and left a single row. The next write used a separate operation ID. Parallel requests, a different payload under the same identity, replay after a row changed, and token rotation were exercised by API tests.
- Both projects reported missing settings, a removed destination field, and a revoked credential. Endpoint tests checked denial of incorrect dataset and operation scopes.
- Inspected every file in both project archives for the source and destination IDs, connection URL, and token. Only blank deployment settings and the schema contract were present.

## Checks Performed

- Export, receipt, Agent, API envelope and architecture regression passed 81 tests, with 38 variants skipped.
- Final focused checks passed 12 tests, with four PostgreSQL variants skipped. The generated TypeScript project passed strict typechecking.
- Full Factory verification started in a dedicated temporary directory. Scoped evidence is recorded independently of the full result.

## References

- [Task](../tasks/done/TASK-0318-dataset-export-api.md)
- [Review](REV-0303-TASK-0318-dataset-export-api.md)
- [Connected Dataset exports](../../docs/dataset-export.md)
