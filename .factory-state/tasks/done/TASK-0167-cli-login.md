# Task

## Metadata

- Project: superstep
- Task ID: TASK-0167
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-30
- Updated: 2026-10-30
- Requirement IDs: REQ-0079
- Design IDs: none
- Architecture IDs: DEC-0071

## Objective

A person can create a personal access token in Settings, approve one from `superstep login` in the browser, and use that token as `whoami`. Later phase 2 tasks call the API with the same token.

## Scope

### In Scope

- DEC-0071 decisions 1, 2 and 3: the `personal_access_tokens` table and the device-code table, Alembic revision after `0042_chat_ratings`, PAT lookup in `AuthService.current` and `ws_user`, the token and device routes, Settings section `tokens`, the `/cli/authorize` page, and `superstep login`, `logout` and `whoami`.
- Error codes `PAT_NAME_TAKEN`, `PAT_NOT_FOUND`, `CLI_DEVICE_INVALID`, `CLI_DEVICE_EXPIRED` and `CLI_DEVICE_DENIED` in `core/errors.py` `CATALOG`, `docs/api-errors.md`, and `errors.<CODE>` in both frontend locale files.
- CLI catalogs gain the same keys in en and vi. Human text on stderr. `--json` is one object on stdout. The token is never printed.
- Completion lists `login`, `logout` and `whoami`.

### Out Of Scope

- `workflows`, `pull`, `push`, `run`, `runs`, `test`, `mcp` (TASK-0168 to TASK-0171).
- Handbook pages (TASK-0172).
- Revoking a token from `logout`. Logout only edits `~/.superstep/cli.json`.

## Inputs

- REQ-0079 group C (`login`, `logout`, `whoami`) and group E (tokens and browser sign-in).
- DEC-0071 decisions 1 to 3.
- `backend/app/services/auth_service.py`, `backend/app/api/deps.py`, `backend/app/services/trigger_service.py` (the hash and prefix pattern), `frontend/src/pages/settings/`, `frontend/src/pages/Auth.tsx` (`safeNext`), `sdk/python/src/superstep/cli/`.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0079-superstep-cli.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0071-cli-workflows.md`
- Decisions: `DEC-0068-superstep-cli.md`, `DEC-0009-layered-backend-sqlalchemy-alembic.md`, `DEC-0010-api-envelope-error-codes-i18n.md`, `DEC-0025-ui-only-delete-confirmation.md`, `DEC-0008-ui-conventions.md`
- Discovery: `.factory-state/artifacts/DISC-0001-project-context.md`
- Clarifications: `.factory-state/artifacts/CLAR-0010-superstep-cli.md`

## Expected Outputs

- `POST /api/me/tokens` returns a `pat_` secret once. A later `GET /api/me` with that Bearer is the same user. `DELETE` then makes it `AUTH_TOKEN_INVALID`.
- `superstep login --no-browser` against a test client stores the token in `cli.json` mode `0600` after the device is approved.
- Settings shows the token prefix and revokes it only after the name is typed.

## Implementation Notes

- Routers call services. Services call repositories. No FastAPI import in a service, including inside a function. No raw SQL.
- The device row stores hashes, not the codes. The PAT secret sits on that row only until the first successful poll, then the column is cleared.
- The approve page does not call approve on load. The name field is editable. `PAT_NAME_TAKEN` stays on the page.
- Tests may pass a fake clock, a fake browser opener and an httpx mock. They must not open a real browser.

## Constraints

- CLI stays Python >= 3.9, argparse, no Click, Typer or `tomllib`. This task adds no dependency.
- New server errors go through the shared envelope and `api/error_handlers.py`. No per-route try/except.
- UI strings only from the locale files. Revoke uses `ConfirmDeleteDialog`. No hard-coded colours.
- `tests/test_layers.py` and `tests/test_api_envelope.py` must pass.

## Dependencies

- None. Branch from `develop` (DEC-0033) after the owner confirms this set. Do not stack on another branch.

## Acceptance Criteria

- A created token works as `Authorization: Bearer` and as `/ws/run?token=` for `ws_user`. A JWT still works. A revoked token and a `pat_` that was never issued are `AUTH_TOKEN_INVALID`.
- Two active tokens with the same name for one user return `PAT_NAME_TAKEN`. The same name is allowed after revoke, and for another user.
- The list and the Settings page never contain the secret. The create response contains it once.
- Device poll returns `pending`, then the secret once, then `CLI_DEVICE_INVALID` for a second read of an already delivered secret. An expired row is `CLI_DEVICE_EXPIRED`. Deny is `CLI_DEVICE_DENIED`. Approve of an unknown user code is `CLI_DEVICE_INVALID`.
- `superstep login --help` shows an example. `--no-browser` does not open a browser. A stored token is mode `0600` and is not on stdout. `logout` removes it and leaves `lang`. `whoami` prints the e-mail. `SUPERSTEP_TOKEN` and `SUPERSTEP_URL` win over the file.
- `--lang vi` selects the Vietnamese catalog. The two CLI catalogs have the same keys. The two frontend locale files have the same new keys.
- Revoke in the UI stays disabled until the typed text equals the token name. The DELETE request has no confirm field.

## Validation Plan

- `cd backend && .venv/bin/python -m pytest -q tests/test_api_envelope.py tests/test_layers.py` plus the new PAT and device tests.
- `cd sdk/python && python -m pytest -q` for the login tests.
- `cd frontend && npm test` for the Settings section, if a component test is added; otherwise the backend and CLI tests above cover the behaviour and the page is checked by reading the locale keys.

## Assumptions

- The designer step is skipped. DEC-0071 records the page, the section and the prompts.
- `login` without a display is `--no-browser`. The command does not detect a display itself beyond that flag.
- A device request with no `STUDIO_PUBLIC_URL` returns a path. The CLI joins it to `--url`.

## Open Questions

- None.

## Activity Log

- 2026-10-30: planned from REQ-0079 phase 2 (DEC-0071).
- 2026-10-30: owner confirmed the phase 2 set. Branch `factory/task-0167-cli-login` from `develop` at `1537c58`. Task moved to doing. No source edited.
- 2026-10-30: implemented tokens, the device sign-in, Settings, `/cli/authorize`, and `login` / `logout` / `whoami`.
- 2026-10-30: validation of the test commands passed on the uncommitted branch. Backend pytest 811 passed, 54 skipped (343s), including `test_personal_access_tokens`, `test_api_envelope`, `test_layers` and `test_auth`. Python SDK pytest 109 passed, 2 skipped (5s), including `test_cli_login`. Frontend vitest 125 passed. TypeScript SDK vitest 22 passed. Lint and build were not run.
- 2026-10-30: Review REV-0143. No blocking findings. Approved for QA.
- 2026-10-30: QA QA-0143. Pass with follow-up. No acceptance criterion failed. The Settings page and `/cli/authorize` were not opened in a browser.
- 2026-10-30: owner approved the pull request ("duyệt"). The frontend build failed on a catch type; both catches now use `any`, matching the other pages. Task moved to done. Review REV-0143. QA QA-0143. PR #214. Not merged.

## Handoff Notes

- TASK-0168 through TASK-0171 wait until this task is merged.
- Review: `.factory-state/artifacts/REV-0143-task-0167.md`. QA: `.factory-state/artifacts/QA-0143-task-0167.md`. Pass with follow-up. PR #214 is Ready. Not merged. TASK-0168 waits until this task is merged.
