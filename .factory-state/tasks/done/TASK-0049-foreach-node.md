# Task

## Metadata

- Project: langgraph-studio
- Task ID: TASK-0049
- Status: done
- Phase: engine
- Owner: Thái Quí Nguyễn
- Created: 2026-10-19
- Updated: 2026-10-19
- Requirement IDs: REQ-0035
- Design IDs: DEC-0038
- Architecture IDs: DEC-0009, DEC-0018

## Objective

A For each node that runs a branch once per item of a list field.

## Scope

### In Scope

- Backend: `engine/foreach.py` (node function, router, validation, step budget), `engine/validator.py`, `engine/compiler.py`, `engine/nodes.py`, `engine/runtime.py`
- Frontend: `components/editor/{meta.ts,use-studio.ts,editor-config.tsx}`, `components/template-preview.tsx`, `index.css` (`--node-foreach*`), locales
- Tests: `backend/tests/test_foreach.py`, `test_core_hardening.py` (loop message), `frontend/e2e/foreach.spec.ts`; `e2e/template-filters.spec.ts` now signs in with the shared helper (it read the token from localStorage, which TASK-0045 removed, so it failed on develop after #48 and #49 merged)
- Docs: both READMEs

### Out Of Scope

- Parallel items (`Send`)

## Inputs

- `.factory-state/artifacts/REQ-0035-foreach-node.md`

## Related Artifacts

- Requirement: `.factory-state/artifacts/REQ-0035-foreach-node.md`
- Decision: `.factory-state/decisions/DEC-0038-foreach-node.md`
- Review: `.factory-state/artifacts/REV-0046-task-0049.md`
- QA: `.factory-state/artifacts/QA-0046-task-0049.md`

## Constraints

- Do not merge until the owner asks.

## Dependencies

- None (branched from develop at `02ba4d0`).

## Acceptance Criteria

- Same as REQ-0035.

## Validation Plan

- `cd backend && .venv/bin/python -m pytest -q`
- `cd frontend && npx tsc -b && npx vitest run && npx oxlint && npx vite build`
- `cd frontend && PW_CHROME=… E2E_UVICORN=../backend/.venv/bin/uvicorn npx playwright test`
- `git diff --check`

## Assumptions

- `factory ready` does not exit 0 here (the CLI needs `textual`). GitHub Actions does not run (billing). Local checks are the evidence.

## Open Questions

- None

## Activity Log

- 2026-10-19: The owner asked whether LangGraph supports a loop node, then "OK, build that too". Built on LangGraph cycles with sequential items (DEC-0038). Found in review: the parallel-writes check treated `each` and `done` as parallel branches; For each now counts as one route at a time, with a test. Found by the full e2e run: `template-filters.spec.ts` still read the token from localStorage; fixed.
