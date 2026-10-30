# Task

## Metadata

- Project: superstep
- Task ID: TASK-0182
- Status: todo
- Owner: Thái Quí Nguyễn
- Created: 2026-10-30
- Updated: 2026-10-30
- Requirement IDs: REQ-0078
- Design IDs: none
- Architecture IDs: DEC-0073

## Objective

Edit hand-off targets in the Agent node Config, draw them as dashed links on the canvas, and show hand-off steps in the trace.

## Scope

### In Scope

- Agent node Config: target list (picker of other Agent nodes in the same graph level, description), workflow setting `max_handoffs` in workflow settings.
- Canvas: dashed agent-to-agent links derived from the target lists; drawing a link from an Agent's hand-off handle to another Agent adds a target; deleting the link removes it.
- Run panel and trace: the hand-off step label and reason; canvas run marks follow the target agent.
- en and vi strings; shadcn components and theme tokens; vitest for the link sync.

### Out Of Scope

- Exports (TASK-0183).
- Template and handbook (TASK-0184).

## Inputs

- REQ-0078 'Canvas', 'Trace'; DEC-0073 decision 1; `docs/ui-conventions.md`.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0078-agent-handoff.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0073-agent-handoff.md`
- Decisions: `DEC-0009-layered-backend-sqlalchemy-alembic.md`, `DEC-0010-api-envelope-error-codes-i18n.md`, `DEC-0008` (`docs/ui-conventions.md`), `DEC-0033` (task branches from `develop`)
- Discovery: `.factory-state/artifacts/DISC-0001-project-context.md`
- Clarifications: `.factory-state/artifacts/CLAR-0009-agent-handoff.md`

## Expected Outputs

- Builders can set up hand-offs on the canvas.

## Implementation Notes

- Links are view-only data derived from the node targets; they are not stored as workflow edges.

## Constraints

- Layers of DEC-0009: routes call services, services call repositories, no FastAPI in a service, no SQLAlchemy in a route. `tests/test_layers.py` passes.
- Every API error uses the common envelope with an English error code listed in `core/errors.py` CATALOG, `docs/api-errors.md`, and `frontend/src/locales/en.json` and `vi.json`. `tests/test_api_envelope.py` passes.
- UI uses shadcn/ui components and theme tokens only. en and vi locale files keep the same keys.
- Schema changes go through a new Alembic revision after the latest one on `develop` at branch time.
- No new heavy dependency.

## Dependencies

- TASK-0179; TASK-0180 for the trace step.

## Acceptance Criteria

- Adding a target in Config draws the dashed link, and drawing the link adds the target.
- A non-Agent target cannot be picked.
- vitest, lint and build pass; en and vi keys match.

## Validation Plan

- `cd frontend && npm run lint && npm test && npm run build`

## Assumptions

- The designer step is skipped. REQ-0078 and its CLAR already describe the screens.

## Open Questions

- None beyond those listed in DEC-0073.

## Activity Log

- 2026-10-30: planned from REQ-0078 (DEC-0073). Status todo. Not started; waits for the owner to confirm the task set.

## Handoff Notes

- Branch `factory/task-0182-agent-handoff-ui` from `develop`.
