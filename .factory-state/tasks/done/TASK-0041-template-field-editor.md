# Task

## Metadata

- Project: langgraph-studio
- Task ID: TASK-0041
- Status: done
- Phase: editor maintenance
- Owner: Thái Quí Nguyễn
- Created: 2026-10-18
- Updated: 2026-10-18
- Requirement IDs: REQ-0029
- Design IDs:
- Architecture IDs:

## Objective

Add a shared template editor with state field tags and use it for every node field that the backend renders as a `{{state.field}}` template.

## Scope

### In Scope

- `frontend/src/components/template-editor.tsx`
- `components/editor/editor-config.tsx` (LLM, Human, HTTP Tool, Retriever) and `components/mcp-settings.tsx`
- `components/editor/editor-header.tsx` (header layout) and `components/ui/button.tsx` (`sm` icon offset), added by the owner during the task
- Locale strings, Playwright specs

### Out Of Scope

- Backend changes, new template syntax

## Inputs

- `.factory-state/artifacts/REQ-0029-template-field-editor.md`

## Related Artifacts

- Requirement: `.factory-state/artifacts/REQ-0029-template-field-editor.md`
- Templating: `backend/app/engine/templating.py`
- UI conventions: `docs/ui-conventions.md`
- Review: `.factory-state/artifacts/REV-0040-task-0041.md`
- QA: `.factory-state/artifacts/QA-0040-task-0041.md`

## Constraints

- Branch from `develop` after PR #43 (`c74814f`). One PR into `develop`. Do not merge until the owner asks.

## Dependencies

- TASK-0040 (PR #43), merged.

## Acceptance Criteria

- Same as REQ-0029.

## Validation Plan

- `cd frontend && npx tsc -b && npx vitest run && npx oxlint && npx vite build`
- `cd frontend && PW_CHROME=... E2E_UVICORN=../backend/.venv/bin/uvicorn npx playwright test`
- `git diff --check`

## Assumptions

- `factory ready` does not exit 0 here (the CLI needs `textual`). GitHub Actions does not run (billing). Local checks are the evidence.

## Open Questions

- None

## Activity Log

- 2026-10-18: Filed from the owner's request. REQ-0029 approved by that request. Branch `factory/task-0041-template-editor` from `develop` (`c74814f`); task moved to `doing`.

- 2026-10-18: `components/template-editor.tsx` (CodeMirror: atomic tags for `{{state.x}}`, missing fields marked, `{{` completion, insert-field menu, one-line mode, read-only for viewers) and `lib/state-refs.ts` (the backend `VAR_RE`). Used for the LLM prompt, Human prompt, HTTP URL and body, Retriever query, and MCP arguments. The owner then asked for the header overlap ("Fix this breaking layout while you are at it") and the button icon offset ("the text keeps sitting off the icon"): the header keeps the back button and logo, hides the product name by container query, and lets the name field shrink; `sm` buttons move the icon up 1px (measured). REV-0040 has no blocking findings. QA-0040 passed. Task set to done. PR into `develop`. Not merged.

## Handoff Notes

- None.
