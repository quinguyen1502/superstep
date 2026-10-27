# Task

## Metadata

- Project: superstep
- Task ID: TASK-0160
- Status: todo
- Owner: Thái Quí Nguyễn
- Created: 2026-10-27
- Updated: 2026-10-27
- Requirement IDs: REQ-0076
- Design IDs: none
- Architecture IDs: DEC-0069, DEC-0063

## Objective

The Python, LangGraph project and TypeScript exports run one round's tool calls concurrently when the Agent setting is on, and one after another when it is off.

## Scope

### In Scope

- `backend/app/engine/python_export.py` (the LangGraph project export shares it) and `backend/app/engine/typescript_export.py`.
- Setting on: a round's calls run together, at most 4 at once, or `STUDIO_AGENT_PARALLEL_TOOLS` when that variable is set in the process that runs the file. Results go back to the model in the model's order.
- Setting off, including an explicit `false`: the calls run one after another. The file does not need the provider flag. The engine's sequential loop is the behaviour.
- A call that fails becomes an error result. The other calls of the round still finish.
- Snapshot tests and the existing run of the exported file (`deno check` and the Python snapshot tests in `backend/tests/test_python_export.py` and `backend/tests/test_typescript_export.py`).

### Out Of Scope

- The studio engine, the cap inside the API process, and the ledger (TASK-0157).
- The editor switch (TASK-0159). A missing field means on, so the export does not wait for the switch.
- Handbook wording and the Support team e2e (TASK-0161).
- `create_react_agent`. DEC-0063 decision 9 still holds.

## Inputs

- DEC-0069 decisions 2, 6 and 10.
- `backend/app/engine/python_export.py`, `typescript_export.py`, `project_export.py`.
- `backend/tests/test_python_export.py`, `backend/tests/test_typescript_export.py`.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0076-parallel-agent-tool-calls.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0069-parallel-agent-tool-calls.md`
- Decisions: `.factory-state/decisions/DEC-0063-agent-node-expansion.md`, `.factory-state/decisions/DEC-0045-python-export.md`, `.factory-state/decisions/DEC-0051-typescript-export.md`, `.factory-state/decisions/DEC-0058-langgraph-project-export.md`
- Discovery: none
- Clarifications: `.factory-state/artifacts/CLAR-0007-parallel-agent-tool-calls.md`

## Expected Outputs

- An exported Agent whose setting is on runs three independent tool calls with overlapping execution and returns the results in the model's order. The same export with the setting off runs them one after another.

## Implementation Notes

- Python may use a thread pool. TypeScript may use a bounded `Promise.all` on chunks of the cap. No new package.
- The cap in the file defaults to 4. Read `STUDIO_AGENT_PARALLEL_TOOLS` when it is a number from 1 to 8. Do not import the studio's `config` module. The exported file runs outside the studio.
- Keep one function per tool call's work, so a failure in one call is caught and turned into that call's tool message. Do not cancel the siblings.
- The project export is the Python writer. One change covers both, and the project snapshot test covers the second.
- Update the generated-shape assertions that name a single `*_tool` node looping to itself, in the Python and TypeScript tests. The handbook samples are TASK-0161.

## Constraints

- The exports must still compile and run: `deno check`, and the Python snapshot tests.
- No new dependency. No studio service imported by the generated file.
- Honour the node setting. Do not run concurrently when it is off.

## Dependencies

- TASK-0157 merged to `develop`, so the setting's default and the sequential-off rule match the engine.

## Acceptance Criteria

- The Python export of an Agent with the setting on, run under the snapshot harness, runs three calls with overlapping start and end times and appends the tool messages in the model's order.
- The same graph with `parallel_tool_calls: false` runs the three calls with no overlap.
- One call raising still leaves the other two results in the conversation, in order.
- The TypeScript export type-checks with `deno check` and the snapshot run shows the same overlap when the setting is on, and no overlap when it is off.
- The LangGraph project export contains the same concurrent tool path as the Python export.
- With `STUDIO_AGENT_PARALLEL_TOOLS=2` in the export's process, the Python snapshot never has three calls in flight.
- `cd backend && .venv/bin/python -m pytest -q backend/tests/test_python_export.py backend/tests/test_typescript_export.py` passes.

## Validation Plan

- `cd backend && .venv/bin/python -m pytest -q backend/tests/test_python_export.py backend/tests/test_typescript_export.py`
- The TypeScript test's existing `deno check` and snapshot run.

## Assumptions

- The exported cap is a copy of the studio default, not a live read of the studio database.
- "Honouring the node setting" is sequential versus concurrent. The provider flag is the studio engine's job (TASK-0157), not the exported file's.

## Open Questions

- None.

## Activity Log

- 2026-10-27: planned from REQ-0076 (DEC-0069). Medium-task workflow.

## Handoff Notes

- Do not start a branch until the owner confirms this set and TASK-0157 has merged. The next skill is `task-start`.
- TASK-0161 updates the handbook samples that quote the generated graph.
