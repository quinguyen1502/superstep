# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0260
- Task ID: TASK-0274
- QA Owner: Grok (advisory; not owner approval)
- Created: 2026-11-07
- Updated: 2026-11-07
- Outcome: pass with follow-up

## Validation Scope

Approval channel, deadline and AI review on PR #336 head `f52a2fc0`. Evidence is the green CI run and inspection of the generated helpers. Review is REV-0260. This QA did not start a new suite.

## Acceptance Criteria Coverage

- Criterion: An auto reject rule returns rejected without asking a person.
  - Result: pass
  - Evidence: `test_approval_rejects_on_a_rule_and_hides_secrets` calls `review_approval` with `state.message` equal to `rm` and expects `rejected`. Suggest mode on the same rule returns `None`.
- Criterion: A short deadline applies `on_timeout`. A Slack webhook receives one POST when the run waits.
  - Result: pass with a fixture gap
  - Evidence: `test_deadline_approves_when_nobody_answers` replaces `"after": 60.0` with `0.2` and the process exits with an approved answer. The channel POST is proved for Telegram in `test_approval_telegram_posts_locally_and_names_a_missing_key` (one local POST, and a live run with no token names `APPROVAL_TELEGRAM_BOT_TOKEN`). Slack uses `notify_approval`'s webhook branch and the same `approval_post` (`follow_redirects=False`). No Slack server was started.
- Criterion: Credential ids, channel ids and escalate addresses are absent.
  - Result: pass
  - Evidence: The approval test refuses `judge-SECRET`, `ch-SECRET`, `boss-SECRET` and `esc-SECRET`. `test_exports_note_ai_review_without_secrets` refuses `cred1` and `Small refunds` and still requires the words `AI review`.

## UX And Accessibility Coverage

- Criterion: No product UI. Both handbook locales describe the export.
  - Result: pass
  - Evidence: `handbook/docs/en/run/ai-review.md`, `handbook/docs/vi/run/ai-review.md`, and both `python-export.md` guides. Strict build passed: `https://github.com/quinguyen1502/superstep/actions/runs/42370417971/job/128397210938`.

## Checks Performed

- Inspected `review_approval`, `notify_approval`, `wait_approval`, and the Human writer.
- Referenced Backend pytest and factory verify on `f52a2fc0`.

## Defects

- None.

## Gaps Or Untested Areas

- Slack, Teams and generic webhooks were not posted in a test. Telegram was.
- The TypeScript approval helpers were not executed here. CI Deno typecheck is part of the green backend job.
- The deadline test covers `on_timeout` approve. Escalate is present in the generated approval file as `"on_timeout": "escalate"` and was not run as a second wait.

## Residual Risk

- Without judge instructions, automatic approval depends on the default "clearly harmless" line. A reject rule does not need those instructions.
- A reject rule still rejects when the cap file cannot be saved. It does not approve.

## Assumptions

- Telegram plus the shared `approval_post` is enough evidence for the channel criterion. The Slack-shaped fixture is a follow-up, not a failed criterion.

## Required Follow-Up

- None required before the owner reads this record. The task stays in doing.

## QA Decision

conditionally passed with documented risk
