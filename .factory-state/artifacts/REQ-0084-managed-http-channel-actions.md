# Requirement

## Metadata

- Project: superstep
- Requirement ID: REQ-0084
- Status: Accepted — owner requested implementation and selected HTTP API plus services in approval channels
- Owner: Thái Quí Nguyễn
- Created: 2026-11-02
- Updated: 2026-11-02
- Source: Owner chat, 2026-11-02

## Summary

Extend managed tools with configurable HTTP API operations and actions for existing approval-channel services. Keep the current MCP node/Agent interface and encrypted connection registry.

## Scope

- Generic HTTP adapter: fixed base URL and reviewed tool definitions (name, method, relative path, input schema, optional response schema/success statuses), encrypted authentication headers, JSON requests/responses and bounded output.
- Existing channel services: add Slack, WhatsApp, Email and Microsoft Teams sending actions; Telegram already exists. Reuse channel credentials and owner/org policy. JSON webhook remains inbound-only.
- Conservative durable outcomes, offline dry runs, en/vi settings/docs, browser evidence and regression coverage.
- No new canvas node, OAuth platform, binary upload, arbitrary runtime-selected URL/headers, live messaging, deployment or automatic merge.

## Business Rules

- Only configured endpoints and tools are callable. Runtime arguments cannot replace targets/authentication. Shared SSRF pinning and redirect refusal apply.
- Tool/schema/argument/response sizes are bounded; no remote JSON Schema references. HTTP 202 is an incomplete outcome, not completed work. APIs with business errors in HTTP 200 require a reviewed response schema.
- Sending or uncertain HTTP outcomes never cause a blind second write. Initial generic/channel adapters cannot automatically reconcile external outcomes; preserve unknown for operator inspection. HTTP Idempotency-Key is advisory unless the remote API promises support.
- Channel targets are fixed and authorised at save and execution; org-channel restrictions cannot be bypassed via personal MCP connections.
- WhatsApp plain text requires the recipient's service window; do not reuse approval templates as ordinary messages. SMTP/Teams acknowledgement means submission acceptance, not end-recipient delivery.
- Secrets never appear in connection metadata, errors or managed results; generic responses redact configured credential values.

## Acceptance Criteria

- HTTP tools discover/call through existing MCP nodes/Agent slots, obey configured input/response schemas, fixed methods/targets and encrypted headers.
- Confirmed results replay without requests; concurrent/unknown/failed operations do not duplicate writes; mock/test runs perform no calls.
- Slack/WhatsApp/Email/Teams actions use the selected existing channel and fixed destination; correct payload/auth/permissions and conservative uncertainty are covered with fake providers.
- Existing Telegram/Sheets and legacy MCP/channel flows remain compatible.
- Settings are labelled/translatable, JSON configuration is usable in existing form, both themes/locales have screenshots. Full project checks, layers/envelope, bilingual handbook and review/QA pass.

## Assumptions And Open Questions

- Owner explicitly chose services by the approval-channel registry; no additional provider list needed. No real credentials requested.
- Binary/file APIs, dynamic path variables, form encoding and general OAuth are future scope; JSON HTTP operations cover the initial generic API contract.

## Related Artifacts

- `.factory-state/artifacts/DES-0002-managed-http-channel-actions.md`
- `.factory-state/decisions/DEC-0082-managed-http-channel-actions.md`
- `.factory-state/artifacts/PLAN-0004-managed-http-channel-actions.md`
- Existing REQ-0083, DEC-0081, `docs/backend-architecture.md`, `docs/ui-conventions.md`.
