# Task

## Metadata

- Project: superstep
- Task ID: TASK-0187
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-30
- Updated: 2026-10-30
- Requirement IDs: REQ-0081
- Design IDs: none
- Architecture IDs: DEC-0075

## Objective

Review waiting approvals with rules, the daily cap and an LLM judge before people are asked, and answer, escalate or suggest.

## Scope

### In Scope

- `services/auto_review_service.py` called by `ApprovalService.on_waiting` before channel messages (DEC-0075 decision 1), for Human nodes and Agent tool steps.
- Order: kill switches, rules (`reject` resumes with a rejection without the judge; `human` escalates), the per-workflow per-day cap (owner decision 5), the judge, the threshold (default 0.8).
- Judge: a separate provider call with its own credential (any configured chat credential, owner decision 4), a fixed system prompt, the request in a delimited untrusted block, JSON output `{decision, confidence, reason, flags}`, no tools, 30 s timeout, usage recorded. The judge's reject escalates (owner decision 2).
- Fail-safe: error, timeout, invalid JSON, missing credential, `injection` flag, cap reached, kill switch on: escalate.
- Never auto-approve: mock judge (no credential and no env key), demo mode, test runs (they never reach `on_waiting`), workflow tests.
- Auto-answer path: close the waiting step with compare-and-set, close channel requests, audit actor `auto` with the new columns, enqueue `resume` with `approved` or the rejection text, notify only the run owner through the existing notifier and channels (owner decision 7).
- Suggest mode: the opinion is stored on the waiting step and added to the channel message; a human answer records `agreed`.
- API: per-workflow metrics (auto-approved, auto-rejected, escalated, suggested, agreement rate) and the kill switch endpoints, owner or admin only.
- The `run_waiting` notification is not sent for a step that was auto-answered.
- Tests: each fail-safe path, cap, rules, threshold, mock and demo never approve, suggest never resumes, agreement recorded, owner-only notification, Agent tool auto-approval runs the tool, kill switch per workflow and per organisation.

### Out Of Scope

- UI (TASK-0188).

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

- TASK-0186

## Acceptance Criteria

- A confident approve resumes the run with `approved`; the audit has actor `auto`, model, confidence, reason and policy hash; only the run owner is notified.
- Judge error, timeout, invalid JSON, `escalate`, injection flag, low confidence and judge reject each escalate (the channel message carries the AI opinion).
- A `reject` rule rejects without calling the judge; a `human` rule escalates.
- The (N+1)th request of a workflow on one day escalates with reason `cap`.
- Mock judge and demo mode never auto-approve.
- Suggest mode never resumes; a human answer records agree or disagree.
- Kill switch per workflow and per organisation makes requests escalate.

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

- 2026-10-30: implemented on `factory/task-0187-auto-review-service` from `develop`. `services/auto_review_service.py` and `engine/approval_judge.py`: AI review in `ApprovalService.on_waiting` before people are asked (kill switches, rules, demo, per-workflow daily cap, separate judge call with a fixed system text, the request as delimited data, strict JSON, 30 s timeout, threshold). Confident approvals resume through the deadline auto-answer path with an `auto` audit entry (outcome, confidence, model, reason, rules, policy hash) and notify only the run owner (`run_auto_answered`); everything else escalates with the opinion on the waiting step, in the inbox and in channel messages. Suggest mode records agreement. The run service now asks for approvals after the run row is stored. `/api/approvals/auto/workflows/{wid}` returns 30-day stats. A shared-database flake in `test_deadlines.py` is fixed by scoping `fire` to its run. `factory verify run --profile full` passed. The owner authorized merging the REQ-0081 task PRs when CI is green. Moved to done on this PR before the merge (TASK-0148).

## Handoff Notes

- Branch `factory/task-0187-auto-review-service` from `develop`.
