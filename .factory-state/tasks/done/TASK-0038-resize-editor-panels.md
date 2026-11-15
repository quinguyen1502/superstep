# Task

## Metadata

- Project: langgraph-studio
- Task ID: TASK-0038
- Status: done
- Phase: editor panels
- Owner: Thái Quí Nguyễn
- Created: 2026-10-18
- Updated: 2026-10-18
- Requirement IDs: REQ-0026
- Design IDs:
- Architecture IDs:

## Objective

Let the author drag the editor borders to resize the palette, the config panel, and the run panel.

## Scope

### In Scope

- shadcn Resizable handles on the three borders in `frontend/src/pages/Editor.tsx`
- The same sizes on `EditorSkeleton`
- Remembering the sizes in this browser

### Out Of Scope

- The top header, collapse, reset, and double-click restore
- Storing sizes on the workflow
- Resizing a sticky or a graph node
- The right-click selection change already on `develop`

## Inputs

- `.factory-state/artifacts/REQ-0026-resize-editor-panels.md`

## Related Artifacts

- Requirement: `.factory-state/artifacts/REQ-0026-resize-editor-panels.md`
- UI conventions: `docs/ui-conventions.md`
- Decision: `.factory-state/decisions/DEC-0008-shadcn-ui-and-theme-tokens-only.md`
- Editor: `frontend/src/pages/Editor.tsx`
- Review: `.factory-state/artifacts/REV-0037-task-0038.md`
- QA: `.factory-state/artifacts/QA-0037-task-0038.md`

## Expected Outputs

- The three panels resize by drag and keep those sizes after reload
- `frontend/src/components/ui/resizable.tsx` from the shadcn CLI, moved into `src/components/ui/` with the project's `cn` import
- Aria labels, if the handle needs them, in `frontend/src/locales/en.json` and `vi.json`

## Implementation Notes

- Add the component with `cd frontend && npx shadcn@latest add resizable`. The CLI writes a literal `@/` folder. Move the file into `src/components/ui/` and import `cn` from `"cn"`.
- Default sizes stay 250px, 320px, and 300px. Minimums are 180px, 260px, and 140px. The canvas keeps at least 280px by 160px. The header stays 56px.
- Store the sizes in `localStorage` under one key. Do not put them in the workflow JSON.
- The handle sits on the panel border, so a node drag on the canvas still moves the node.
- The loading skeleton reads the same stored sizes.

## Constraints

- shadcn components and theme tokens. No hard-coded colours. No new API and no new error code.
- Branch `factory/task-0038-resize-editor-panels` from `develop` when the owner asks to start. One Draft PR into `develop`. Do not merge until the owner asks.
- Frontend typecheck is `cd frontend && npx tsc -b`. Do not run `npx tsc` from the repo root.

## Dependencies

- None. Start from `develop`.

## Acceptance Criteria

- Same as REQ-0026.

## Validation Plan

- `cd frontend && npx tsc -b`
- `git diff --check`
- In the browser, drag each of the three borders, confirm the matching panel changes size and a canvas node still drags, reload, and confirm the sizes are still there. Check light and dark.

## Assumptions

- Small-task workflow. Designer and architect are skipped. The interaction is dragging the existing borders, and ui-conventions already requires shadcn Resizable.
- `factory ready` does not exit 0 here. The owner asked for the task anyway. Do not install packages to clear that check.
- GitHub Actions fails from quota. Local checks are the evidence.

## Open Questions

- None

## Activity Log

- 2026-10-18: Owner asked for one task. REQ-0026 approved. Task filed in `todo`. Not started.
- 2026-10-18: Owner asked to complete TASK-0038 ("First finish task 0038"). Branch `factory/task-0038-resize-editor-panels` at `develop` (`00d9a8e`). Task moved to `doing`. `factory ready` still does not exit 0 (the CLI needs `textual`); no packages installed for it.
- 2026-10-18: Implemented. `npx shadcn@latest add resizable` added `react-resizable-panels` 4.14.5; the component moved to `src/components/ui/resizable.tsx`. New `components/editor-layout.tsx` (header + nested vertical/horizontal groups) is used by `Studio` and `EditorSkeleton`. Sizes in px under `localStorage.lgs.editorPanels` (`lib/panel-sizes.ts`). The config panel no longer pins its content to 318px/286px, so a wider panel gives the fields more room. The lockfile carries only the new package. New `e2e/resize.spec.ts` and `lib/__tests__/panel-sizes.test.ts`. README en/vi describe the drag.
- 2026-10-18: REV-0037 has no blocking findings. QA-0037 passed. Task set to done. PR into `develop`. Not merged.
- 2026-10-18: Owner asked to merge ("Merge it"). PR [#41](https://github.com/quinguyen1502/langgraph-studio/pull/41) merged into `develop` (`68512e6`).

## Handoff Notes

- Do not implement until the owner asks to start.
- Branch `factory/task-0038-resize-editor-panels` from `develop`. Do not stack it on an older task branch.
