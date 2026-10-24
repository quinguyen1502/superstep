# Decision Record

## Metadata

- Project: superstep
- Decision ID: DEC-0057
- Status: Accepted
- Owner: Thái Quí Nguyễn
- Created: 2026-10-24
- Updated: 2026-10-24
- Related Requirements: REQ-0051
- Related Architecture: DEC-0008
- Related Tasks: TASK-0088

## Decision

1. Checkpoints are derived from the stored event log (`node_finished.input` = state before the node; same-state runs in a row = one superstep), so every existing run has them and no table is added.
2. A fork is a new run (LangGraph Studio semantics), using the same `resume = {nodes, state, counts}` entry path as recovery.
3. States truncated in the event log (over the trace cap) are listed but not forkable.
