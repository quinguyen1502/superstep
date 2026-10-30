# Task

## Metadata

- Project: superstep
- Task ID: TASK-0188
- Status: todo
- Owner: Thái Quí Nguyễn
- Created: 2026-10-30
- Updated: 2026-10-30
- Requirement IDs: REQ-0081
- Design IDs: none
- Architecture IDs: DEC-0075

## Objective

Editor settings for AI review on the Human node and Agent tool approval, the Approvals page badge, opinion, rates and kill switch, and export notes.

## Scope

### In Scope

- A shared `AutoApprovalSettings` component in the Human node and in the Agent node approval settings: mode select, rules editor, daily cap, judge credential, model and instructions, min confidence, notify; `auto` disabled with a tooltip for non-owners; the suggest-mode agreement rate next to the threshold (owner decision 1).
- Approvals page: an AI badge on suggested and auto-answered items, the AI opinion above Approve and Reject, per-workflow rates and a pause switch (owner or admin).
- Admin settings: the organisation kill switch.
- Python, LangGraph project and TypeScript exports: a note that AI review is a Superstep feature (graph unchanged), like channels and deadlines (DEC-0075 decision 8); snapshot updates.
- en and vi strings; vitest for the component and the page.

### Out Of Scope

- Handbook and e2e (TASK-0189).

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

- TASK-0187

## Acceptance Criteria

- The settings render and save on both node kinds; an editor cannot choose auto.
- The Approvals page shows the badge, the opinion, the rates and the switch.
- Exports carry the note; snapshots updated; vitest, lint and build pass.

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

## Handoff Notes

- Branch `factory/task-0188-auto-approval-ui-exports` from `develop`.
