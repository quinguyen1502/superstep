# Review

## Metadata

- Project: superstep
- Review ID: REV-0235
- Task ID: TASK-0245
- Reviewer: Codex (self-review; owner review pending)
- Created: 2026-11-05
- Updated: 2026-11-05
- Outcome: scoped pass; declared checks passed

## Reference Artifacts

- REQ-0086, DES-0004, ARCH-0002 session refinement, DEC-0085, PLAN-0006.
- `.factory-state/tasks/review/TASK-0245-browser-run-sessions.md`.
- `docs/browser-sessions.md`, `docs/browser-remote.md`, `docs/browser-runtime.md`.
- TASK-0244 #309 / REV-0234 / QA-0234; TASK-0243 #308; #304/#303/#299 remain prerequisites.

## Findings And Scope

No blocking finding in scoped session delivery after focused and real-worker checks; full declared validation is pending. The model step reserves a batch before Send. SQL CAS claims only the head; browser steps bypass the generic result ledgers. Scope/argument hashes cannot be replaced through model input. Private health proves an existing page and never opens/replays or refreshes idle. Resource/config/actor identity remains service-owned; actual visitor/app/child context is derived from stored chat records. Raw profile arguments/results are not persisted in scheduler tables.

Cancellation/fencing checks and watcher close stop new dispatch and reject late results. Already-dispatched external effects may have happened and remain unknown, never retried or described as undone. Cleanup is idempotent and durable pending metadata survives account purge; remote control tokens clear after confirmed cleanup. Global capacity uses one short DB lock, not a long transaction spanning browser I/O. Generic tool concurrency/ledger behavior remains unchanged.

Explicit follow-ups already assigned: TASK-0246 durable verified Human approval and stale/recovery UX; TASK-0250 public trace filtering. The separate runtime flag remains experimental/default off; browser click/fill do not acquire approval merely because the model/tool calls them. No release readiness, public settings UI, export or live account/provider deployment is claimed.

## Standards And Verification

Router/service/repository/engine direction retained; SQLAlchemy models + Alembic 0056, no raw SQL added. Existing user delete API/confirmation contract stays intact; cleanup hooks apply after existing authorization. No UI components or literal UI strings added.

Actual multi-process Docker proof passed navigate/snapshot order, creator exit with same-page reattachment, one approved fixture POST, no extra POST after stale fence and resource removal. Real HTTPS fixture passed attachment plus all six actions/profile/proxy cases. 142 focused regressions passed/2 optional skips before final additions. Disposable PostgreSQL/SQLite suite: 7 passed, including independent-process CAS and migration round trips. Full Factory validation results are appended to QA-0235.

## Review Decision

Scoped advisory pass; owner review/QA/final validation before done or Ready. No merge/deployment/release approval inferred.

- 2026-11-05 declared verification on committed 4b65144f: full backend passed (462.99 s), Python SDK passed (14.09 s), TS build/typecheck passed. Initial Factory Node checks inherited x64 from the Rosetta-only Python while installed native dependencies are arm64; no source/dependency defect. Native arm64 Node reruns passed all remaining declared commands: root npm 280 tests/build/lint and explicit TS SDK tests/build/typecheck. Factory filtered full-profile build/lint/typecheck and verify validate passed. Thus all eight declared commands passed across these runs; a single all-eight canonical run remains a Ready/integration gate. The temporary Node architecture wrapper is outside Git. No source changed during verification.
