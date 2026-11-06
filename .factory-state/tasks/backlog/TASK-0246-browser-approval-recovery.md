# Task

## Metadata

- Project: superstep
- Task ID: TASK-0246
- Title: Configurable mutating approvals, stale sessions and uncertain-effect recovery
- Status: backlog
- Owner: Thái Quí Nguyễn
- Created: 2026-11-03
- Updated: 2026-11-06
- Requirement IDs: REQ-0086
- Design IDs: DES-0004
- Architecture IDs: ARCH-0002, DEC-0085
- Plan: PLAN-0006
- Size: L (provisional; split again before task-start if the reviewed proof exceeds one independently reviewable delivery)

## Objective

Configurable mutating-action approvals (default OFF), stale sessions and uncertain-effect recovery, satisfying the assigned acceptance criteria of REQ-0086.

## Scope

### In Scope

- Apply **connection-configurable** mutating-action approval through existing Human/Agent approval and child-run mechanisms. Default **OFF**: click, fill, upload, download and evaluate JS run immediately. When ON, those mutating actions wait for approval; reject/timeout is returned to the model. Navigate, snapshot, structured extraction and screenshot **never** wait on this toggle.
- Track observation generations and distinguish confirmed results, before-effect failures and unknown external outcomes; do not reuse the generic operation cache as browser state.
- Handle browser loss, idle/max expiry during approval or between chat turns, worker restart, late approval, cancellation and time-travel/replay without replaying uncertain UI effects — regardless of whether mutating approval is ON or OFF.

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
- Dependency artifact: `.factory-state/tasks/backlog/TASK-0245-browser-run-sessions.md`.

## Expected Outputs

- Approval/outcome/recovery integration, failure-mode contract and crash/expiry evidence.

## Implementation Notes And Constraints

- Preserve router/service/repository/engine boundaries, shared error envelope/catalog and en/vi key parity. New schema requires Alembic; browser dependencies belong in isolated/export environments with pinned compatibility.
- Use current managed/MCP/Agent/approval/trace seams. Model input and page text cannot change authority, proxy/profile or network policy.
- No UI-only security guarantees, silent export stubs or automatic repeats of uncertain external effects. Mock/dry runs remain offline.
- UI work uses shadcn/theme tokens, common Settings/Data/Execution tabs and exact-name delete/revoke/unlink confirmation. Evidence screenshots remain outside Git/CI artifacts.
- Commands below are the declared validation intent. New test filenames are planned and must be created/discovered during implementation; they are not evidence of checks already run.

## Dependencies

- TASK-0245 — Run-bound sessions, ordered Agent calls and lifecycle integration
- Owner accepts REQ-0086, DES-0004, ARCH-0002/DEC-0085 and PLAN-0006 before promotion to todo/task-start.
- Start from the integration branch after dependencies are merged, or explicitly document an owner-authorised stack.

## Acceptance Criteria

- When mutating approval is ON, click/fill/upload/download/evaluate JS require approval; when OFF they run immediately. Navigate/snapshot/extract/screenshot never wait. Model/page text cannot mark itself safe or change the connection toggle.
- Approval resumes only against a live authorised session and valid target/page references; changed target/arguments require renewed approval; expired approvals do not silently succeed.
- Unknown browser effects are not auto-repeated after timeout/crash/retry/fork. Recovered runs re-observe or stop with a clear session-lost state. Crash survival is not promised even though cross-turn persistence is.
- No false promise of exactly-once UI submission or persistent live browser after worker restart; confirm/reject/wait/expired/unknown transitions remain visible when approval applies.

## Validation Plan

- Planned tests/test_browser_approval_recovery.py; regressions tests/test_agent_approval.py, tests/test_parallel_agent_tools.py and existing child-run/effect/restart tests.
- Inject crashes after fixture-side effect but before acknowledgment and prove absence of a second effect; test expired-session/stale-ref approvals.
- At implementation: run appropriate declared project checks plus Factory validation/ID checks; each task records review and QA before completion.

## Assumptions

- Owner authorised requirement capture and breakdown only. Technical defaults in the linked artifacts remain proposals until accepted.
- Controlled fixtures and synthetic credentials supply mandatory evidence; real proxy/provider accounts are operator setup.

## Open Questions

- Owner confirmation of the proposed task set is pending; no implementation command is authorised by creation of this backlog artifact.
- Resolve scoped technical capability/contract details from ARCH-0002 within the task; amend the plan rather than claiming unsupported behavior.

## Activity Log

- 2026-11-03: Created by plan-tasks after successful fetch and a fresh `factory ids next TASK --all-refs` allocation. No source changes, branch, dependency installation, execution evidence or PR created.

- 2026-11-04: Renumbered: TASK-0243 → TASK-0246 before publication after a fresh all-ref allocation; owner authorised commit/push only.

- 2026-11-06: Amended for owner clarifications on open draft PR #299 (relaxed mutating-approval defaults; session persistence across chat turns; Browserless required; deferred exports; upload/download + evaluate JS; mandatory origin whitelist; two-layer flexible-but-safe toggles and risk analysis). Status remains backlog; not implementation authorisation. Draft implementation PRs #303–#315 need reconciliation after package acceptance.

## Handoff Notes

- Future branch: `factory/task-0246-browser-approval-recovery`, from `develop` after the stated gates.
- One task PR with review/QA; no merge without explicit owner approval.
