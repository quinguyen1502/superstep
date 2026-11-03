# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0210
- Task ID: TASK-0233
- QA Owner: Codex
- Created: 2026-11-01
- Updated: 2026-11-01
- Outcome: pass

## Validation Scope

Managed MCP/Agent integration, configuration/authentication/permissions, non-idempotent outcome safety, migration and configuration/operation UI.

## Acceptance Criteria Coverage

- Managed discovery through the existing registry, MCP and Agent port execution with stable keys: passed. No vendor graph types.
- Fixed Telegram destination, encrypted service account, RS256 token audience/scope, typed scalar RAW sheet values and operation-id column: passed with fake HTTP service.
- Known result reuse and changed-argument/target conflicts: passed.
- Lost response after accepted write, gateway/request timeout, malformed success, crash before request and crash after write before local result: passed. Sheets read-only reconciliation confirms accepted writes; missing rows and Telegram uncertainty do not resend.
- Concurrent call while append is in flight: passed; one append. Provider rejection is not success and is not blindly repeated.
- Owner/org enforcement, personal Telegram delegation refusal and indirect org-channel policy: passed. Dry runs perform no outbound calls or intent writes.
- Migration upgrade/downgrade preserves existing MCP data: passed. Shared layer/envelope checks pass.
- UI create/discover/use via existing MCP node, operation states/read-only check and exact typed-name delete: five final browser tests passed in 47.2 s across en/vi and light/dark, including stdio regression.

## UX And Accessibility Coverage

- Twelve screenshots under .factory-state/evidence/task-0233: Sheets form without populated secret, Telegram form and unknown operation panel in both locales/themes.
- Inspected labels, theme controls, responsive layouts, danger/warning tokens and typed-name confirmation per docs/ui-conventions.md. Strict UI class check has no hits.
- Browser unknown-state presentation is intentionally mocked at the API boundary; backend tests exercise real outcome logic against a fake external HTTP service.

## Checks Performed

- Managed/layers/envelope/migration: 28 passed (9.05 s).
- Existing MCP/effects/Agent/migration regression: 52 passed, one optional skip (21.94 s), with local socket permissions.
- Final frontend build/lint and 149 unit tests passed. Browser five passed in 47.2 s.
- English/Vietnamese handbook builds and media check passed.
- Factory validation, artifact IDs and diff check passed.
- Final full profile passed all eight checks on isolated d1f9eb4 (backend 460.68 s; frontend build/lint/unit; Python SDK; TypeScript SDK build/test/typecheck). Combined-order managed/MCP/layer/envelope regression passed 31 tests (18.94 s) after fixture scope cleanup. No implementation change was needed for that test pollution.
- First isolated full run at cf10f63: 1087 backend passed, 18 skipped, one legacy registry assertion failed because a new permission test left its synthetic MCP connection org-visible. The test now restores its scope in a finally block (and its synthetic org channel likewise); no implementation change. Other seven full-profile checks passed; the combined-order regression and fresh full run above resolved this failure.
- CI at c13ecc2 exposed a separate existing rate-limit test sharing its budget with earlier requests from the common testclient IP (three expected 200 responses were 429). The test now monkeypatches a fresh in-memory limiter, restored automatically afterward. Public-chat/user-token regression: 35 passed (10.23 s). No application behavior changed; fresh CI required.

## Defects

- Locale glossary spellings corrected; the managed service label is translated.
- Browser initially targeted a child of the contenteditable element; fixed the selector and reran on a stable frontend.
- Review identified indirect org-channel policy enforcement through a personal managed MCP connection; fixed and covered by a focused test.

## Gaps Or Untested Areas

- No live Google/Telegram writes or production credential setup. No claim of external exactly-once delivery.
- Optional PostgreSQL/Redis integration depends on the landing CI; local full profile uses repository defaults.

## Residual Risk

- Keep the operation-id column intact; external editors can change sheet data. Scanning is bounded to 100,000 rows.
- Unknown Telegram sends require manual inspection and remain blocked for the original operation key. Starting a new run creates a new key; do not use that to bypass uncertainty.
- Agent instructions must require a confirmed write before claiming success. TASK-0234 uses explicit graph ordering/conditions.

## Assumptions

- Owner review/merge approval remain pending; the expense example is the next task.

## Required Follow-Up

- Wait for fresh CI after the test-isolation fix; owner review on the same Draft PR; complete TASK-0234.

## QA Decision

Passed local QA; task remains in review pending owner approval. Do not mark done or merge without approval.


## Landing Approval

Owner approved implementation and merge of #280 on 2026-11-02. All screenshot evidence is intentionally removed at the owner's request; the historical validation results above remain recorded. Final rebased/squashed head must pass required integration checks before merging.
