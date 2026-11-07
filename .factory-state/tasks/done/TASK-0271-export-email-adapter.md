# Task

## Metadata

- Project: superstep
- Task ID: TASK-0271
- Title: Export Send email adapter
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-07
- Updated: 2026-11-07
- Requirement IDs: REQ-0089
- Architecture IDs: DEC-0088
- Plan: PLAN-0009

## Objective

Replace the Send email stub in Python and TypeScript exports with real SMTP delivery configured by `SMTP_*` environment variables, keeping Studio's dry-run rule for nodes without a credential, per DEC-0088. Split from TASK-0266.

## Acceptance Criteria

- Configured node with a studio credential: one delivery to a local SMTP server, Bcc only in the envelope, auth used, stable Message-ID per run (Python and Deno).
- Private SMTP host refused without `STUDIO_SMTP_ALLOW_PRIVATE=1`; STARTTLS required by default.
- Unconfigured: offline dry run announced; live run refused naming variables. A node without a studio credential never sends.
- No credential or SMTP setting in the generated file.

## Related Artifacts

- Review: `.factory-state/artifacts/REV-0253-TASK-0271-export-email-adapter.md`
- QA: `.factory-state/artifacts/QA-0253-TASK-0271-export-email-adapter.md`

## Activity Log

- 2026-11-07: Created (split from TASK-0266) and implemented.
