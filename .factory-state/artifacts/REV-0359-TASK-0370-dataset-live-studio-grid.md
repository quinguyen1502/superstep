# Review

## Metadata

- Project: superstep
- Review ID: REV-0359
- Task ID: TASK-0370
- Reviewer: Codex
- Created: 2026-11-22
- Updated: 2026-11-22
- Outcome: Approved for merge

## Review Scope

Reviewed the Studio Rows subscription, authorized snapshot scheduling, pagination and editor behavior against develop at `dad1125f`.

## References

- [Task](../tasks/done/TASK-0370-dataset-live-studio-grid.md)
- [Design](DES-0009-dataset-integrations-and-live-sharing.md)
- [Architecture](ARCH-0005-dataset-integrations-and-live-sharing.md)
- [Predecessor contract](../../docs/backend-architecture.md#dataset-realtime)
- [UI conventions](../../docs/ui-conventions.md)

## Findings

### Blocking

- No blocking findings.

### Non-Blocking

- Rows, group totals and summaries use separate authorized requests. Concurrent commits can land during those reads. The pending revision schedules a follow-up so they converge without an added snapshot API.
- Retaining the loaded extent can require multiple row queries for a grid that has been scrolled through many pages. Unloaded pages are left for ordinary pagination.
- After an accepted subscription loses network connectivity, fallback is a revision check every five seconds while the tab is visible. With a healthy stream, the periodic check is once per minute. Turning back to the tab checks immediately.

## Standards And Design Alignment

The page retains the existing query, theme and grid controls. The footer uses an accessible warning only while updates are delayed. Access loss clears the visible grid and catalog entry and uses the existing missing-Dataset screen. Subscriptions are scoped to the active Rows tab and are closed on unmount or session loss. Both locales cover the new text.

Every re-read uses the shared API client and existing permissioned routes. The grid lets the current snapshot finish and retains the last pending revision. It waits through inline and dialog drafts. Row save still uses the original optimistic revision and conflict recovery. In-flight reads are aborted when the query or Dataset changes, and an authorization failure cancels sibling reads.

## Validation Review

The full Dataset browser selection exposed a catalog fixture with names that differ only by case. The existing selector now uses an exact name. That spec passed alongside the Formula fixture on rerun.

## Review Decision

The owner approved merging PR #430 into develop on 2026-11-22. Require successful checks on the final PR head before integration.
