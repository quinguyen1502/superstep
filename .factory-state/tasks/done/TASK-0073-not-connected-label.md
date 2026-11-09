# Task

## Metadata

- Project: superstep
- Task ID: TASK-0073
- Status: done (PR #95, REV-0066, QA-0066)
- Phase: release
- Owner: Thái Quí Nguyễn
- Created: 2026-10-22
- Updated: 2026-10-22
- Requirement IDs: none (a UI fix reported by the owner; found on REQ-0040 channel templates)
- Design IDs: none
- Architecture IDs: DEC-0008

## Objective

Show a translated label for a Human node whose approval channel kind has no connection yet. The owner reported that
on a workflow made from a channel template (for example "Leave request", Microsoft Teams) the "Send approval requests
to" select showed "Microsoft Teams · approvals.notConnected".

## Cause

`components/human-approval-settings.tsx` renders the disabled `missing` item with `t('approvals.notConnected')`, but
the key was in neither `locales/en.json` nor `locales/vi.json`, so i18next printed the raw key.

## Fix

- Add `approvals.notConnected` to both locale files with identical keys: en "not connected" (and its vi label).
- No component change.

## Acceptance Criteria

- The select shows "<Channel> · not connected" in English and "<Channel> · not connected" in Vietnamese, never the raw
  key.

## Validation

- `frontend/e2e/templates.spec.ts` "process templates": after opening the Social post template's Human node, the
  `#approval-channel` select contains "not connected" and no `approvals.` key. Without the locale fix it fails with
  `Received string: "Telegram · approvals.notConnected"`; with it, it passes.
- `npx tsc -b`, `npm run lint` (exit 0) and `npx vitest run` (62 passed).
- `npx playwright test e2e/templates.spec.ts e2e/approval-channels.spec.ts`: 4 passed.
- QA in the browser, "Leave request" template, `manager` node: `Microsoft Teams · not connected` (en),
  `Microsoft Teams · not connected` (vi) (QA-0066).
- CI on PR #95: all six checks passed.
