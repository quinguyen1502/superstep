# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0234
- Task ID: TASK-0244
- QA Owner: Codex (advisory; owner approval pending)
- Created: 2026-11-05
- Updated: 2026-11-05
- Outcome: pass within controlled remote/profile scope; full regression to be recorded against commit

## Acceptance Criteria Coverage

- Remote fixture uses same six-action/result contract, with no credential disclosure: pass. Production pinned HTTPS client authenticates to real controller; controller starts the same network=none local worker. All operations, approved click/fill, protected PNG, context validation and no retry semantics verified. Capability mismatch refuses before open. Token/endpoint/proxy/profile hints are fully masked/encrypted. No raw CDP capability inferred.
- Profiles cannot cross authorised principals/origins or share sessions: pass for trusted provisioning and worker boundaries. Personal profile preparation requires user:<owner>, current connection/configuration digest and matching seed. Other user, visitor, app or org scope denied. Both create/update refuse org profiles. Actual Chromium loads a secure exact-host cookie/localStorage only at the declared HTTPS origin; other origin/subdomain/port is denied; fresh anonymous context has neither login. Broad/expired/duplicate/unsupported/oversized state refuses. Known provisioned text is redacted and captures remain private.
- Unsupported enforcement/storage/proxy/stealth is explicit: pass. Controlled deployment and independent endpoint/address approval required. TLS verification remains on; redirects/environment proxies/raw CDP/WSS/query tokens/stealth/unsupported storage refuse. Direct/custom/operator-default actual routes passed; deliberate upstream failure never reached the destination directly.
- Configuration immutability/revocation: pass for worker binding and service validation. Current digest includes encrypted state; metadata/secret removal makes old contexts fail preparation. Sessions never mutate profile/proxy in flight. Live-run invalidation/revalidation hooks and persistent cleanup are TASK-0245 integration requirements, not yet product-enabled behavior.

## Checks Performed

- `backend/.venv/bin/python scripts/test-browser-remote.py --docker /Applications/Docker.app/Contents/Resources/bin/docker`: passed real HTTPS/Chromium six-operation/profile/proxy/restart cases. Test-only CA is installed in a child image, never a production TLS-disable flag. Same physical host fixture, not third-party provider evidence.
- Backend browser + shared managed/MCP suite: 206 passed (33.80 s). Final focused schema/strictness checks: 71 passed; after org-update guard: 36 passed. Existing warnings only.
- Root declared npm test: 280 passed (frontend157, React21, TS SDK102); root build/lint passed. No new UI components or UI-class violations.
- Factory ready passed before implementation; validate, generated schema parity, Node syntax, whitespace and all-ref IDs checked. SDK-specific results/full backend to be appended.
- No new runtime dependencies or database migration; reuse existing httpx/FastAPI/uvicorn/Playwright/Ajv and encrypted MCP storage. Docker fixtures clean their own containers/networks/volumes and write no screenshot files to Git.

## Gaps And Residual Risk

No live account, purchased provider, physical remote host, deployment, UI flow or executable export is claimed. Capability JSON cannot attest arbitrary infrastructure. The operator controls TLS/allowlist/unique controller identity/reverse-proxy limits and trusted Docker authority. Controller supports one process per ID; restart invalidates its old pages. Private site content can exceed known-token redaction and must remain protected. TASK-0245 supplies durable run/fence/principal/revocation lifecycle; TASK-0246 supplies durable approval and trace filtering. Managed calls remain gated.

## QA Decision

Scoped pass; remain review pending final regression/owner review. No done/merge approval inferred.

- Final fixture rerun passed after strict proxy/profile validation; direct/custom/operator-default, no fallback, profile and restart cases all passed. Python SDK declared suite: **229 passed, 8 skipped** (10.49 s); TS SDK declared typecheck passed. Full backend is running on isolated commit 252aedff; subsequent documentation does not change source.
