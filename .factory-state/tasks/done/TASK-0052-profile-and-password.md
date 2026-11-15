# Task

## Metadata

- Project: langgraph-studio
- Task ID: TASK-0052
- Status: done
- Phase: auth
- Owner: Thái Quí Nguyễn
- Created: 2026-10-19
- Updated: 2026-10-19
- Requirement IDs: REQ-0038
- Design IDs: none yet
- Architecture IDs: DEC-0009, DEC-0025

## Objective

Profile page and self-service password change.

## Scope

### In Scope

- Backend: `POST /api/me/password` {current_password, new_password} in `api/routes/auth.py` → `AuthService.change_password` (verify, `password_problem`, set `password_changed`, keep the caller's session, audit). Lockout counting as in sign-in.
- Frontend: user menu entry, a Profile page or Settings section (`pages/settings/sections.ts`), the change-password form reusing `components/password-rules.tsx`.
- Tests: pytest for the endpoint (right, wrong, weak, other sessions signed out); an e2e spec.
- Docs: READMEs (accounts section), docs/api-errors.md for any new code.

### Out Of Scope

- E-mail change, account deletion, 2FA.

## Related Artifacts

- Requirement: `.factory-state/artifacts/REQ-0038-profile-and-password.md`

## Constraints

- Do not merge until the owner asks.

## Dependencies

- None.

## Acceptance Criteria

- Same as REQ-0038.

## Validation Plan

- `cd backend && .venv/bin/python -m pytest -q`
- `cd frontend && npx tsc -b && npx vitest run && npx oxlint && npx vite build`
- `cd frontend && PW_CHROME=… E2E_UVICORN=../backend/.venv/bin/uvicorn npx playwright test`

## Open Questions

- Display name: not added (e-mail only, no migration); the owner can ask for it later.

## Activity Log

- 2026-10-19: Created from owner feedback; not started.
- 2026-10-19: Started on `factory/task-0052-profile-and-password` (owner: "Do task 0052"). Profile is the first Settings section (`/settings/profile`).
- 2026-10-19: Implemented; review REV-0049, QA QA-0049 (pass). Merged in PR #58 (owner: "Merge PR #58").
