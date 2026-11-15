# Requirement

## Metadata

- Project: langgraph-studio
- Requirement ID: REQ-0026
- Status: Implemented
- Owner: Thái Quí Nguyễn
- Created: 2026-10-18
- Updated: 2026-10-18
- Source: owner request 2026-10-18, “add a task for drag-resizing the panels.”

## Summary

The author can drag the editor panel borders to change the size of the palette, the config panel, and the run panel.

## Problem Or Opportunity

Those three panels have fixed sizes. A long prompt, a wide graph, or a tall trace cannot be given more room without changing the code.

## Scope

### In Scope

- Drag the border between the left palette and the canvas.
- Drag the border between the canvas and the right config panel.
- Drag the border between the canvas row and the bottom run panel.
- Remember the three sizes in this browser.

### Out Of Scope

- Resizing the top header.
- Collapsing a panel, a reset button, and a double-click to restore the default.
- Saving the sizes on the workflow, so another author does not inherit them.
- Resizing a sticky note or a graph node.

## Stakeholders Or Users

- Workflow authors using the editor

## Current Context

- `Studio` in `frontend/src/pages/Editor.tsx` is a fixed grid: header `56px`, left column `250px`, right column `320px`, bottom row `300px`, canvas filling the rest.
- The left panel is the palette and the state schema. The right panel is the node or edge config. The bottom panel is run input, logs, and history.
- `EditorSkeleton` uses the same fixed grid.
- `docs/ui-conventions.md` rule 1 names shadcn Resizable. `frontend/src/components/ui/` does not have it yet.
- The right-click selection fix on `develop` is a separate change and is not part of this requirement.

## Desired Behavior

- Each of the three borders has a drag handle. Dragging it changes only that panel's size. The canvas takes the space that is left.
- The header stays `56px`.
- A drag stops at a minimum, so none of the palette, the config panel, the run panel, or the canvas disappears.
- The starting sizes stay `250px`, `320px`, and `300px` until the author drags.
- After a reload, and after opening another workflow, the dragged sizes are still there.
- Dragging a node on the canvas still moves that node.

## Business Rules

- Sizes live in this browser only. They are not fields on the workflow document.
- View-only and imported graphs use the same chrome, so their panels resize too.
- Any new UI string is in `en.json` and `vi.json` with the same keys.

## Constraints

- Use the shadcn Resizable component. No hand-rolled drag layer and no hard-coded colours.
- No new API route and no new error code.

## Acceptance Criteria

- Dragging the left border changes the palette width. Dragging the right border changes the config width. Dragging the top of the run panel changes its height.
- The palette cannot go below 180px, the config panel cannot go below 260px, the run panel cannot go below 140px, and the canvas keeps at least 280px of width and 160px of height.
- The header stays 56px.
- Reload keeps the three sizes. Opening a different workflow keeps them too.
- A node drag on the canvas does not resize a panel.

## Edge Cases

- A viewport too small for every minimum shrinks the canvas down to its minimum and then the drag stops.
- The loading skeleton uses the remembered sizes, so the editor does not jump when the workflow appears.
- Clearing the site data restores 250px, 320px, and 300px.

## Assumptions

- One task. Designer and architect are skipped: the owner asked to drag the existing panel borders, and ui-conventions already names shadcn Resizable.
- Sizes are remembered in `localStorage`, not on the workflow.
- `factory ready` does not exit 0 on this machine. The owner asked for the task anyway. Do not install packages to clear it.

## Open Questions

- None

## Related Artifacts

- Task: `.factory-state/tasks/done/TASK-0038-resize-editor-panels.md`
- UI conventions: `docs/ui-conventions.md`
- Decision: `.factory-state/decisions/DEC-0008-shadcn-ui-and-theme-tokens-only.md`
