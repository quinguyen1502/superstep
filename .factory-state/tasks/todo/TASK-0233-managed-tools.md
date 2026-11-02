# Task

## Metadata

- Project: superstep
- Task ID: TASK-0233
- Status: todo
- Owner: Thái Quí Nguyễn
- Created: 2026-11-01
- Updated: 2026-11-01
- Requirement IDs: REQ-0083
- Design IDs: DES-0001
- Architecture IDs: DEC-0081

## Objective

Expose managed service actions through the existing MCP tool contract, with Telegram and Google Sheets adapters and explicit write outcomes.

## Scope

### In Scope

- Small service-side adapter registry with schema discovery/call; existing MCP nodes and Agent slots consume the same tool contract, with no vendor-specific graph types.
- Telegram actions reference existing channel secrets; Google Sheets service-account auth uses encrypted connection secrets and existing cryptography/PyJWT/httpx dependencies.
- Managed connection configuration UI, argument validation and scope enforcement.
- Stable operation ids, confirmed/failed/unknown outcomes and reconciliation for Sheets; no blind retry of uncertain non-idempotent effects. Reuse existing effect ledger/queue where applicable.
- Migrations, translated errors/docs and tests.

### Out Of Scope

- General OAuth marketplace, arbitrary plugins, a full Sheets UI, automatic live credential setup or real external writes.

## Inputs

- REQ-0083, DEC-0081 and existing MCP/Channel services.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0083-event-connections-model-policy.md`
- Design: `.factory-state/artifacts/DES-0001-event-connections-model-policy.md`
- Architecture: `.factory-state/decisions/DEC-0081-event-connections-model-policy.md`
- Plan: `.factory-state/artifacts/PLAN-0003-event-connections-model-policy.md`
- Standards: `AGENTS.md`, `docs/backend-architecture.md`, `docs/ui-conventions.md`

## Expected Outputs

- Managed connection adapters/API/UI, durable outcome semantics and one tested Draft PR with review/QA.

## Constraints

- No new dependency anticipated. All vendor network/auth logic stays outside the graph compiler. Encrypted owner-bound credentials; tests mock outbound APIs. Never claim external exactly-once behavior without endpoint support.

## Dependencies

- Planning baseline TASK-0231 and any event context used from TASK-0232; explicitly stack if those PRs are not merged, per PLAN-0003.

## Acceptance Criteria

- Existing MCP and Agent tool selection discover and call managed adapters with validated arguments and owner/org access checks; secrets never enter workflow JSON or tool metadata.
- Telegram actions use the selected existing channel; Sheets writes map values and return row/result metadata through the generic tool interface.
- Known completed operations are reused; uncertain writes are reconciled or blocked from blind repetition, including timeout/crash tests. Test-mode behavior cannot send real messages or append rows.
- Existing MCP HTTP/stdio behavior remains compatible. Delete uses typed-name confirmation; en/vi UI/docs and screenshots included.

## Validation Plan

- Focused adapter/auth/permission/outcome/Agent/MCP tests, migration/layer/envelope tests, frontend checks and browser regression.
- Full Factory verification, validation, IDs and diff check.

## Assumptions

- Service-account auth for a shared sheet is the initial Google connection; provider-specific end-user OAuth remains a future adapter.

## Open Questions

- None blocking local implementation; live setup waits for review.

## Activity Log

- 2026-11-01: Planned under owner-authorised REQ-0083.

## Handoff Notes

- Branch `factory/task-0233-managed-tools`; record actual base/stack before implementation.
