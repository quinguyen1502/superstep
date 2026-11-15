# Requirement

## Metadata

- Project: superstep
- Requirement ID: REQ-0045
- Status: Implemented (TASK-0078 PR #107)
- Owner: Thái Quí Nguyễn
- Created: 2026-10-23
- Updated: 2026-10-23
- Source: owner request in chat, 2026-10-23: review the Vietnamese language quality of the UI, README and docs, then
  apply the approved glossary and fix plan (steps 1-8).

## Summary

- The Vietnamese UI (`frontend/src/locales/vi.json`), `README.vi.md` and `handbook/docs/vi` use one glossary and one
  register, contain no leftover English labels, and the README describes the current features.

## Problem Or Opportunity

- The review (2026-10-23) found three different Vietnamese words for "run", the Vietnamese word for button used for nodes, mixed English and Vietnamese words for "field", "key" and "credential", both "e-mail" and "email", old and new
  tone marks mixed, about 25 untranslated labels, a hint that names a button that does not exist ("Press Run"), an
  English trace summary, three hard-coded English strings, and README feature lists missing templates, tests, Python
  export and the approvals inbox and deadlines.

## Scope

### In Scope

- A glossary in `docs/ui-conventions.md` (rule 10).
- vi.json fixes; i18n for the hard-coded dialog "Close" (two places) and the default workflow name.
- A unit test for key and placeholder parity, banned terms and reviewed vi = en strings.
- README.md and README.vi.md feature lists and wording; the glossary applied to the Vietnamese handbook.

### Out Of Scope

- English wording changes beyond the README; backend messages (`core/errors.py`, chat/email bodies).

## Acceptance Criteria

- `npm test` (incl. `locales.test.ts`), `npm run lint`, `npm run build`, the e2e suite and both strict handbook builds pass.
- Vietnamese screenshots of the screens with long strings show no broken layout.

## Open Questions

- None.
