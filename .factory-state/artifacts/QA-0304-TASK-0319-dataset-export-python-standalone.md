# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0304
- Task ID: TASK-0319
- QA Owner: Codex
- Created: 2026-11-13
- Updated: 2026-11-13
- Outcome: Pass for scoped checks

## Acceptance Criteria Coverage

- Ran the generated Python project against SQLite and a local PostgreSQL 17.11 fixture. Both supported nested workflow Dataset operations and Agent lookup, and preserved false and zero values.
- Setup preserved rows when repeated. Both backends rejected an incompatible schema without changing existing data, and reported missing or malformed binding settings.
- Parallel requests with the same operation ID returned the original outcome. Concurrent upserts with different IDs serialized correctly. A conflicting payload and duplicate unique value were rejected.
- A generated Python file used one standalone binding and one connected API binding in the same run on each database.

## Checks Performed

- All 34 Dataset, export, receipt, layer and API-envelope tests passed against SQLite and live PostgreSQL. The run also included both existing connected project exports.
- The first broad run exhausted temporary disk space during PostgreSQL database creation. The complete rerun passed after reclaiming space from an earlier temporary worktree.
- The preceding stack's full Factory run exhausted temporary disk space while recording evidence. The scoped live database results were captured separately.

## References

- [Task](../tasks/done/TASK-0319-dataset-export-python-standalone.md)
- [Review](REV-0304-TASK-0319-dataset-export-python-standalone.md)
- [Dataset exports](../../docs/dataset-export.md)
