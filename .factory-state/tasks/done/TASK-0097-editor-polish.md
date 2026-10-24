# Task

## Metadata

- Project: superstep
- Task ID: TASK-0097
- Status: done (backfilled)
- Owner: Thái Quí Nguyễn
- Created: 2026-10-22
- Updated: 2026-10-24
- Requirement IDs: REQ-0058
- Design IDs: none
- Architecture IDs: none
- Pull request: [#104](https://github.com/quinguyen1502/superstep/pull/104) `fix/editor-polish`
- Merge commit: `e899c368cc4f79263c64b16494f880b5e856f722` (2026-10-22)

## Objective

Editor polish: focus ring, quoted node names, split left panel, Add node.

> Backfilled 2026-10-24 (TASK-0093): reconstructed from the PR description and diff after the fact; the work was merged outside the factory workflow, so no task, review or QA record existed at the time.

## Scope (from the PR)

- **Focus ring in the test case dialog.** The scroll area now has 4 px of room on every side (`-mx-1 px-1 py-1`, the same pattern the API, schedules and chat-trigger dialogs use), so an input's focus ring is no longer cut off.
- **Node names in quotes.** UI text that names a node now puts the name in quotes, for example `Showing “Classify intent”` / `Đang chỉ “Classify intent”`. A name written in one language no longer runs into a sentence in another. Strings changed in en and vi: `codeView.showing`, `editor.runToTip`, `transfer.rebindFor`, `transfer.flaggedLine`, and the test check results `ran`, `notRan` and `no_answer`. Error-catalog messages are unchanged.
- **Left panel in two halves.** The node palette and the state schema each take half the panel and scroll separately. **Add field** stays visible under the schema, so a long node list no longer pushes the schema out of view.
- **Add node on the canvas.** Right-click on an empty part of the canvas to get **Add node** (a submenu of node types). The new node goes where you clicked and is selected. **Add note** is the next item.
- `tsc -b`: passes.
- `oxlint`: no findings.
- `vitest`: 64 of 64 pass.
- Playwright specs run locally: `canvas-menu` (new), `code-export`, `workflow-tests` and `clipboard`, all passing.
- I compared screenshots of the dialog, the left panel and the right-click menu by eye.

## Changed files

- 8 files: `frontend/e2e/canvas-menu.spec.ts`, `frontend/e2e/code-export.spec.ts`, `frontend/src/components/editor/editor-canvas.tsx`, `frontend/src/components/editor/editor-palette.tsx`, `frontend/src/components/editor/editor-tests-panel.tsx`, `frontend/src/components/editor/use-studio.ts`, `frontend/src/locales/en.json`, `frontend/src/locales/vi.json`.

## Activity Log

- 2026-10-22: merged into develop (e899c36).
- 2026-10-24: task record backfilled (TASK-0093); verified retroactively on develop by QA-0085.

## Handoff Notes

- Review REV-0089, QA QA-0089 (retroactive records).
