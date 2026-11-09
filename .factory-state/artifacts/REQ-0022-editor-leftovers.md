# Requirement

## Metadata

- Project: langgraph-studio
- Requirement ID: REQ-0022
- Status: Implemented
- Owner: Thái Quí Nguyễn
- Created: 2026-10-18
- Updated: 2026-10-18
- Source: owner request 2026-10-18 to handle the leftover editor notes from QA-0031, excluding GitHub Actions.

## Summary

Translate the JSON fold tooltip and cover `spliceNode` with unit tests. Correct the node-colour example that still mentions a left accent bar.

## Problem Or Opportunity

The fold gutter tooltip is English in both languages. Insert-on-edge behaviour has no unit test. `docs/ui-conventions.md` still shows `bg-node-llm` as an accent stripe after the canvas dropped that bar.

## Scope

### In Scope

- `editor.foldLine` and `editor.unfoldLine` in `en.json` and `vi.json`, used by the fold marker.
- Vitest cases for `spliceNode` in `frontend/src/lib/__tests__/graph-ops.test.ts`.
- The accent-stripe example in `docs/ui-conventions.md`.

### Out Of Scope

- Menu visibility rules in `NodeMenu`. Those stay as implemented for REQ-0020.
- GitHub Actions quota, delivery-record status, per-node input schema, `Command`, and `Send`.

## Stakeholders Or Users

- Workflow authors using the JSON editor in Vietnamese
- The next change to insert-before, insert-after, or insert-on-edge

## Current Context

- `foldIcon` in `frontend/src/components/json-editor.tsx` sets `title` to English literals.
- `spliceNode` in `frontend/src/lib/graph-ops.ts` keeps the old edge's fields on the source-to-new half.

## Desired Behavior

- The fold marker title follows the active language.
- The unit tests lock the splice wiring, including the label staying on the first half.

## Business Rules

- UI strings live in both locale files with the same keys.
- Theme tokens stay. This requirement does not add a colour.

## Constraints

- shadcn and theme tokens. No new palette colours.

## Acceptance Criteria

- The fold marker title is "Fold line" / "Unfold line" in English and "Fold lines" / "Unfold lines" in Vietnamese.
- `npm test` covers insert on an edge, insert before, insert after, an anchor with no neighbour, a missing edge or anchor, and clearing the previous selection.
- The conventions example no longer calls `bg-node-llm` an accent stripe.

## Edge Cases

- A missing edge or anchor returns the same node and edge arrays.
- An edge label and the conditional flag stay on the source-to-new half only.

## Assumptions

- The owner approved this pass with the leftover plan. `factory ready` does not exit 0 here. Proceed as with TASK-0033.
- This branch starts from `factory/task-0033-align-delivery-records` so the roadmap edit does not collide. Merge PR #36 before this pull request.

## Open Questions

- None

## Related Artifacts

- `.factory-state/artifacts/REQ-0020-editor-polish-and-readme.md`
- `.factory-state/artifacts/QA-0031-task-0032.md`
- `.factory-state/tasks/done/TASK-0034-editor-leftovers.md`
- `.factory-state/artifacts/REV-0033-task-0034.md`
- `.factory-state/artifacts/QA-0033-task-0034.md`
- `docs/ui-conventions.md`
