# Review

## Metadata

- Project: superstep
- Review ID: REV-0261
- Task ID: TASK-0275
- Reviewer: Grok (advisory; not owner approval)
- Created: 2026-11-07
- Updated: 2026-11-07
- Outcome: approved for QA

## Review Scope

`factory/req-0090-export-remaining` against `develop` `5f68852f`, PR #336, head `f52a2fc0`. This review covers `PY_MANAGED` and `TS_MANAGED` in `export_runtime.py`, `check_export` in `mcp_service.py`, `note_mcp` / `managed_prefix`, and `test_managed_telegram_is_idempotent_and_does_not_retry_unknown`. Slots are REV-0259. Approval is REV-0260.

## Reference Artifacts

- REQ-0090, DEC-0089, PLAN-0010, TASK-0275

## Findings

### Blocking

- None. No blocking findings.

### Non-Blocking

- The journal key is a hash of the run id, the prefix and the tool. Arguments are only a fingerprint on that row. A second call with different arguments on the same prefix and tool in one run conflicts. REQ-0090 states that conflict. Two different Telegram sends on one connection in one run stop on the second.
- `managed_save` after a successful send raises when the write fails. The next call does not see the row, so it can send again.
- The executed adapter is Python Telegram. TypeScript email is a small SMTP client and was not executed. Google token URL is the fixed `https://oauth2.googleapis.com/token` in both languages. The TypeScript missing-JWT error still names PyJWT and cryptography.
- A call without a string prefix or adapter still raises `Managed connection placeholder` before any network call. Invalid browser settings stay on that path.

## Standards And Architecture Alignment

- `check_export` stays in the service. The exporter reads the adapter id from an internal key and does not write the server id or secrets.
- Targets are pinned, redirects are not followed, and a private address needs `STUDIO_MCP_ALLOW_PRIVATE=1`. Approval posts do not use this pin.
- `managed_placeholders` stays true when any managed reference exists, including a real adapter. The two-argument call still raises.
- No new API error code.

## Design Alignment

- No product UI. English and Vietnamese handbook rows describe `MANAGED_<n>_SETTINGS` and `MANAGED_<n>_SECRETS`. The strict handbook build passed.

## Validation Review

- `test_managed_telegram_is_idempotent_and_does_not_retry_unknown` is in the green Backend pytest run on `f52a2fc0`: `https://github.com/quinguyen1502/superstep/actions/runs/42370417978/job/128397211356`.
- `test_invalid_browser_settings_stay_a_placeholder` is in that same job.
- Factory verify passed: `https://github.com/quinguyen1502/superstep/actions/runs/42370418030/job/128397211110`.
- This review did not re-run the suite.

## Assumptions

- One journal row per prefix and tool per run is the idempotency rule the requirement describes.

## Required Follow-Up

- None before QA. Owner approval is still required before done.

## Review Decision

approved for QA
