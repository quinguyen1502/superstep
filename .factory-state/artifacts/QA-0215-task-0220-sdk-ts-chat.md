# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0215
- Task ID: TASK-0220
- QA Owner: Codex, advisory; owner accepted 2026-11-02
- Created/Updated: 2026-11-02
- Outcome: pass; owner accepted 2026-11-02
- References: REQ-0082, PLAN-0002, DEC-0077–0080, REV-0215, TASK-0220 in done

## Acceptance Coverage

| Criterion | Result / evidence |
| --- | --- |
| Same recorded v1 contract across Node, jsdom and no-DOM native-like | Passed: 19 shared cases per environment in `sdk/typescript/test/chat-contract.ts`; frames captured from an actual offline backend and validated again with its published schema. |
| Server helper tokens verify in backend | Passed: `sdk/fixtures/chat-token-vectors.json`, Web Crypto/Node fallback unit tests, real Hs256ChatTokenVerifier tests and live app-key sessions. ASCII/Unicode secrets and claims, TTL/meta bounds and secret-safe errors covered. |
| Session/info/history, send/answer, attachments and ratings | Passed: typed client contract and live integration, including Human text/form answers, Buffer upload/download/unsent deletion and ratings. Native URI is forwarded through injected native FormData without URI reads; browser Blob/File use multipart boundaries from the runtime. |
| Refresh/recovery/cancel | Passed: HTTP/socket expiry once; no revoked/origin or post-start retry; unknown/duplicate frames; dropped socket read-only recovery; missing run acknowledgement stays interrupted; timeout/abort/break/dispose cleanup and bounded event queue. |
| Framework-neutral store | Passed: stable snapshots, history merge, listeners, loading/error/waiting state, single active send, cancel/dispose and stale load/implicit-start races. |
| Zero runtime dependencies, generated types, 0.2.0/package docs | Passed: lock/package inspection, `gen:check`, typecheck, ESM/CJS build/import smoke, `npm pack --dry-run` (82 files, 48283 compressed bytes at initial build; no tests/fixtures/node_modules). No package published. |

## Checks Performed

- `cd sdk/typescript && npm test`: 91 passed; `npm run typecheck`, `npm run gen:check`, `npm run build`, `npm run test:package` passed. Native tests remove DOM, Blob/File/FormData and Buffer globals and inject compatible host transports.
- From backend: `.venv/bin/python -m pytest -q tests/test_chat_sdk_tokens.py tests/test_hitl.py tests/test_inbox.py tests/test_agent_server_api.py tests/test_chat_ws_v1.py tests/test_layers.py tests/test_api_envelope.py`: 40 passed (12.91 s) after restricting form support to v1.
- `scripts/sdk_integration.sh`: Python 2 passed and TypeScript 7 passed against a temporary SQLite backend using mock models, ephemeral app keys and two isolated users. Credentials are removed with the temporary directory.
- Public OpenAPI `--check` passed; Factory IDs allocated after fetch and all-ref scans; whitespace check passed.
- First full Factory run: 7/8 checks passed; backend 1200 passed, 18 skipped, one legacy LangGraph rejection assertion failed. Corrected the scope of form validation, preserving the original assertion, and verified it in the 40-case targeted regression.
- Final full Factory rerun on corrected commit 9aeeba8: all eight passed. Backend 471.48 s; frontend build/lint/test 6.38/0.88/5.28 s; Python SDK 13.44 s; TypeScript build/test/typecheck 1.25/1.10/1.38 s. `.factory-state/verification/latest.yaml` records the final passing outcomes. The earlier failed run is retained here as a resolved regression, not a passing delivery claim.

## Gaps, Risks And Assumptions

No real device/emulator, deployed host, actual provider calls or UI visual changes were tested. Native UI and cross-origin host e2e belong to subsequent tasks. Node runtimes lacking WebSocket need a host adapter. A lost run ID cannot be safely recovered as confirmed; callers reload history before deciding on another send. Cancel/disconnect can race server completion. The README describes these limits and host-controlled identity storage.

`npm audit` reports existing dev-tool findings in Vitest/tinypool/Vite/esbuild/Redocly/minimatch (9 total, including transitive reports); none are introduced by jsdom and no runtime package is shipped. Upgrading that toolchain is separate from chat delivery. Existing backend migration/test JWT and frontend warnings remain non-blocking.

## Decision And Follow-Up

Local QA passed; source CI status is recorded by the Draft PR's checks. Task remains in review for human acceptance; approval is required for merge or package publication. Later PLAN-0002 tasks stay in backlog. No screenshot evidence is tracked, per owner preference.

## Owner Approval And Finalisation

Owner approved the reviewed phase-2 stack on 2026-11-02 ("Duyệt"). The task moves to done in the existing #285, to be squashed and marked Ready after final gates. This does not authorise merging or package publication. The browser fetch binding correction discovered and reviewed in TASK-0222 is included here with its existing default/explicit-fetch regression: 20 shared contract cases, 94 total SDK unit tests. No new behaviour is added beyond the reviewed final stack. Earlier pending-acceptance entries above are historical. Final-head CI remains the delivery gate.

Finalisation rerun: 94 TypeScript unit tests passed, typecheck, generated-contract check, ESM/CJS build and all root/chat/server package-export smoke checks passed. Backend/frontend source is unchanged from the passing full profile; each rewritten PR must pass its exact-head CI before delivery.
