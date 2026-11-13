# Review

## Metadata

- Project: superstep
- Review ID: REV-0312
- Task ID: TASK-0328
- Reviewer: implementation review
- Created: 2026-11-13
- Updated: 2026-11-13
- Outcome: approved for QA

## Review Scope

Diff for the public-entry Dataset rule against REQ-0099, DEC-0098, DES-0007, ARCH-0003, and the TASK-0328 acceptance criteria. Snapshot, CSV, export, and handbook behavior were checked to stay unchanged.

## Reference Artifacts

- REQ-0099-dataset-writes.md
- DEC-0098-dataset-delete-and-public.md
- ARCH-0003-datasets.md
- PLAN-0017-dataset-writes.md
- docs/backend-architecture.md

## Findings

### Blocking

- None.

### Non-Blocking

- The branch stacks on TASK-0327 so the Agent write case runs against the new rule. The PR targets the TASK-0327 branch until it merges.
- Demo mode is passed into `DatasetAccessService.workflow_dataset` and denies every operation, including Studio Run. Before this change demo mode only marked the run public, and a public run was denied anyway. The result for demo deployments is the same, and the denial no longer depends on the run source.

## Standards And Architecture Alignment

- Classification stays in `RunService._bind_dataset`: demo mode, or a top-run source other than `ui`, `schedule`, and `test`, is public. A workflow-tool child uses its top run's source.
- `DatasetAccessService.workflow_dataset` denies when demo mode is on, when the workflow is not saved, or when a public run asks for `delete_row`. Otherwise the saved workflow grant decides, as for Studio Run. The service reuses `DATASET_GRANT_DENIED`.
- The rule is read on each call from the saved grant. A grant removed while a run waits is denied when the run resumes.
- Agent writes go through the same `DatasetRuntimeService.execute` path, so they follow the same rule.

## Design Alignment

- No UI change. The handbook entry matrix belongs to TASK-0331.

## Validation Review

- `tests/test_dataset_public_entry.py` covers Studio chat and API sources, a real API trigger through the application, Studio Run and schedule deletes, demo mode, a nested workflow tool, resume after grant removal, and an Agent write from chat.
- `tests/test_dataset_runtime.py` and `tests/test_dataset_access.py` were updated where they asserted the old blanket denial.

## Assumptions

- Workflow tests (`test` source) stay in the Studio group, as before.

## Required Follow-Up

- TASK-0331 documents the entry matrix.

## Review Decision

Approved for QA. No blocking findings.
