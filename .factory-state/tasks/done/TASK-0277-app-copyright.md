# Task

## Metadata

- Project: superstep
- Task ID: TASK-0277
- Title: Show copyright and the running version
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-08
- Updated: 2026-11-08
- Requirement IDs: owner request 2026-11-08

## Objective

Show the MIT copyright notice and the running server version on the Studio web app.

## Scope

### In Scope

- A shared footer on sign-in, password reset, approval link, CLI authorize, workflow list, settings and the approval inbox.
- The copyright line follows the handbook: Superstep, then Qui Nguyen, then the current calendar year. `LICENSE` stays unchanged.
- Version from `GET /api/health` (`backend_version()`). Omit the version when that call fails. Still show the copyright.

### Out Of Scope

- The workflow editor canvas and the public chat page `/c/:slug`.
- A new API field, a hardcoded frontend package version, or a release.
- TASK-0227, cross-language code nodes, and marking REQ-0086, REQ-0089 or REQ-0090 done.

## Acceptance Criteria

- Signed-out and signed-in Studio pages listed in scope show the copyright line in English and Vietnamese.
- When `/api/health` returns a version, the same line includes that version. A failed health call leaves the copyright and hides the version.
- The editor canvas and public chat do not gain a footer.
- Locale strings differ between `en` and `vi`. No hard-coded colours.

## Validation Plan

- Frontend locale key check, then the login and workflow list in a browser.
- Tool-policy commands recorded in QA-0263. Review is REV-0263.

## Assumptions

- The footer follows the handbook line `Superstep · Qui Nguyen · 2026`. `LICENSE` still names Thái Quí Nguyễn and is unchanged.
- One cached health read per page load is enough. The workflow list may still read `import_enabled` on its own.

## Open Questions

- None.

## Activity Log

- 2026-11-08: Owner asked to add copyright and the current version on the web app. Allocated TASK-0277 after `git fetch --all --prune`. Branch `factory/task-0277-app-copyright` from `origin/develop` at `90ab1070`.
- 2026-11-08: `factory ready` passed with this task in `todo`. Moved it to `doing` and added the Studio footer. Not committed.
- 2026-11-08: Owner said the copyright belongs to Superstep. The footer now names Superstep. `LICENSE` is unchanged.
- 2026-11-08: Owner asked to align the footer with the handbook. It now reads Superstep, Qui Nguyen, then the year. `LICENSE` is unchanged.
- 2026-11-08: Owner asked to take the branch through finish-pr. Review REV-0263 found no blocking issues. QA QA-0263 passed with the cached-health and notice-overlap follow-ups. Frontend lint, test and build passed. TypeScript SDK typecheck, test and build passed. Python SDK pytest: 229 passed, 8 skipped. Backend pytest: 1492 passed, 112 skipped.

## Handoff Notes

- PR #339 targets `develop`. It is Ready after finish-pr. Do not merge until the owner asks.
- The main checkout stays on local `develop` and is not the worktree for this task.
