# Task

## Metadata

- Project: superstep
- Task ID: TASK-0146
- Status: review
- Owner: Thái Quí Nguyễn
- Created: 2026-10-27
- Updated: 2026-10-27
- Requirement IDs: none (owner request)
- Design IDs: none
- Architecture IDs: DEC-0008 (UI conventions)

## Objective

Fix three layout faults in the run trace, from the owner's screenshots on 2026-10-27 ("Sửa nhanh UI. 1. Bị break
2. Thụt vào cân đối hơn"; "Xem lại cái divider này luôn").

## Scope

### In Scope

- `frontend/src/components/run-trace.tsx`:
  - the summary bar: items such as "66 ms", "36 token" and "Hoàn thành" no longer break inside; the bar wraps between
    items when it is narrow;
  - its vertical divider stays 16 px and centred (the shadcn vertical Separator stretches to the tallest item);
  - a workflow tool's child steps: their line sits under the tool call's icon, and the block ends at the duration
    column, so "Open run" and the times line up with the rows above.

### Out Of Scope

- The chat's step list, which uses the same child steps block with its own margins.

## Inputs

- The owner's screenshots of the trace in Vietnamese.

## Related Artifacts

- Requirements: none
- Design: none
- Architecture: none
- Decisions: `docs/ui-conventions.md` (DEC-0008)
- Discovery: none

## Expected Outputs

- The trace summary and the nested steps read cleanly in en and vi.

## Implementation Notes

- Class changes only. The divider override uses the Separator's own `data-[orientation=vertical]` variant, with a
  `ui-class-ok` note.

## Constraints

- shadcn/ui and theme tokens only.

## Dependencies

- None.

## Acceptance Criteria

- No item in the summary bar breaks inside, in en or vi.
- The divider is as tall as the text.
- The child steps block sits under the tool call and ends at the duration column.

## Validation Plan

- `cd frontend && npm run lint && npx tsc -b`
- `npx playwright test e2e/workflow-tools.spec.ts` with `REVIEW_SHOTS`

## Assumptions

- None.

## Open Questions

- None.

## Activity Log

- 2026-10-27: asked for by the owner and fixed on `factory/task-0146-trace-summary-layout`.

## Handoff Notes

- Review: class-only change in one component; lint, `tsc -b` and `lint:ui --strict` pass.
- QA: `e2e/workflow-tools.spec.ts` 6 passed (en and vi). Screenshots of the waiting and finished parent runs show the
  summary on one line per item, the short divider, and the child steps under the tool call.
