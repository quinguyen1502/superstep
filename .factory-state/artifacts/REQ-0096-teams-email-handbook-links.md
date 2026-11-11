# Requirement

## Metadata

- Project: superstep
- Requirement ID: REQ-0096
- Status: Proposed 2026-11-10 (Asia/Saigon); awaiting owner acceptance
- Owner: Thái Quí Nguyễn
- Created/Updated: 2026-11-10
- Source: Owner chat 2026-11-10 (pt279u, asking to file tasks for the remaining work); REQ-0087 deferred Teams and e-mail links to a future requirement on 2026-11-07
- Related: REQ-0087, DES-0005, DEC-0086, PLAN-0007, TASK-0260, PLAN-0015, TASK-0309

## Summary And Scope

TASK-0260 linked the Channels "public URL missing" notice and the Slack, Telegram and WhatsApp add-connection helpers to the handbook. Teams and e-mail were deferred. This requirement adds the same "Setup guide" link for the Microsoft Teams and e-mail approval channels, pointing to the handbook section on e-mail and Microsoft Teams.

Out of scope: guided tours or onboarding walkthroughs. Superstep has no product tour today, so there is no tour to link; a tour would need its own requirement and owner decision. Also out of scope: new help texts, a docs panel, and any change to DEC-0086 (fixed published handbook URLs).

## Business Rules

- Same rules as REQ-0087: `HandbookLink` opens the published handbook in a new tab with `rel="noopener noreferrer"`, an accessible name and en and vi labels; links never block the setting they explain.
- Anchors are identical in both locales, as DEC-0086 requires; explicit heading ids are added where the localized headings differ.

## Acceptance Criteria

- The Teams and e-mail add-connection helpers show a "Setup guide" link to the correct locale and anchor; unit and e2e tests assert href, target and rel.
- Strict en and vi handbook builds and locale parity pass; full Factory verify and validate, REV and QA artifacts, all required CI green before merge.
