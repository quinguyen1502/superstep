# Task

## Metadata

- Project: superstep
- Task ID: TASK-0133
- Status: review
- Owner: Thái Quí Nguyễn
- Created: 2026-10-26
- Updated: 2026-10-26
- Requirement IDs: REQ-0073
- Design IDs: none
- Architecture IDs: DEC-0066, DEC-0063, DEC-0065

## Objective

Let an Agent node list another saved workflow as a tool: the settings, the parameter schema and result fields, the
snapshot taken when a run is planned, and every validator check, with message codes in en and vi. The tool does not
run yet (TASK-0134).

## Scope

### In Scope

- `engine/agents.py`: `SOURCES` gains `workflow`; settings `workflow_id`, `inputs`, `outputs` (DEC-0066 decision 1);
  `parameters()` from `state_schema` limited to `inputs`.
- Snapshot at planning (decision 2): the expansion that resolves subgraphs also copies each workflow tool's child
  (latest saved version) into `snapshot` and `version` on the expanded copy, recursively, through the same loader
  (`RunService._expand`, `WorkflowService` save validation, `workflow_loader`).
- Cycle and depth checks across subgraphs and workflow tools together (`subgraphs.check` or a shared helper),
  `MAX_DEPTH` 5, on save and on planning.
- Validator: no workflow chosen, a missing or unreadable workflow, an imported (code) workflow, a cycle, too deep,
  an unknown or duplicate field in `inputs` or `outputs`, empty `outputs`. Codes in `engine/issues.py` `MESSAGES`,
  `validation.<CODE>` in `en.json` and `vi.json` (DEC-0065).
- Until TASK-0134 lands, running a workflow tool returns the error result "not available yet" to the model (no new
  public error code).
- `backend/tests/test_agent_workflow_tools.py` (settings, schema, snapshot, validator).

### Out Of Scope

- Running the child (TASK-0134), approvals and runs pages (TASK-0135), the editor (TASK-0136), exports and template
  (TASK-0137), handbook (TASK-0138).

## Inputs

- REQ-0073 (Owner Decisions), DEC-0066, CLAR-0004.
- `engine/agents.py`, `engine/subgraphs.py`, `engine/state_schema.py`, `engine/validator.py`, `engine/issues.py`,
  `services/run_service.py` (`_expand`, `workflow_loader`), `services/workflow_service.py`.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0073-agent-workflow-tools.md`
- Design: none (UI in TASK-0136)
- Architecture: `.factory-state/decisions/DEC-0066-workflow-tools-child-runs.md`
- Decisions: `DEC-0009-layered-backend-sqlalchemy-alembic.md`, `DEC-0063-agent-node-expansion.md`,
  `DEC-0065-validation-message-codes.md`
- Discovery: none
- Clarifications: `.factory-state/artifacts/CLAR-0004-agent-workflow-tools.md`

## Expected Outputs

- A workflow JSON with a workflow tool saves, versions and copies; the validator lists each mistake in the UI
  language; a planned run carries the child snapshot.

## Implementation Notes

- The snapshot lives only in the expanded copy, never in the saved workflow (as subgraph expansion works on a copy).
- Reuse `subgraphs` access rules: the loader returns only workflows the resource owner may read.

## Constraints

- Layers (DEC-0009): the engine sees other workflows only through the loader. No migration in this task.
- English validation text through `Issue` codes; `errors` stays unchanged for API clients.

## Dependencies

- None. Based on develop (after TASK-0132, merged in PR #174).

## Acceptance Criteria

- pytest: `parameters()` of a workflow tool equals the `state_schema` of the chosen input fields; a planned run's
  expanded workflow holds the child snapshot and version, nested two levels.
- Saving A with a tool calling B that calls A (through a tool or a subgraph) fails with the cycle code; six levels
  fail with the depth code; an imported workflow, a missing one and an unknown field each give their code.
- `test_validation_messages.py`, `test_layers.py` and `test_api_envelope.py` pass; vitest locale checks pass.

## Validation Plan

- `cd backend && .venv/bin/python -m pytest -q`; `cd frontend && npm run lint && npx vitest run`;
  `factory verify run --profile full`.

## Assumptions

- A workflow's state fields are its contract, as for MCP tools (REQ-0070).

## Open Questions

- None.

## Activity Log

- 2026-10-26: planned from REQ-0073 (CLAR-0004 answered).
- 2026-10-26: started on `factory/task-0133-workflow-tool-settings` (owner in chat: "Bắt đầu triển khai đi"), from the
  planning branch of PR #175 with develop bfa096f merged in (TASK-0132's `issues.py`). The planning commits ride this
  task's PR if #175 is not merged first. DEC-0066 accepted with the start, as DEC-0063 was.
- 2026-10-26: implemented. `agents.py`: the `workflow` source, `parameters()` from the child's state fields (required),
  settings checks, `snapshot()`, and the expansion keeps the full snapshot on the tool step only (the other steps keep
  the child's state fields). `subgraphs.py`: `tool_refs()`, `all_refs()`, and `check()` follows workflow tools, so
  cycles and depth count both kinds. `RunService._expand` snapshots after subgraph expansion with the version of the
  child. `WorkflowService.dependents` and `children_changed` count workflow tools. Nine codes in `issues.py` and both
  locales. A run that calls a workflow tool gets a failed tool call until TASK-0134.
- 2026-10-26: review fixes before QA. A non-list `inputs` no longer gives one "unknown field" per character, and
  snapshots sent with a workflow are dropped when planning, so only the planner's snapshots can run.

## Validation Results

- See QA-0117.

## Review And QA

- Review: REV-0117. QA: QA-0117.

## Handoff Notes

- TASK-0134 replaces the "cannot run yet" error in `agents.run_tool` with the child run. The tool step's
  `tools[i]["snapshot"]` is the child to run (subgraphs expanded, its own workflow tools snapshotted), and
  `tools[i]["version"]` its version number (None for unsaved edits, as `RunService._version_of` gives).
- Deleting a workflow used as a tool is now refused with WORKFLOW_IN_USE (as for subgraphs), unless forced.
