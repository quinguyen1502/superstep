# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0230
- Task ID: TASK-0242
- QA Owner: Codex
- Created: 2026-11-05
- Updated: 2026-11-05
- Outcome: pass within TASK-0242 local/controlled-proxy fixture scope

## Validation Scope

Actual gateway resolution/connection enforcement and isolated Chromium traffic on disposable synthetic targets, plus policy/MCP/HTTP/contract regressions. No real accounts or provider deployment.

## Acceptance Criteria Coverage

- Browser fixtures deny private/loopback/link-local/metadata navigation, redirects/subresources, proxy-resolved targets and DNS changes: pass. `python3 scripts/test-browser-egress.py --docker /Applications/Docker.app/Contents/Resources/bin/docker` passed all three routes; forbidden destination paths never reached fixture server. Unit checks additionally cover IPv6/mapped/transition/CGNAT/mixed answers.
- Allowed traffic follows selected route; proxy failure has no direct fallback; credentials not logged: pass. Direct/custom/operator-default fixture; custom/default upstream accepts numeric CONNECT only, intentionally rejects a reachable port, and no forbidden fallback request arrives. Proxy resolved once per session; destination sees no Proxy-Authorization. Query secret absent from gateway audit; route repr excludes auth.
- Policy covers actual resolution/connection; unsupported routes fail before use: pass for local/proven numeric-CONNECT path. Numeric socket connect and all-answer validation prevent second DNS resolution. Browser without proxy cannot connect to fixture IP or host.docker.internal. Missing default/unapproved proxy/unsupported protocol fail closed. Arbitrary remote/proxy providers are not claimed verified and remain follow-on refusals/proof gates.
- Production and fixture policies separate; chat cannot enable test exception: pass. No allow_private argument/setting; production policy ignores STUDIO_MCP_ALLOW_PRIVATE. FixturePolicy lives only under tests/fixtures and permits one exact test container IP with synthetic DNS, no internet. Browser schema forbids unknown authority fields.

## UX And Accessibility Coverage

No UI components or browser settings UI delivered by this task. Common tabs/deletion/localisation surfaces remain unchanged.

## Checks Performed

- 179 backend tests passed in 28.37 seconds: browser contract/connections/network policy, MCP/managed, layers, envelope/locales, SQLite migrations, core HTTP hardening and managed HTTP API.
- Real Chromium final fixture: direct denied 13; custom denied 14; operator_default denied 14; 3 routes passed, 14 numeric upstream CONNECTs. Repro script asserts actual Docker isolation settings and no negative target paths or proxy-auth leakage.
- Secure-origin HTTPS/self-signed fixture and service-worker API present; registration blocked, no sw.js/service-worker destination request. Test-only ignoreHTTPSErrors does not enter production code.
- Docker Desktop 28.3.3 aarch64; Playwright 1.64.1 image pinned to digest; gateway Python 3.12 stdlib. Host backend tests use Python 3.14.6/SQLite.
- Factory ready passed with TASK-0242 in todo before source work. Factory validate, Node fixture syntax and diff whitespace passed; artifact IDs rechecked before push.
- Container listing after fixture was empty for ss-browser-egress-*; script removes only its uniquely named containers/network/volumes.

## Defects

No open blocking defect in scoped criteria. Initial sandbox startup exposed a missing chroot seccomp admission (fixed without granting capabilities or disabling sandbox). Initial socket connection exposed UID mismatch between images (fixed by matching non-root UID 1001 while retaining socket mode 0600). All final three-route fixtures passed.

## Gaps Or Untested Areas

No public provider, production browser image, live proxy credentials, hosted CDP, run orchestration/approvals, protected screenshot artifacts, export or UI test claimed. Product runtime remains unavailable. Full suite was not repeated after task-0242; the changed boundary and related seams have 179 targeted passing tests.

## Residual Risk

Production must use the documented isolated topology; using the gateway library with an unrestricted browser network would violate this proof. Provider attestation, protected worker control, lifecycle/fencing and origin hooks are explicit follow-on tasks. Fixture image and test-only TLS exception are not production deployment guidance.

## Assumptions

Existing owner chain instruction authorises this documented stack and local Docker fixtures, not merge/release/deployment.

## Required Follow-Up

Owner review before done/merge. Integrate the boundary without weakening it in TASK-0243–0246; remote/export tests retain the same effective controls.

## QA Decision

Pass within scoped criteria; task remains review pending owner approval, with follow-on work tracked by PLAN-0006 rather than hidden claims.
