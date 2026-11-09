# Requirement

## Metadata

- Project: langgraph-studio
- Requirement ID: REQ-0034
- Status: Implemented
- Owner: Thái Quí Nguyễn
- Created: 2026-10-19
- Updated: 2026-10-19
- Source: remaining-work report of 2026-10-18 (item 7: "WhatsApp, Teams and e-mail only have an adapter interface so far") and the owner's reply, "Except 2, 3, 4. Do the rest"

## Summary

Human approval requests can go through WhatsApp (buttons), e-mail, and Microsoft Teams (links to the studio's approval page).

## Problem Or Opportunity

- Only Slack and Telegram could carry approval requests.

## Scope

### In Scope

- WhatsApp Cloud API adapter, e-mail and Teams link adapters, the `/approve` page and its API, settings and node UI, docs, tests

### Out Of Scope

- A Teams bot (Bot Framework), WhatsApp template creation, inbound e-mail replies

## Stakeholders Or Users

- Workflow owners and approvers

## Desired Behavior

- See DEC-0037.

## Business Rules

- Only the run owner or a listed approver decides; a request is answered once; expired requests are refused; every attempt is audited.

## Constraints

- No new dependency. The existing adapter interface, extended rather than bypassed.

## Acceptance Criteria

- WhatsApp: the GET verification returns the challenge only for the right verify token; a request has two reply buttons; a correctly signed press approves and the run resumes; a wrong signature gets 401; a second press is refused privately; template mode sends the template with the tokens as quick-reply payloads.
- E-mail: a connection needs SMTP and a public URL; every target address receives Approve / Reject links; a stranger cannot view or decide; the approver's POST resumes the run; a second answer is refused; a bad address is audited as `send_failed` and the run keeps waiting.
- Teams: a connection per webhook URL, which must be HTTPS outside tests; the node needs no target; the card's Approve link opens `/approve`; confirming resumes the run and posts an outcome card.
- The settings page shows no callback URL for link channels, and "My accounts" has no slot for them.

## Edge Cases

- One verified owner per WhatsApp number, as for other chat accounts.

## Assumptions

- A Workflows webhook is an acceptable way to reach Teams.

## Open Questions

- None

## Related Artifacts

- Decision: `.factory-state/decisions/DEC-0037-whatsapp-email-teams-approvals.md`
- Task: `.factory-state/tasks/done/TASK-0047-more-approval-channels.md`
- Earlier decision: `.factory-state/decisions/DEC-0019-approval-channels.md`
