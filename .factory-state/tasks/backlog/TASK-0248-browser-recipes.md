# Task

## Metadata

- Project: superstep
- Task ID: TASK-0248
- Title: Reusable typed browser recipes through existing tool surfaces
- Status: backlog
- Owner: Thái Quí Nguyễn
- Created: 2026-11-03
- Updated: 2026-11-06
- Requirement IDs: REQ-0086
- Design IDs: DES-0004
- Architecture IDs: ARCH-0002, DEC-0085
- Plan: PLAN-0006
- Size: M (provisional; split again before task-start if the reviewed proof exceeds one independently reviewable delivery)

## Objective

Reusable typed browser recipes through existing tool surfaces, satisfying the assigned acceptance criteria of REQ-0086.

## Scope

### In Scope

- Implement bounded versioned recipes over the shared action handlers with typed per-call inputs/output mapping; reuse workflow-as-tool composition where sufficient.
- Expose recipe definitions/discovery/call through existing generic MCP/Agent selection without a vendor-specific node or a second expression/runtime language.
- Snapshot recipe version at run planning; preserve connection/profile/proxy/whitelist/toggle/approval/unknown-outcome policy and explicit layout failures. Recipes may use upload/download/evaluate_js only when the connection allows and the calling surface grants them.

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
- Dependency artifact: `.factory-state/tasks/backlog/TASK-0241-browser-connection-contract.md`.
- Dependency artifact: `.factory-state/tasks/backlog/TASK-0245-browser-run-sessions.md`.
- Dependency artifact: `.factory-state/tasks/backlog/TASK-0246-browser-approval-recovery.md`.

## Expected Outputs

- Bounded recipe definitions/versioning, invocation/discovery and fixture-backed input/output/error tests.

## Implementation Notes And Constraints

- Preserve router/service/repository/engine boundaries, shared error envelope/catalog and en/vi key parity. New schema requires Alembic; browser dependencies belong in isolated/export environments with pinned compatibility.
- Use current managed/MCP/Agent/approval/trace seams. Model input and page text cannot change authority, proxy/profile or network policy.
- No UI-only security guarantees, silent export stubs or automatic repeats of uncertain external effects. Mock/dry runs remain offline.
- UI work uses shadcn/theme tokens, common Settings/Data/Execution tabs and exact-name delete/revoke/unlink confirmation. Evidence screenshots remain outside Git/CI artifacts.
- Commands below are the declared validation intent. New test filenames are planned and must be created/discovered during implementation; they are not evidence of checks already run.

## Dependencies

- TASK-0241 — Browser contracts and scoped connection metadata
- TASK-0245 — Run-bound sessions, ordered Agent calls and lifecycle integration
- TASK-0246 — Browser approvals, stale sessions and uncertain-effect recovery
- Owner accepts REQ-0086, DES-0004, ARCH-0002/DEC-0085 and PLAN-0006 before promotion to todo/task-start.
- Start from the integration branch after dependencies are merged, or explicitly document an owner-authorised stack.

## Acceptance Criteria

- lookup_shipment(url, order_id) accepts a different authorised URL per call and returns declared bounded state outputs.
- Same action semantics and network/session/whitelist/toggle policy apply to recipe and autonomous tools; recipe is callable by generic MCP nodes and existing Agent slots.
- Unknown arguments, oversized sequences, inaccessible recipes and invalid versions are rejected; a changed selector/layout fails without secretly starting an Agent.
- Recorded completed recipe results do not recreate missing page state or replay uncertain writes; deletes use exact-name confirmation through shared management UI.

## Validation Plan

- Planned tests/test_browser_recipes.py with local fixtures and schema/version snapshots.
- Regressions tests/test_mcp.py, tests/test_agent_workflow_tools.py and relevant effects/approval/recovery tests.
- At implementation: run appropriate declared project checks plus Factory validation/ID checks; each task records review and QA before completion.

## Assumptions

- Owner authorised requirement capture and breakdown only. Technical defaults in the linked artifacts remain proposals until accepted.
- Controlled fixtures and synthetic credentials supply mandatory evidence; real proxy/provider accounts are operator setup.

## Open Questions

- Owner confirmation of the proposed task set is pending; no implementation command is authorised by creation of this backlog artifact.
- Resolve scoped technical capability/contract details from ARCH-0002 within the task; amend the plan rather than claiming unsupported behavior.

## Activity Log

- 2026-11-03: Created by plan-tasks after successful fetch and a fresh `factory ids next TASK --all-refs` allocation. No source changes, branch, dependency installation, execution evidence or PR created.

- 2026-11-04: Renumbered: TASK-0245 → TASK-0248 before publication after a fresh all-ref allocation; owner authorised commit/push only.

- 2026-11-06: Amended for owner clarifications on open draft PR #299 (relaxed mutating-approval defaults; session persistence across chat turns; Browserless required; deferred exports; upload/download + evaluate JS; mandatory origin whitelist; two-layer flexible-but-safe toggles and risk analysis). Status remains backlog; not implementation authorisation. Draft implementation PRs #303–#315 need reconciliation after package acceptance.

## Handoff Notes

- Future branch: `factory/task-0248-browser-recipes`, from `develop` after the stated gates.
- One task PR with review/QA; no merge without explicit owner approval.
