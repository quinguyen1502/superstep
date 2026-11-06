# Task

## Metadata

- Project: superstep
- Task ID: TASK-0253
- Title: Integrated browser acceptance, example workflow and bilingual handbook
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

Integrated browser acceptance, example workflow and bilingual handbook, satisfying the assigned acceptance criteria of REQ-0086.

## Scope

### In Scope

- Provide a disposable tracking-portal fixture, fake search/proxy/remote endpoints and an offline example workflow covering chat/workflow/unknown URL and recipe paths.
- Document local/remote setup, proxy modes/capabilities, profile scope, browser action/approval limits, unknown outcomes, session expiry and executable export setup.
- Run integrated security/permission/export/UI acceptance and declared project checks; capture review/QA evidence and record residual provider limitations.

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
- Dependency artifact: `.factory-state/tasks/backlog/TASK-0250-browser-agent-recipe-trace-ui.md`.
- Dependency artifact: `.factory-state/tasks/backlog/TASK-0251-browser-python-export.md`.
- Dependency artifact: `.factory-state/tasks/backlog/TASK-0252-browser-typescript-export.md`.

## Expected Outputs

- Example/template/fixtures, en/vi handbook, integrated traceability/evidence and completion handoff.

## Implementation Notes And Constraints

- Preserve router/service/repository/engine boundaries, shared error envelope/catalog and en/vi key parity. New schema requires Alembic; browser dependencies belong in isolated/export environments with pinned compatibility.
- Use current managed/MCP/Agent/approval/trace seams. Model input and page text cannot change authority, proxy/profile or network policy.
- No UI-only security guarantees, silent export stubs or automatic repeats of uncertain external effects. Mock/dry runs remain offline.
- UI work uses shadcn/theme tokens, common Settings/Data/Execution tabs and exact-name delete/revoke/unlink confirmation. Evidence screenshots remain outside Git/CI artifacts.
- Commands below are the declared validation intent. New test filenames are planned and must be created/discovered during implementation; they are not evidence of checks already run.

## Dependencies

- TASK-0250 — Agent/recipe configuration and filtered browser trace/chat UI
- TASK-0251 — Executable Python and project export for browser tools/recipes
- TASK-0252 — Executable TypeScript and project export with browser parity
- Owner accepts REQ-0086, DES-0004, ARCH-0002/DEC-0085 and PLAN-0006 before promotion to todo/task-start.
- Start from the integration branch after dependencies are merged, or explicitly document an owner-authorised stack.

## Acceptance Criteria

- REQ-0086 AC1–AC10 map to real fixture/contract/export/UI evidence, including changed layout, ask-for-context, proxy policy failures and cancellation/recovery.
- No live account, paid provider, automatic CAPTCHA solving, real external write or production cutover is needed for mandatory automated acceptance.
- Mock remains network-free; screenshots are protected/filtered and evidence stays outside Git. en/vi handbook/example/CHANGELOG accurately state supported capabilities and gaps.
- Every delivery task has review/QA and dependency integration evidence; full Factory/project checks pass before the requirement is marked complete. Owner approves any merge/release separately.

## Validation Plan

- Declared full Factory profile, factory validate/ready/ID checks; full backend including layers/envelope/migrations; root npm test/build/lint and targeted browser e2e.
- Actual local/remote controlled browser, DNS/proxy, permission, crash/approval and Python/TypeScript export parity suites; handbook checks discovered from the current repository.
- At implementation: run appropriate declared project checks plus Factory validation/ID checks; each task records review and QA before completion.

## Assumptions

- Owner authorised requirement capture and breakdown only. Technical defaults in the linked artifacts remain proposals until accepted.
- Controlled fixtures and synthetic credentials supply mandatory evidence; real proxy/provider accounts are operator setup.

## Open Questions

- Owner confirmation of the proposed task set is pending; no implementation command is authorised by creation of this backlog artifact.
- Resolve scoped technical capability/contract details from ARCH-0002 within the task; amend the plan rather than claiming unsupported behavior.

## Activity Log

- 2026-11-03: Created by plan-tasks after successful fetch and a fresh `factory ids next TASK --all-refs` allocation. No source changes, branch, dependency installation, execution evidence or PR created.

- 2026-11-04: Renumbered: TASK-0250 → TASK-0253 before publication after a fresh all-ref allocation; owner authorised commit/push only.

## Handoff Notes

- Future branch: `factory/task-0253-browser-e2e-handbook`, from `develop` after the stated gates.
- One task PR with review/QA; no merge without explicit owner approval.
