# Task

## Metadata

- Project: superstep
- Task ID: TASK-0307
- Title: SLO targets and burn-rate alerts
- Status: todo
- Owner: Thái Quí Nguyễn
- Created: 2026-11-10
- Updated: 2026-11-12
- Requirement IDs: REQ-0095
- Design IDs: DES-0006
- Architecture IDs: DEC-0094, DEC-0095
- Plan: PLAN-0014
- Phase: 3
- Size: M

## Objective

Turn the MVP health signals into explicit service level objectives with error budgets.

## Owner-Facing Outcome

Operators get fast and slow burn-rate alerts in Grafana for run success and API availability, and Settings, Usage shows each SLO target, the measured value and the error budget left in the window.

## Scope

### In Scope

- Two SLOs with configurable targets (for example `STUDIO_SLO_RUN_SUCCESS`, `STUDIO_SLO_API_AVAILABILITY`; defaults proposed in the task PR for owner approval): run success from `studio.runs` (ok over finished, cancelled excluded) and API availability from `studio.http.server.requests` (non-5xx over total, probes excluded).
- Grafana recording rules and multi-window burn-rate alerts (fast: 1 h and 5 min windows; slow: 6 h and 30 min) using existing metrics only.
- Usage page SLO card computed in SQL from `runs` for run success; API availability shown as a link to Grafana when `STUDIO_GRAFANA_URL` is set (the database does not record HTTP requests).
- Handbook section (en and vi) on reading burn rates.

### Out Of Scope

- Paging integrations beyond Grafana contact points.
- New metrics.

## Dependencies

- TASK-0305 merged (phase 2 complete), so dashboards and alerts are in their final layout.

## Acceptance Criteria

- Recording and alert rules load in Grafana provisioning; a synthetic error burst in a test Prometheus dataset or a documented manual check triggers the fast alert.
- The Usage SLO card matches a hand-computed success rate on seeded runs.
- Targets outside 0 to 1 are rejected at start-up with a clear log message.

## Validation Plan

- Targeted backend tests (`pytest`) and, where the frontend is touched, `npm run lint`, `npm run build`, `npm test` and the matching Playwright spec.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts; all required CI including the three E2E shards green before merge.

## Open Questions

- Which default targets? Recommended: 99 percent run success, 99.5 percent API availability, 30-day window.

## Activity Log

- 2026-11-10: Created by planning on branch factory/plan-observability-next. No implementation. Stays in backlog until the owner accepts REQ-0095 and PLAN-0014.
- 2026-11-12: Moved from backlog to todo after the Phase 2 stack merged. Owner approved starting Phase 3 on 2026-11-11.

## Handoff Notes

- Use branch `factory/task-0307-slo-burn` from `develop` when implementation begins.
