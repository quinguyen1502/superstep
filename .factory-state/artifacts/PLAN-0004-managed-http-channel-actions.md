# Plan

- Plan ID: PLAN-0004
- Project: superstep
- Created/Updated: 2026-11-02
- Status: owner-authorised implementation
- Related: REQ-0084, DES-0002, DEC-0082

1. TASK-0235: managed HTTP API definitions, authenticated pinned execution, response validation/redaction, settings/docs/tests/screenshots.
2. TASK-0236: Slack/WhatsApp/Email/Teams managed actions, channel-authorisation reuse, docs/tests/screenshots. JSON webhook remains inbound-only.

Each task gets one branch/Draft PR and full verification, review and QA. Explicit stack: TASK-0235 starts at TASK-0233 (#280, 4aa3a60); the channel task may stack on TASK-0235 while human review is pending. TASK-0234 is an independent example and is not a source dependency. Record final parents in tasks. After predecessors merge, rebase/retarget onto develop, squash per task and rerun landing checks. No merge/deployment/live API calls without owner authorisation.
