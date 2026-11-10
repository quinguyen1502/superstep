# Task

## Metadata

- Project: superstep
- Task ID: TASK-0305
- Title: Observability handbook and dashboard pass for phase 2
- Status: todo
- Owner: Thái Quí Nguyễn
- Created: 2026-11-10
- Updated: 2026-11-10
- Requirement IDs: REQ-0095
- Design IDs: 
- Architecture IDs: DEC-0094, DEC-0095
- Plan: PLAN-0014
- Phase: 2
- Size: S

## Objective

Bring the operator documentation and the starter dashboard in line with everything phase 2 added.

## Owner-Facing Outcome

The handbook observability page (en and vi) explains JSON logs and correlation, the new spans, database and Redis panels, model latency, embedding usage, activity and rate-limit counters, the usage table and the new Usage page tables, and the dashboard groups the new panels in clear rows.

## Scope

### In Scope

- `handbook/docs/{en,vi}/operate/observability.md` and the configuration reference updated together; real screenshots only if captured.
- Dashboard rows reordered and titled; alert list in the handbook matches the provisioned rules.
- Deploy templates stay on `/api/health` (DEC-0095); the page keeps explaining how an operator can switch to `/api/ready`.

### Out Of Scope

- Republishing the github.io handbook (happens with the next `main` release).
- Changing deploy template health checks.

## Dependencies

- TASK-0294 to TASK-0304 merged (or this task documents only what has merged and lists the rest).

## Acceptance Criteria

- Strict en and vi handbook builds pass; every metric and variable named in the handbook exists on `develop`.
- Alert list on the page equals the provisioned alert rules (scripted check or review checklist).

## Validation Plan

- Targeted backend tests (`pytest`) and, where the frontend is touched, `npm run lint`, `npm run build`, `npm test` and the matching Playwright spec.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts; all required CI including the three E2E shards green before merge.

## Open Questions

- None

## Activity Log

- 2026-11-10: Created by planning on branch factory/plan-observability-next. No implementation. Stays in backlog until the owner accepts REQ-0095 and PLAN-0014.
- 2026-11-10: Owner accepted REQ-0095 and PLAN-0014 (pt280u, "go ahead with phase 2"). Moved from backlog to todo.

## Handoff Notes

- Use branch `factory/task-0305-phase2-handbook-dashboard` from `develop` when implementation begins.
