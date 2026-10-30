# Task

## Metadata

- Project: superstep
- Task ID: TASK-0183
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-30
- Updated: 2026-10-30
- Requirement IDs: REQ-0078
- Design IDs: none
- Architecture IDs: DEC-0073

## Objective

Export hand-offs to Python, the LangGraph project and TypeScript.

## Scope

### In Scope

- Python export and the LangGraph project: transfer tools and the router after the agent's exit, the limit, and the start-agent input.
- TypeScript export: the same with LangGraph.js.
- Snapshot tests, the Python run test with a fake model, and `deno check` for TypeScript.

### Out Of Scope

- Engine (TASK-0180).

## Inputs

- REQ-0078 'Exports'; DEC-0073 decision 5.
- `engine/python_export.py`, `engine/project_export.py`, `engine/typescript_export.py`, `engine/export_common.py`.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0078-agent-handoff.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0073-agent-handoff.md`
- Decisions: `DEC-0009-layered-backend-sqlalchemy-alembic.md`, `DEC-0010-api-envelope-error-codes-i18n.md`, `DEC-0008` (`docs/ui-conventions.md`), `DEC-0033` (task branches from `develop`)
- Discovery: `.factory-state/artifacts/DISC-0001-project-context.md`
- Clarifications: `.factory-state/artifacts/CLAR-0009-agent-handoff.md`

## Expected Outputs

- Exported code compiles and runs a hand-off.

## Implementation Notes

- Mirror the engine's expansion so the exported graph and the studio trace match step names.

## Constraints

- Layers of DEC-0009: routes call services, services call repositories, no FastAPI in a service, no SQLAlchemy in a route. `tests/test_layers.py` passes.
- Every API error uses the common envelope with an English error code listed in `core/errors.py` CATALOG, `docs/api-errors.md`, and `frontend/src/locales/en.json` and `vi.json`. `tests/test_api_envelope.py` passes.
- UI uses shadcn/ui components and theme tokens only. en and vi locale files keep the same keys.
- Schema changes go through a new Alembic revision after the latest one on `develop` at branch time.
- No new heavy dependency.

## Dependencies

- TASK-0180.

## Acceptance Criteria

- A Triage → Billing workflow exports to Python, the LangGraph project and TypeScript; the Python run test hands off with a fake model; `deno check` passes; snapshots updated.

## Validation Plan

- `cd backend && .venv/bin/python -m pytest -q`
- `cd backend && .venv/bin/python -m pytest -q tests/test_layers.py tests/test_api_envelope.py`

## Assumptions

- The designer step is skipped. REQ-0078 and its CLAR already describe the screens.

## Open Questions

- None. DEC-0073 is accepted.

## Activity Log

- 2026-10-30: planned from REQ-0078 (DEC-0073). Status todo. Not started.
- 2026-10-30: owner confirmed the task set and accepted the decision record.
- 2026-10-30: implemented on `factory/task-0183-handoff-exports` from `develop`. Hand-offs export to Python, the LangGraph project and TypeScript `factory verify run --profile full` passed. The owner authorized the merge of the REQ-0077/REQ-0078 task PRs. Moved to done on this PR before the merge (TASK-0148).

## Handoff Notes

- Branch `factory/task-0183-agent-handoff-exports` from `develop`.
- Review: `.factory-state/artifacts/REV-0160-task-0183.md`. QA: `.factory-state/artifacts/QA-0160-task-0183.md`.
