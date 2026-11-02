# QA Report

- QA ID: QA-0212
- Project: superstep
- Task ID: TASK-0235
- Created/Updated: 2026-11-02
- Outcome: pass
- Related: REQ-0084, DES-0002, DEC-0082, PLAN-0004, REV-0212, TASK-0235

## Acceptance Coverage

- Create/edit/discover, multiple tools, GET scalar query coercion, JSON write body and empty 204 responses: passed. Configuration above the former 4 KiB ceiling works. Headers remain encrypted/write-only and retained on edit.
- Invalid base URLs, target/auth overrides, traversal/template paths, duplicate/oversized definitions, unsupported methods/statuses, remote schema references and unsafe/control headers: refused. Real bounded streaming helper pins IP/Host/SNI and stops at the byte bound.
- Credentials echoed in nested data/keys are redacted from results/operation history. Ordinary API data named `$ref` is preserved. Malformed/oversized/schema-invalid responses, lost response, HTTP 202/408/503: unknown, no repeat or secret leak.
- Confirmed replay, changed arguments/configuration conflicts, provider rejection, cross-owner denial, no-op dry runs and concurrent intent reservation: passed. Existing managed/MCP/layer/envelope regression passed.
- Browser: actual HTTP fixture call through MCP node returns confirmed 201 with redacted auth; discovery, editor use, reopen JSON configuration and blank saved secret fields passed in en/vi and light/dark. Legacy managed tests retain typed-name deletion.

## Checks And Evidence

- Combined focused backend: 67 passed (23.83 s). Final HTTP/MCP/layer/envelope: 50 passed (19.24 s), including 36 HTTP cases.
- Frontend build/lint, strict UI class check and 149 unit tests: passed. Existing warnings remain non-blocking.
- Browser HTTP plus managed regression: eight passed (1.1m). Final HTTP-only after field sizing/hint masking: four passed (28.4 s).
- Eight HTTP screenshots (`managed-http-{en,vi}-{light,dark}.png` and `managed-http-result-*`) plus twelve regression screenshots under `.factory-state/evidence/task-0235/`. Representative form images included in handbook.
- First browser attempt asserted redacted content while its JSON subtree was collapsed; expanded it. A locale edit during that attempt reloaded one legacy form; final stable-source rerun passed all eight. No application functional defect was involved.
- Final full Factory profile on isolated a267226: all eight passed (backend 484.39 s; frontend build 7.02 s/lint 0.94 s/unit 5.73 s; Python SDK 15.91 s; TypeScript SDK build 1.43 s/test 0.96 s/typecheck 1.37 s). Both final handbook builds/media and Factory validation/ID/diff checks passed. Source CI on #282 passed (6m39s). This follow-up changes verification records only.

## Gaps And Residual Risk

Only fake HTTP providers and synthetic authentication. No production calls/deployment. HTTP success is not a universal business-success/delivery guarantee; review response schema and remote idempotency semantics. Initial adapter has no read-only external lookup and never resends uncertain operations. Static paths/JSON only; documented limits: 20 tools, tool JSON 32 KiB, auth JSON 4 KiB, nesting 16, arguments 128 KiB, response 256 KiB, timeout 20 s. Integration CI matrices run after stack retargeting to develop.

## QA Decision

Passed local QA and source CI. Draft #282 remains in review; owner review/merge approval not inferred.

## Landing Approval

Owner approved implementation and merge of #282 on 2026-11-02. All screenshot evidence is intentionally removed at the owner's request; the historical validation results above remain recorded. Final rebased/squashed head must pass required integration checks before merging.
