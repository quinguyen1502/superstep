# Task

## Metadata

- Project: superstep
- Task ID: TASK-0252
- Title: Executable TypeScript and project export with browser parity
- Status: backlog (deferred — after studio browser tools are accepted and integrated; depends on TASK-0251)
- Owner: Thái Quí Nguyễn
- Created: 2026-11-03
- Updated: 2026-11-06
- Requirement IDs: REQ-0086
- Design IDs: DES-0004
- Architecture IDs: ARCH-0002, DEC-0085
- Plan: PLAN-0006
- Size: L (provisional; split again before task-start if the reviewed proof exceeds one independently reviewable delivery)

## Objective

Executable TypeScript and project export with browser parity (AC8), deferred until after studio delivery and TASK-0251 per owner amendment 2026-11-06.

## Scope

### Deferred trigger

- Start only after TASK-0251. Not on the first-delivery critical path.

### In Scope

- Implement TypeScript/LangGraph.js equivalents of the reviewed browser tool/recipe/runtime contracts, preserving current exporter registry behavior.
- Package Node-compatible browser dependencies/helpers, environments and compatible browser versions; preserve dynamic binding, proxy/policy/profile and approval semantics.
- Use Python task parity scenarios as a contract, not a Python-code translation shortcut or TS stub.

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
- Dependency artifact: `.factory-state/tasks/backlog/TASK-0251-browser-python-export.md`.

## Expected Outputs

- TypeScript exporter/helpers/project packaging and executable cross-language parity evidence.

## Implementation Notes And Constraints

- Preserve router/service/repository/engine boundaries, shared error envelope/catalog and en/vi key parity. New schema requires Alembic; browser dependencies belong in isolated/export environments with pinned compatibility.
- Use current managed/MCP/Agent/approval/trace seams. Model input and page text cannot change authority, proxy/profile or network policy.
- No UI-only security guarantees, silent export stubs or automatic repeats of uncertain external effects. Mock/dry runs remain offline.
- UI work uses shadcn/theme tokens, common Settings/Data/Execution tabs and exact-name delete/revoke/unlink confirmation. Evidence screenshots remain outside Git/CI artifacts.
- Commands below are the declared validation intent. New test filenames are planned and must be created/discovered during implementation; they are not evidence of checks already run.

## Dependencies

- TASK-0251 — Executable Python and project export for browser tools/recipes
- Owner accepts REQ-0086, DES-0004, ARCH-0002/DEC-0085 and PLAN-0006 before promotion to todo/task-start.
- Start from the integration branch after dependencies are merged, or explicitly document an owner-authorised stack.

## Acceptance Criteria

- TypeScript standalone/project browser Agent and recipes execute the same supported local/remote fixture scenarios outside Superstep.
- No credentials, Superstep-only IDs as runtime authority, silent MCP stub or dropped policy/proxy setting appears in output.
- Same-session serialization, stale observation/recovery and unknown effects match the Python/Studio contract despite parallel Agent tool calls.
- Unsupported capabilities fail explicitly; existing non-browser TypeScript/Agent/handoff exports remain compatible.

## Validation Plan

- Planned tests/test_browser_typescript_export.py plus actual Node execution of exported fixture projects and type/syntax checks.
- Regressions tests/test_typescript_export.py, tests/test_project_export.py and tests/test_handoff_exports.py; run shared Python/TypeScript parity cases.
- At implementation: run appropriate declared project checks plus Factory validation/ID checks; each task records review and QA before completion.

## Assumptions

- Owner authorised requirement capture and breakdown only. Technical defaults in the linked artifacts remain proposals until accepted.
- Controlled fixtures and synthetic credentials supply mandatory evidence; real proxy/provider accounts are operator setup.

## Open Questions

- Owner confirmation of the proposed task set is pending; no implementation command is authorised by creation of this backlog artifact.
- Resolve scoped technical capability/contract details from ARCH-0002 within the task; amend the plan rather than claiming unsupported behavior.

## Activity Log

- 2026-11-03: Created by plan-tasks after successful fetch and a fresh `factory ids next TASK --all-refs` allocation. No source changes, branch, dependency installation, execution evidence or PR created.

- 2026-11-04: Renumbered: TASK-0249 → TASK-0252 before publication after a fresh all-ref allocation; owner authorised commit/push only.

- 2026-11-06: Amended for owner clarifications on open draft PR #299 (relaxed mutating-approval defaults; session persistence across chat turns; Browserless required; deferred exports; upload/download + evaluate JS; mandatory origin whitelist; two-layer flexible-but-safe toggles and risk analysis). Status remains backlog; not implementation authorisation. Draft implementation PRs #303–#315 need reconciliation after package acceptance.

## Handoff Notes

- Future branch: `factory/task-0252-browser-typescript-export`, from `develop` after the stated gates.
- One task PR with review/QA; no merge without explicit owner approval.
