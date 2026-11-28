# Task

## Metadata

- Project: superstep
- Task ID: TASK-0376
- Title: Edit Dataset Relations in Studio
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-28
- Updated: 2026-11-29
- Requirement IDs: REQ-0102
- Design IDs: DES-0008
- Architecture IDs: ARCH-0004

## Objective

Configure and edit Relation columns from Studio with scoped, keyboard-operable pickers and readable linked labels.

## Dependencies

- [Relation storage and authorization](../done/TASK-0375-dataset-relation-storage.md) is merged into develop.

## Scope

- Author Relation columns in Schema while the existing server preview flag is on. Choose a visible, same-scope target and an eligible display column. Keep the target immutable on edit.
- Use the authenticated Relation endpoints for lookup, link and unlink. Render authorized labels for visible cells in bounded batches. Use the shared unlink confirmation.
- Filter by target identity or empty link using the existing Rows filter builder. Preserve revision conflicts and referenced-delete guidance through the localized error catalog.
- Connected bindings, standalone exports and CSV link import remain later work items.

## Acceptance Criteria

- The column dialog lays out Column type and Target dataset in one row on desktop. Mobile stacks the controls. Same-scope options, unavailable targets and empty display column lists are handled.
- Click, double-click and keyboard editing preserve the existing grid focus model. The picker searches and paginates on the server, and duplicate or empty labels remain distinguishable.
- Link and unlink use the current schema and row revisions. Failures preserve the saved value. Viewers can see authorized labels and cannot edit. Unavailable targets receive a neutral unavailable state.
- Relation filters support matching identities and empty links. Existing grids, Formula and public shares continue to work.

## Validation Plan

Run frontend build, lint and tests. Verify schema, picker, linking, unlinking, filters, viewer access and guarded target deletion using Playwright against a local SQLite demo. Review both themes and a narrow viewport. Require GitHub checks before merging.

## Related Artifacts

- [Plan](../../artifacts/PLAN-0020-dataset-formulas-and-relations.md)
- [Requirement](../../artifacts/REQ-0102-dataset-formulas-and-relations.md)
- [Design](../../artifacts/DES-0008-dataset-formulas-and-relations.md)
- [Architecture](../../artifacts/ARCH-0004-dataset-formulas-and-relations.md)
- [Storage decision](../../decisions/DEC-0102-dataset-formula-relation-storage.md)

- [Review](../../artifacts/REV-0365-TASK-0376-dataset-relation-studio.md)
- [QA](../../artifacts/QA-0365-TASK-0376-dataset-relation-studio.md)

## Activity Log

- 2026-11-28: The owner requested the next approved task. The Studio slice follows the merged Relation storage contract.
- 2026-11-28: Implemented Relation configuration and authenticated editing in Studio. Production build, lint, 330 JavaScript tests and nine focused browser regression cases passed. Re-ran all three Relation cases after reviewing the desktop dialog and mobile Vietnamese layout. Present the task for owner review.

- 2026-11-29: The owner approved merging [PR #437](https://github.com/quinguyen1502/superstep/pull/437) into develop. Reviewed head `84357ac2` passed 24 CI checks. The container publish job was skipped. Require CI on the final state-only head before integration.
