# Task

## Metadata

- Project: superstep
- Task ID: TASK-0236
- Status: todo
- Owner: Thái Quí Nguyễn
- Created/Updated: 2026-11-02
- Requirement IDs: REQ-0084
- Design IDs: DES-0002
- Architecture IDs: DEC-0082

## Objective And Scope

Expose Slack, WhatsApp, Email and Microsoft Teams sending actions as managed adapters, using existing approval-channel credentials and fixed destinations. Share authorisation with Telegram, preserve owner/org rules, durable conservative outcomes and offline dry runs. Add bilingual settings/docs and browser evidence. JSON webhook is inbound-only; Telegram/Sheets already exist.

No new graph types, inbound platform expansion, approval-template reuse, service credential provisioning, live sends or deployment.

## Related Artifacts

- `.factory-state/artifacts/REQ-0084-managed-http-channel-actions.md`
- `.factory-state/artifacts/DES-0002-managed-http-channel-actions.md`
- `.factory-state/decisions/DEC-0082-managed-http-channel-actions.md`
- `.factory-state/artifacts/PLAN-0004-managed-http-channel-actions.md`
- `docs/backend-architecture.md`, `docs/ui-conventions.md`, TASK-0233 and TASK-0235.

## Acceptance Criteria

- Existing MCP/Agent discovery and calls send bounded text/subject through the chosen channel to its configured destination; no model-chosen targets or secrets.
- Personal/org/indirect org-channel rules match Telegram. A removed/unavailable channel fails safely at execution.
- Known results replay without another send; uncertain/failed sends are never blindly repeated; dry runs do no network/SMTP work.
- Provider payload/auth/acknowledgement, error/timeout/malformed/partial SMTP outcomes covered with fake providers; existing Telegram/Sheets/MCP/channel tests pass.
- en/vi forms/docs explain WhatsApp service window and submission-vs-delivery semantics. Screenshots in both themes/locales, typed-name deletion unchanged.

## Validation Plan

- Focused channel-action/managed/approval/MCP/layer/envelope tests, frontend build/lint/unit and browser creation/discovery/use/screenshots.
- Full Factory verification, both handbook builds/media, IDs/diff, advisory review and QA.

## Dependencies And Assumptions

- Explicit stack on TASK-0235 under PLAN-0004; record actual parent when starting. Owner explicitly selected the approval-channel registry as the service list.
- No new dependency/migration anticipated. Existing SMTP/pinned HTTP helpers are authoritative.

## Activity Log

- 2026-11-02: Planned from owner clarification: use services in approval channels. Implementation follows TASK-0235 in a separate branch/Draft PR; no merge approval inferred.
