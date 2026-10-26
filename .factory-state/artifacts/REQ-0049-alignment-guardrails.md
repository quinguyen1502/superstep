# Requirement

## Metadata

- Project: superstep
- Requirement ID: REQ-0049
- Status: Done (TASK-0086, PR #118)
- Owner: Thái Quí Nguyễn
- Created: 2026-10-23
- Updated: 2026-10-23
- Source: owner request in chat, 2026-10-23, after a misaligned History picker (badge, time and run id against the
  TabsList and the "View all" button) in the panel layout mockup: approved alignment guardrails.

## Summary

- Controls in one row line up by construction: shadcn size variants instead of hand-set heights, paddings and line
  heights; baseline alignment for mixed fonts; a lint check and an e2e check keep it that way.

## Acceptance Criteria

- `docs/ui-conventions.md` has an "Alignment & sizing" rule with a do/don't table (en), and the handbook's
  contributor page mentions it.
- `e2e/helpers/alignment.ts` provides `expectRowAligned(locators, { tolerance: 1 })` (same height and vertical centre)
  and `expectBaselineAligned(textLocators)` (text baselines measured with a baseline probe).
- `e2e/alignment.spec.ts` covers the editor header, the run panel tab row (and the trace summary row), config field
  rows, the workflow list toolbar and dialog footers, in light/dark and en/vi; every real misalignment it finds on
  develop is fixed with shadcn sizes, not ad-hoc overrides.
- A lint check warns when `className` on a component from `@/components/ui/*` contains `h-\d`, `py-\d`,
  `leading-none` or a `text-[…]` size; an inline `ui-class-ok: <reason>` opts out; it runs in `npm run lint`
  (factory verify) and on CI. Existing hits are fixed or opted out with a reason.

## Out Of Scope

- The chat / panel layout work (#117, `mock/panel-layout`); violations seen there are listed in the PR for later.
