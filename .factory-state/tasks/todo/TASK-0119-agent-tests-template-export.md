# Task

## Metadata

- Project: superstep
- Task ID: TASK-0119
- Status: todo
- Owner: Thái Quí Nguyễn
- Created: 2026-10-25
- Updated: 2026-10-25
- Requirement IDs: REQ-0072
- Design IDs: none
- Architecture IDs: DEC-0063

## Objective

Make the Agent node testable and exportable: a "tool called" test check, a built-in template with test cases, Python
and LangGraph project export, and a clear TypeScript refusal.

## Scope

### In Scope

- `engine/checks.py`: `{"kind": "tool", "node": <agent id>, "tool": name, "called": true | false}`, read from the
  run's events; the Tests panel check editor gains the kind (en, vi).
- A built-in template (for example "Support agent": the `lookup_order` built-in and a refund-policy knowledge base
  search, a `send_refund` HTTP tool with approval) with test cases that pass with the mock option, including one
  that approves and one that rejects.
- `python_export.py` (shared by `project_export.py`): the agent's four functions and two routers per DEC-0063 with
  `interrupt()` for approval and the existing stubs; the same-path check against the studio's mock run for the
  template; snapshot test.
- `typescript_export.py`: refuse the node with a new error code (catalog, `docs/api-errors.md`, en and vi); the Code
  tab shows the message.

### Out Of Scope

- A TypeScript (LangGraph.js) agent export (CLAR-0003 Q8, later task).

## Inputs

- REQ-0072, DEC-0063 (decision 9), `engine/checks.py`, `engine/python_export.py`, `engine/project_export.py`,
  `engine/typescript_export.py`, `engine/templates.py` / `engine/examples.py`, `components/editor/editor-tests-panel.tsx`.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0072-agent-node.md`, `REQ-0042-workflow-tests.md`,
  `REQ-0043-python-export.md`, `REQ-0047-typescript-export.md`, `REQ-0053-langgraph-project-export.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0063-agent-node-expansion.md`
- Decisions: `DEC-0044-workflow-test-runs.md`
- Discovery: none
- Clarifications: `.factory-state/artifacts/CLAR-0003-agent-node.md`

## Expected Outputs

- The template appears in the template library with passing tests; exporting it gives runnable Python.

## Implementation Notes

- The exported mock must follow the same path as `llm.mock_agent`, so the same-path check holds.

## Constraints

- The exported file stays readable (English comments, one function per step), as REQ-0043 requires.

## Dependencies

- TASK-0116 and TASK-0117 (approval in the template tests).

## Acceptance Criteria

- pytest: the new check passes and fails as expected; the template's test cases pass with the mock; the Python
  export of the template runs and follows the studio's mock path; the project export builds; the TypeScript export
  returns the new error code.
- The Tests panel can add the "tool called" check (vitest or e2e).

## Validation Plan

- `cd backend && .venv/bin/python -m pytest -q`; `cd frontend && npm run build && npm test`;
  `factory verify run --profile full`.

## Assumptions

- Templates and their test cases are defined the way REQ-0042 set up (TASK-0069).

## Open Questions

- None.

## Activity Log

- 2026-10-25: planned from REQ-0072 (CLAR-0003 answered).

## Handoff Notes

- Start after TASK-0117 is merged.
