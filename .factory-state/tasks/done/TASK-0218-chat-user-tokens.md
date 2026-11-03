# Task

## Metadata

- Project: superstep
- Task ID: TASK-0218
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-11-01
- Requirement IDs: REQ-0082
- Design IDs: none
- Architecture IDs: DEC-0077
- Phase: Phase 1 (PLAN-0002)
- Estimate: L (S up to half a day, M about one day, L two to three days)

## Objective

Accept third-party user tokens (HS256 JWT) on the v1 HTTP API and socket, with per-user scoping, CORS and limits.

## Scope

### In Scope

- `ChatTokenVerifier` port and HS256 implementation with the standard library: pinned algorithm, `kid`, `aud`, `exp`/`iat` with 60 s leeway, 1 hour lifetime cap, key cache at most 30 s.
- HTTP `Authorization: Bearer`; socket first frame `auth` (and `?token=` fallback).
- Sessions, attachments and ratings scoped by `(trigger, external_user)`; `chat.user = {id, name, kind}` and capped `meta` passed to the workflow as untrusted input.
- Cross-origin HTTP and socket only for Bearer requests from the key's origins (any when empty); no credentials in CORS.
- Per-external-user message limit; failed verifications count toward the per-IP limit.
- Error codes `CHAT_TOKEN_REQUIRED`, `CHAT_TOKEN_INVALID`, `CHAT_TOKEN_EXPIRED`, `CHAT_APP_KEY_REVOKED`, `CHAT_ORIGIN_FORBIDDEN` in CATALOG, `docs/api-errors.md`, en and vi.

### Out Of Scope

- Anything assigned to another task in PLAN-0002.

## Inputs

- REQ-0082, PLAN-0002, DEC-0077.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0082-chat-sdk-toolkit.md`
- Plan: `.factory-state/artifacts/PLAN-0002-chat-sdk-toolkit.md`
- Architecture: DEC-0077
- Decisions: `DEC-0009-layered-backend-sqlalchemy-alembic.md`, `DEC-0010-api-envelope-error-codes-i18n.md`, `DEC-0008` (`docs/ui-conventions.md`), `DEC-0033` (task branches from `develop`)

## Expected Outputs

- The acceptance criteria below, tested.

## Constraints

- Layers of DEC-0009; common error envelope with codes in `core/errors.py` CATALOG, `docs/api-errors.md` and both locales.
- shadcn/ui and theme tokens only; en and vi keep the same keys; no emoji in docs.
- Schema changes through a new Alembic revision after the latest on `develop` at branch time.
- No secrets in logs, URLs or fixtures committed with real values.

## Dependencies

- TASK-0216
- TASK-0217

## Acceptance Criteria

- Tests: valid token chats end to end; user A cannot read, rate or attach to user B's or an anonymous session; `alg: none`, wrong `alg`, wrong `aud`, expired, future `iat`, unknown `kid`, revoked key, bad signature each rejected with the right code.
- Rotation: tokens from both active keys work; after revoke the old key's tokens fail within 30 s.
- Anonymous and studio access unchanged.

## Validation Plan

- `cd backend && .venv/bin/python -m pytest -q`
- `factory verify run --profile full`

## Assumptions

- The owner accepts REQ-0082 and DEC-0077 to DEC-0080 (or their amended versions) before this task moves to todo.

## Open Questions

- See PLAN-0002 and the related DECs.

## Activity Log

- 2026-11-01: Final CI caught the attachment fixture's `ws://`/HTTPS-Origin mismatch after legacy-origin hardening. Reproduced locally and corrected the test to use explicit `wss://testserver`; production origin enforcement unchanged. Final CI reruns before merge.
- 2026-11-01: Owner approved merging PR #276 ("Duyệt"). Review and local QA passed. Moved to done on this same PR; merge remains gated on all final-head CI checks passing.
- 2026-11-01: Started locally after TASK-0217 merged as PR #275, with all final CI checks passed (24a65a8). Continues the owner's request to reconstruct the interrupted cloud implementation. Implement a stdlib HS256 verifier with no key cache, shared external-user session isolation, Bearer/first-frame auth, scoped CORS, per-user and failed-auth IP limits; then security tests and full declared verification. The workflow's `chat` object state field retains untrusted identity/meta in LangGraph like other input fields.

- 2026-10-31: proposed in PLAN-0002 from REQ-0082. Status backlog until the owner approves the plan.
- 2026-10-31: backlog to todo. The owner approved PLAN-0002 and DEC-0077 to DEC-0080 on PR #271.

## Handoff Notes

- Branch `factory/task-0218-chat-user-tokens` from `develop`.
- Dependency TASK-0217 merged as PR #275, c57ea03, after final CI for 24a65a8 passed all checks (https://github.com/quinguyen1502/superstep/actions/runs/41286769269). This closes QA-0205's remaining Postgres/CI follow-up.
- Implemented stdlib HS256 verifier behind ChatTokenVerifier, no key cache, conditional last-used write/revocation check, external-user session ownership, untrusted chat identity/meta input, Bearer and v1 auth/query transport, token-only CORS independent of global studio CORS, strict legacy socket origin checks, quotas, errors, API schemas and configuration. Existing 0051 columns suffice; no new migration/dependency.
- Full verification: all eight policy checks passed; focused final security/legacy/API checks: 47 passed; real browser cross-origin plus chat/key regression: 9 passed. See `.factory-state/artifacts/REV-0206-task-0218.md` and `.factory-state/artifacts/QA-0206-task-0218.md`.
- A workflow declares `chat` as an object state field to retain/use `chat.user` and `chat.meta`, consistent with LangGraph state input. Identity/meta are untrusted data. Existing Human text/bool behavior is preserved; adding form behavior is not this task.
- Owner approved PR #276 on 2026-11-01. Final-head CI must pass before merge; TASK-0219 starts after this task merges, per PLAN-0002.
