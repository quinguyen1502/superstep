# Task

## Metadata

- Project: superstep
- Task ID: TASK-0260
- Title: Contextual handbook links in Channels settings
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-06
- Updated: 2026-11-07
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

## Related Artifacts

- Review: `.factory-state/artifacts/REV-0243-TASK-0260-handbook-links.md`
- QA: `.factory-state/artifacts/QA-0243-TASK-0260-handbook-links.md`

## Validation Plan

- Strict en/vi handbook build and image check; frontend build/lint/vitest; targeted Playwright; full `factory verify` and `factory validate`; REV/QA artifacts.

## Activity Log

- 2026-11-06: Created by planning on branch factory/plan-docs-links-tunnel. No implementation.
- 2026-11-07: Owner accepted DEC-0086 option A. Added `frontend/src/lib/handbook.ts` (fixed `https://quinguyen1502.github.io/superstep/`, `vi/` for Vietnamese), `HandbookLink` (new tab, `noopener noreferrer`, accessible name with "opens in a new tab"), `docs.*` en/vi keys. Links: "Learn more" (with its vi label) after the STUDIO_PUBLIC_URL-missing note → `operate/expose-local/`; "Setup guide" after the Slack/Telegram/WhatsApp add-connection help → `operate/channels/#slack|#telegram|#whatsapp-cloud-api` (anchors identical in both locales). Teams, e-mail and tour deferred by the owner.
- 2026-11-07: Root `npm ci`, `npm run lint` (warnings only, pre-existing), `npm run build`, `npm test` (frontend 39 files/172 tests incl. new `handbook.test.ts`; React 22; TypeScript SDK 102) passed. Playwright `e2e/handbook-links.spec.ts` and `e2e/approval-channels.spec.ts` passed locally with system Chrome.
