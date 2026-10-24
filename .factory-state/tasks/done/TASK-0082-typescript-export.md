# Task

## Metadata

- Project: superstep
- Task ID: TASK-0082
- Status: done (PR #112)
- Owner: Thái Quí Nguyễn
- Created: 2026-10-23
- Updated: 2026-10-23
- Requirement IDs: REQ-0047
- Design IDs: none
- Architecture IDs: DEC-0051

## Objective

Export a workflow as a runnable LangGraph.js TypeScript file next to the Python export.

## Scope

### In Scope

- `engine/export_common.py`: the language-neutral half (sanitised graph, names, order, subgraphs, fields, helpers a
  graph needs, example input) as `GraphWriter`; `python_export` now subclasses it (same output, byte for byte).
- `engine/typescript_export.py`: `to_typescript`, the LangGraph.js writer; `engine/exporters.py`: the registry.
- `WorkflowService.export(language)`; `GET /workflows/{wid}/code?language=`, `/python?language=`,
  `/export/{language}`; `EXPORT_LANGUAGE_UNSUPPORTED`, `TYPESCRIPT_EXPORT_UNAVAILABLE`.
- Code tab: shadcn `Select` Python / TypeScript (remembered), TypeScript highlighting, `Download .ts`; en/vi.
- Handbook `guide/python-export.md` and `reference/api.md` (en, vi).
- Tests: snapshot and unit tests, API, `deno check` + run against the studio's mock path; vitest; e2e.

### Out of Scope

- Type-check diagnostics in the editor, full IntelliSense, porting Python tool functions.

## Tests

- `tests/test_typescript_export.py` (snapshot `tests/snapshots/typescript_export_demo.ts`), `test_python_export.py`
  unchanged and green, vitest `code-export.test.ts`, e2e `code-export.spec.ts`.

## Progress Log

- 2026-10-23: owner approved the merge; merged into develop (PR #112).

## Handoff Notes

- Backfilled 2026-10-24 (TASK-0093): Review REV-0075; QA QA-0075; develop verified retroactively by QA-0085.
