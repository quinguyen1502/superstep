# Task

## Metadata

- Project: superstep
- Task ID: TASK-0309
- Title: Teams and e-mail handbook links in Channels settings
- Status: backlog
- Owner: Thái Quí Nguyễn
- Created: 2026-11-10
- Updated: 2026-11-10
- Requirement IDs: REQ-0096
- Design IDs: DES-0005
- Architecture IDs: DEC-0086
- Plan: PLAN-0015
- Phase: docs
- Size: S

## Objective

Finish the contextual handbook links that TASK-0260 deferred for Microsoft Teams and e-mail connections.

## Owner-Facing Outcome

When adding a Teams or e-mail approval channel in Settings, Channels, the help text ends with a "Setup guide" link that opens the handbook section on e-mail and Microsoft Teams in the user's language, like Slack, Telegram and WhatsApp today.

## Scope

### In Scope

- Stable, identical heading anchors for the section in both locales (today the en heading `## E-mail and Microsoft Teams` and the localized vi heading produce different slugs): add explicit ids, for example `{#email}` and a `{#teams}` anchor, in `handbook/docs/{en,vi}/operate/channels.md`; split the section only if one anchor per platform reads better.
- Extend the `GUIDE` map in `frontend/src/components/approvals/channel-parts.tsx` with `email` and `teams`; reuse `HandbookLink` and the existing `docs.setupGuide` / `docs.setupGuideAria` keys.
- Unit test for the anchors and an e2e assertion of href, target and rel for both kinds (extend `frontend/e2e/handbook-links.spec.ts`).

### Out Of Scope

- Any guided tour or onboarding walkthrough (Superstep has none today; a tour would need its own requirement).
- Rewriting channel help texts.

## Dependencies

- None.

## Acceptance Criteria

- Teams and e-mail add-connection helpers show the link to the correct locale and anchor; existing Slack, Telegram and WhatsApp links unchanged.
- Strict en and vi handbook builds pass; en/vi locale parity passes.

## Validation Plan

- Strict en/vi handbook build; frontend `npm run lint`, `npm run build`, `npm test`; targeted Playwright `frontend/e2e/handbook-links.spec.ts`.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts; all required CI including E2E green before merge.

## Open Questions

- None

## Activity Log

- 2026-11-10: Created by planning on branch factory/plan-observability-next. No implementation. Stays in backlog until the owner accepts REQ-0096 and PLAN-0015.

## Handoff Notes

- Use branch `factory/task-0309-teams-email-handbook-links` from `develop` when implementation begins.
