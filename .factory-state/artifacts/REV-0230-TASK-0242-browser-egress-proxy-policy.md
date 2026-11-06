# Review

## Metadata

- Project: superstep
- Review ID: REV-0230
- Task ID: TASK-0242
- Reviewer: Codex (self-review; owner review pending)
- Created: 2026-11-05
- Updated: 2026-11-05
- Outcome: approved for QA within egress boundary scope

## Review Scope

Scoped diff from TASK-0241: shared URL syntax helper, pinned destination/proxy policy, Unix-socket HTTP/CONNECT gateway, disposable Docker/Chromium fixture and operator documentation. No browser adapter execution activation or application deployment.

## Reference Artifacts

- REQ-0086, DES-0004, ARCH-0002, DEC-0085, PLAN-0006.
- `.factory-state/tasks/review/TASK-0242-browser-egress-proxy-policy.md`.
- `docs/browser-contract.md`, `docs/browser-egress.md`.
- TASK-0241 PR #303; REV-0229 / QA-0229.

## Findings

### Blocking

- No blocking findings within TASK-0242 scope after final fixture and regression checks. Network isolation is enforced by network=none plus a per-session Unix gateway socket, not inferred from browser proxy settings.

### Non-Blocking

- HTTPS CONNECT cannot inspect encrypted origins/headers. The product runtime must additionally enforce exact origin requests and service-worker/websocket policy. Actual IP connection remains gateway-controlled; these hooks are TASK-0243 integration work.
- Third-party proxy/CDP behavior is not verified by a controlled fixture or by operator approval alone. Unknown provider combinations must stay refused under TASK-0244.
- Unix gateway lifecycle must be bound to session/cancel/fence deadlines by the runtime/supervisor. DNS uses the OS resolver; connection admission is bounded, and lifetime termination is follow-on runtime work.
- Plain HTTP websocket Upgrade/streaming request bodies are refused; secure websocket tunnels use guarded CONNECT. Documented compatibility limit, not an unguarded fallback.

## Standards And Architecture Alignment

No raw SQL/migrations, API dependency in services, browser process in API, proxy environment inheritance, host filesystem/socket mounts or broad private-network flag. Existing HTTP/MCP guard remains unchanged; URL syntax is shared rather than duplicated. Secrets are stripped/redacted and never emitted to audit/errors.

## Design Alignment

No UI change. Browser proxy remains connection metadata; runtime target input cannot alter proxy, policy or fixture exceptions. No new canvas node, tool loop or config tabs.

## Validation Review

179 targeted regression tests passed. Real Chromium fixture passed direct/custom/operator-default paths on Docker Desktop 28.3.3 aarch64, with 13/14/14 gateway denials and 14 numeric upstream CONNECTs. Sandbox=true, non-root UID 1001, cap-drop ALL, read-only root, bounded tmpfs/CPU/memory/pids and network=none inspected. Direct browser without proxy cannot reach fixture/host network. HTTPS secure-origin service worker registration is blocked with no script request reaching the server. Resources cleaned after tests. Factory validate and whitespace passed; full task-0241 suite baseline was 1,234 passed/65 skipped, not reattributed as full post-task-0242 coverage.

## Assumptions

Owner selected local Docker and requested the chain. Explicit stack is TASK-0242 over unmerged TASK-0241 / published planning package; no merge permission.

## Required Follow-Up

TASK-0243 integrates supervisor/runtime and protected artifacts; TASK-0244 proves/refuses remote paths; TASK-0245/0246 bind run/fencing/approval semantics. None of those capabilities is claimed here.

## Review Decision

Approved for QA; advisory self-review only. Owner approval remains necessary before done/merge.


## 2026-11-06 reconciliation with Accepted plan

- Merged `origin/develop` at f95ad1a1 (TASK-0241 #303 + Accepted plan #299).
- `DestinationPolicy` now requires a non-empty origin whitelist by default; empty
  allowlists raise `EgressDenied`. Page resolves fail closed when the origin is
  absent from the list. Private/link-local/metadata IP denial unchanged.
- Tests: `pytest tests/test_browser_network_policy.py tests/test_browser_contract.py tests/test_browser_connections.py` → 88 passed.
