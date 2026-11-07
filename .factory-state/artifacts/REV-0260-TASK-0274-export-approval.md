# Review

## Metadata

- Project: superstep
- Review ID: REV-0260
- Task ID: TASK-0274
- Reviewer: Grok (advisory; not owner approval)
- Created: 2026-11-07
- Updated: 2026-11-07
- Outcome: approved for QA

## Review Scope

`factory/req-0090-export-remaining` against `develop` `5f68852f`, PR #336, head `f52a2fc0`. This review covers approval channels, deadlines and AI review in `export_runtime.py` (`PY_APPROVAL`, `TS_APPROVAL`), the writers in both exporters, and `tests/test_export_remaining.py` approval and deadline cases. Slots are REV-0259. Managed calls are a separate review.

## Reference Artifacts

- REQ-0090, DEC-0089, PLAN-0010, TASK-0274, TASK-0188 (`test_exports_note_ai_review_without_secrets`)

## Findings

### Blocking

- None. No blocking findings.

### Non-Blocking

- Judge instructions are not written. TASK-0188 forbids them, and `b6c9e52b` removed the leak that failed the first CI run. The judge then uses the sentence that it should escalate unless the request is clearly harmless, so the exported rubric is stricter than the Studio instructions.
- The executed channel proof is Telegram through a local `TELEGRAM_API_URL`. Slack, Teams and a generic channel use the same `approval_post` with `APPROVAL_<KIND>_WEBHOOK_URL`. There is no separate Slack fixture.
- A reject rule still returns `rejected` when the cap file cannot be written. That path does not auto-approve. The cap file blocks automatic approval, which is the edge case in REQ-0090.
- Approval webhook URLs are operator environment and are not pinned. Managed targets stay pinned. That split is the task assumption.

## Standards And Architecture Alignment

- The helpers are generated source. No FastAPI type and no new API error code.
- Channel ids, approver addresses and escalate addresses are dropped before emission. The approval test refuses `judge-SECRET`, `ch-SECRET`, `boss-SECRET` and `esc-SECRET`.
- Example answers return before `notify_approval`. A simple Human node without a channel, deadline or policy still uses the one-line `interrupt`.
- Cross-language code nodes still raise `NotImplementedError`.

## Design Alignment

- No product UI. English and Vietnamese export and AI-review pages describe the channel, the deadline and the omitted judge credential and instructions. The strict handbook build passed.

## Validation Review

- `test_approval_rejects_on_a_rule_and_hides_secrets`, `test_deadline_approves_when_nobody_answers` and `test_approval_telegram_posts_locally_and_names_a_missing_key` are in the green Backend pytest run on `f52a2fc0`: `https://github.com/quinguyen1502/superstep/actions/runs/42370417978/job/128397211356`.
- Factory verify passed: `https://github.com/quinguyen1502/superstep/actions/runs/42370418030/job/128397211110`.
- This review did not re-run the suite. Local Deno was not installed.

## Assumptions

- Omitting judge instructions is required by TASK-0188 and is the intended export, not a missing field.

## Required Follow-Up

- None before QA. Owner approval is still required before done.

## Review Decision

approved for QA
