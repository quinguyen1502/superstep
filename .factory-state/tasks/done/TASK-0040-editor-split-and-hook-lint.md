# Task

## Metadata

- Project: langgraph-studio
- Task ID: TASK-0040
- Status: done
- Phase: editor maintenance
- Owner: Thái Quí Nguyễn
- Created: 2026-10-18
- Updated: 2026-10-18
- Requirement IDs: REQ-0028
- Design IDs:
- Architecture IDs:

## Objective

Split `Editor.tsx` into components and hooks, and clear the React hook oxlint warnings, with no behaviour change.

## Scope

### In Scope

- `frontend/src/pages/Editor.tsx` → `frontend/src/components/editor/*` and `frontend/src/lib/use-editor-*.ts`
- A shared load-on-open hook for the dialogs and settings sections listed by `npx oxlint`
- `lib/use-graph-history.ts` and `lib/use-shortcuts.ts` ref warnings

### Out Of Scope

- Visual or behaviour changes, new routes, backend changes

## Inputs

- `.factory-state/artifacts/REQ-0028-editor-split-and-hook-lint.md`

## Related Artifacts

- Requirement: `.factory-state/artifacts/REQ-0028-editor-split-and-hook-lint.md`
- UI conventions: `docs/ui-conventions.md`
- Editor: `frontend/src/pages/Editor.tsx`
- Review: `.factory-state/artifacts/REV-0039-task-0040.md`
- QA: `.factory-state/artifacts/QA-0039-task-0040.md`

## Constraints

- Started after PR #41 and PR #42 merged into `develop`; the planning branch was rebased onto `develop` (`5f303db`).
- One PR into `develop`. Do not merge until the owner asks.

## Dependencies

- TASK-0038 (PR #41) and TASK-0039 (PR #42), both merged.

## Acceptance Criteria

- Same as REQ-0028.

## Validation Plan

- `cd frontend && npx tsc -b && npx vitest run && npx oxlint && npx vite build`
- `cd frontend && PW_CHROME=... E2E_UVICORN=../backend/.venv/bin/uvicorn npx playwright test`, compared with `develop`
- `git diff --check`

## Assumptions

- `factory ready` does not exit 0 here (the CLI needs `textual`). GitHub Actions does not run (billing). Local checks are the evidence.

## Open Questions

- None

## Activity Log

- 2026-10-18: Filed from the project review follow-up after TASK-0039. REQ-0028 approved by the owner's request to resolve the remaining items. Waiting for PR #41 and PR #42.
- 2026-10-18: Owner said "Merge it". PR #41 and PR #42 merged into `develop` (`5f303db`). Branch rebased onto it; task moved to `doing`.
- 2026-10-18: `Editor.tsx` split into `components/editor/` (generated from the old line ranges so the JSX is unchanged): `use-studio.ts`, `studio-context.ts`, `meta.ts`, `canvas-nodes.tsx`, `canvas-edit.ts`, `node-types.ts`, `parts.tsx`, `editor-skeleton.tsx`, and five panels. oxlint 46 → 0: `lib/use-when.ts` (`useLoadWhen`, `useOnChange`), `useEffectEvent` in `use-studio` and `use-shortcuts`, state instead of a render-time ref in `use-graph-history`, hooks moved out of component files, shadcn variant exports annotated. REV-0039 has no blocking findings. QA-0039 passed. Task set to done. PR into `develop`. Not merged.

## Handoff Notes

- None.
