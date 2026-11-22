# Task

## Metadata

- Project: superstep
- Task ID: TASK-0370
- Title: Refresh the Studio Dataset grid on live changes
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-22
- Updated: 2026-11-22
- Requirement IDs: REQ-0103
- Design IDs: DES-0009
- Architecture IDs: ARCH-0005

## Objective

Refresh the open view automatically while retaining the current view and unsaved input.

## Scope

Connect the authenticated Rows tab to the invalidation feed, coalesce signals, resync on reconnect or tab focus, and use a lightweight revision check during degraded delivery. Route refreshes through the existing Rows, grouping and summary requests.

## Inputs

- Dataset live WebSocket and revision contract, DatasetGrid pagination/grouping/summary behavior, and Workflow Studio connection logic.

## Related Artifacts

- [Requirement](../../artifacts/REQ-0103-dataset-integrations-and-live-sharing.md)
- [Design](../../artifacts/DES-0009-dataset-integrations-and-live-sharing.md)
- [Architecture](../../artifacts/ARCH-0005-dataset-integrations-and-live-sharing.md)
- [Decision](../../decisions/DEC-0103-dataset-integration-and-sharing-boundaries.md)
- [Delivery plan](../../artifacts/PLAN-0021-dataset-integrations-and-live-sharing.md)
- [Review](../../artifacts/REV-0359-TASK-0370-dataset-live-studio-grid.md)
- [QA](../../artifacts/QA-0359-TASK-0370-dataset-live-studio-grid.md)

## Expected Outputs

Studio subscription, refresh scheduling, localized delayed/offline and access-loss state, handbook updates, and two-session Playwright coverage.

## Implementation Notes

Open the stream before the first authoritative snapshot and merge a pending invalidation while a query is in flight. Preserve filters, sorts, grouping, scroll and selected cell where it still exists. While an edit is active queue changes and keep the draft. Use the existing row revision conflict behavior on save.

## Constraints

- Follow the existing backend layers, permission checks, API envelope and error catalog. Use EN/VI locale parity, shared UI components and theme tokens where applicable.
- Review and QA precede approval to merge into develop. Recheck shared Dataset schema and export changes from PLAN-0020 at task start.

## Dependencies

- [TASK-0369](../done/TASK-0369-dataset-live-invalidations.md). Start after this dependency integrates, or document an approved stack.

## Acceptance Criteria

- A second session sees an update made by another Studio client, CSV import, workflow or Connected client without reloading the page. Rows, group totals and summaries converge to the same committed state.
- Pending notifications coalesce. Reconnect, tab refocus and missed-event fallback converge without resetting the active query or dropping a draft. A conflicting row update stays visible as the existing conflict after a save attempt.
- Access removal closes the subscription and removes inaccessible data from the open Studio view. The feature is exercised with mouse, keyboard and existing narrow grid modes.

## Validation Plan

Run Playwright with two browser sessions covering a burst, group or summary, same-row edit conflict, a disconnected writer and a revoked viewer. Run grid regression, locale parity, lint and production build. Run the applicable repository and Factory checks and record review and QA evidence on the task PR.

## Assumptions

Use the v1 scope of REQ-0103 and the proposed interfaces in ARCH-0005.

## Open Questions

None blocking. The predecessor contract is integrated into develop at `dad1125f`.

## Activity Log

- 2026-11-22: Planned from the owner-approved scope and sequence.
- 2026-11-22: Started from develop at `dad1125f` after PR #429 merged. Factory ready passed. Formula runs on migration 0072, the live revision is on 0073, and Relation remains tracked separately. The open Rows grid will reconcile active reads and defer refresh while an editor has a draft.
- 2026-11-22: Implemented authorized snapshot refresh, draft deferral, focus and scroll continuity, reconnect and fallback, and access-loss cleanup. The three new browser cases, frontend checks and focused backend checks passed. Moved to review with REV-0359 and QA-0359.
- 2026-11-22: The owner approved merging PR #430 into develop. All 25 runnable checks passed on reviewed head `d6fd32f8`, including all Playwright shards, the bilingual handbook, PostgreSQL 17 and Redis 7. Integration remains gated on checks for the final head.
- 2026-11-22: The final-head Playwright shard exposed a timing assumption in the grouped-refresh count. The scenario now waits for the latest committed revision to reach the actual socket and finish coalescing while the draft is open. Product source remains as reviewed.

## Handoff Notes

Start TASK-0371 from develop after PR #430 merges.
