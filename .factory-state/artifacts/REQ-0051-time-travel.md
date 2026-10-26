# Requirement

## Metadata

- Project: superstep
- Requirement ID: REQ-0051
- Status: Done (TASK-0088, PR #133)
- Owner: Thái Quí Nguyễn
- Created: 2026-10-24
- Updated: 2026-10-24
- Source: owner request in chat, 2026-10-24 (item 4 of 5: time travel / fork from a checkpoint in the Run panel).

## Summary

- List a finished run's checkpoints, inspect and edit a state, and fork a new run from it, from the Run panel.

## Acceptance Criteria

- `GET /api/runs/{run_id}/checkpoints` lists one checkpoint per superstep (nodes that ran next, the state before them, iteration counts) and the final state; visible to the run owner, the workflow owner and admins.
- A `{"fork": {run_id, checkpoint, state?}}` request on `/ws/run` starts a new run at those nodes with that (optionally edited) state, on the original run's stored version; `run_started.forked_from` records the origin; the original run is unchanged.
- Run panel: **Time travel** dialog (checkpoint list, JSON state editor, Edited badge, Reset, Fork from here) and a "Forked from" line on the forked run.
- Errors `CHECKPOINT_NOT_FOUND`, `RUN_FORK_UNSUPPORTED` (catalog, docs, both locales). Unit, vitest, e2e; handbook en+vi; CHANGELOG.

## Out Of Scope

- Forking imported LangGraph graphs, waiting or running runs, and the final state.
- A persistent checkpoint store (events are the source).
