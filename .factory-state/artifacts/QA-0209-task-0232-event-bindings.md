# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0209
- Task ID: TASK-0232
- QA Owner: Codex
- Created: 2026-11-01
- Updated: 2026-11-01
- Outcome: pass

## Validation Scope

Telegram/signed JSON admission and mapping, callback verification, concurrent duplicate delivery, queue failure/retry, legacy command/approval compatibility and management UI.

## Acceptance Criteria Coverage

- Telegram ordinary text and actor/message/timestamp context mapped to declared typed fields: passed in test_event_bindings.py.
- Wrong signatures, old/malformed signatures, place/sender/type, bots/edits, absent IDs/timestamps, oversized input, disabled bindings: passed focused tests.
- Atomic duplicate suppression under 16 simultaneous deliveries: passed; one run and one audit. Queue failure after commit/retry reuses the original input: passed.
- Signed JSON uses the same envelope/mapping and owner-bound run queue: passed. Inbound-only channel excluded from Human approvals and identity linking.
- Legacy chat trigger/run and approval tests: initial focused suite 47 passed. Additional org-policy test fixture was corrected to invoke the service instance whose policy was overridden; final focused/full result follows below.
- Translated create/edit/toggle/delete with exact typed-name confirmation and persisted mapping: five final browser tests passed in 26.1 s, including the legacy Slack command flow.

## UX And Accessibility Coverage

- `.factory-state/evidence/task-0232/event-binding-{en,vi}-{light,dark}.png`; visually inspected. Labelled shared controls, responsive grid, scrollable dialog and shared confirmation used.
- docs/ui-conventions.md checklist reviewed. Strict UI class check has no hits. No colours or node types introduced.
- Header differentiates run-as-owner event admission from linked-account commands.

## Checks Performed

- Frontend build/lint/unit: passed (149 tests, 32 files).
- Browser: five passed, final 26.1 s.
- Both handbook builds: no issues; media: all images found.
- Factory validation, IDs against origin/develop and diff check passed.
- Full profile: all eight checks passed on isolated checkout 6b9657b at `/private/tmp/superstep-task-0232-verify` (backend 457.84 s; frontend build/lint/unit; Python SDK; TypeScript SDK build/test/typecheck). App import path was verified to be that checkout. Existing dependency runtimes were symlinked; PYTHONPATH selected its backend. Source uses existing settings/ref columns, no migration required.
- Final focused event suite: eight passed (4.13 s), including revoked organisation policy and rejection of webhook account linking. The first full run was interrupted after this fixture correction; a fresh full run is in progress on the final source.

## Defects

- Initial tests assumed an old fixed channel-kind list and used an incorrect input-limit env name; updated tests for the actual contract.
- Added organisation-policy test initially overrode a different service instance from the callback's; corrected fixture to exercise that instance directly.

## Gaps Or Untested Areas

- No real bot/webhook cutover. No new remote APIs exercised. Optional PostgreSQL/Redis integration depends on CI services.

## Residual Risk

- Explicit wildcard permits every sender in the configured place to consume owner resources; UI and handbook explain this delegation. Operator must configure allowlists and bot privacy mode.
- Telegram/JSON event mode only; arbitrary source adapters and polling remain future work.

## Assumptions

- Owner review and merge approval remain pending. Managed outbound tools and expense example are subsequent tasks.

## Required Follow-Up

- Owner review on Draft PR #279 (stacked on #278); no merge approval inferred.

## QA Decision

Passed local QA; task stays in review pending owner approval. Do not mark done or merge without approval.

## Landing Approval

Owner approved implementation and merge of #279 on 2026-11-02. All screenshot evidence is intentionally removed at the owner's request; the historical validation results above remain recorded. Final rebased/squashed head must pass required integration checks before merging.
