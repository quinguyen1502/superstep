# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0300
- Task ID: TASK-0315
- QA Owner: Codex
- Created: 2026-11-13
- Updated: 2026-11-13
- Outcome: Pass for targeted checks

## Acceptance Coverage

- SQLite live WebSocket runs verified typed upsert, find and get, explicit projection, public and unsaved denial, nested effective grants and revocation before resume.
- Simulated worker loss immediately after a committed insert and edited the stored workflow before recovery. The recovered plan replayed the prior result, leaving one row. Concurrent retries, stale leases, changed arguments, distinct logical iterations and rollback after a uniqueness error were also exercised.
- Verified test-mode writes and a debug run resumed from a Human node leave the dataset untouched.
- The targeted backend suite passed 73 tests, with 15 skipped. It included architecture, API envelope, validation messages, worker effects, Human resume, subgraphs and workflow tools.

## References

- [Task](../tasks/done/TASK-0315-dataset-node-runtime.md)
- [Review](REV-0300-TASK-0315-dataset-node-runtime.md)
