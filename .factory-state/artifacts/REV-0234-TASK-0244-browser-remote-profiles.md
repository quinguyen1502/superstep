# Review

## Metadata

- Project: superstep
- Review ID: REV-0234
- Task ID: TASK-0244
- Reviewer: Codex (self-review; owner review pending)
- Created: 2026-11-05
- Updated: 2026-11-05
- Outcome: approved for QA within controlled remote/profile primitive scope

## Review Scope

Explicit controlled_remote HTTPS worker transport/controller, operator endpoint/address approval, compatibility/refusal checks, immutable personal profile seed contract using encrypted MCP storage, principal/origin restrictions, known-secret text masking, own-label restart cleanup and controlled real-browser evidence. No public Studio launch/call API, extra Agent loop, vendor integration, login capture UI or deployment.

## Reference Artifacts

- REQ-0086, DES-0004, ARCH-0002 remote/profile refinement, DEC-0085, PLAN-0006.
- `.factory-state/tasks/review/TASK-0244-browser-remote-profiles.md`.
- `docs/browser-remote.md`, `docs/browser-contract.md`, `docs/browser-runtime.md`.
- TASK-0243 #308 / REV-0233 / QA-0233; prerequisites #304/#303/#299 remain unmerged.

## Findings

No blocking finding within the declared worker/profile delivery after checks. Endpoint capability JSON is explicitly compatibility, not attestation; independent operator approval of the known deployment is required. Raw CDP/WSS, redirects, environment proxies, disabled TLS verification, unsupported storage/stealth and incomplete/unused proxy credentials refuse. Both personal connection create and update deny org profiles. Worker and supervisor validate the same seed principal and effective origin policy. No profile write-back or shared tab directory.

Non-blocking integration gates: TASK-0245 must derive the effective principal, allocate sequences before scheduling, revalidate current connection/secret digest on every call, revoke affected sessions and persist cleanup_pending across Studio failures. TASK-0246 must bind approve to durable verified Human approval. Managed execution stays gated, so these seams are not advertised as complete. Controller is single-process per unique operator ID; startup destroys its own prior pages, never reattaches/replays them. It has no distributed registry or arbitrary-vendor proof.

## Standards And Design Alignment

Dedicated API calls service; service calls engine. No FastAPI in services/engine, raw SQL or new schema. Existing encrypted personal MCP row is the single source of profile state and secret hints; error catalog/docs/en+vi remain aligned. UI components are unchanged. Profile removal uses existing API semantics; future interactive remove/revoke UI must use exact-name confirmation.

## Validation Review

Real HTTPS client/controller + Docker Chromium proved all six operations, approval/private artifact flow, all three proxy routes, upstream failure without direct fallback, private target denial, secure cookie/localStorage origin isolation, anonymous separate context, secret text redaction and own-label restart cleanup. 206 targeted backend/managed/MCP regressions passed before final strictness refinements; focused refinements passed. Root npm 280 tests/build/lint passed on develop 0.11.2. Full backend regression: 1300 passed, 67 skipped. Final fixture results are recorded in QA-0234. No screenshot images or raw secrets committed.

## Review Decision

Scoped pass / advisory self-review. Owner approval is pending; task remains review. No merge, deployment, release or paid provider setup authorised.

- 2026-11-05 full regression: declared `.venv/bin/python -m pytest` against isolated implementation commit 252aedff: **1300 passed, 67 skipped**, 458.78 s, no failures. Source is unchanged by subsequent documentation. Final real HTTPS/Chromium fixture and all declared SDK/root checks passed. Draft PR #309; owner review remains pending.
