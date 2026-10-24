# Task

## Metadata

- Project: superstep
- Task ID: TASK-0081
- Status: done (PR #111)
- Owner: Thái Quí Nguyễn
- Created: 2026-10-23
- Updated: 2026-10-23
- Requirement IDs: REQ-0046
- Design IDs: none
- Architecture IDs: DEC-0050

## Objective

Let people with `code.write` pick Python or TypeScript in Code mode and see the state's type while writing TypeScript.

## Scope

### In Scope

- `CodeEditor` (CodeMirror, python | typescript) replaces the Python-only editor; `PythonEditor` stays as a thin wrapper for the Code tab.
- Language picker in Code mode (only languages the server offers); switching replaces only an untouched starter (edited code is kept, with a hint); TS starter from the server.
- Generated `State` type from the workflow's state schema, shown above the editor and offered as `state.` completions.
- Admin card: one row per language (image, packages, availability).
- en/vi strings (parity test, glossary), handbook `guide/code-mode.md` en/vi.
- vitest and an e2e TypeScript variant of the subprocess spec.

### Out of Scope

- P3 items of REQ-0046 (type-check diagnostics, LangGraph.js export, full IntelliSense).

## Tests

- vitest (`state-type`, `code-editor`), e2e `code-typescript.spec.ts`.

## Progress Log

- 2026-10-23: owner approved the merge; merged into develop (PR #111).

## Handoff Notes

- Backfilled 2026-10-24 (TASK-0093): Review REV-0074; QA QA-0074; develop verified retroactively by QA-0085.
