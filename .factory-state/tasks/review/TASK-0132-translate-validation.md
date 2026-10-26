# Task

## Metadata

- Project: superstep
- Task ID: TASK-0132
- Status: review
- Owner: Thái Quí Nguyễn
- Created: 2026-10-26
- Updated: 2026-10-26
- Requirement IDs: REQ-0045 (Vietnamese language quality)
- Design IDs: none
- Architecture IDs: DEC-0065 (validation message codes), DEC-0010 (API envelope and error codes)

## Objective

Show the workflow check messages in the UI language (owner request in chat on 2026-10-26: "Cả 2 lần lượt", the first
of two). REV-0114 found that a Vietnamese editor listed them in English, for example "1 lỗi cần sửa" over "Retriever
node retrieve: choose a knowledge base".

## Scope

- Every static check message gets a code and parameters (`engine/issues.py`). The English text stays the same.
- The API sends `issues` next to `errors` in `POST /api/validate`, workflow save, template use and the run `error`
  event.
- `validation.<CODE>` in `en.json` and `vi.json`; the editor translates by code and falls back to the English text.

## Out Of Scope

- Runtime errors (a node's exception, `NODE_FAILED`), which are not check messages.
- The detail of a code checker's message (a Python or TypeScript syntax error). Its node prefix is translated.

## Acceptance Criteria

- In Vietnamese, a workflow made from the RAG template lists "Node Retriever retrieve: hãy chọn kho tri thức".
- A run of an invalid workflow lists its problems in Vietnamese.
- `errors` is unchanged for API clients; `issues` has one entry per message, in the same order.
- `en.json` equals the backend's English messages, and `vi.json` has the same keys and follows the glossary.

## Changes

- `engine/issues.py`: `MESSAGES` (132 codes), `Issue` (a `str` with `code` and `params`), `at_node()`, `issues_of()`.
- The checks in `validator`, `templating`, `reducers`, `node_policy`, `code_runtime`, `agents`, `decisions`, `emails`,
  `foreach`, `deadlines`, `subgraphs` and `runtime` (run input) return `Issue`s. `subgraphs.readable()` keeps the code
  and also renames nodes in the parameters.
- `WorkflowService.checked()` returns `errors` and `issues`, for save, template use and `POST /api/validate`.
  `run_service.error_event()` adds `issues`.
- Frontend: `issueTexts()` and `eventErrors()` in `lib/i18n.ts`; the editor's save, the template gallery and run
  errors use them. `validation` in both locales (vi written by hand to the glossary). `validation.NODE_PROBLEM` is on
  the allowlist of strings left the same as en.
- Tests: `tests/test_validation_messages.py` (7), `src/lib/__tests__/issues.test.ts` (2). The e2e checks in
  `templates.spec.ts` and `runtime.spec.ts` now expect the Vietnamese text.
- Handbook `reference/api.md` (en, vi), CHANGELOG (Unreleased), DEC-0065.

## Validation Results

- Backend: the check-related suites (agent, deadlines, decisions, email, foreach, node policy, subgraphs, template
  refs, templates, code) 164 passed, 3 skipped, with no change to their English assertions. The new
  `test_validation_messages.py`, `test_layers.py` and `test_api_envelope.py`: 15 passed.
- Frontend: `tsc -b`, `npm run lint` (with `lint:ui`), vitest 22 files / 107 tests (the locale glossary and
  placeholder checks included).
- e2e `templates`, `runtime`, `subgraphs`: 7 passed. They cover the template list, a run of an invalid workflow, and a
  save with a parallel write, in Vietnamese.
- Local environment note: the frontend `node_modules` had been installed by `factory deps apply` under an x86_64
  Python (Rosetta), so it held `@rollup/rollup-darwin-x64` and vitest failed in an arm64 shell. A native `npm ci` in
  `frontend` and `sdk/typescript` fixed it. Nothing in the repository changed.

## Review And QA

- Review: REV-0116 (no blocking findings). QA: QA-0116 (pass). Full backend suite: 729 passed, 56 skipped.
