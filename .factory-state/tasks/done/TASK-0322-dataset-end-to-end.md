# Task

## Metadata

- Project: superstep
- Task ID: TASK-0322
- Title: Dataset end-to-end acceptance and handbook
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-12
- Updated: 2026-11-13
- Requirement IDs: REQ-0097
- Design IDs: DES-0007
- Architecture IDs: ARCH-0003
- Plan: PLAN-0016
- Phase: Acceptance

## Objective

Verify the complete Dataset lifecycle and provide deployment instructions.

## Scope

Integrated support-ticket scenario, cross-language/backend parity, en/vi handbook, upgrade and recovery notes, screenshot evidence.

## Inputs

Merged Studio, workflow, Agent and export implementation tasks, and their QA evidence.

## Expected Outputs

Repeatable acceptance fixtures and documented authoring, authorization, deployment, backup and supported limits.

## Dependencies

[TASK-0313](TASK-0313-dataset-csv.md), [TASK-0321](TASK-0321-dataset-export-bindings-ui.md)

## Acceptance Criteria

- Run CSV import, lookup, upsert and Studio verification end to end.
- Execute generated Python and TypeScript projects on API, SQLite, PostgreSQL and a mixed binding scenario.
- Record access denial, stale edits, retry and snapshot results.
- Capture representative desktop and narrow Studio views and run both handbook builds.

## Validation Plan

Run full Factory verify, targeted Playwright, both strict handbook builds and local PostgreSQL checks. Attach observed artifacts and record any unmet requirement as a blocker.

Run the applicable full Factory profile and repository gates. Capture review and QA on the task's own PR before integration.

## Related Artifacts

- [Requirement](../../artifacts/REQ-0097-datasets.md)
- [Design](../../artifacts/DES-0007-datasets.md)
- [Architecture](../../artifacts/ARCH-0003-datasets.md)
- [Decision](../../decisions/DEC-0097-dataset-grid-and-export.md)
- [Plan](../../artifacts/PLAN-0016-datasets.md)

- [Review](../../artifacts/REV-0307-TASK-0322-dataset-end-to-end.md)
- [QA](../../artifacts/QA-0307-TASK-0322-dataset-end-to-end.md)

## Open Questions

None blocking. Use the plan and architecture boundaries for implementation choices.

## Activity Log

- 2026-11-13: Owner approved finish and merge. Moved to done. Review REV-0307. QA QA-0307.
- 2026-11-12: Created during owner-approved requirements planning.
- 2026-11-13: Reviewed TASK-0313 and cherry-picked it onto `factory/task-0321-dataset-export-bindings-ui`. CSV preview, atomic import, formula-safe export, and the Studio dialog are kept. Repository helpers were adapted to the current row writer and receipt path.
- 2026-11-13: Added the en/vi Datasets handbook and `tests/test_dataset_acceptance.py`. The support-ticket path passed on SQLite: CSV import, lookup, upsert, denied CSV download, stale schema, and a repeatable standalone snapshot. PostgreSQL parameters skipped locally. Moved to review.
- 2026-11-13: Captured real Studio screenshots for the grid, the narrow layout, and the CSV preview in English and Vietnamese.

## Handoff Notes

The branch is stacked on the CSV commit, which itself sits on the export stack. A pull request should target `factory/task-0313-dataset-csv` after that branch is updated to this CSV commit. PR #369 should use `factory/task-0321-dataset-export-bindings-ui` as its base. The handbook figures are real Studio captures at 1440×900 and 390×844.
