# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0211
- Task ID: TASK-0234
- QA Owner: Codex
- Created: 2026-11-02
- Updated: 2026-11-02
- Outcome: pass

## Scope And References

Exact portable expense template from import/use through Telegram event admission, queued worker, model policy, real Code execution and managed effects. Related: REQ-0083, DES-0001, DEC-0081, PLAN-0003, REV-0211 and TASK-0234.

## Acceptance Coverage

- Valid expense: one eight-field row; separate expense/submission dates and authenticated employee; processing reply precedes append and recorded reply follows it.
- Invalid/missing/zero/negative/string/boolean/fractional/too-large amount: feedback, no append. Unrelated text and invalid calendar/date formats also do not append. Missing date defaults to submission date in UTC+07:00.
- Malformed model JSON and exhausted fallback are visible run errors. Primary provider failure uses the configured alternate model.
- Model-provided employee/time/targets are ignored; formula-looking description remains RAW text. Template contains no resource IDs or secrets.
- Duplicate Telegram delivery creates one run. Forced engine replay after transient node-cache cleanup makes no further external calls/writes.
- Accepted append with lost response is reconciled read-only by the retry and then confirmed, with one append. Rejected append and unavailable lookup never send success.
- Existing template UI import/use, setup validation, bound actual graph, callback/worker and confirmed trace: four browser variants passed, English/Vietnamese and light/dark.

## Checks And Evidence

- Combined focused suite (expense, managed tools, templates, layers, envelope): 67 passed in 61.56 s; 19 expense cases.
- Final browser acceptance: four passed in 35.9 s.
- Final frontend build/lint and 149 unit tests passed as part of the full profile.
- Eight screenshots: `.factory-state/evidence/task-0234/expense-workflow-{en,vi}-{light,dark}.png` and `expense-confirmed-{en,vi}-{light,dark}.png`. Representative en/vi images are included in the handbook.
- Final full Factory profile on source 7b030b2: all eight passed (backend 474.02 s, frontend build 6.82 s/lint 0.94 s/unit 5.78 s, Python SDK 13.30 s, TypeScript SDK build 1.03 s/test 0.87 s/typecheck 1.16 s).
- Final English/Vietnamese handbook builds and `check_images.py site`: passed. Factory validation, IDs against origin/develop and diff check: passed. Validation's no-todo warning is the expected final-task lifecycle state after the pre-implementation ready gate passed.
- #281 source CI passed on 7b030b2 (Factory verification, 7m46s). #280 latest CI passed on 4aa3a60 (8m0s); #278 and #279 checks also passed. Stacked feature branches currently run Factory verification; integration matrices must run when retargeted to develop.

## UX Review

Reviewed the graph layout, input, successful node states and confirmed output on both themes/locales. The example uses existing Settings, editor and trace controls. No new component or UI string keys; workflow labels/replies are editable template content. Screenshots show the fake-provider run, not a live Google sheet.

## Gaps And Residual Risk

- Providers are synthetic: backend transport doubles and browser Google/model fixture plus local Telegram HTTP API. No live bot, spreadsheet, paid model, real service key or cutover was used.
- Local Code subprocess executes the reviewed template; production uses the documented Docker/remote isolation. Google initially uses service-account auth.
- Keep the operation-id column, remain below the 100,000-row lookup bound and reconcile uncertain sends manually. New runs create new keys and must not bypass uncertainty.
- n8n deduplication history is not migrated. Pause/drain/reconcile before switching the single Telegram webhook. “Chờ duyệt” is a row status, not an approval process.
- Optional PostgreSQL/Redis/S3/Docker landing checks depend on integration CI after stack retargeting; local verification uses repository defaults.

## QA Decision

Passed local QA and source CI. This follow-up records results without changing implementation. Owner review and merge approval remain pending; task stays in review on Draft #281.

## Landing Approval

Owner approved implementation and merge of #281 on 2026-11-02. All screenshot evidence is intentionally removed at the owner's request; the historical validation results above remain recorded. Final rebased/squashed head must pass required integration checks before merging.

## Combined Landing Verification

Integrated the expense example with all managed adapters before final landing, resolving the shared Playwright entrypoint while retaining both explicit fixture flags, optional channel SMTP and WhatsApp routing. Simultaneous Drive/expense opt-in refuses before server startup. This changes test configuration only; normal app startup remains the default.

On combined source a4e78c3, backend expense/Drive/managed/HTTP/channel/layer/envelope regression: 133 passed (46.21 s). Expense browser four passed (34.9 s); separate Drive browser four passed (39.3 s); default fixture-off MCP/session browser four passed (23.7 s). Mutual-exclusion guard checked. Both handbook builds and image validation passed. Local symlinked dependencies caused font-serving warnings, so these results cover behavior rather than typography; no screenshots were captured. Final rebased PR still requires the full develop CI matrix.
