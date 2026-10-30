# Task

## Metadata

- Project: superstep
- Task ID: TASK-0179
- Status: todo
- Owner: Thái Quí Nguyễn
- Created: 2026-10-30
- Updated: 2026-10-30
- Requirement IDs: REQ-0078
- Design IDs: none
- Architecture IDs: DEC-0073

## Objective

Add hand-off targets to the Agent node and the hand-off limit to the workflow, with save-time validation.

## Scope

### In Scope

- Agent node data `handoffs: [{target: <node id>, description}]`; workflow setting `max_handoffs` (default 5, 0 to 20).
- Validator: a target must be another Agent node in the same workflow or the same subgraph; not itself; unique per node. Errors `AGENT_HANDOFF_TARGET_INVALID` (translated issue message) on save and run.
- Deleting an Agent node removes it from other nodes' target lists in the editor model; the server refuses dangling targets.
- Workflow JSON schema and the TypeScript SDK types gain the fields.

### Out Of Scope

- Engine routing (TASK-0180).
- Canvas (TASK-0182).

## Inputs

- REQ-0078 'Hand-off targets', 'Limit'; DEC-0073 decision 1.
- `engine/validator.py`, `engine/agents.py`, `engine/issues.py`, `schemas` for workflows.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0078-agent-handoff.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0073-agent-handoff.md`
- Decisions: `DEC-0009-layered-backend-sqlalchemy-alembic.md`, `DEC-0010-api-envelope-error-codes-i18n.md`, `DEC-0008` (`docs/ui-conventions.md`), `DEC-0033` (task branches from `develop`)
- Discovery: `.factory-state/artifacts/DISC-0001-project-context.md`
- Clarifications: `.factory-state/artifacts/CLAR-0009-agent-handoff.md`

## Expected Outputs

- Workflows with hand-off targets save and validate.

## Implementation Notes

- Keep the targets in node data, not as edges, so the canvas links are derived (DEC-0073 decision 1).

## Constraints

- Layers of DEC-0009: routes call services, services call repositories, no FastAPI in a service, no SQLAlchemy in a route. `tests/test_layers.py` passes.
- Every API error uses the common envelope with an English error code listed in `core/errors.py` CATALOG, `docs/api-errors.md`, and `frontend/src/locales/en.json` and `vi.json`. `tests/test_api_envelope.py` passes.
- UI uses shadcn/ui components and theme tokens only. en and vi locale files keep the same keys.
- Schema changes go through a new Alembic revision after the latest one on `develop` at branch time.
- No new heavy dependency.

## Dependencies

- None. Based on `develop`.

## Acceptance Criteria

- A target that is not an Agent node of the same workflow or subgraph is refused on save with `AGENT_HANDOFF_TARGET_INVALID`.
- `max_handoffs` outside 0 to 20 is refused.
- Existing workflows without the fields load and run unchanged.

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

## Handoff Notes

- Branch `factory/task-0179-agent-handoff-model` from `develop`.
