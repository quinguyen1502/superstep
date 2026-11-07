# Task

## Metadata

- Project: superstep
- Task ID: TASK-0253
- Title: Studio integrated browser acceptance, example workflow and bilingual handbook
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-03
- Updated: 2026-11-06
- Requirement IDs: REQ-0086
- Design IDs: DES-0004
- Architecture IDs: ARCH-0002, DEC-0085
- Plan: PLAN-0006
- Size: M (provisional; split again before task-start if the reviewed proof exceeds one independently reviewable delivery)

## Objective

Studio first-milestone integrated browser acceptance, example workflow and bilingual handbook (export handbook deferred with TASK-0251/0252), satisfying the studio acceptance criteria of REQ-0086.

## Scope

### In Scope

- Provide a disposable tracking-portal fixture, fake search/proxy/Browserless endpoints and an offline example workflow covering chat/workflow/unknown URL, whitelist denial, multi-turn session and recipe paths.
- Document local and Browserless setup, whitelist, proxy modes/capabilities, safety toggles and risks, profile scope, browser action/approval defaults, unknown outcomes and session idle/max behaviour. **Studio handbook only** for this milestone; executable export setup waits with TASK-0251/0252.
- Run integrated security/permission/UI acceptance and declared project checks for studio; capture review/QA evidence and record residual Browserless limitations. Export parity suites are out of this milestone.

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
- Dependency artifact: `.factory-state/tasks/backlog/TASK-0250-browser-agent-recipe-trace-ui.md`.

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
- Owner accepts the amended REQ-0086, DES-0004, ARCH-0002/DEC-0085 and PLAN-0006 before promotion to todo/task-start.
- TASK-0251 and TASK-0252 are **not** dependencies of this studio milestone.
- Start from the integration branch after dependencies are merged, or explicitly document an owner-authorised stack.

## Acceptance Criteria

- REQ-0086 AC1–AC7, AC9 and studio AC10 map to real fixture/contract/UI evidence, including changed layout, ask-for-context, whitelist denials, Browserless policy failures, multi-turn session idle and cancellation/recovery. AC8/export evidence is explicitly deferred.
- No live account, paid provider, automatic CAPTCHA solving, real external write or production cutover is needed for mandatory automated acceptance (Browserless fixtures may use controlled/fake control APIs).
- Mock remains network-free; screenshots are protected/filtered and evidence stays outside Git. en/vi studio handbook/example/CHANGELOG accurately state supported capabilities, toggle defaults, risks and gaps.
- Every studio delivery task has review/QA and dependency integration evidence; full Factory/project checks pass before the studio milestone is marked complete. Overall REQ-0086 remains incomplete until deferred exports finish. Owner approves any merge/release separately.

## Validation Plan

- Declared full Factory profile, factory validate/ready/ID checks; full backend including layers/envelope/migrations; root npm test/build/lint and targeted browser e2e.
- Actual local/Browserless controlled browser, DNS/proxy/whitelist, permission, crash/approval ON/OFF and multi-turn session suites; studio handbook checks discovered from the current repository. Export parity waits with TASK-0251/0252.
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

- 2026-11-06: Amended for owner clarifications on open draft PR #299 (relaxed mutating-approval defaults; session persistence across chat turns; Browserless required; deferred exports; upload/download + evaluate JS; mandatory origin whitelist; two-layer flexible-but-safe toggles and risk analysis). Status remains backlog; not implementation authorisation. Draft implementation PRs #303–#315 need reconciliation after package acceptance.

## Handoff Notes

- Future branch: `factory/task-0253-browser-e2e-handbook`, from `develop` after the stated gates.
- One task PR with review/QA; no merge without explicit owner approval.

- 2026-11-06: Implementation started on `factory/task-0253-browser-e2e-handbook` stacked after TASK-0250. English-only Studio handbook guide and connection settings doc corrections; screenshots placeholders pending real Studio captures after #315 merges.

- 2026-11-06: Merged #316 (English handbook guide + en/vi parity). English UI screenshots refreshed for connection settings and Agent URL binding. TASK-0251/0252 remain deferred.
- 2026-11-07: TASK-0272 recorded the missing review. Review REV-0257. QA QA-0257. `scripts/check-browser-handbook.py` passed. This does not re-run the original pull-request suite.

