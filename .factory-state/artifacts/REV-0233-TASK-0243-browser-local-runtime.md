# Review

## Metadata

- Project: superstep
- Review ID: REV-0233
- Task ID: TASK-0243
- Reviewer: Codex (self-review; owner review pending)
- Created: 2026-11-05
- Updated: 2026-11-05
- Outcome: approved for QA within isolated local worker/artifact scope

## Review Scope

Scoped diff from TASK-0242: separate production Node/Chromium and stdlib gateway builds, generated shared schemas, private Docker-exec/Unix HTTP control, six bounded handlers, trusted exact-command approval primitive, watchdog/cleanup, owner-only screenshot service/API/model/Alembic 0055, retention/account/workflow purge and smoke/regression tests. The existing managed adapter still refuses real calls until run/session integration.

## Reference Artifacts

- REQ-0086, DES-0004, ARCH-0002, DEC-0085, PLAN-0006.
- `.factory-state/tasks/review/TASK-0243-browser-local-runtime.md`.
- `docs/browser-runtime.md`, `docs/browser-contract.md`, `docs/browser-egress.md`.
- TASK-0241/#303 and TASK-0242/#304; REV-0229/0230, QA-0229/0230.

## Findings

### Blocking

- No blocking findings in scoped worker/artifact delivery after smoke, migration and targeted regression checks. No private TCP control endpoint, raw selectors/evaluate/files/keyboard tools, host mounts, unbounded screenshot response or silent effect retries were introduced.

### Non-Blocking

- The worker approval endpoint is a trusted primitive, not a durable Human approval product. TASK-0246 must bind it to verified approval identity/outcome/expiry and sanitize trace arguments.
- No Agent/run port or distributed session registry is wired here. TASK-0245 must allocate sequence before parallel dispatch, bind effective visitor/app-user identity, validate fences and retain/reap cleanup_pending after Docker outages.
- Initial observations/actions target the main page. Popups/downloads are closed/cancelled, service workers blocked and plain ws/streaming forms remain gateway refusals. Unsupported capabilities must remain explicit.
- Input masks/text omission do not sanitise all website-rendered private content; screenshots remain protected owner data, never public chat URLs or general state.

## Standards And Architecture Alignment

Routers call services; services call engine/repositories; no FastAPI in services, SQL text or speculative plugin layer. BrowserArtifact has SQLAlchemy/Alembic schema and SQLite/Postgres round-trip evidence. Shared error catalog/envelope and en/vi parity retained. Account/workflow deletion removes captures; no new interactive delete API/UI requiring a different confirmation contract.

## Design Alignment

No UI components changed. Existing Settings/Data/Execution and generic Agent/MCP concepts retained. Metadata enablement alone launches no browser; task docs distinguish implemented worker from later integration/UI/export capabilities.

## Validation Review

Real production worker smoke passed all six operations, exact-command approval/mutation denial, stale refs, cross-principal screenshot denial, bounded captures/actions, automatic idle cleanup without another call, uncertain click timeout closed without retry and production gateway private-IP denial. 131 targeted backend tests/2 optional skips passed before final cleanup/capture/purge refinements; later focused checks cover those refinements. PostgreSQL/SQLite migration suite: 4 passed. Root npm test 280, build and lint passed. Backend wheel includes the one packaged seccomp profile/license. Full backend regression is to be recorded against the committed task head before Ready.

## Assumptions

The owner authorised the chain and local Docker fixtures. Stack is explicit over #304/#303 and planning #299; no merge/release/deployment authorisation.

## Required Follow-Up

Record final focused/full regression evidence before Ready. Owner review before done/merge. TASK-0244–0253 supply their declared capabilities; none is claimed complete here.

## Review Decision

Approved for QA within this delivery scope; advisory self-review does not approve on behalf of the owner.

- Renumbered: REV-0231 → REV-0233 after fresh all-ref allocation; develop already merged the earlier allocation for TASK-0256.

- 2026-11-05 full regression: declared `.venv/bin/python -m pytest` against rebased implementation 1b52abff in an isolated checkout: **1284 passed, 67 skipped**, 458.45 s, no failures. This includes develop 21ddce1a. Optional environment skips and existing warnings remain. Commit 22a5d935 only normalises source/license whitespace. Draft PR #308; owner review remains pending.
