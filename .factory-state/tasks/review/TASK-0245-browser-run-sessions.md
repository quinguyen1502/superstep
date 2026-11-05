# Task

## Metadata

- Project: superstep
- Task ID: TASK-0245
- Title: Run-bound sessions, ordered Agent calls and lifecycle integration
- Status: review
- Owner: Thái Quí Nguyễn
- Created: 2026-11-03
- Updated: 2026-11-05
- Requirement IDs: REQ-0086
- Design IDs: DES-0004
- Architecture IDs: ARCH-0002, DEC-0085
- Plan: PLAN-0006
- Size: L (provisional; split again before task-start if the reviewed proof exceeds one independently reviewable delivery)

## Objective

Run-bound sessions, ordered Agent calls and lifecycle integration, satisfying the assigned acceptance criteria of REQ-0086.

## Scope

### In Scope

- Bind browser ports to trusted effective principal/run/Agent-tool group/connection snapshots through RunService and existing tool call paths.
- Keep sessions across rounds while serialising same-session commands in model call order, including parallel slots and multiple workers; preserve unrelated tool concurrency.
- Integrate lease fencing, revocation, cancellation, bounds, idle expiry and terminal cleanup with the current run queue and MCP/Agent behavior.

### Out Of Scope

- Other PLAN-0006 task outputs; hosted browser-Agent delegation, arbitrary script/files, live provider/account setup, deployment, release and merge.
- Durable approval policy and recovery UX are TASK-0246.

## Inputs And Related Artifacts

- Requirement: `.factory-state/artifacts/REQ-0086-browser-tools.md`.
- Design: `.factory-state/artifacts/DES-0004-browser-tools.md`.
- Architecture: `.factory-state/artifacts/ARCH-0002-browser-tools.md`.
- Decision proposal: `.factory-state/decisions/DEC-0085-browser-tools.md`.
- Discovery: `.factory-state/artifacts/DISC-0002-browser-tools-research.md`.
- Plan: `.factory-state/artifacts/PLAN-0006-browser-tools.md`.
- Standards: `AGENTS.md`, `docs/backend-architecture.md`, `docs/ui-conventions.md`; DEC-0008/0009/0010/0018/0033/0063/0066/0069/0081 referenced by the requirement/architecture.
- Dependency artifact: `.factory-state/tasks/review/TASK-0243-browser-local-runtime.md`.
- Dependency artifact: `.factory-state/tasks/review/TASK-0244-browser-remote-profiles.md`.

## Expected Outputs

- Run context/ports integration, session scheduler/lifecycle and concurrency/fencing evidence.

## Implementation Notes And Constraints

- Preserve router/service/repository/engine boundaries, shared error envelope/catalog and en/vi key parity. New schema requires Alembic; browser dependencies belong in isolated/export environments with pinned compatibility.
- Use current managed/MCP/Agent/approval/trace seams. Model input and page text cannot change authority, proxy/profile or network policy.
- No UI-only security guarantees, silent export stubs or automatic repeats of uncertain external effects. Mock/dry runs remain offline.
- UI work uses shadcn/theme tokens, common Settings/Data/Execution tabs and exact-name delete/revoke/unlink confirmation. Evidence screenshots remain outside Git/CI artifacts.
- Commands below are the declared validation intent. New test filenames are planned and must be created/discovered during implementation; they are not evidence of checks already run.

## Dependencies

- TASK-0243 — Isolated local Playwright runtime and bounded browser tools
- TASK-0244 — Remote browser capabilities and origin-scoped login profiles
- Owner accepts REQ-0086, DES-0004, ARCH-0002/DEC-0085 and PLAN-0006 before promotion to todo/task-start.
- Start from the integration branch after dependencies are merged, or explicitly document an owner-authorised stack.

## Acceptance Criteria

- Two same-round browser calls execute in deterministic tool-call order; thread lock acquisition order is not treated as an ordering guarantee.
- Separate principals, visitor identities, runs, child groups and connections cannot discover/control one another's live sessions.
- Unrelated tools/sessions retain parallel execution and existing result ordering; existing generic MCP per-call sessions remain compatible.
- Cancellation, stale worker lease, connection revoke, timeout and terminal completion stop late commands and clean up resources.

## Validation Plan

- Planned tests/test_browser_run_sessions.py with multi-worker/parallel races; regressions tests/test_parallel_agent_tools.py, tests/test_agent_node.py, tests/test_mcp.py and relevant run recovery/effect tests.
- Assert ordered navigation/observation/click against real fixtures and enforce no late writes after fence loss.
- At implementation: run appropriate declared project checks plus Factory validation/ID checks; each task records review and QA before completion.

## Assumptions

- Owner authorised the full browser chain and local Docker fixtures.
- Controlled fixtures and synthetic credentials supply mandatory evidence; real proxy/provider accounts are operator setup.

## Open Questions

- Owner start accepted; no owner merge approval.
- Resolve scoped technical capability/contract details from ARCH-0002 within the task; amend the plan rather than claiming unsupported behavior.

## Activity Log

- 2026-11-03: Created by plan-tasks after successful fetch and a fresh `factory ids next TASK --all-refs` allocation. No source changes, branch, dependency installation, execution evidence or PR created.

- 2026-11-04: Renumbered: TASK-0242 → TASK-0245 before publication after a fresh all-ref allocation; owner authorised commit/push only.

## Handoff Notes

- Future branch: `factory/task-0245-browser-run-sessions`, from `develop` after the stated gates.
- One task PR with review/QA; no merge without explicit owner approval.

- 2026-11-05: Explicit owner-authorised stack on TASK-0244 (controlled remote/profile review/QA), TASK-0243 #308, TASK-0242 #304, TASK-0241 #303 and planning #299; all unmerged. Current base includes develop 21ddce1a.

- 2026-11-05: factory ready passed before source work. Task-start complete, stack includes TASK-0244 #309 (REV-0234/QA-0234). Next: durable session identity/order and trusted RunService ports; no merge approval inferred.

- 2026-11-05: Implemented trusted run/actor/group ports, pre-dispatch ticket batch/CAS order, ledger bypass, exact-context page attachment, config/fence/cancel lifecycle and durable bounded cleanup (Alembic 0056). Real multi-process Chromium and HTTPS fixtures passed; PostgreSQL/SQLite suite 7 passed. REV-0235/QA-0235 record scoped self-review; full declared profile pending. Runtime flag remains experimental/default off; TASK-0246 approval/recovery and TASK-0250 filtering remain explicit gates.
