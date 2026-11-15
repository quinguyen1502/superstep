# Decision Record

## Metadata

- Project: superstep
- Decision ID: DEC-0096
- Status: Accepted
- Owner: Thái Quí Nguyễn
- Created: 2026-11-12
- Updated: 2026-11-12
- Related Requirements: REQ-0095
- Related Plan: PLAN-0014
- Related Tasks: TASK-0306

## Context

Phase 3 adds monthly cost budgets for individual users and teams. Budget enforcement requires an owner decision before implementation.

## Decision

Monthly budgets send warnings at 80 percent and 100 percent. Each threshold sends one notification per budget per calendar month. Runs can start and continue at every spend level.

## Rationale

Warnings let administrators and teams see when spending crosses a threshold while keeping workflow execution available. The existing notification service delivers the warnings.

## Alternatives Considered

Blocking new runs at 100 percent would cap new execution after the threshold. It would require consistent admission checks across all run entry points and could interrupt scheduled and interactive workflows. The owner selected warnings only.

## Impacts

- The Usage page shows month-to-date priced spend alongside unpriced usage.
- Budget thresholds are advisory and can be exceeded.
- Threshold notifications use the existing notification service.

## Approval

- Approved By: Thái Quí Nguyễn
- Approved On: 2026-11-11 (Asia/Ho_Chi_Minh)
- Scope And Limits: Warnings at 80 percent and 100 percent for TASK-0306. Run admission remains independent of budget state.

## Review Or Revisit Trigger

Revisit when the owner requests budget enforcement or changes to notification thresholds.
