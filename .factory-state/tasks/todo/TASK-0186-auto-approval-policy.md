# Task

## Metadata

- Project: superstep
- Task ID: TASK-0186
- Status: todo
- Owner: Thái Quí Nguyễn
- Created: 2026-10-30
- Updated: 2026-10-30
- Requirement IDs: REQ-0081
- Design IDs: none
- Architecture IDs: DEC-0075

## Objective

Add the `approval.auto` policy to Human nodes and Agent tool approval, with save-time validation, roles, kill switches and the audit columns.

## Scope

### In Scope

- `engine/approval_policy.py` (pure): parse and validate `approval.auto` {mode off|suggest|auto, rules [{field, op, value, effect human|reject}], max_per_day (default 50), judge {credential_id, model, instructions}, min_confidence (default 0.8), notify (default on)}, the rule operators, `policy_hash`, and the evaluation of rules against a request (DEC-0075 decisions 2, 4, 5).
- The validator reports invalid policies as issues on the Human node and on Agent nodes with approval tools (`AUTO_APPROVAL_RULE_INVALID`, `AUTO_APPROVAL_JUDGE_REQUIRED`).
- Roles (owner decision 3): saving a workflow that turns `mode: auto` on, or changes an auto policy, needs the workflow owner or an admin; others get `AUTO_APPROVAL_FORBIDDEN`. Editors may set `suggest`.
- Kill switches: the workflow setting `auto_approval_paused`, an organisation admin setting, and the operator variable `STUDIO_AUTO_APPROVAL=off` (`AUTO_APPROVAL_DISABLED` when an API asks for a paused feature).
- Alembic revision: nullable `auto_outcome`, `auto_confidence`, `auto_model`, `auto_reason`, `auto_rules`, `policy_hash`, `agreed` on `approval_audit`; nullable `ai_decision`, `ai_confidence`, `ai_reason` on `approval_waits` (DEC-0075 decision 7).
- Tests: policy parsing and validation, rule evaluation per operator, RBAC on save (editor auto refused, editor suggest allowed, owner and admin auto allowed), migration up and down.

### Out Of Scope

- The review itself (TASK-0187). UI (TASK-0188).

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

- none

## Acceptance Criteria

- Saving `mode: auto` as a sharing editor returns `AUTO_APPROVAL_FORBIDDEN`; as the owner or an admin it saves.
- An invalid rule (unknown operator, missing field) and auto without a judge credential are reported with their codes.
- Rules evaluate per operator as specified (unit tests).
- The Alembic revision upgrades and downgrades.

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

- Branch `factory/task-0186-auto-approval-policy` from `develop`.
