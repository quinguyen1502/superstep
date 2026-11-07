# Task

## Metadata

- Project: superstep
- Task ID: TASK-0260
- Title: Contextual handbook links in Channels settings
- Status: backlog (awaiting owner acceptance of REQ-0087)
- Owner: Thái Quí Nguyễn
- Created: 2026-11-06
- Updated: 2026-11-06
- Requirement IDs: REQ-0087
- Design IDs: DES-0005
- Architecture IDs: DEC-0086
- Plan: PLAN-0007

## Objective

Add a locale-aware handbook URL helper per DEC-0086 and link the Channels public-URL notice and Slack/Telegram/WhatsApp helpers to the handbook.

## Scope

- `frontend/src/lib/handbook.ts` helper; `docs.learnMore` en/vi keys; links in `channel-parts.tsx` and connection helpers.
- Unit test for URL building; e2e asserts href/target/rel for the missing-public-URL notice.

## Acceptance Criteria

- REQ-0087 UI criteria; locale parity; no tour or redesign.

## Validation Plan

- Strict en/vi handbook build and image check; frontend build/lint/vitest; targeted Playwright; full `factory verify` and `factory validate`; REV/QA artifacts.

## Activity Log

- 2026-11-06: Created by planning on branch factory/plan-docs-links-tunnel. No implementation.
