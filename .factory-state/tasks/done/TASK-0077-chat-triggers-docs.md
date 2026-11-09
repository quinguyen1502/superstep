# Task

## Metadata

- Project: superstep
- Task ID: TASK-0077
- Status: done (PR #101, REV-0071, QA-0071)
- Owner: Thái Quí Nguyễn
- Created: 2026-10-22
- Updated: 2026-10-22
- Requirement IDs: REQ-0044
- Design IDs: none
- Architecture IDs: DEC-0046

## Objective

Explain chat triggers in the handbook (en, vi): setup for Slack and Telegram, the dialog, what the bot replies and why
a message can be refused.

## Scope

### In Scope

- **New page `run/chat-triggers.md`** (en "Chat triggers", vi "Run from chat"). It covers:
  - what a chat trigger is;
  - Slack setup: the scopes, the Event Subscriptions URL, the `app_mention` and `message.im` events, reinstalling;
  - Telegram setup: "Register webhook" again, group privacy mode, the group id;
  - linking your chat account (Profile);
  - the dialog fields;
  - the replies (started, result, error, waiting) and the private refusals;
  - limits and security: who may run, the owner's credentials, rate limits.
- **Links:** nav in both `mkdocs*.yml`, the Run index, the Channels page, the API trigger and schedules
  pages, and the README feature list (en, vi).
- **Screenshot** `chat-triggers.png` (en, vi) from `e2e/handbook.spec.ts`: the dialog with one trigger. Only the new
  image is kept.

### Out Of Scope

- Behaviour changes.

## Inputs

- TASK-0074 to TASK-0076; DEC-0046; the existing Channels and Schedules handbook pages.

## Related Artifacts

- Requirement: `.factory-state/artifacts/REQ-0044-chat-triggers.md`
- Clarification: `.factory-state/artifacts/CLAR-0002-chat-triggers.md`
- Design: none
- Architecture: none
- Decisions: DEC-0046
- Discovery: none

## Expected Outputs

- `handbook/docs/{en,vi}/run/chat-triggers.md`, nav, links, README lines, screenshot

## Implementation Notes

- Capture the screenshot the same way as `code-tab.png` (TASK-0072), then restore the other re-rendered images.

## Constraints

- en and vi pages have the same structure. Strict builds and `check_images.py` pass.

## Dependencies

- TASK-0076.

## Acceptance Criteria

- The page (en, vi) covers setup for both platforms, the dialog, the replies and the refusals, with a screenshot.
- Both strict builds, the same-pages check and `check_images.py` pass. The handbook capture e2e passes.

## Validation Plan

- `zensical build -f mkdocs.yml --strict`, `-f mkdocs.vi.yml --strict`, `check_images.py site`,
  `HANDBOOK_SHOTS=1 npx playwright test handbook`.

## Assumptions

- None.

## Open Questions

- None.

## Activity Log

- 2026-10-22: planned from REQ-0044.
- 2026-10-22: started after PR #100 merged (owner approved).
- 2026-10-22: implemented; the page is `run/chat-triggers.md` (next to API triggers and Schedules). Review REV-0071, QA QA-0071.
- 2026-10-22: CI green on PR #101 (Postgres included); the owner approved the merge.

## Handoff Notes

- None.
