# Task

## Metadata

- Project: langgraph-studio
- Task ID: TASK-0055
- Status: done
- Phase: nodes
- Owner: Thái Quí Nguyễn
- Created: 2026-10-19
- Updated: 2026-10-19
- Requirement IDs: REQ-0039
- Design IDs: none. The layout follows the existing Tool node config and template editor (DEC-0008, `docs/ui-conventions.md`); this is noted as a designer skip.
- Architecture IDs: DEC-0041, DEC-0008, DEC-0009

## Objective

In the editor, a user with `code.write` can pick **Code** for a Tool node, write `main(state)` with syntax highlighting, and test it against a sample state. Results, `print()` output and errors appear in the run panel and trace.

## Scope

### In Scope

- `GET /api/meta/runtime` (`api/routes/meta.py`) returns `{code_runtime, image, limits, packages}`. The frontend reads it once through `lib/api.ts`.
- `POST /api/workflows/{id}/nodes/{node_id}/test-code` with body `{source, state}`:
  - it needs run access and `code.write`;
  - it calls `run_code`, writes no run, and is rate-limited per user;
  - it goes route → service → engine.
- Editor (`components/editor/editor-config.tsx`):
  - a third Tool mode, **Code**;
  - a CodeMirror Python editor (`@codemirror/lang-python`, reusing the template editor's theme setup so light and dark use tokens);
  - a starter `def main(state):` template;
  - the image's package list;
  - the output field;
  - **Test with sample state**, using the run panel input, with the result, stdout and error shown inline.
- Read-only code and no test button for users without `code.write`, with a hint saying why.
- When `code_runtime` is `off`, the Code mode is shown disabled with a hint.
- Run panel and trace (`editor-run-panel.tsx`, the trace timeline): Code calls show the value, the truncated stdout and the traceback, with one row per loop iteration.
- Every string in en and vi. shadcn components only.
- Playwright e2e:
  - write code, test it, run the workflow, see the output in the next node;
  - an error with a traceback;
  - read-only for an editor.
  - The e2e server must start with the Code mode turned on, and it skips when Docker is missing.
- README en and vi: a short "Code mode" section with an example.

### Out Of Scope

- Subprocess warnings (TASK-0056).
- Autocomplete or a language server for Python.

## Inputs

- REQ-0039 Desired Behavior and Acceptance Criteria, DEC-0041 decisions 6 and 7.
- `components/editor/editor-config.tsx`, `use-studio.ts`, `editor-run-panel.tsx`, the template editor (CodeMirror setup), `lib/rbac.ts`, `api/routes/meta.py`.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0039-tool-code-mode.md`
- Design: none (the existing editor patterns are followed)
- Architecture: `.factory-state/decisions/DEC-0041-tool-code-mode.md`
- Decisions: DEC-0008, DEC-0041
- Discovery: none
- Clarifications: `.factory-state/artifacts/CLAR-0001-tool-code-mode.md`

## Expected Outputs

- Backend: the meta runtime route, the test-code route and service method, and pytest.
- Frontend:
  - the Code mode UI and a `code-editor` component;
  - trace and run panel display;
  - locales en and vi;
  - `e2e/code-node.spec.ts`.
- README en and vi.

## Implementation Notes

- The template editor already uses `@uiw/react-codemirror`. Add `@codemirror/lang-python` at an exact, published version.
- Send unsaved source in the test body, so a user can test before saving.

## Constraints

- shadcn and theme tokens only; no hard-coded colours.
- Call the API only through `api()`, and show errors through `errorText`.

## Dependencies

- TASK-0053 (runtime and node mode) and TASK-0054 (`code.write`).

## Acceptance Criteria

- A user with `code.write` writes `return state["message"].upper()`, tests it against the sample input, sees the value, saves, runs, and the next node shows the upper-cased message.
- Raising an exception shows the traceback in the test result and in the trace, and the run fails.
- An editor sees the code read-only, cannot test it, and can still run the workflow.
- With the runtime `off`, the Code mode is disabled and a hint explains why.
- vitest, tsc, oxlint, the build and the e2e spec pass.

## Validation Plan

- `cd backend && .venv/bin/python -m pytest -q`
- `cd frontend && npx tsc -b && npx vitest run && npx oxlint && npx vite build`
- `cd frontend && PW_CHROME=… E2E_UVICORN=../backend/.venv/bin/uvicorn npx playwright test e2e/code-node.spec.ts`

## Assumptions

- The run panel's input JSON is a good enough sample state.

## Open Questions

- None.

## Activity Log

- 2026-10-19: Created from REQ-0039; not started.
- 2026-10-19: Task set and DEC-0041 approved by the owner ("Approve the task set and DEC-0041").
- 2026-10-19: Started on `factory/task-0055-code-mode-editor`, branched from TASK-0054 (owner: "Do the tasks as one chain: 54, 55, 56").
- 2026-10-19: Implemented. Test with sample state is `POST /api/code/test`; see the DEC-0041 addendum. Review REV-0052, QA QA-0052 (pass). PR open; not merged.
- 2026-10-19: Merged in PR #63 (owner: "Merge PR #62, #63, #64 in turn").

## Handoff Notes

- TASK-0056 adds the subprocess badges and Alert in the same components.
