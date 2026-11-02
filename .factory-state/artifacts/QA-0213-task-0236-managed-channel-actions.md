# QA Report

- QA ID: QA-0213
- Project: superstep
- Task ID: TASK-0236
- Created/Updated: 2026-11-02
- Outcome: pass
- Related: REQ-0084, DES-0002, DEC-0082, PLAN-0004, REV-0213, TASK-0236

## Acceptance Coverage

- Slack/WhatsApp/Email/Teams discovery and calls via existing MCP: passed. Selected channel secrets and fixed destinations reused; no duplicated credentials. Plain text/thread, WhatsApp text without approval template, SMTP headers/Message-ID and Teams card/202 acceptance verified.
- Owner isolation, wrong platform, indirect org policy and policy revocation: passed. Test fixtures restore changed org scopes. Deleted channels and non-string references refuse safely.
- Known result reuse and dry runs: no additional network/SMTP or intents. Timeout/HTTP 5xx/malformed success/partial SMTP stay unknown; manual check/replay never resends. Rejections and SMTP authentication failures are not success. No secret/error body in results.
- Email shares quota with actual RunService email callback; replay/mock does not charge, new sends over the budget fail before transport. Header injection is normalised; recipient validation and stable Message-ID use existing helpers.
- Browser create/discover/actual workflow run/history operation/delete: all four adapters across en/vi and light/dark. Exact typed-name deletion retained.

## Checks And Evidence

- Combined backend channel/approval/chat/managed/HTTP/email/layer/envelope: 135 passed (35.98 s). Final relevant regression: 66 passed (10.47 s), including 21 channel-action cases.
- Frontend build/lint, strict UI classes and 149 unit tests passed. Existing warnings remain non-blocking.
- Combined browser actions/HTTP/managed/stdio MCP: 13 passed (2.4m). Explicit `E2E_CHANNEL_SMTP=1` final browser four variants passed (1.4m), exercising 16 adapter workflows against local HTTP/SMTP.
- Sixteen new form screenshots `managed-{slack,whatsapp,email,teams}-{en,vi}-{light,dark}.png` in `.factory-state/evidence/task-0236/`, plus existing adapter regression images. Representative en/vi Slack images embedded in handbook.
- Default SMTP-off session/notification/channel regression: ten passed (1.5m). Both final handbook builds/media and Factory validation/IDs/diff passed.
- Full Factory profile on committed c3ff1f0: all eight passed (backend 450.07 s; frontend build 6.66 s/lint 0.90 s/unit 5.73 s; Python SDK 16.75 s; TypeScript SDK build 1.25 s/test 1.19 s/typecheck 1.18 s). Source CI on #283 passed (7m8s); parent #282 verification-only head 0f323e8 also passed CI (7m27s). This follow-up records verification only, without implementation changes.

## Gaps And Residual Risk

No live services, paid calls or production cutover. Provider acknowledgement confirms submission only; WhatsApp's customer-service window and Teams workflow/SMTP downstream delivery remain operator responsibilities. Unknown operations cannot automatically reconcile; inspect the provider before starting a new run. Source channels can be reused by authorised workflows, so restrict event admission and recipients deliberately. SMTP configuration is the existing administrator-controlled studio sender. Optional integration matrices run after stack retargeting to develop.

## QA Decision

Passed local QA and source CI. Draft #283 stays in review; owner review/merge approval not inferred.

## Landing Approval

Owner approved implementation and merge of #283 on 2026-11-02. All screenshot evidence is intentionally removed at the owner's request; the historical validation results above remain recorded. Final rebased/squashed head must pass required integration checks before merging.
