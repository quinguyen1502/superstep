# Plan

## Metadata

- Project: superstep
- Plan ID: PLAN-0021
- Status: In progress (scope accepted)
- Owner: Thái Quí Nguyễn
- Created: 2026-11-22
- Updated: 2026-11-22
- Related Requirements: REQ-0103
- Related Design: DES-0009
- Related Architecture: ARCH-0005
- Baseline: origin/develop at 848f2351

## Objective

Deliver official Dataset integration clients, then authenticated live grid refresh, then limited anonymous sharing. Each milestone has its own release evidence and can be reviewed independently.

## Context Reviewed

- [Approved scope](REQ-0103-dataset-integrations-and-live-sharing.md), [design](DES-0009-dataset-integrations-and-live-sharing.md), [architecture](ARCH-0005-dataset-integrations-and-live-sharing.md) and [decision](../decisions/DEC-0103-dataset-integration-and-sharing-boundaries.md).
- [Connected export contract](../../docs/dataset-export.md), [Connected adapter task](../tasks/done/TASK-0318-dataset-export-api.md), [Phase 3 deferrals](REQ-0101-datasets-phase-3.md), [existing workflow-history WebSocket](../../backend/app/api/routes/runs_ws.py).
- [Formula and Relation delivery plan](PLAN-0020-dataset-formulas-and-relations.md).

## Work Breakdown

| Milestone | Task | Depends on | Exit check |
| --- | --- | --- | --- |
| 1. OpenAPI and SDK | [TASK-0367 — Connected v1 OpenAPI](../tasks/done/TASK-0367-dataset-connected-openapi.md) | Existing Connected API | Typed six-operation contract, generated spec sync, and compatible deployed exporters |
| 1. OpenAPI and SDK | [TASK-0368 — Python and TypeScript SDKs](../tasks/done/TASK-0368-dataset-python-typescript-sdk.md) | TASK-0367 | Both clients pass live read/write, scope, retry and drift scenarios |
| 2. Studio realtime | [TASK-0369 — Commit signals and resync](../tasks/done/TASK-0369-dataset-live-invalidations.md) | Milestone 1 | Database revision and authorized push cover every changed writer on SQLite and PostgreSQL, including Redis across processes |
| 2. Studio realtime | [TASK-0370 — Studio query refresh](../tasks/backlog/TASK-0370-dataset-live-studio-grid.md) | TASK-0369 | Two browser sessions see the same rows and summaries after writes and reconnect. An editor keeps its draft |
| 3. Public link | [TASK-0371 — Share authorization and projection](../tasks/backlog/TASK-0371-dataset-public-share-api.md) | Milestone 2 | Server projection and filter apply to every anonymous read. Revocation, rotation and schema drift fail closed |
| 3. Public link | [TASK-0372 — Access controls and public viewer](../tasks/backlog/TASK-0372-dataset-public-share-studio.md) | TASK-0371 | Manager preview matches a logged-out viewer, including narrow screens and both themes |

## Delivery

1. Start with TASK-0367 when implementation is requested. Each task uses one PR on develop after its predecessor integrates, or an explicitly tracked stack. Promote pending tasks when their dependencies and interfaces are ready. Run each task's focused tests and record code review and QA.
2. Sequence changes to migration heads and shared write paths with PLAN-0020. The Connected spec can start from the current API, including the currently gated Formula metadata. Add future Relation capabilities only after the Relation API and authorization contract is available.
3. Document setup and errors, realtime editing behavior, and the public link flow in the English and Vietnamese handbook alongside their milestones. Run an integrated demo with a private tickets dataset, a bound SDK client, two Studio sessions, and an anonymous view of selected columns and filtered rows.
4. Gate integration through per-PR owner approval and CI. Package publication or enabling public sharing in a deployed instance is a separate release or operator action.

## Risks And Recovery

| Risk | Validation or recovery |
| --- | --- |
| OpenAPI disagrees with the Connected handler or an SDK duplicates a write | Verify the generated spec against the running API, test legacy export bodies, and retry with the same operation ID |
| A missed push, burst or background tab shows stale or jumping data | Persist revision with commits, test return-to-tab and reconnect, coalesce reads and retain view/draft state |
| A client discovers hidden data through public search, metadata or paging | Project and filter in the query, exercise forged requests, and fail closed on revision or authority loss |
| Migration or shared writer conflicts with Formula or Relation work | Recheck Alembic and writer changes when a task starts, land migrations in order and test upgrade on both databases |

## Completion Criteria

All REQ-0103 scenarios pass with review and QA on develop. The public spec, both SDKs, Studio realtime, and limited public viewer have documented migration and rollback behavior. Record completion evidence after the final milestone.
