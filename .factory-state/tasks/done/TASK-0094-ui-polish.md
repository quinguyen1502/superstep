# Task

## Metadata

- Project: superstep
- Task ID: TASK-0094
- Status: done (backfilled)
- Owner: Thái Quí Nguyễn
- Created: 2026-10-19
- Updated: 2026-10-24
- Requirement IDs: REQ-0056
- Design IDs: none
- Architecture IDs: none
- Pull request: [#57](https://github.com/quinguyen1502/superstep/pull/57) `fix/ui-polish`
- Merge commit: `0201b4724586db453f511e1f088a3d0872b8a651` (2026-10-19)

## Objective

UI polish: tooltips, shortcut keys, history columns, extra Start/End.

> Backfilled 2026-10-24 (TASK-0093): reconstructed from the PR description and diff after the fact; the work was merged outside the factory workflow, so no task, review or QA record existed at the time.

## Scope (from the PR)

- **Shortcut cheat sheet**: key symbols (⌘ ⇧ ↵ ⌫) now sit in the middle of their key boxes, and the wider dialog keeps every label on one line.
- **Template editor**: clicking anywhere in the box puts the cursor in it, including when the field is empty.
- **Raw events**: when a long line wraps, the continuation lines up with the text instead of running under the line number.
- **Run history**: each column has a fixed width, and the error badge has its own slot, so the rows line up.
- **Workflow list**: the "All workflows" switch now comes before the search box.
- **Tooltips**: the browser's built-in `title` tooltips are replaced with the shadcn Tooltip, through a shared `Tip` component, in 11 places (password reset, theme, language, copy JSON, Insert field, canvas lock, badges, long names).
- **Start/End**: extra Start or End nodes can now be deleted from the selection or the context menu. One of each always stays.
- **Records**: REQ-0038 and TASK-0052 (profile page and password change) are added to the backlog as todo. The roadmap marks TASK-0051 as merged (#56).

## Changed files

- 22 files: `.factory-state/artifacts/REQ-0038-profile-and-password.md`, `.factory-state/tasks/todo/TASK-0052-profile-and-password.md`, `frontend/e2e/studio.spec.ts`, `frontend/src/components/credentials-dialog.tsx`, `frontend/src/components/editor/editor-canvas.tsx`, `frontend/src/components/editor/editor-header.tsx`, `frontend/src/components/editor/editor-run-panel.tsx`, `frontend/src/components/editor/parts.tsx`, `frontend/src/components/json-view.tsx`, `frontend/src/components/language-switcher.tsx`, `frontend/src/components/run-trace.tsx`, `frontend/src/components/shortcut-cheatsheet.tsx`, `frontend/src/components/template-editor.tsx`, `frontend/src/components/theme-toggle.tsx`, `frontend/src/components/tip.tsx`, `frontend/src/lib/__tests__/graph-ops.test.ts`, `frontend/src/lib/graph-ops.ts`, `frontend/src/locales/en.json`, `frontend/src/locales/vi.json`, `frontend/src/pages/Workflows.tsx`, `frontend/src/pages/settings/UsersSection.tsx`, `roadmap.md`.

## Activity Log

- 2026-10-19: merged into develop (0201b47).
- 2026-10-24: task record backfilled (TASK-0093); verified retroactively on develop by QA-0085.

## Handoff Notes

- Review REV-0086, QA QA-0086 (retroactive records).
