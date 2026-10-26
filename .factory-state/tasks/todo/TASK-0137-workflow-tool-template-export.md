# Task

## Metadata

- Project: superstep
- Task ID: TASK-0137
- Status: todo
- Owner: Thái Quí Nguyễn
- Created: 2026-10-26
- Updated: 2026-10-26
- Requirement IDs: REQ-0073, REQ-0042, REQ-0043, REQ-0047
- Design IDs: none
- Architecture IDs: DEC-0066, DEC-0063, DEC-0044

## Objective

Make workflow tools work in workflow tests, ship a "Support team" template, and support workflow tools in the Python,
LangGraph project and TypeScript exports (DEC-0066 decision 9).

## Scope

### In Scope

- Workflow tests (REQ-0042): the "tool called" check works for workflow tools; a test run's children run with the
  test-run rules and the mock.
- Template "Support team": a supervisor Agent with two specialist workflows ("Order desk", "Refund desk", the latter
  with an approval tool) created with it, and test cases that pass with the mock; template setup hints (TASK-0126).
- Exports: each child as its own compiled graph in the same file, written once; the tool function invokes it and
  returns the output fields; interrupts in a child pause the parent. Python (`python_export.py`), the LangGraph
  project (`project_export.py`) and TypeScript (`typescript_export.py`).
- Tests: the same-path test (the export and the studio take the same path through the supervisor with the mock),
  `py_compile`, `deno check`.

### Out Of Scope

- Handbook (TASK-0138).

## Inputs

- TASK-0133 snapshot (the exports read the child from it), TASK-0134 runs.
- `engine/python_export.py`, `engine/typescript_export.py`, `engine/project_export.py`, `engine/checks.py`,
  `engine/templates.py`, `services/template_service.py`, `services/workflow_test_service.py`.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0073-agent-workflow-tools.md`, `REQ-0042-workflow-tests.md`,
  `REQ-0043-python-export.md`, `REQ-0047-typescript-export.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0066-workflow-tools-child-runs.md`
- Decisions: `DEC-0044-workflow-test-runs.md`, `DEC-0063-agent-node-expansion.md`
- Discovery: none
- Clarifications: `.factory-state/artifacts/CLAR-0004-agent-workflow-tools.md`

## Expected Outputs

- The template runs offline and its tests pass; the three exports of it compile and follow the same path.

## Implementation Notes

- A template that needs other workflows creates them with it (as the template gallery creates one workflow today);
  the tools point to the new ids.

## Constraints

- No new dependency in the exports beyond LangGraph and LangGraph.js already used.

## Dependencies

- TASK-0134.

## Acceptance Criteria

- pytest: the template's test cases pass with the mock; the "tool called" check passes and fails as expected for a
  workflow tool.
- The Python and project exports pass `py_compile` and the same-path test; the TypeScript export passes `deno check`
  and the same-path test.

## Validation Plan

- Backend pytest (export and template suites, then the full suite); `factory verify run --profile full`.

## Assumptions

- None.

## Open Questions

- None.

## Activity Log

- 2026-10-26: planned from REQ-0073 (CLAR-0004 answered).

## Handoff Notes

-
