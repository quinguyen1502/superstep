# Plan

- Plan ID: PLAN-0009
- Project: superstep
- Status: owner-authorised implementation (REQ-0089, "Do it" 2026-11-07)
- Created/Updated: 2026-11-07
- Related: REQ-0089, DEC-0088, REQ-0088 / PLAN-0008

| Task | Purpose | Size |
| --- | --- | --- |
| TASK-0267 | HTTP Tool: connect to the checked address (DNS-rebinding), SNI/cert on the name; Python + Deno executed tests | M |
| TASK-0268 | LLM fallback for messages with attachments, Studio semantics; executed tests | S |
| TASK-0269 | MCP export adapter (env-configured), executed against a local MCP server | M |
| TASK-0270 | Retriever export adapter (env-configured), executed against a local server | M |
| TASK-0271 | Send email export adapter (env-configured SMTP), executed against a local SMTP server | M |
| TASK-0272 | Factory metadata cleanup: real TASK-0253 review, distinct REV/QA ids, status reconciliation, validate | S |

Order: 0267+0268 (one PR), adapters (scoped PRs), then 0272. Each merged only with all required CI green. No edits to browser export paths (TASK-0261/0262).

TASK-0267 through TASK-0271 are merged. TASK-0271 merged in PR #333 (`bbbd23b2`). TASK-0272 is done (REV-0258, QA-0258) and is not merged. REQ-0089 is not marked done.
