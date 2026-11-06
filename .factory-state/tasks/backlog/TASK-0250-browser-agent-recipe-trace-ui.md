# Task

## Metadata

- Project: superstep
- Task ID: TASK-0250
- Title: Agent/recipe configuration and filtered browser trace/chat UI
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

Agent/recipe configuration and filtered browser trace/chat UI, satisfying the assigned acceptance criteria of REQ-0086.

## Scope

### In Scope

- Add browser tool grants for all nine operations, per-argument sources and recipe settings in existing Agent/MCP config; preserve Settings/Data/Execution tabs. Ungranted tools are not advertised. Builder cannot edit connection whitelist or always-on network rules from the node form.
- Extend existing run trace and chat presentation for ordered actions, bounded observations, protected screenshots (filtered from public chat by default), missing input, whitelist denial, approval (when mutating approval ON), challenge, idle/expired and unknown states. Show cross-turn session continuity only to authorised builder/operator views.
- Explain provider/proxy/whitelist/session state without debug endpoints, secret URLs or unrestricted page/form content; reuse shared React presentation when applicable.

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
- Dependency artifact: `.factory-state/tasks/backlog/TASK-0249-browser-connection-settings-ui.md`.

## Expected Outputs

- Editor/recipe controls, filtered trace/chat states, locale/docs snippets and UI evidence.

## Implementation Notes And Constraints

- Preserve router/service/repository/engine boundaries, shared error envelope/catalog and en/vi key parity. New schema requires Alembic; browser dependencies belong in isolated/export environments with pinned compatibility.
- Use current managed/MCP/Agent/approval/trace seams. Model input and page text cannot change authority, proxy/profile or network policy.
- No UI-only security guarantees, silent export stubs or automatic repeats of uncertain external effects. Mock/dry runs remain offline.
- UI work uses shadcn/theme tokens, common Settings/Data/Execution tabs and exact-name delete/revoke/unlink confirmation. Evidence screenshots remain outside Git/CI artifacts.
- Commands below are the declared validation intent. New test filenames are planned and must be created/discovered during implementation; they are not evidence of checks already run.

## Dependencies

- TASK-0247 — Dynamic URL bindings, search/fetch and missing-context flows
- TASK-0248 — Reusable typed browser recipes through existing tool surfaces
- TASK-0249 — Connection, proxy and profile configuration UI
- Owner accepts REQ-0086, DES-0004, ARCH-0002/DEC-0085 and PLAN-0006 before promotion to todo/task-start.
- Start from the integration branch after dependencies are merged, or explicitly document an owner-authorised stack.

## Acceptance Criteria

- No Browser-specific canvas node/tab taxonomy or second Agent/model control is introduced. Data/execution fields live in their conventional tabs.
- URL-from-chat, workflow binding, search-first, ask-for-context, tool grants and recipe invocation can be configured and inspected with current surfaces.
- Public chat sees only permitted safe results/approval context; no raw session handles, remote endpoints, cookies, secret queries or private screenshots leak (screenshots filtered by default).
- Keyboard/mobile/en/vi/light/dark state matrix and existing trace alignment/parallel-tool presentation remain correct.

## Validation Plan

- Frontend/React presentation tests, root npm test/build/lint; planned browser-agent-tools.spec.ts, browser-recipes.spec.ts and browser-trace.spec.ts.
- Exercise approval allowed/rejected/expired, session loss, unknown outcome and public-output filtering; use local fixtures and synthetic identities.
- At implementation: run appropriate declared project checks plus Factory validation/ID checks; each task records review and QA before completion.

## Assumptions

- Owner authorised requirement capture and breakdown only. Technical defaults in the linked artifacts remain proposals until accepted.
- Controlled fixtures and synthetic credentials supply mandatory evidence; real proxy/provider accounts are operator setup.

## Open Questions

- Owner confirmation of the proposed task set is pending; no implementation command is authorised by creation of this backlog artifact.
- Resolve scoped technical capability/contract details from ARCH-0002 within the task; amend the plan rather than claiming unsupported behavior.

## Activity Log

- 2026-11-03: Created by plan-tasks after successful fetch and a fresh `factory ids next TASK --all-refs` allocation. No source changes, branch, dependency installation, execution evidence or PR created.

- 2026-11-04: Renumbered: TASK-0247 → TASK-0250 before publication after a fresh all-ref allocation; owner authorised commit/push only.

- 2026-11-06: Amended for owner clarifications on open draft PR #299 (relaxed mutating-approval defaults; session persistence across chat turns; Browserless required; deferred exports; upload/download + evaluate JS; mandatory origin whitelist; two-layer flexible-but-safe toggles and risk analysis). Status remains backlog; not implementation authorisation. Draft implementation PRs #303–#315 need reconciliation after package acceptance.

## Handoff Notes

- Future branch: `factory/task-0250-browser-agent-recipe-trace-ui`, from `develop` after the stated gates.
- One task PR with review/QA; no merge without explicit owner approval.
