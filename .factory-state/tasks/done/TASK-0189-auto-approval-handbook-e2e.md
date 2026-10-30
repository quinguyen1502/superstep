# Task

## Metadata

- Project: superstep
- Task ID: TASK-0189
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-30
- Updated: 2026-10-30
- Requirement IDs: REQ-0081
- Design IDs: none
- Architecture IDs: DEC-0075

## Objective

Handbook pages, Playwright e2e in en and vi, screenshots and CHANGELOG for AI auto-approval.

## Scope

### In Scope

- Handbook en and vi: Human node and Agent node pages, and an "AI review of approvals" guide (modes, rules, cap, judge, fail-safe, risks: overconfidence and prompt injection).
- Playwright e2e in en and vi: settings on the Human node and Agent tool approval, a suggest-mode opinion in the Approvals inbox, the AI badge and rates, the kill switch.
- Screenshots for review.
- CHANGELOG Unreleased entry.

### Out Of Scope

- New behaviour.

## Inputs

- REQ-0081, DEC-0075 (decisions 1 to 8 and the owner decisions 1 to 7).
- `services/approval_service.py`, `engine/deadlines.py`, `engine/agents.py`, `services/run_service.py`, `services/notification_service.py`, `frontend/src/pages/Approvals.tsx`.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0081-ai-auto-approval.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0075-ai-auto-approval.md`
- Decisions: `DEC-0009-layered-backend-sqlalchemy-alembic.md`, `DEC-0010-api-envelope-error-codes-i18n.md`, `DEC-0008` (`docs/ui-conventions.md`), `DEC-0033` (task branches from `develop`)
- Discovery: `.factory-state/artifacts/DISC-0001-project-context.md`
- Clarifications: none (the owner decisions are recorded in DEC-0075)

## Expected Outputs

- The acceptance criteria below, tested.

## Implementation Notes

- Reuse the deadline auto-answer path of `ApprovalService` rather than adding a second resume path.

## Constraints

- Layers of DEC-0009: routes call services, services call repositories, no FastAPI in a service, no SQLAlchemy in a route. `tests/test_layers.py` passes.
- Every API error uses the common envelope with an English error code listed in `core/errors.py` CATALOG, `docs/api-errors.md`, and `frontend/src/locales/en.json` and `vi.json`. `tests/test_api_envelope.py` passes.
- UI uses shadcn/ui components and theme tokens only, default control sizes. en and vi locale files keep the same keys.
- Schema changes go through a new Alembic revision after the latest one on `develop` at branch time.
- No new heavy dependency.

## Dependencies

- TASK-0188

## Acceptance Criteria

- The handbook builds in strict mode in en and vi.
- e2e passes in en and vi.
- CHANGELOG has the entry.

## Validation Plan

- `cd backend && .venv/bin/python -m pytest -q`
- `cd frontend && npm run lint && npm test && npm run build`
- `factory verify run --profile full`, `factory validate`

## Assumptions

- The designer step is skipped. REQ-0081 and DEC-0075 describe the screens.

## Open Questions

- None. DEC-0075 is accepted.

## Activity Log

- 2026-10-30: planned from REQ-0081 (DEC-0075). Status todo. Not started.
- 2026-10-30: owner approved implementing REQ-0081 for 0.10.0 and merging the task PRs when CI is green.

- 2026-10-30: implemented on `factory/task-0189-auto-approval-handbook-e2e` from `develop`. Handbook page `run/ai-review.md` in en and vi with links from the Human node, Agent node and Human approval pages; Playwright `e2e/auto-approval.spec.ts` in en and vi with a fixed judge verdict from the fake Ollama API; review screenshots. `factory verify run --profile full` passed. The owner authorized merging the REQ-0081 task PRs when CI is green. Moved to done on this PR before the merge (TASK-0148).

## Handoff Notes

- Branch `factory/task-0189-auto-approval-handbook-e2e` from `develop`.
- Review: `.factory-state/artifacts/REV-0173-task-0189.md`. QA: `.factory-state/artifacts/QA-0173-task-0189.md`.
