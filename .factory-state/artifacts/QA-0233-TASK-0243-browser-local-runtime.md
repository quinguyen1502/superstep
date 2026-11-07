# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0233
- Task ID: TASK-0243
- QA Owner: Codex
- Created: 2026-11-05
- Updated: 2026-11-05
- Outcome: pass within local worker/artifact scope; full regression passed

## Validation Scope

Actual isolated production worker/control transport, six operations and failure paths, private capture persistence/access/retention and portable schema/packaging. No Agent/remote/profile/UI/export behavior claimed.

## Acceptance Criteria Coverage

- Disposable fixture navigates, observes, fills, queries and captures bounded results; stale refs fail: pass via `backend/.venv/bin/python scripts/test-browser-worker.py --docker /Applications/Docker.app/Contents/Resources/bin/docker`. All six operations confirmed; changed approval arguments and old/out-of-order references refused. Actual viewport PNG is 1024x768, at most 2 MiB; four-image/action budgets enforced.
- No browser in API process or host mounts/secrets; resource limits enforced: pass. Dedicated Node LTS/Chromium Docker image, non-root 1001, Chromium sandbox, network=none, cap-drop ALL, no-new-privileges, read-only root and only a read-only per-session Unix socket volume. Docker inspect verified 768 MiB memory/no swap, one CPU and 128 pids. Gateway receives only filtered proxy secrets through a private temporary env file; worker gets no unrelated server secrets.
- Terminal/cancel/expiry/error cleanup; mock/dry starts nothing: pass for worker primitives and existing offline MCP gate. Real idle watchdog removes both containers/volume without another tool call. Hanging approved click returns unknown, never retries and closes. Budget expiry and explicit close remove resources. Simulated Docker failure exposes cleanup_pending and a retryable close rather than claiming verified cleanup. Existing dry-run path still returns before any runtime call.
- Protected captures cannot be read by another principal or public URL; retention explicit: pass. Real worker rejects foreign context artifact read; API requires owner auth and returns identical missing/other-owner/expired 404. Owner capture response is PNG/no-store/nosniff/restricted CSP. Runtime service persists before returning a stored ID and refuses missing bytes. One-hour expiry, minute sweep, account purge and workflow/run deletion verified. No screenshot image written to Git.

## UX And Accessibility Coverage

No browser UI components delivered. Catalog errors have en/vi parity; binary screenshot endpoint is owner-authenticated and is not a public/visitor endpoint. UI/trace/artifact presentation remains TASK-0250.

## Checks Performed

- Real worker smoke passed with all operations plus approval/stale/foreign-artifact/resource/idle/unknown-effect/production-gateway cases. Fixtures use only synthetic data and clean their own Docker objects.
- 131 targeted backend tests passed/2 optional Postgres skips before final refinements; 56 focused checks/1 optional skip passed after capture-persistence and cleanup changes. Final focused checks: 71 passed, 1 optional PostgreSQL skip.
- Disposable PostgreSQL 17 and SQLite migration/seed suite: 4 passed, including downgrade/upgrade preserving existing users. Container/database removed afterward.
- Root npm test: 280 passed; npm build/lint passed with existing warnings and no UI-class violations.
- Worker schemas compile under Ajv in the runtime image and match Python source. Production Node base v24.22.2 digest pinned, Playwright/Ajv locked; gateway Python 3.12 base pinned. Runtime proof: Docker Desktop 28.3.3/aarch64.
- Backend wheel built in an isolated build environment and contains app/engine/browser_seccomp.json and license. Build output stays outside Git.
- Factory ready passed before source work; Factory validate and whitespace passed. All-ref artifact/migration collision checks re-run before publication.

## Defects

No open blocking defect within scope. Resolved issues: typed model envelope serialization, bounded element scanning, automatic watchdog cleanup, screenshot persistence before reference return and purge on account/workflow deletion. Docker cleanup failure is explicit and tested; durable reap belongs to TASK-0245.

## Gaps Or Untested Areas

Full backend suite passed against task commit; see final evidence below. No live accounts, production deployment, remote provider/login profile, distributed scheduler/fence, completed Human approval workflow, public trace filter, executable export or browser settings UI claimed. Other CPU/OS combinations need separate evidence.

## Residual Risk

Protected screenshot content may remain private even with input masks; it must not be exposed through public state/chat. Supervisor Docker authority is trusted infrastructure, never granted to page/model input. A lost controller/daemon can leave bounded stopped resources; cleanup_pending must be persisted/reaped by session integration. Existing API flags do not enable runtime before that integration.

## Assumptions

Owner chain instruction permits the documented stack and local fixture work. It does not approve merging/releasing/deploying.

## Required Follow-Up

Record final regression output, owner review and full-stack integration evidence before done/merge. Follow PLAN-0006 for remote/profile, sessions, durable approvals, bindings, recipes, UI, exports and final acceptance.

## QA Decision

Pass within scoped acceptance; remain review pending owner approval and final regression. No done/merge approval inferred.

- Renumbered: QA-0231 → QA-0233 after fresh all-ref allocation; develop already merged the earlier allocation for TASK-0256.

- 2026-11-05 full regression: declared `.venv/bin/python -m pytest` against rebased implementation 1b52abff in an isolated checkout: **1284 passed, 67 skipped**, 458.45 s, no failures. This includes develop 21ddce1a. Optional environment skips and existing warnings remain. Commit 22a5d935 only normalises source/license whitespace. Draft PR #308; owner review remains pending.

## 2026-11-06 reconciliation with Accepted plan

- Merged develop (TASK-0241 #303, TASK-0242 #304, plan #299).
- Kept Accepted nine-tool Browserless contract; restored WorkerOpen/Control/Artifact.
- WorkerEnvelope size check accepts nested pydantic models; contracts.json regenerated.
- Artifact error codes restored; runtime tests use required whitelist.
- Tests: browser contract/network/connections/runtime/migration → 100 passed, 1 skipped.
