# Decision Record

## Metadata

- Project: superstep
- Decision ID: DEC-0081
- Status: Implementation design under owner-authorised REQ-0083; detailed decisions reviewed on the task PRs.
- Owner: Thái Quí Nguyễn
- Created: 2026-11-01
- Updated: 2026-11-01
- Related Requirements: REQ-0083
- Related Architecture: DEC-0009, DEC-0018, DEC-0032, DEC-0046

## Context

The owner wants the n8n expense flow entirely in Superstep, while explicitly rejecting one canvas node type per integration. Existing MCP discovery, user-bound ports, encrypted connection stores and event job queue should be reused.

## Decision

1. Keep vendor logic in service-side adapters. Managed adapters expose the existing MCP tool definition/call contract; graph nodes and Agent tool slots use the same `server_id`, `tool`, `arguments` interface as remote MCP servers.
2. Event binding owns admission, filters, state mapping and duplicate delivery handling; it starts the existing run queue. Event identity/metadata is data, never a credential or implicit permission. Keep old command trigger semantics compatible.
3. Initial event adapters are Telegram text and signed JSON webhooks. Normalised events contain id/source/type/time/actor/conversation/data; only explicitly mapped bounded values reach declared state fields.
4. Initial managed action adapters use existing Telegram channel secrets and Google service-account credentials. OAuth provider adapters can follow; do not implement a general OAuth product for this one workflow.
5. LLM nodes gain an opt-in fallback credential/model policy. A shared engine helper owns attempt ordering; services resolve permissions; the UI presents the same policy in the existing node config. At most one fallback per node initially. Provider/network errors can switch before output is exposed; cancellation and credential access errors must not trigger silent failover.
6. Effect results distinguish confirmed success, confirmed failure and unknown external outcome. A non-idempotent write with unknown outcome must not auto-repeat; reconcile using a stable operation id where supported. Existing result ledger alone is not an exactly-once guarantee.
7. Preserve portable exports: support the new policy where possible; otherwise fail explicitly for a configured unsupported feature instead of silently dropping it.

## Rationale

This extends existing seams without introducing a vendor-specific node taxonomy or a second graph runtime. A small adapter registry is sufficient; no plugin execution framework is needed.

## Alternatives Considered

- Separate Telegram and Sheets node types: rejected by owner.
- A raw HTTP URL for every action with secrets embedded in workflow data: lacks safe credential lifecycle and schema/outcome semantics.
- All integrations through an external automation orchestrator: does not meet the owner's complete migration goal.

## Impacts

New event/managed-connection configuration and migrations where required; focused generic UI extensions, model attempt traces and bilingual docs. Existing workflows remain valid without new settings.

## Risks

Provider-specific OAuth, payloads and idempotency still require adapter code. Non-idempotent APIs cannot be made exactly-once merely by sending an idempotency header. Live integration permissions and bot cutover remain operator actions.

## Approval

- Approved By: owner authorised the generic three-feature outcome in chat on 2026-11-01.
- Scope And Limits: local implementation, tests and Draft PR delivery. Detailed design remains reviewable on PRs; no merge, production cutover, deployment or release approval is inferred.

## Review Or Revisit Trigger

Second managed provider with different auth requirements, an event source needing polling, or a need for multiple fallback models.

## Owner Amendment — Export Presentation (2026-11-04, TASK-0254)

The owner explicitly requested a commented empty managed step with the remaining workflow code visible instead of refusing the entire export. Managed MCP node/Agent-tool references now generate explicit Python/TypeScript TODO placeholders, including nested graphs and project ZIPs. They raise/throw if invoked until the operator implements the integration, operation tracking, idempotency and reconciliation. Connection settings, credentials and secrets remain excluded; managed runtime execution policy is unchanged. The code response/UI identifies incomplete managed steps. This amendment authorises source preparation for preview only; testing, merge and publication remain subject to the current owner's staged approvals. Prior approval/status sections are preserved.
