# Task

## Metadata

- Project: superstep
- Task ID: TASK-0244
- Title: Remote browser capabilities and origin-scoped login profiles
- Status: backlog
- Owner: Thái Quí Nguyễn
- Created: 2026-11-03
- Updated: 2026-11-04
- Requirement IDs: REQ-0086
- Design IDs: DES-0004
- Architecture IDs: ARCH-0002, DEC-0085
- Plan: PLAN-0006
- Size: M (provisional; split again before task-start if the reviewed proof exceeds one independently reviewable delivery)

## Objective

Remote browser capabilities and origin-scoped login profiles, satisfying the assigned acceptance criteria of REQ-0086.

## Scope

### In Scope

- Implement the remote-browser provider against the command contract, without delegating the Agent loop.
- Support operator-provisioned encrypted origin-filtered login state and explicit local/remote provider capability checking, including proxy/stealth options.
- Require evidence of destination enforcement through the selected remote/proxy path; unsupported combinations return a specific refusal instead of silently dropping a setting.

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
- Dependency artifact: `.factory-state/tasks/review/TASK-0241-browser-connection-contract.md`.
- Dependency artifact: `.factory-state/tasks/review/TASK-0242-browser-egress-proxy-policy.md`.
- Dependency artifact: `.factory-state/tasks/review/TASK-0243-browser-local-runtime.md`.

## Expected Outputs

- Remote provider implementation, scoped profile service/storage, capability matrix and compatibility tests.

## Implementation Notes And Constraints

- Preserve router/service/repository/engine boundaries, shared error envelope/catalog and en/vi key parity. New schema requires Alembic; browser dependencies belong in isolated/export environments with pinned compatibility.
- Use current managed/MCP/Agent/approval/trace seams. Model input and page text cannot change authority, proxy/profile or network policy.
- No UI-only security guarantees, silent export stubs or automatic repeats of uncertain external effects. Mock/dry runs remain offline.
- UI work uses shadcn/theme tokens, common Settings/Data/Execution tabs and exact-name delete/revoke/unlink confirmation. Evidence screenshots remain outside Git/CI artifacts.
- Commands below are the declared validation intent. New test filenames are planned and must be created/discovered during implementation; they are not evidence of checks already run.

## Dependencies

- TASK-0241 — Browser contracts and scoped connection metadata
- TASK-0242 — Enforce browser egress and connection-level proxy policy
- TASK-0243 — Isolated local Playwright runtime and bounded browser tools
- Owner accepts REQ-0086, DES-0004, ARCH-0002/DEC-0085 and PLAN-0006 before promotion to todo/task-start.
- Start from the integration branch after dependencies are merged, or explicitly document an owner-authorised stack.

## Acceptance Criteria

- A controlled remote fixture reaches the same action/result contract as local; provider endpoint tokens and proxy secrets are never exposed.
- A login profile cannot be attached outside its authorised principal/origins; separate runs/org users do not share live tabs or cookie state.
- Unsupported remote enforcement, profile filtering, proxy auth or stealth is refused and documented; no capability is inferred from a CDP URL.
- Provider/proxy/profile configuration is immutable within a live session; revoke/update invalidates affected sessions.

## Validation Plan

- Planned tests/test_browser_remote.py and tests/test_browser_profiles.py with fake control APIs plus a controlled remote browser fixture.
- Prove origin separation, secret redaction, provider capability errors and revoked-profile behavior; no purchased provider/live account required for automated checks.
- At implementation: run appropriate declared project checks plus Factory validation/ID checks; each task records review and QA before completion.

## Assumptions

- Owner authorised requirement capture and breakdown only. Technical defaults in the linked artifacts remain proposals until accepted.
- Controlled fixtures and synthetic credentials supply mandatory evidence; real proxy/provider accounts are operator setup.

## Open Questions

- Owner confirmation of the proposed task set is pending; no implementation command is authorised by creation of this backlog artifact.
- Resolve scoped technical capability/contract details from ARCH-0002 within the task; amend the plan rather than claiming unsupported behavior.

## Activity Log

- 2026-11-03: Created by plan-tasks after successful fetch and a fresh `factory ids next TASK --all-refs` allocation. No source changes, branch, dependency installation, execution evidence or PR created.

- 2026-11-04: Renumbered: TASK-0241 → TASK-0244 before publication after a fresh all-ref allocation; owner authorised commit/push only.

## Handoff Notes

- Future branch: `factory/task-0244-browser-remote-profiles`, from `develop` after the stated gates.
- One task PR with review/QA; no merge without explicit owner approval.
