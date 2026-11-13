# Task

## Metadata

- Project: superstep
- Task ID: TASK-0322
- Title: Dataset end-to-end acceptance and handbook
- Status: todo
- Owner: Thái Quí Nguyễn
- Created: 2026-11-12
- Updated: 2026-11-12
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

[TASK-0313](../done/TASK-0313-dataset-csv.md), [TASK-0321](../done/TASK-0321-dataset-export-bindings-ui.md)

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

## Open Questions

None blocking. Use the plan and architecture boundaries for implementation choices.

## Activity Log

- 2026-11-12: Created during owner-approved requirements planning.

## Handoff Notes

Start from integrated develop on `factory/task-0322-dataset-end-to-end` after its dependencies land, or document an explicit stack. Follow the normal owner approval and CI gates.
