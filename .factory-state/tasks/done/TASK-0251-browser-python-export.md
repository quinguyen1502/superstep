# Task

## Metadata

- Project: superstep
- Task ID: TASK-0251
- Title: Executable Python and project export for browser tools/recipes
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-03
- Updated: 2026-11-07
- Requirement IDs: REQ-0086
- Design IDs: DES-0004
- Architecture IDs: ARCH-0002, DEC-0085
- Plan: PLAN-0006
- Size: L (provisional; split again before task-start if the reviewed proof exceeds one independently reviewable delivery)

## Objective

Executable Python and project export for browser tools/recipes (AC8), deferred until after studio delivery per owner amendment 2026-11-06.

## Scope

### Deferred trigger

- Start only after studio tasks TASK-0241–0250 and studio-scoped TASK-0253 are accepted and integrated. Not on the first-delivery critical path.

### In Scope

- Generate self-contained browser/runtime helpers for Python and LangGraph projects, including the existing Agent loop, dynamic arguments, recipes, provider/proxy/whitelist/toggle configuration and externally supplied secrets.
- Carry effective network/whitelist/session ordering (including cross-turn semantics where exportable), scoped profiles, bounds and approval/outcome semantics into the export; package dependencies and browser/container setup for local and Browserless.
- Replace managed export refusal only for the supported browser adapter; preserve refusals for unrelated managed integrations and unsupported browser capabilities.

### Out Of Scope

- Other PLAN-0006 task outputs; hosted browser-Agent delegation, unrestricted host filesystem/shell, live provider/account setup, deployment, release and merge. Upload/download/evaluate JS are in first delivery with the bounds in REQ-0086; interactive profile capture and deferred exports remain out of this task unless listed below.
- Starting implementation under this planning-only request.

## Inputs And Related Artifacts

- Requirement: `.factory-state/artifacts/REQ-0086-browser-tools.md`.
- Design: `.factory-state/artifacts/DES-0004-browser-tools.md`.
- Architecture: `.factory-state/artifacts/ARCH-0002-browser-tools.md`.
- Decision proposal: `.factory-state/decisions/DEC-0085-browser-tools.md`.
- Discovery: `.factory-state/artifacts/DISC-0002-browser-tools-research.md`.
- Plan: `.factory-state/artifacts/PLAN-0006-browser-tools.md`.
- Standards: `AGENTS.md`, `docs/backend-architecture.md`, `docs/ui-conventions.md`; DEC-0008/0009/0010/0018/0033/0063/0066/0069/0081 referenced by the requirement/architecture.
- Dependency artifact: `.factory-state/tasks/backlog/TASK-0247-browser-url-web-tools.md`.
- Dependency artifact: `.factory-state/tasks/backlog/TASK-0248-browser-recipes.md`.
- Dependency artifact: `.factory-state/tasks/backlog/TASK-0246-browser-approval-recovery.md`.
- Dependency artifact: `.factory-state/tasks/review/TASK-0244-browser-remote-profiles.md`.

## Expected Outputs

- Python/plain and project export helpers, runtime/setup packaging and executable parity evidence.

## Implementation Notes And Constraints

- Preserve router/service/repository/engine boundaries, shared error envelope/catalog and en/vi key parity. New schema requires Alembic; browser dependencies belong in isolated/export environments with pinned compatibility.
- Use current managed/MCP/Agent/approval/trace seams. Model input and page text cannot change authority, proxy/profile or network policy.
- No UI-only security guarantees, silent export stubs or automatic repeats of uncertain external effects. Mock/dry runs remain offline.
- UI work uses shadcn/theme tokens, common Settings/Data/Execution tabs and exact-name delete/revoke/unlink confirmation. Evidence screenshots remain outside Git/CI artifacts.
- Commands below are the declared validation intent. New test filenames are planned and must be created/discovered during implementation; they are not evidence of checks already run.

## Dependencies

