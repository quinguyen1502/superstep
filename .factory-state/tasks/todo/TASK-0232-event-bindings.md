# Task

## Metadata

- Project: superstep
- Task ID: TASK-0232
- Status: todo
- Owner: Thái Quí Nguyễn
- Created: 2026-11-01
- Updated: 2026-11-01
- Requirement IDs: REQ-0083
- Design IDs: DES-0001
- Architecture IDs: DEC-0081

## Objective

Bind authenticated external events to workflow state through a shared event envelope, starting with Telegram text and signed JSON webhooks.

## Scope

### In Scope

- Event source/binding configuration, explicit admission, filters, field mapping, metadata and duplicate suppression.
- Reuse channel verification/normalisation and the existing queue; preserve command trigger semantics. No extra canvas node type.
- UI, en/vi, migrations, error codes, documentation and security/concurrency tests.

### Out Of Scope

- Managed outbound tools, new provider-specific graph nodes, production webhook registration/cutover, arbitrary event scripts.

## Inputs

- REQ-0083; owner's Telegram expense workflow as acceptance fixture (no real credentials in fixtures).

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0083-event-connections-model-policy.md`
- Design: `.factory-state/artifacts/DES-0001-event-connections-model-policy.md`
- Architecture: `.factory-state/decisions/DEC-0081-event-connections-model-policy.md`
- Plan: `.factory-state/artifacts/PLAN-0003-event-connections-model-policy.md`
- Standards: `AGENTS.md`, `docs/backend-architecture.md`, `docs/ui-conventions.md`

## Expected Outputs

- Event binding API/UI, shared normalisation/mapping, migrations/tests, review/QA and one Draft PR.

## Constraints

- Owner-bound execution with explicit source/place/sender admission; preserve existing linked-user command behavior. Secrets encrypted, no credentials in workflow input. Bounded payload and typed mapping. No merge without owner approval.

## Dependencies

- Planning baseline carried by TASK-0231; independent model logic. If unmerged, explicitly stack the branch/PR as permitted by PLAN-0003.

## Acceptance Criteria

- Plain Telegram text from the configured group/sender can start a run with text, actor, message id and timestamp mapped to declared state fields.
- Invalid signatures, wrong place/sender/type, oversized payloads and disabled bindings do not start runs; duplicate concurrent deliveries start at most one run per binding.
- Signed generic JSON events use the same envelope/mapping/queue path. Legacy chat tests pass unchanged.
- Owner can create/edit/toggle/delete a binding with translated validation and typed-name deletion confirmation; UI evidence covers changed forms.

## Validation Plan

- Backend binding, channel callback, deduplication/concurrency, migration, layer and envelope tests; UI build/lint/tests and browser checks.
- Full Factory verification, Factory validation, artifact IDs and diff check.

## Assumptions

- Production setup and credential entry remain operator actions after review. No live messages are sent during implementation.

## Open Questions

- None blocking local implementation.

## Activity Log

- 2026-11-01: Planned under owner-authorised REQ-0083.

## Handoff Notes

- Branch `factory/task-0232-event-bindings`; record its actual base and PR stacking explicitly before implementation.
