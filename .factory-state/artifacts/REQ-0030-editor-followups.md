# Requirement

## Metadata

- Project: langgraph-studio
- Requirement ID: REQ-0030
- Status: Implemented
- Owner: Thái Quí Nguyễn
- Created: 2026-10-18
- Updated: 2026-10-18
- Source: the remaining-work report of 2026-10-18 (items 9 and 11) and the owner's reply, “Except 2, 3, 4. Do the rest”

## Summary

Two editor follow-ups: a key pressed right after picking from the template insert menu goes into the field, and no JavaScript chunk passes Vite's 500 kB warning.

## Problem Or Opportunity

- The insert menu was modal. Focus stayed trapped in the menu until it finished closing, so a key pressed in that moment reached the canvas (Backspace deleted the selected node). QA-0040 recorded this as residual risk.
- The build emitted `Editor` at 827 kB and `index` at 695 kB. Any app change invalidated the cached libraries inside them.

## Scope

### In Scope

- `components/template-editor.tsx` insert menu focus
- Vendor chunks in `frontend/vite.config.ts`

### Out Of Scope

- Replacing or removing libraries; lazy-loading inside the editor

## Stakeholders Or Users

- Workflow authors; anyone loading the UI

## Desired Behavior

- After picking a field from the insert menu, focus is in the editor at once.
- React, CodeMirror, React Flow, the UI primitives, and i18next each load from their own chunk. The first page loads the same libraries as before; CodeMirror still loads only with the editor.

## Business Rules

- None

## Constraints

- No dependency change.

## Acceptance Criteria

- Typing right after picking a field puts the text after the new tag, and the selected node stays.
- `vite build` reports no chunk above 500 kB.
- The full Playwright suite passes.

## Edge Cases

- None

## Assumptions

- A non-modal dropdown is acceptable for a small field menu: it still closes on Escape and on an outside click.

## Open Questions

- None

## Related Artifacts

- Task: `.factory-state/tasks/done/TASK-0043-editor-followups.md`
- QA that recorded the risk: `.factory-state/artifacts/QA-0040-task-0041.md`
