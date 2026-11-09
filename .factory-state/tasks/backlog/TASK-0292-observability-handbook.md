# Task

## Metadata

- Project: superstep
- Task ID: TASK-0292
- Title: Handbook: observability, readiness, Usage page and alerts
- Status: backlog
- Owner: Thái Quí Nguyễn
- Created: 2026-11-09
- Updated: 2026-11-09
- Requirement IDs: REQ-0094
- Design IDs: 
- Architecture IDs: DEC-0094, DEC-0095
- Plan: PLAN-0013
- Size: S

## Objective

Rewrite `operate/observability.md` in en and vi for the new surface.

## Scope

### In Scope

- Sections: liveness versus readiness (and when to point a platform at `/api/ready`), metrics (enable, collector, full metric and label table, cardinality rules), the `observability` Compose profile and Grafana dashboard, the Usage page (who sees it, what cost means, unpriced runs and `STUDIO_PRICES`), the minimum alert list with suggested thresholds, the `tzdata` note for schedules.
- `.env.example` and the configuration reference consistent with the page; nav unchanged unless a new page is needed.
- Real screenshots only (Usage page, Grafana dashboard) captured from a running stack.

### Out Of Scope

- Factory IDs in the handbook; translating unrelated pages.

## Dependencies

- TASK-0291 merged.

## Acceptance Criteria

- en and vi pages have the same structure and facts; strict `zensical build` for en and vi and the image check pass.
- Every metric, label, variable and route named in the page exists in the code.

## Validation Plan

- Strict handbook builds (en, vi), `check_images.py`, `factory validate --only hygiene`, `factory pr check`; REV and QA artifacts.

## Activity Log

- 2026-11-09: Created by planning on branch factory/plan-observability. No implementation.