- TASK-0247 — Dynamic URL bindings, search/fetch and missing-context flows
- TASK-0248 — Reusable typed browser recipes through existing tool surfaces
- TASK-0246 — Browser approvals, stale sessions and uncertain-effect recovery
- TASK-0244 — Remote browser capabilities and origin-scoped login profiles
- Owner accepts REQ-0086, DES-0004, ARCH-0002/DEC-0085 and PLAN-0006 before promotion to todo/task-start.
- Start from the integration branch after dependencies are merged, or explicitly document an owner-authorised stack.

## Acceptance Criteria

- Exported Agent and recipe fixture scenarios run outside Superstep with no MCP placeholder, no Superstep service dependency and no fixed URL substituted for dynamic input.
- Supported proxy/profile/policy settings are retained and tested; credentials/cookies/provider tokens are absent from generated code and example environment values.
- Concurrent tool calls retain same-session command order; approval/rejection/lost-session/unknown effects retain the required behavior.
- Unsupported behavior is refused with an explicit feature/capability explanation. Plain/project code, dependency manifests and setup guidance agree.

## Validation Plan

- Planned tests/test_browser_python_export.py and execution of exported fixture projects, plus tests/test_python_export.py, tests/test_project_export.py and tests/test_handoff_exports.py.
- Compare Studio vs export data/results/policy/approval scenarios; compile/syntax-only checks are insufficient.
- At implementation: run appropriate declared project checks plus Factory validation/ID checks; each task records review and QA before completion.

## Assumptions

- Owner authorised requirement capture and breakdown only. Technical defaults in the linked artifacts remain proposals until accepted.
- Controlled fixtures and synthetic credentials supply mandatory evidence; real proxy/provider accounts are operator setup.

## Open Questions

- Owner confirmation of the proposed task set is pending; no implementation command is authorised by creation of this backlog artifact.
- Resolve scoped technical capability/contract details from ARCH-0002 within the task; amend the plan rather than claiming unsupported behavior.

## Activity Log

- 2026-11-03: Created by plan-tasks after successful fetch and a fresh `factory ids next TASK --all-refs` allocation. No source changes, branch, dependency installation, execution evidence or PR created.

- 2026-11-04: Renumbered: TASK-0248 → TASK-0251 before publication after a fresh all-ref allocation; owner authorised commit/push only.

- 2026-11-06: Amended for owner clarifications on open draft PR #299 (relaxed mutating-approval defaults; session persistence across chat turns; Browserless required; deferred exports; upload/download + evaluate JS; mandatory origin whitelist; two-layer flexible-but-safe toggles and risk analysis). Status remains backlog; not implementation authorisation. Draft implementation PRs #303–#315 need reconciliation after package acceptance.
- 2026-11-07: Studio tasks through TASK-0253 and the handbook screenshot replacement are merged. The owner asked to proceed with this task and TASK-0252 through Ready pull requests. Deferral is lifted. Status moves to todo. TASK-0252 stays stacked until this task's branch exists. Do not merge until the owner asks.
- 2026-11-07: `factory ready` passed with this task in todo. Branch `factory/task-0251-browser-python-export` from `develop` at `e26e39e9`. Moved to doing. TASK-0250 was moved to done on this branch because PR #315 had already merged. Implementation follows. Not validated. Not merged.
- 2026-11-07: Python export implemented. Review REV-0255 found no blocking issues. QA QA-0255 passed. Tool-policy checks passed on this worktree with arm64 Node: backend pytest 1427 passed / 71 skipped in 522.03s; sdk/python pytest 229 passed / 8 skipped; repo-root npm build, lint, and test; sdk/typescript build, test (102), and typecheck. Handbook check passed. Status is done. Not merged. TASK-0252 remains stacked.
- 2026-11-07: CI Python 3.12 failed `test_idle_timeout_drops_the_page_and_does_not_replay` because `time.monotonic()` on a freshly booted runner is below the 1800s idle. The test now sets `touched` to 100000 seconds before the clock. Local re-run of that test passed. Not merged.

## Handoff Notes

- Future branch: `factory/task-0251-browser-python-export`, from `develop` after the stated gates.
- One task PR with review/QA; no merge without explicit owner approval.
