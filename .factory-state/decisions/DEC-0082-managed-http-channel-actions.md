# Decision

- Decision ID: DEC-0082
- Project: superstep
- Created/Updated: 2026-11-02
- Status: implementation decision within owner-authorised REQ-0084; advisory review on task PRs
- Related: REQ-0084, DES-0002, PLAN-0004, DEC-0081

Keep the managed adapter boundary and durable operation repository. HTTP exposes a bounded list of static operation definitions, not a runtime URL-fetch tool. Definitions and auth remain on the owner-controlled connection; JSON tool arguments become GET query parameters or JSON write bodies. Only local, bounded schemas are allowed. Optional response schemas can reject HTTP-200 business failures. HTTP 202/transport failure/oversized or invalid responses leave unknown; no generic lookup contract is invented. The stable Idempotency-Key header does not promise remote deduplication.

Extend the shared pinned HTTP helper with an opt-in response byte limit for generic calls. Do not change existing callers' behavior. Return status and bounded redacted data, never headers, request URLs or raw error text. Existing encrypted secrets and configuration fingerprints remain authoritative; no schema migration/dependency is needed.

Channel actions share one channel lookup/authorisation helper with Telegram, preserving run-time org restrictions. Vendor-specific payload code stays inside adapters; SMTP uses the existing core mail transport with its outbound guard. Teams uses its existing encrypted Workflows webhook; Slack/WhatsApp use existing API configuration and channel secrets. A provider acknowledgement confirms acceptance only. Unknown sends cannot be reconciled automatically and never resend.

Tradeoff: static paths and JSON-only tools avoid adding a general integration language. Extra capabilities can later extend the adapter contract based on concrete API needs. Reusing channel secrets avoids a second credential source and keeps existing access controls.
