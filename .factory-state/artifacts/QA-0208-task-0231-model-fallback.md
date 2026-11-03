# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0208
- Task ID: TASK-0231
- QA Owner: Codex
- Created: 2026-11-01
- Updated: 2026-11-01
- Outcome: pass

## Validation Scope

Opt-in primary/fallback LLM policy, owner-bound credentials, cancellation/timeout/error boundaries, output safety, export/template behavior, UI persistence and existing-provider regression.

## Acceptance Criteria Coverage

- Existing behavior and offline mock: passed; test_model_fallback.py verifies live tokens without a policy and no credential reads in mock mode.
- Bounded attempts, permission/auth failure, both failed, cancellation and timeout: passed in focused backend tests. A saved run cannot use another owner's alternate credential.
- Safe output and trace: passed; only complete successful text is emitted and attempts carry provider/model/status/code without secrets.
- Configuration/validation/export: passed; invalid policies give translated issues, sanitisation blanks the alternate reference, both exporters explicitly reject configured unsupported policies.
- Editor configuration persists through save/reload and can be disabled: browser regression covers both languages and themes, plus existing llm-providers.spec.ts.

## UX And Accessibility Coverage

- Existing labelled shadcn controls and theme tokens; read-only covered by existing editor fieldset.
- Four screenshots under `.factory-state/evidence/task-0231/`; model-picker row alignment asserted by Playwright. No new destructive control.
- docs/ui-conventions.md checklist reviewed; strict UI class check has no hits.

## Checks Performed

- Backend focused policy/provider/layer/envelope/validation/node policy: 57 passed.
- Frontend unit tests: 149 passed across 32 files.
- Full `factory verify run --profile full`: eight checks passed (backend 456.33 s; frontend build/lint/unit; Python SDK; TypeScript SDK build/test/typecheck). Real Deno and ARM Node wrapper used as recorded in project runtime notes.
- Final frontend controlled-Select change: build and lint passed; browser suite rerun.
- Final browser suite: five passed in 48.8 s, including all four language/theme variants and the existing provider regression.
- Handbook English and Vietnamese builds: no issues. `check_images.py site`: all images found.
- Factory validation passed.

## Defects

- Browser test selectors initially assumed expanded trace JSON and globally unique credential labels; corrected test selectors and fixtures, then rerun.
- Controlled Select warning corrected in implementation.

## Gaps Or Untested Areas

- No live paid-model calls or production cutover. Browser calls use a local fake Ollama endpoint and an intentionally unreachable local primary.
- No PostgreSQL/Redis service available for optional integration checks; full profile uses repository defaults.

## Residual Risk

- Failed-provider billing can be unknown. Buffered policy output is delivered after success; fallback remains unsupported by standalone code exports and is explicitly refused.

## Assumptions

- Owner review and merge approval are separate from this local QA result.

## Required Follow-Up

- Owner review of the Draft PR before completion/merge. Event/managed-tool/expense tasks remain outstanding.

## QA Decision

Passed local QA; task remains in review pending owner approval.
