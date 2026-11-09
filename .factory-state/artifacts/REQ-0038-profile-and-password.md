# Requirement

## Metadata

- Project: langgraph-studio
- Requirement ID: REQ-0038
- Status: Implemented
- Owner: Thái Quí Nguyễn
- Created: 2026-10-19
- Updated: 2026-10-19
- Source: owner feedback "Viewing and updating the profile or password is missing (create a task)" (2026-10-19), with a screenshot of the user menu (e-mail, Settings, Sign out)

## Summary

A signed-in user can see their own profile and change their password, without asking an admin.

## Problem Or Opportunity

- The user menu shows only the e-mail, Settings and Sign out. `GET /api/me` exists, but nothing in the UI shows the account, and the only way to change a password is the reset link (admin-made, or e-mailed when SMTP is set).

## Scope

### In Scope

- A **Profile** page (or Settings section) reached from the user menu: e-mail, role, created date, language, notification preferences (link to the existing settings)
- **Change password**: current password, new password (same rules as `security.password_problem`, the shared password-rules UI), confirm
- Optional display name, if the owner wants one (open question)

### Out Of Scope

- Changing the e-mail address (needs verification), deleting one's own account, two-factor sign-in

## Business Rules

- Changing the password needs the current password; a wrong one counts toward the sign-in lockout (TASK-0045).
- After a change, every other session of the account is signed out (`password_changed`), the current one stays signed in, and the audit log records `user.password_changed`.
- en and vi strings; error codes in CATALOG, docs/api-errors.md and both locales.

## Acceptance Criteria

- The user menu has a Profile entry; the page shows the account.
- Change password works with the right current password, fails clearly with a wrong one or a weak new one, and signs out other sessions.
- pytest and e2e cover both paths.

## Open Questions

- Add a display name (needs a migration), or keep e-mail only? Answered in TASK-0052: e-mail only for now.
