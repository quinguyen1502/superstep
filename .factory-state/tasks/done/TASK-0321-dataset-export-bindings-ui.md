# Task

## Metadata

- Project: superstep
- Task ID: TASK-0321
- Title: Project export binding UI and optional snapshots
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-12
- Updated: 2026-11-13
- Requirement IDs: REQ-0097
- Design IDs: DES-0007
- Architecture IDs: ARCH-0003
- Plan: PLAN-0016
- Phase: Export

## Objective

Choose a deployment backend for each dataset and optionally seed a standalone project.

## Scope

Project export dialog, per-binding backend choices, generated configuration, permission-checked snapshot creation and explicit restore.

## Inputs

Both standalone adapters, connected binding contract, project export and CSV limits.

## Expected Outputs

A guided export flow in both languages, generated README and environment templates, plus an optional seed artifact.

## Dependencies

[TASK-0316](TASK-0316-dataset-node-editor.md), [TASK-0319](TASK-0319-dataset-export-python-standalone.md), [TASK-0320](TASK-0320-dataset-export-typescript-standalone.md)

## Acceptance Criteria

- A project can use mixed bindings and change backends at deployment without regenerating the graph.
- Default archives include no data or secrets.
- A snapshot requires explicit selection and read access and is bounded and disclosed in the UI.
- Restore checks schema and is safe to repeat without silently overwriting data.

## Validation Plan

Run export archive inspections and Playwright for mixed bindings, default export, snapshot selection and denied access. Restore the generated seed in both languages.

Run the applicable full Factory profile and repository gates. Capture review and QA on the task's own PR before integration.

## Related Artifacts

- [Requirement](../../artifacts/REQ-0097-datasets.md)
- [Design](../../artifacts/DES-0007-datasets.md)
- [Architecture](../../artifacts/ARCH-0003-datasets.md)
- [Decision](../../decisions/DEC-0097-dataset-grid-and-export.md)
- [Plan](../../artifacts/PLAN-0016-datasets.md)

- [Review](../../artifacts/REV-0306-TASK-0321-dataset-export-bindings-ui.md)
- [QA](../../artifacts/QA-0306-TASK-0321-dataset-export-bindings-ui.md)

## Open Questions

None blocking. Use the plan and architecture boundaries for implementation choices.

## Activity Log

- 2026-11-13: Owner approved finish and merge. Moved to done. Review REV-0306. QA QA-0306.
- 2026-11-12: Created during owner-approved requirements planning.
- 2026-11-13: Added the project-export binding dialog and optional snapshots on `factory/task-0321-dataset-export-bindings-ui`, stacked on `factory/task-0320-dataset-export-typescript-standalone` at `edc2145e`. Backend choices are deployment settings. A snapshot is off unless selected, requires dataset read access, and is capped at 1,000 rows. Setup imports missing ids and does not replace stored rows.
- 2026-11-13: `tests/test_dataset_export_snapshot.py` passed on SQLite for Python and TypeScript (Deno 2.9.8), including identical graph bytes across backend choices, denied and oversized snapshots, and repeat setup. Connected project export and Python standalone regressions passed. PostgreSQL parameters skipped locally. Moved to review.

## Handoff Notes

The branch is stacked on the TypeScript standalone branch. A pull request should target `factory/task-0320-dataset-export-typescript-standalone`. The dialog was not exercised in a browser in this session. CI `backend-postgres` still needs to run the same tests with `TEST_DATABASE_URL`.
