# Requirement

## Metadata

- Project: superstep
- Requirement ID: REQ-0083
- Status: Implemented — owner accepted implementation and approved merge on 2026-11-02
- Owner: Thái Quí Nguyễn
- Created: 2026-11-01
- Updated: 2026-11-01
- Source: owner's n8n expense workflow and request for reusable integrations without one canvas node type per third-party service.

## Summary

Run the owner's Telegram-to-Sheets expense flow entirely through Superstep using generic event inputs, existing tool/MCP nodes and a reusable model fallback policy. Service-specific behavior belongs in connection adapters, not in graph node types.

## Problem Or Opportunity

Command chat triggers discard useful event metadata, managed Google/Telegram actions are absent, and a failed LLM call cannot select another configured model. The existing LLM/Code/Condition/MCP/Agent primitives cover the workflow's graph logic.

## Scope

### In Scope

- Bounded, authenticated event bindings with filtering, state mapping, platform metadata and durable duplicate suppression; Telegram text messages and signed generic JSON webhooks are the first event sources. Existing command/verified-account chat behavior remains compatible.
- Managed connections exposed through existing MCP tool discovery/call and Agent tool selection. Initial adapters: Telegram actions using an existing channel connection, and Google Sheets using a service account; encrypted secrets and schema-driven arguments.
- Explicit LLM model fallback configuration, credential access enforcement, bounded failover, safe streaming and visible attempt metadata.
- Reliable write outcomes: do not blindly retry a non-idempotent external write after an uncertain outcome. Sheets writes must have a reconciliation strategy and a stable operation key. No false exactly-once promise.
- Rebuild the expense example as a portable workflow template and document setup, dates, user policy and cutover; test the complete flow with local fake providers and provide an opt-in live setup guide.

### Out Of Scope

- A general n8n importer, new canvas node types for Telegram/Sheets, arbitrary user plugins executed in-process, a marketplace, all-provider OAuth implementation, changes to SDK roadmap phases, production webhook cutover, real financial writes or deployment without separate owner authorisation.
- Real approval of expenses; the initial example preserves the existing "Chờ duyệt" sheet status.

## Stakeholders Or Users

- Workflow builders connect services and map input/output without learning a new graph node for each vendor.
- Operators manage connection secrets and event admission; message senders submit an expense through an allowed Telegram group.

## Current Context

- `services/chat_run_service.py` accepts command text only; Telegram adapter has chat/message references but no full event state input.
- `services/mcp_service.py`, `engine/ports.py` and existing MCP/Agent settings already discover typed tools and call owner-bound services.
- `engine/llm.py` dispatches one model; retry repeats it. Code nodes can parse/validate expense JSON.
- Existing effect ledger prevents replay after a recorded result but cannot alone resolve an external success followed by a network timeout/crash.

## Desired Behavior

An owner connects Telegram and a spreadsheet, binds messages from an allowed place to workflow input, selects primary/fallback model credentials and uses generic tools to reply and write a validated expense. Another service can use the same event envelope and tool interface without changing the graph compiler.

## Business Rules

- Existing trigger/account permissions and owner-bound credential resolution remain defaults. Any run-as-owner event admission is explicit, scoped to a configured source/place/sender policy and audited.
- Never expose signing keys, bot tokens or service-account keys in workflow JSON, templates, logs or exports.
- Failover is disabled unless configured; do not blend a failed provider's partial output into the fallback's answer.
- A reply claiming success follows a confirmed write. Uncertain non-idempotent effects require reconciliation instead of an automatic second write.
- Expense input is untrusted; date of submission and expense date are distinct, timezone defaults to Asia/Ho_Chi_Minh in the example.

## Constraints

- AGENTS.md, DEC-0008/0009/0010, typed-name delete confirmation, en/vi parity, migrations for schema changes, no vendored framework changes.
- Prefer existing dependencies (httpx, PyJWT, cryptography, jsonschema) and existing queue/repository/MCP ports. No speculative platform abstractions.

## Acceptance Criteria

- A configured failed primary model selects the fallback, with no secret/partial-output leak, bounded attempts and tests for permission, cancellation and non-retryable errors.
- Telegram and a generic signed event can populate typed workflow state; wrong source/sender/signature and duplicate delivery do not start extra runs.
- Managed Telegram/Sheets tools are discoverable/callable by existing MCP nodes and Agent tool slots; no additional canvas node types.
- Ambiguous write outcomes do not blindly append/send again; known completed results can be reused.
- Expense examples cover valid/invalid amount, unrelated text, malformed model JSON, model failover, sheet failure, duplicate delivery and reply-after-confirmed-write.
- Backend layer/envelope checks, UI checks, full Factory verification, screenshots where UI changes, bilingual docs and review/QA artifacts.

## Edge Cases

- Two deliveries race; a worker restarts; a model streams text and then fails; a credential is deleted or belongs to another owner; a sheet write succeeds but the response is lost; a sender edits a message; malformed or oversized event data.

## Assumptions

- Implementation defaults and task decomposition are covered by the owner's request; merges still require explicit approval. Live credentials will be entered in Settings during deployment, not requested in chat.
- The Google adapter starts with service-account auth for a specifically shared sheet; end-user OAuth can be a later connection adapter.

## Open Questions

- No blocking questions for local implementation. Real bot/sheet/credential selection and production cutover occur after review.

## Related Artifacts

- `.factory-state/artifacts/PLAN-0003-event-connections-model-policy.md`
- `.factory-state/artifacts/DES-0001-event-connections-model-policy.md`
- `.factory-state/decisions/DEC-0081-event-connections-model-policy.md`
- Existing REQ-0044/DEC-0046 chat triggers, DEC-0018 effect ledger, DEC-0032 providers and REQ-0082 SDK plan (independent).

## Delivery Approval

Owner explicitly approved the implementation and merging the delivery PRs into develop on 2026-11-02. Related tasks: TASK-0231, TASK-0232, TASK-0233, TASK-0234. Review/QA results are recorded in those tasks. Final rebased one-commit PR checks must pass before the merge. Evidence screenshots are intentionally removed at the owner's request; handbook illustrations and textual verification records remain.
