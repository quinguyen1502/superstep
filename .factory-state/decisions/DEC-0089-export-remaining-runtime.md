# Decision Record

## Metadata

- Project: superstep
- Decision ID: DEC-0089
- Status: accepted
- Owner: Thái Quí Nguyễn
- Created: 2026-11-07
- Updated: 2026-11-07
- Related Requirements: REQ-0090
- Related Architecture:
- Related Tasks: TASK-0273, TASK-0274, TASK-0275

## Context

TASK-0266 left four export gaps. The owner declined cross-language code nodes and asked for the other three. Existing fallback tests call `call_llm` with today's provider argument. `managed_operation(tool, arguments)` must keep raising the placeholder. Sanitize blanks credential, channel and server ids before the file is written.

## Decision

1. A raw credential id becomes a stable `LLM_CRED_<n>` slot in first-use order, shared by nodes with the same id. The id is never written. When `<SLOT>_PROVIDER` is set, the call uses that provider, `<SLOT>_API_KEY` and optional `<SLOT>_BASE_URL`. When it is unset, the call keeps `LLM_PROVIDER` / `LLM_FALLBACK_PROVIDER`.
2. Approval helpers are emitted only when a Human or Agent node has a channel, a parsed deadline or a parsed AI-review policy. The decision stays local. A channel is a notice: `APPROVAL_<KIND>_WEBHOOK_URL`, or Telegram `APPROVAL_TELEGRAM_BOT_TOKEN` and `APPROVAL_TELEGRAM_CHAT_ID`. Deadlines keep `after`, `remind_every` and `on_timeout` in seconds and drop addresses. The judge credential becomes a slot. Suggest never answers. Auto approves only on approve plus confidence. Reject rules may reject. The daily cap is a local JSON file; if it cannot be written, the run does not auto-approve. Example answers return before any notice.
3. `check_export` stores the adapter id on `_managed_export`. An invalid browser connection stays `True` and keeps the placeholder. A real call passes `MANAGED_<n>` and the adapter name. Settings and secrets come from environment JSON. Targets are pinned, redirects are not followed, and `STUDIO_MCP_ALLOW_PRIVATE` is the private-address flag. The Google token URL is not overridable. A local journal returns a stored result, conflicts on different arguments, and does not retry an unknown outcome.
4. Cross-language code nodes are not implemented.

## Rationale

The slot fallback keeps every current live export working when the operator only sets `LLM_PROVIDER`. The placeholder signature keeps broken browser exports and the existing two-argument call failing closed. Environment JSON matches the MCP and SMTP adapters: the file names the slot, never the secret.

## Alternatives Considered

- Option: Require a slot environment whenever Studio had a credential.
  - Benefits: A node cannot silently share `LLM_PROVIDER`.
  - Tradeoffs: Breaks fallback tests and every export that only sets `LLM_PROVIDER`.
  - Reason Not Chosen: The owner already ships those exports. Separation happens when the slot is set.
- Option: Embed channel targets and managed settings in the file.
  - Benefits: The file runs with no extra environment.
  - Tradeoffs: Secrets leave Studio.
  - Reason Not Chosen: Sanitize already removes them, and REQ-0090 forbids writing them.
- Option: Three branches, one per behaviour.
  - Benefits: Smaller reviews.
  - Tradeoffs: The exporters are one pair of files. The branches would conflict.
  - Reason Not Chosen: One branch lands TASK-0273, TASK-0274 and TASK-0275 together.

## Impacts

- Python and TypeScript exporters, `export_common.Graph`, `mcp_service.check_export`, the project README, and the handbook in both languages.
- Fallback tests accept a `slot` parameter. Their printed provider is unchanged when the slot environment is unset.

## Risks

- A large generated helper can drift from Studio. Tests execute the telegram, approval and slot paths against local fakes.
- An approval notice to an operator webhook is not pinned. That matches operator-supplied MCP URLs. Managed tool targets stay pinned.

## Approval

- Approved By: Thái Quí Nguyễn
- Approved On: 2026-11-07
- Scope And Limits: The three behaviours above. Cross-language code is out of scope. Do not mark REQ-0086 or REQ-0089 done.

## Review Or Revisit Trigger

- Revisit if an export must refuse to run until every Studio credential has its own slot environment.
