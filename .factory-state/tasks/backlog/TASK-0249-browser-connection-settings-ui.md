# Task

## Metadata

- Project: superstep
- Task ID: TASK-0249
- Title: Connection, whitelist, proxy, toggles and profile configuration UI
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

Connection, required whitelist, proxy, safety toggles and profile configuration UI, satisfying the assigned acceptance criteria of REQ-0086.

## Scope

### In Scope

- Extend existing Settings managed connection forms for browser provider (local and Browserless), **required origin/domain whitelist editor**, Network / Proxy, safety toggles (mutating approval default OFF; allow JS/upload/download; download limits; session idle/max; action/page budget), secret hints, profile and lifecycle/resource settings. List always-on rules as non-disableable help text.
- Show direct/operator-default/custom proxy modes and provider-dependent capabilities; no single fixed workflow URL in connection setup; empty whitelist cannot be saved.
- Place short risk hints beside mutating-approval, JS, upload and download toggles (see DEC-0085 risk table).
- Use shared delete/revoke/unlink dialogs, API/i18n helpers and shadcn components; make setup errors and secret edit/keep behavior accessible.

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
- Dependency artifact: `.factory-state/tasks/backlog/TASK-0242-browser-egress-proxy-policy.md`.
- Dependency artifact: `.factory-state/tasks/backlog/TASK-0244-browser-remote-profiles.md`.

## Expected Outputs

- Existing-surface Settings UI, en/vi strings/help and accessibility/visual evidence.

## Implementation Notes And Constraints

- Preserve router/service/repository/engine boundaries, shared error envelope/catalog and en/vi key parity. New schema requires Alembic; browser dependencies belong in isolated/export environments with pinned compatibility.
- Use current managed/MCP/Agent/approval/trace seams. Model input and page text cannot change authority, proxy/profile or network policy.
- No UI-only security guarantees, silent export stubs or automatic repeats of uncertain external effects. Mock/dry runs remain offline.
- UI work uses shadcn/theme tokens, common Settings/Data/Execution tabs and exact-name delete/revoke/unlink confirmation. Evidence screenshots remain outside Git/CI artifacts.
- Commands below are the declared validation intent. New test filenames are planned and must be created/discovered during implementation; they are not evidence of checks already run.

## Dependencies

- TASK-0241 — Browser contracts and scoped connection metadata
- TASK-0242 — Enforce browser egress and connection-level proxy policy
- TASK-0244 — Remote browser capabilities and origin-scoped login profiles
- Owner accepts REQ-0086, DES-0004, ARCH-0002/DEC-0085 and PLAN-0006 before promotion to todo/task-start.
- Start from the integration branch after dependencies are merged, or explicitly document an owner-authorised stack.

## Acceptance Criteria

- Operator can configure/discover local and Browserless connections with a non-empty whitelist and safety toggles without exposing or re-entering stored secrets.
- Proxy and whitelist config live on the connection, stay stable per session and explicitly distinguish browser networking from separate Search/Fetch tools.
- Unsupported provider/proxy/whitelist combinations fail with a useful translated field error; public visitors cannot access configuration or secret hints.
- Keyboard/narrow layout/theme/locale behavior and typed-name connection/profile deletion satisfy docs/ui-conventions.md; en/vi risk/toggle copy is present.

## Validation Plan

- Frontend unit/locale/API error tests, root npm test/build/lint and planned browser-connections.spec.ts.
- Browser evidence covers create/edit/discover/whitelist/proxy/toggles/profile/policy/failure/delete in en/vi and light/dark. Keep evidence outside Git/under CI artifacts.
- At implementation: run appropriate declared project checks plus Factory validation/ID checks; each task records review and QA before completion.

## Assumptions

- Owner authorised requirement capture and breakdown only. Technical defaults in the linked artifacts remain proposals until accepted.
- Controlled fixtures and synthetic credentials supply mandatory evidence; real proxy/provider accounts are operator setup.

## Open Questions

- Owner confirmation of the proposed task set is pending; no implementation command is authorised by creation of this backlog artifact.
- Resolve scoped technical capability/contract details from ARCH-0002 within the task; amend the plan rather than claiming unsupported behavior.

## Activity Log

- 2026-11-03: Created by plan-tasks after successful fetch and a fresh `factory ids next TASK --all-refs` allocation. No source changes, branch, dependency installation, execution evidence or PR created.

- 2026-11-04: Renumbered: TASK-0246 → TASK-0249 before publication after a fresh all-ref allocation; owner authorised commit/push only.

- 2026-11-06: Amended for owner clarifications on open draft PR #299 (relaxed mutating-approval defaults; session persistence across chat turns; Browserless required; deferred exports; upload/download + evaluate JS; mandatory origin whitelist; two-layer flexible-but-safe toggles and risk analysis). Status remains backlog; not implementation authorisation. Draft implementation PRs #303–#315 need reconciliation after package acceptance.

## Handoff Notes

- Future branch: `factory/task-0249-browser-connection-settings-ui`, from `develop` after the stated gates.
- One task PR with review/QA; no merge without explicit owner approval.
