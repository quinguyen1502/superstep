# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0261
- Task ID: TASK-0275
- QA Owner: Grok (advisory; not owner approval)
- Created: 2026-11-07
- Updated: 2026-11-07
- Outcome: pass with follow-up

## Validation Scope

Managed connections on PR #336 head `f52a2fc0`. Evidence is the green CI run and inspection of `managed_operation`. Review is REV-0261. This QA did not start a new suite.

## Acceptance Criteria Coverage

- Criterion: A telegram export posts once to a local API when the environment is set, returns the stored result on the same arguments, and does not retry HTTP 500.
  - Result: pass
  - Evidence: `test_managed_telegram_is_idempotent_and_does_not_retry_unknown`. The local server records one POST for two calls with the same arguments. An HTTP 500 becomes `ManagedUnknown`, is stored as unknown, and the next call does not POST.
- Criterion: The server id and secret values are absent.
  - Result: pass
  - Evidence: The same test refuses `srv-SECRET` and `bot-SECRET-VALUE`. The file contains `MANAGED_1` and the adapter name `telegram`.
- Criterion: An invalid browser export still contains `Managed connection placeholder` and does not contain `browser_call(`.
  - Result: pass
  - Evidence: `tests/test_browser_python_export.py::test_invalid_browser_settings_stay_a_placeholder`, included in the green Backend pytest job above.

## UX And Accessibility Coverage

- Criterion: No product UI. Both handbook locales describe managed connections.
  - Result: pass
  - Evidence: The managed rows in `handbook/docs/en/guide/python-export.md` and `handbook/docs/vi/guide/python-export.md`. Strict build passed: `https://github.com/quinguyen1502/superstep/actions/runs/42370417971/job/128397210938`.

## Checks Performed

- Inspected the journal, the pin, the Google token URL, and the placeholder guard.
- Referenced Backend pytest and factory verify on `f52a2fc0`.

## Defects

- None.

## Gaps Or Untested Areas

- Slack, WhatsApp, Teams, HTTP API, email, Sheets, Drive and web were not executed. Telegram was.
- TypeScript managed email was not executed. CI Deno covers typecheck of generated TypeScript, not this SMTP client.
- A failed save after a successful send was not exercised.

## Residual Risk

- The journal key ignores the arguments. Different arguments on the same prefix and tool in one run conflict instead of sending.
- A save failure after a successful send raises, and a later call can send again.

## Assumptions

- Proving Telegram plus the shared dispatch table is enough for this task's written criteria. The other adapters are follow-up risk.

## Required Follow-Up

- None required before the owner reads this record. The task stays in doing.

## QA Decision

conditionally passed with documented risk
