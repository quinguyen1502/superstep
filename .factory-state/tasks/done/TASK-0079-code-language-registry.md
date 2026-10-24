# Task

## Metadata

- Project: superstep
- Task ID: TASK-0079
- Status: done (PR #109)
- Owner: Thái Quí Nguyễn
- Created: 2026-10-23
- Updated: 2026-10-23
- Requirement IDs: REQ-0046
- Design IDs: none
- Architecture IDs: DEC-0048

## Objective

Make the Tool node Code mode language-pluggable without changing what Python users see, so TypeScript (TASK-0080) is one new strategy.

## Scope

### In Scope

- `engine/code_languages.py`: `CodeLanguage` interface (problems, command, host_command, host_env, image, packages, host_problem, starter), `Python` strategy, `LANGUAGES`, `language_of`, `enabled`, `get`.
- `code_runtime.run_code/problems/unavailable/runtime_error` take a `language` (default Python); everything shared (payload, limits, kill, result parsing, error codes) stays in one place.
- `data.language` on Code-mode Tool nodes; missing = `python` (no migration).
- `STUDIO_CODE_LANGUAGES` (default `python`).
- `CODE_LANGUAGE_UNSUPPORTED` (400) in `core/errors.py`, `docs/api-errors.md`, en/vi locales.
- `code.write`: switching a node's language counts as writing code (`permissions.code_sources`).
- Validator checks per language; `/api/meta/runtime` adds `languages[]`; `/api/code/test` takes `language`.
- Python export writes a `NotImplementedError` stub for a non-Python Code node.

### Out of Scope

- P3 items of REQ-0046 (type-check diagnostics, LangGraph.js export, full IntelliSense).

## Tests

- `tests/test_code_languages.py` (8 tests); existing Code-mode tests unchanged in behaviour (monkeypatched `unavailable` now accepts the language argument).

## Progress Log

- 2026-10-23: merged into develop (PR #109, merge commit 9ff7259); marked done in PR #110 since #109 is already merged.

## Handoff Notes

- Backfilled 2026-10-24 (TASK-0093): Review REV-0072; QA QA-0072; develop verified retroactively by QA-0085.
