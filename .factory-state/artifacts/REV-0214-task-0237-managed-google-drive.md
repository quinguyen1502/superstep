# Review

- Review ID: REV-0214
- Project: superstep
- Task ID: TASK-0237
- Created/Updated: 2026-11-02
- Reviewer: Codex self-review, advisory; owner approval pending
- Outcome: approved for QA
- Related: REQ-0085, DES-0003, DEC-0083, PLAN-0005, TASK-0237

## Review Scope And Findings

Own diff above TASK-0236/#283 at b3fe373: Drive adapter, shared Google auth/redaction, MCP configuration/UTF-8 bounds, schema-driven UI/locales, fake HTTP acceptance tests and bilingual guide. No blocking implementation findings.

Folder and direct-child/trashed/drive identity checks precede file content requests; IDs build fixed Google URLs. Search strings are escaped, shortcuts are not followed, pages and streaming responses are bounded. OAuth only refreshes the existing grant, service-account JWT has fixed scope/audience and no delegated subject. Supplied token URLs are ignored. My Drive creation via a service account refuses before upload; Shared Drive permission metadata is checked.

Creation uses a hashed operation marker and content hash, verifies scoped receipt/MD5/size, and recovers by bounded read-only lookup plus actual byte checks. Missing, duplicate, incomplete, paginated or modified matches cannot confirm or resend. Durable intent/replay and existing owner/org admission are reused. Secrets remain encrypted/write-only, fully masked, and redacted from results. Non-UTF-8 arguments now fail before fingerprinting and the existing 128 KiB JSON budget measures UTF-8 bytes.

Shared Google auth retains Sheets request injection and its own scope. Common result redaction retains HTTP Authorization token handling. No new dependencies, schema, canvas node, external-file delete or consent wizard.

## Standards And Design Alignment

Backend service boundaries, shared envelope/domain errors and repository operation storage retained. Existing shadcn controls, labels/focus, theme tokens, en/vi help and typed-name connection deletion retained. UI convention colour searches found no matches; frontend build/lint/149 tests passed. Screenshots cover both themes/locales. The fixture entry point requires an explicit flag and is absent from normal app routes; all credentials/data are synthetic.

## Validation Review And Follow-Up

Focused Drive/managed/HTTP/channel/MCP/layer/envelope regression: 120 passed (28.52 s), including 32 Drive cases. Combined browser Drive/HTTP/Telegram/Sheets: 12 passed (1.5m); final four Drive variants passed (40.7 s), including actual fake-provider lost-response UI recovery with no repeat upload. Both handbook builds/media and Factory validation/ID checks passed. Full Factory profile passed all eight checks on fe56192 (backend 466.85 s); #284 source CI passed (6m19s). No live Google access was tested or authorised. Owner review and merge approval remain separate.

## Assumptions And Residual Risk

Operators provision Google consent/refresh credentials and permissions. App-private marker visibility depends on the same app/account; external edits/moves and eventual indexing may leave recovery unknown. No external exactly-once guarantee is claimed. These limits match REQ-0085/DEC-0083 and the handbook. Default app MCP/session browser regression also passed four cases (25.2 s) with the opt-in Drive fixture disabled.

## Landing Approval

Owner approved implementation and merge of #284 on 2026-11-02. All screenshot evidence is intentionally removed at the owner's request; the historical validation results above remain recorded. Final rebased/squashed head must pass required integration checks before merging.
