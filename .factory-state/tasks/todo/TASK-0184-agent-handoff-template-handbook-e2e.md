# Task

## Metadata

- Project: superstep
- Task ID: TASK-0184
- Status: todo
- Owner: Thái Quí Nguyễn
- Created: 2026-10-30
- Updated: 2026-10-30
- Requirement IDs: REQ-0078
- Design IDs: none
- Architecture IDs: DEC-0073

## Objective

Add the "Help desk with hand-offs" template, document hand-offs, and add e2e tests.

## Scope

### In Scope

- Template: triage agent, Billing and Technical agents, with test cases that use the mock model.
- Handbook en and vi: Agent node page section and a hand-off guide; comparison with supervisor and workflow tools.
- `docs/api-errors.md` for the new codes.
- Playwright e2e in en and vi: the template in the Chat tab and on the public page; the second message stays with the agent that answered.
- CHANGELOG Unreleased entry; REQ-0078 status updated when merged.

### Out Of Scope

- Feature code (TASK-0179 to TASK-0183).

## Inputs

- REQ-0078 'Template' and acceptance criteria.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0078-agent-handoff.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0073-agent-handoff.md`
- Decisions: `DEC-0009-layered-backend-sqlalchemy-alembic.md`, `DEC-0010-api-envelope-error-codes-i18n.md`, `DEC-0008` (`docs/ui-conventions.md`), `DEC-0033` (task branches from `develop`)
- Discovery: `.factory-state/artifacts/DISC-0001-project-context.md`
- Clarifications: `.factory-state/artifacts/CLAR-0009-agent-handoff.md`

## Expected Outputs

- Template, docs and e2e are in place.

## Implementation Notes

- Keep en and vi page headings in the same structure.

## Constraints

- Layers of DEC-0009: routes call services, services call repositories, no FastAPI in a service, no SQLAlchemy in a route. `tests/test_layers.py` passes.
- Every API error uses the common envelope with an English error code listed in `core/errors.py` CATALOG, `docs/api-errors.md`, and `frontend/src/locales/en.json` and `vi.json`. `tests/test_api_envelope.py` passes.
- UI uses shadcn/ui components and theme tokens only. en and vi locale files keep the same keys.
- Schema changes go through a new Alembic revision after the latest one on `develop` at branch time.
- No new heavy dependency.

## Dependencies

- TASK-0181, TASK-0182, TASK-0183.

## Acceptance Criteria

- The REQ-0078 acceptance criteria are covered by tests or the handbook.
- Strict handbook builds pass; e2e passes in en and vi.

## Validation Plan

- `cd handbook && .venv/bin/mkdocs build --strict -f mkdocs.yml && .venv/bin/mkdocs build --strict -f mkdocs.vi.yml`
- `cd frontend && npx playwright test` (the new specs, en and vi)

## Assumptions

- The designer step is skipped. REQ-0078 and its CLAR already describe the screens.

## Open Questions

- None beyond those listed in DEC-0073.

## Activity Log

- 2026-10-30: planned from REQ-0078 (DEC-0073). Status todo. Not started; waits for the owner to confirm the task set.

## Handoff Notes

- Branch `factory/task-0184-agent-handoff-template-handbook-e2e` from `develop`.
