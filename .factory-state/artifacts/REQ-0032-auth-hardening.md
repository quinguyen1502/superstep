# Requirement

## Metadata

- Project: langgraph-studio
- Requirement ID: REQ-0032
- Status: Implemented
- Owner: Thái Quí Nguyễn
- Created: 2026-10-18
- Updated: 2026-10-18
- Source: remaining-work report of 2026-10-18 (item 5: "no account lock after many failed sign-ins, no password reset yet, and the session token is still kept in localStorage"; and the demo account found in production) and the owner's reply, "Except 2, 3, 4. Do the rest"

## Summary

Lock an e-mail after repeated failed sign-ins, let users reset a password through a one-time link, move the browser session into an HttpOnly cookie, and stop creating the demo account in production.

## Problem Or Opportunity

- Passwords could be guessed without limit.
- A forgotten password had no way back short of editing the database.
- Any script on the page could read the JWT from `localStorage`.
- Every production database had `admin@example.com` / `admin123` as an admin.

## Scope

### In Scope

- Backend: lockout, reset links (admin and e-mail), session cookie with CSRF and socket origin checks, production seeding
- Frontend: cookie-based session, sign-in page (demo hint, forgot link, reset notice), forgot and reset pages, Settings → Users reset link
- Docs, `.env.example`, e2e and pytest

### Out Of Scope

- Changing your own password while signed in, MFA, SSO, IP-based lockout

## Stakeholders Or Users

- Every user; administrators

## Desired Behavior

- See DEC-0035.

## Business Rules

- New error codes in `CATALOG`, `docs/api-errors.md`, both locale files: `AUTH_LOCKED`, `AUTH_CSRF`, `PASSWORD_RESET_INVALID`.
- A failed sign-in never says whether the e-mail exists, and neither does a lockout or a reset request.

## Constraints

- Bearer-token API clients keep working unchanged.
- Backend layers per DEC-0009; schema change by Alembic migration.

## Acceptance Criteria

- The fifth failed sign-in within the window returns `AUTH_LOCKED`, and so does the right password until the lock ends. Unknown e-mails behave the same.
- An admin link sets a new password once; the old session returns `AUTH_TOKEN_EXPIRED`; a used or expired link returns `PASSWORD_RESET_INVALID`; the lockout is cleared.
- With SMTP and a public URL, "forgot password" e-mails the link only to an existing active account and answers the same for any address. Without them, the page says to ask an admin.
- The session cookie is HttpOnly and SameSite=Lax; the page has no token in `localStorage` or `document.cookie`; cookie writes without `X-Requested-With: studio` return `AUTH_CSRF`; a cookie socket from another origin is refused; logout ends the session.
- Production creates no demo account and deactivates one that still has the demo password.

## Edge Cases

- A lock that ends starts a fresh count.
- Several open links for one account: using one cancels the others.

## Assumptions

- 5 failures / 15 minutes / 15 minutes and a 1-hour link are acceptable defaults; all are configurable.

## Open Questions

- None

## Related Artifacts

- Decision: `.factory-state/decisions/DEC-0035-session-cookie-lockout-reset.md`
- Task: `.factory-state/tasks/done/TASK-0045-auth-hardening.md`
- Earlier question this answers: REQ-0001 "Should the demo user be removed or disabled outside local development?"
