# Review

## Metadata

- Project: superstep
- Review ID: REV-0310
- Task ID: TASK-0326
- Reviewer: implementation review
- Created: 2026-11-13
- Updated: 2026-11-13
- Outcome: approved for QA

## Review Scope

Diff for the Dataset node Delete row editor against REQ-0099, DEC-0098, DES-0007, and the TASK-0326 acceptance criteria. Agent tool settings, public-entry behavior, export generators, the handbook, and the Studio grid delete confirmation were checked to stay unchanged.

## Reference Artifacts

- REQ-0099-dataset-writes.md
- DEC-0098-dataset-delete-and-public.md
- DES-0007-datasets.md
- PLAN-0017-dataset-writes.md

## Findings

### Blocking

- None.

### Non-Blocking

- The runtime still requires one schema field in the binding's `fields` list, although delete returns only the row id. The editor fills that list from the chosen unique field or the first column and hides the Fields to return group for Delete row. Changing the binding contract would also change both export runtimes, so it stays as is.
- The missing-target warning shows as soon as Delete row is chosen, before the author maps a target. This matches the existing Upsert unique-field warning.

## Standards And Architecture Alignment

- The editor saves `row_id` alone, or `key` with `value`, and never both, which is the DEC-0098 argument shape that `dataset_nodes.valid` accepts.
- The key picker lists only columns with the Unique constraint. A key that loses that constraint shows a warning, and the saved binding is still checked by the TASK-0325 authoring rule.
- The grant notice reads `allow_delete` from the existing grant lookup. Read and write permissions do not hide the delete warning.

## Design Alignment

- The new controls reuse the shadcn Select, the existing column picker, the state template editor, and the literal or template value mapping. Alert icons use the shared Alert layout.
- English and Vietnamese catalogs gained the same keys. No literal UI text was added to components.

## Validation Review

- The new Playwright case saves Delete row by unique field, runs it denied without `allow_delete`, runs it after the grant gains delete, and switches to Row ID with the keyboard in Vietnamese.
- Frontend unit tests, type check, lint, and the UI class check passed.

## Assumptions

- Keyboard reachability is shown with the Select and template editor in Vietnamese. The same controls render in English.

## Required Follow-Up

- None for this task. TASK-0331 documents Delete row in the handbook.

## Review Decision

Approved for QA. No blocking findings.
