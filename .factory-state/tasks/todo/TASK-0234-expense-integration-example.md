# Task

## Metadata

- Project: superstep
- Task ID: TASK-0234
- Status: todo
- Owner: Thái Quí Nguyễn
- Created: 2026-11-01
- Updated: 2026-11-01
- Requirement IDs: REQ-0083
- Design IDs: DES-0001
- Architecture IDs: DEC-0081

## Objective

Prove generic events/tools/model policy with the owner's expense flow, and document complete Superstep setup without n8n.

## Scope

### In Scope

- Portable expense workflow/template using existing LLM/Code/Condition/MCP nodes, separate expense/submission dates, amount validation and explicit reply-after-confirmed-write.
- Mocked end-to-end Telegram/event -> model -> Sheets -> reply coverage, duplicate delivery and ambiguous write checks, model fallback and failure paths.
- Bilingual setup/operation guide, example configuration with placeholders, screenshots and CHANGELOG.

### Out Of Scope

- Real credential provisioning, production webhook cutover, live expenses, n8n import, expense approval process or app/package releases.

## Inputs

- Owner's n8n expense JSON (use sanitised example data only), REQ-0083 and the implemented PLAN-0003 features.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0083-event-connections-model-policy.md`
- Design: `.factory-state/artifacts/DES-0001-event-connections-model-policy.md`
- Architecture: `.factory-state/decisions/DEC-0081-event-connections-model-policy.md`
- Plan: `.factory-state/artifacts/PLAN-0003-event-connections-model-policy.md`
- Standards: `AGENTS.md`, `docs/ui-conventions.md`

## Expected Outputs

- Working generic integration example, browser/E2E evidence, docs and review/QA in its Draft PR.

## Constraints

- No actual bot ids, sheet ids, user ids or credentials in fixtures/templates. Model output cannot authorise tool targets or choose secrets. Google sheet stores plain untrusted text safely.

## Dependencies

- TASK-0231, TASK-0232, TASK-0233. Explicitly record stacked delivery if not merged.

## Acceptance Criteria

- Valid expense writes one record then confirms; missing/invalid amount or unrelated text does not write.
- Both model failure and malformed JSON are visible; fallback works; Sheets errors/unknown outcomes never produce a false success reply.
- Duplicate event/worker replay does not blindly produce duplicate expenses. Setup guide explains admission, credential scope, date rules and safe production cutover.
- Both handbook language builds and complete declared checks pass.

## Validation Plan

- Focused backend integration tests and browser workflow checks with screenshots, all outbound providers mocked.
- Handbook en/vi builds and media checks; full Factory verification, validation, IDs and diff check.

## Assumptions

- The initial status remains "Chờ duyệt"; actual approval is future scope. Full REQ-0083 closes only after all feature PRs are approved and merged.

## Open Questions

- No blocking local questions; actual production connection and cutover remain owner decisions.

## Activity Log

- 2026-11-01: Planned under owner-authorised REQ-0083.

## Handoff Notes

- Branch `factory/task-0234-expense-integration-example`; record actual base/stack before implementation.
