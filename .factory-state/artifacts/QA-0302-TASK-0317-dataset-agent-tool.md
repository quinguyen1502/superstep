# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0302
- Task ID: TASK-0317
- QA Owner: Codex
- Created: 2026-11-13
- Updated: 2026-11-13
- Outcome: Pass for scoped checks

## Acceptance Criteria Coverage

- Live WebSocket runs returned only the configured column and respected the configured result limit. They rejected attempted writes, a different dataset, unselected output fields, unconfigured filter fields and operators, too many filters, and an overridden row limit.
- A parent grant could not authorize a tool owned by a nested workflow. After the nested workflow's grant was revoked between calls, the first call succeeded and the next one failed.
- The model received the selected rows. The trace and Agent steps retained outcome and count without a copy of the row data. Chrome confirmed the trace detail showed neither the projected value nor an excluded value.
- Playwright configured the tool, selected a return field and allowed operator, set the row limit, saved and ran it. The Dataset node editor regression passed on the same stack.

## Checks Performed

- Root production build and lint passed. Vitest passed 184 frontend, 22 shared React and 106 TypeScript SDK tests.
- The backend Agent, Dataset, layer, validation and API-envelope regression passed 86 tests. Fifteen PostgreSQL variants were skipped.
- Both targeted Chrome specs passed. Light and dark screenshots were reviewed using the local fallback font.

## References

- [Task](../tasks/done/TASK-0317-dataset-agent-tool.md)
- [Review](REV-0302-TASK-0317-dataset-agent-tool.md)
