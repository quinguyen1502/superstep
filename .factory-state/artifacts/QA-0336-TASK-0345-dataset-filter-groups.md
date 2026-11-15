# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0336
- Task ID: TASK-0345
- Created: 2026-11-14
- Outcome: pass with follow-up

## Evidence

SQLite checks passed for nested filters through the API, Dataset node and Agent, plus filter limits, node error paths, flat queries, API envelope and backend layers (38 passed, 30 skipped). PostgreSQL is parametrized and needs CI confirmation.

## Required Follow-Up

Confirm the GitHub checks on the proposed merge head. Generated code reports unsupported filters until Python and TypeScript export parity land. This branch depends on PR #402.
