# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0291
- Task ID: TASK-0306
- QA Owner: Codex
- Created: 2026-11-12
- Updated: 2026-11-12
- Outcome: Pass
- Review ID: REV-0291

## Validation Scope

Monthly budget CRUD, calendar spend, warning claims, notifications, admin UI and the schema migration. Product diff reviewed at `a1439e71` on PR #362.

## Acceptance Criteria Coverage

- Criterion: User and team spend matches calendar-month usage, and unpriced rows are visible.
  - Result: Pass
  - Evidence: The budget API regression checks both scopes, excludes a prior-month row and reports unpriced rows. The local screenshot showed both scopes with separate amounts.
- Criterion: Runs continue at and above 100 percent and each monthly threshold is issued at most once.
  - Result: Pass
  - Evidence: Run completion records usage and calls the advisory checker after the run is persisted. Concurrent evaluations of the same spend produced one notification per budget and threshold. The preview showed 80 and 100 percent warnings.
- Criterion: The API rejects unauthorized access and the UI requires the exact target name to delete.
  - Result: Pass
  - Evidence: The backend regression asserts 403 and Playwright verifies case-sensitive confirmation and successful deletion.

## UX And Accessibility Coverage

- The admin Usage card uses existing UI components, localized labels and the shared exact-name delete confirmation. The backend retains its API envelope and repository boundaries.

## Checks Performed

- [Full Factory verification](https://github.com/quinguyen1502/superstep/actions/runs/43118990015)
- [Product CI and three Playwright shards](https://github.com/quinguyen1502/superstep/actions/runs/43118990020)
- Local checks and preview evidence are listed above.

## Defects

- No open blocking defects.

## Gaps Or Untested Areas

- The local preview exercised in-app delivery. SMTP and webhooks use the existing delivery service. External delivery after the database claim remains best effort.

## QA Decision

Passed to done. The final delivery commit will run through the required GitHub checks before merge.
