# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0329
- Task ID: TASK-0340
- QA Owner: implementation QA
- Created: 2026-11-13
- Updated: 2026-11-13
- Outcome: pass

## Validation Scope

TASK-0340 on `factory/task-0340-dataset-studio-states`. Backend tests used `backend/.venv` on SQLite; PostgreSQL cases run in CI. Playwright ran against an isolated local stack with the system Chrome.

## Acceptance Criteria Coverage

- Criterion: Screenshots of viewer, empty, not found, row delete, and CSV issues in en/vi light/dark show the explanation and action.
  - Result: pass
  - Evidence: `e2e/dataset-studio-states.spec.ts` attaches `dataset-empty`, `dataset-not-found`, `dataset-viewer`, `dataset-delete-row`, and `dataset-csv-issues` for en-light, en-dark, vi-light, and vi-dark, plus the viewer Schema dialog in Vietnamese. Each variant asserts the explanation text and the action (Create and Import CSV, Back to datasets, disabled controls with the reason, the named delete text, the issue list).
- Criterion: Delete confirmation shows the row's key value.
  - Result: pass
  - Evidence: the spec opens Delete row for the `T-1` row and sees "This permanently deletes the row where Ticket is T-1." in both languages; a row without a unique value shows its row ID. `e2e/datasets.spec.ts` checks the named text on its own dataset.
- Criterion: CSV issues are ordered by line and show label, value, and message.
  - Result: pass
  - Evidence: the spec imports a file with a repeated unique value, an invalid number, a short record, and a 90-character invalid value. The list is lines 2, 3, 4, 5 with "Ticket", "Score", the rejected values, the long value shortened with an ellipsis, and the counts per kind. `tests/test_dataset_csv.py` checks the server order and the 200-character cut.

## UX And Accessibility Coverage

- Criterion: Show-and-explain for users who may not change the dataset, keyboard reachable, both themes.
  - Result: pass
  - Evidence: disabled controls carry `aria-describedby` to the visible reason (asserted with `toHaveAccessibleDescription`). The disabled Create button sits in a focusable wrapper that shows the reason as a tooltip. The empty and not-found blocks stay inside the viewport (asserted). Dark and light screenshots were reviewed.

## Checks Performed

- `pytest tests/test_dataset_csv.py` — 4 passed.
- `npx vitest run src/lib/__tests__/locales.test.ts src/lib/__tests__/dataset-csv-issues.test.ts` — 9 passed.
- `npm run lint` and `npm run build` — passed.
- `npx playwright test e2e/dataset-studio-states.spec.ts e2e/datasets.spec.ts e2e/dataset-csv.spec.ts e2e/dataset-access.spec.ts` with `PW_CHROME=/usr/bin/google-chrome` — passed.
- `factory verify run --profile full` — passed: frontend build, lint, and test; backend pytest; Python SDK tests; TypeScript SDK build, test, and typecheck.
- `factory validate` and `factory validate --only hygiene` — passed.

## Defects

- None.

## Gaps Or Untested Areas

- PostgreSQL and the other E2E shards run in CI.
- Team managers without `resources.manage` are not covered until TASK-0335 lands.

## Residual Risk

- Low. The changes are presentation and preview issue fields.

## Assumptions

- None.

## Required Follow-Up

- After TASK-0335: use the per-dataset permission for the disabled state and add a team-manager reason.

## QA Decision

Passed to done.
