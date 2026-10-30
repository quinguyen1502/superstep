# Task

## Metadata

- Project: superstep
- Task ID: TASK-0178
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-30
- Updated: 2026-10-30
- Requirement IDs: REQ-0077
- Design IDs: none
- Architecture IDs: DEC-0072

## Objective

Document chat attachments, add the Playwright end-to-end tests, and record the change.

## Scope

### In Scope

- Handbook en and vi: the chat page and Chat settings pages describe attachments, limits, the state field and "Include attachments"; the LLM and Agent node pages mention the switch.
- `docs/api-errors.md` lists the `CHAT_ATTACHMENT*` codes.
- Playwright e2e in en and vi: attach a PDF and an image on the public page; the mock answer names both; the turn shows both chips; a second visitor cannot download.
- CHANGELOG Unreleased entry; REQ-0077 status updated when merged.

### Out Of Scope

- Feature code (TASK-0174 to TASK-0177).

## Inputs

- REQ-0077 acceptance criteria.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0077-chat-attachments.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0072-chat-attachments.md`
- Decisions: `DEC-0009-layered-backend-sqlalchemy-alembic.md`, `DEC-0010-api-envelope-error-codes-i18n.md`, `DEC-0008` (`docs/ui-conventions.md`), `DEC-0033` (task branches from `develop`)
- Discovery: `.factory-state/artifacts/DISC-0001-project-context.md`
- Clarifications: `.factory-state/artifacts/CLAR-0008-chat-attachments.md`

## Expected Outputs

- Strict handbook builds pass; e2e passes in CI.

## Implementation Notes

- Keep heading structure identical between en and vi pages.

## Constraints

- Layers of DEC-0009: routes call services, services call repositories, no FastAPI in a service, no SQLAlchemy in a route. `tests/test_layers.py` passes.
- Every API error uses the common envelope with an English error code listed in `core/errors.py` CATALOG, `docs/api-errors.md`, and `frontend/src/locales/en.json` and `vi.json`. `tests/test_api_envelope.py` passes.
- UI uses shadcn/ui components and theme tokens only. en and vi locale files keep the same keys.
- Schema changes go through a new Alembic revision after the latest one on `develop` at branch time.
- No new heavy dependency.

## Dependencies

- TASK-0177.

## Acceptance Criteria

- The REQ-0077 acceptance criteria are covered by tests or the handbook.
- Strict handbook builds pass.
- The e2e specs pass in en and vi.

## Validation Plan

- `cd handbook && .venv/bin/mkdocs build --strict -f mkdocs.yml && .venv/bin/mkdocs build --strict -f mkdocs.vi.yml`
- `cd frontend && npx playwright test` (the new specs, en and vi)

## Assumptions

- The designer step is skipped. REQ-0077 and its CLAR already describe the screens.

## Open Questions

- None. DEC-0072 is accepted.

## Activity Log

- 2026-10-30: planned from REQ-0077 (DEC-0072). Status todo. Not started.
- 2026-10-30: owner confirmed the task set and accepted the decision record.
- 2026-10-30: implemented on `factory/task-0178-chat-attachment-docs-e2e` from `develop`. Chat attachments documented in the handbook (en, vi) and covered end to end `factory verify run --profile full` passed. The owner authorized the merge of the REQ-0077/REQ-0078 task PRs. Moved to done on this PR before the merge (TASK-0148).

## Handoff Notes

- Branch `factory/task-0178-chat-attachment-handbook-e2e` from `develop`.
- Review: `.factory-state/artifacts/REV-0155-task-0178.md`. QA: `.factory-state/artifacts/QA-0155-task-0178.md`.
