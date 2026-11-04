# Task

## Metadata

- Project: superstep
- Task ID: TASK-0251
- Title: Executable Python and project export for browser tools/recipes
- Status: backlog
- Owner: Thái Quí Nguyễn
- Created: 2026-11-03
- Updated: 2026-11-04
- Requirement IDs: REQ-0086
- Design IDs: DES-0004
- Architecture IDs: ARCH-0002, DEC-0085
- Plan: PLAN-0006
- Size: L (provisional; split again before task-start if the reviewed proof exceeds one independently reviewable delivery)

## Objective

Executable Python and project export for browser tools/recipes, satisfying the assigned acceptance criteria of REQ-0086.

## Scope

### In Scope

- Generate self-contained browser/runtime helpers for Python and LangGraph projects, including the existing Agent loop, dynamic arguments, recipes, provider/proxy configuration and externally supplied secrets.
- Carry effective network/session ordering, scoped profiles, bounds and approval/outcome semantics into the export; package dependencies and browser/container setup.
- Replace managed export refusal only for the supported browser adapter; preserve refusals for unrelated managed integrations and unsupported browser capabilities.

### Out Of Scope

- Other PLAN-0006 task outputs; hosted browser-Agent delegation, arbitrary script/files, live provider/account setup, deployment, release and merge.
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
- Dependency artifact: `.factory-state/tasks/backlog/TASK-0244-browser-remote-profiles.md`.

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

## Handoff Notes

- Future branch: `factory/task-0251-browser-python-export`, from `develop` after the stated gates.
- One task PR with review/QA; no merge without explicit owner approval.
