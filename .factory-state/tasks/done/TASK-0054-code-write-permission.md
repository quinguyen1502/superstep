# Task

## Metadata

- Project: langgraph-studio
- Task ID: TASK-0054
- Status: done
- Phase: nodes
- Owner: Thái Quí Nguyễn
- Created: 2026-10-19
- Updated: 2026-10-19
- Requirement IDs: REQ-0039
- Design IDs: none (one row in the existing role matrix)
- Architecture IDs: DEC-0041, DEC-0023, DEC-0009

## Objective

Only users with the new `code.write` permission (admins by default) can add a Code node or change its source. This is checked on every path that writes a graph.

## Scope

### In Scope

- `core/permissions.py`: `CODE_WRITE = "code.write"`, in `PERMISSIONS["admin"]` only. The admin role matrix and `Me.permissions` show it.
- `services/access.py`: `require_code_write(old_graph, new_graph, user)`, which compares each Code node's `code` by node id and raises `CODE_WRITE_FORBIDDEN` (403).
- Wired into every path that writes a graph:
  - workflow create and save (`workflow_service.save` / `create`);
  - import;
  - template use and template import;
  - version restore;
  - duplicate (allowed, since the source does not change).
- Error code `CODE_WRITE_FORBIDDEN`, in CATALOG, `docs/api-errors.md` and both locales.
- en and vi strings for the role matrix row.
- pytest for each path, with an editor and an admin.

### Out Of Scope

- The code editor and its read-only state (TASK-0055).
- Granting `code.write` per user or per role in the UI. Permissions stay fixed in code (DEC-0023), so the owner changes `PERMISSIONS` to widen it.

## Inputs

- REQ-0039 Business Rules, DEC-0041 decision 5.
- `core/permissions.py`, `services/access.py`, `services/workflow_service.py`, `services/template_service.py`, `services/import_service.py`, the version restore code, and the admin role matrix in the frontend.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0039-tool-code-mode.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0041-tool-code-mode.md`
- Decisions: DEC-0023, DEC-0041
- Discovery: none
- Clarifications: `.factory-state/artifacts/CLAR-0001-tool-code-mode.md`

## Expected Outputs

- Changes:
  - `core/permissions.py`, `services/access.py` and the graph-writing services;
  - `core/errors.py`, `docs/api-errors.md` and both locales;
  - the role matrix component.
- New: `tests/test_code_permission.py`.

## Implementation Notes

- The rule covers the `code` field only. Moving, renaming or deleting a node, or changing the output field or mode away from `code`, stays allowed.
- Admins keep `workflows.all`, but the check is about the permission, not about workflow access.

## Constraints

- One helper, called from services; no checks inside routers (DEC-0009).
- The API stays plain. The UI only reflects the rule.

## Dependencies

- None. The check is on graph JSON (`mode == "code"` and `code`), so it does not need TASK-0053's runtime.

## Acceptance Criteria

- An editor's save, import, template use or version restore that adds or changes a Code node's source gets `CODE_WRITE_FORBIDDEN` (403) with en and vi text, and nothing is stored.
- The same editor can open, run, move, rename and delete a Code node, and duplicate a workflow that has one.
- An admin can do everything in the list above.
- `/api/me` lists `code.write` for admins only, and the role matrix shows it.

## Validation Plan

- `cd backend && .venv/bin/python -m pytest -q`
- `cd frontend && npx tsc -b && npx vitest run && npx oxlint && npx vite build`

## Assumptions

- Viewers cannot save a workflow, so they need no extra rule.

## Open Questions

- None.

## Activity Log

- 2026-10-19: Created from REQ-0039; not started.
- 2026-10-19: Task set and DEC-0041 approved by the owner ("Approve the task set and DEC-0041").
- 2026-10-19: Started on `factory/task-0054-code-write-permission` (owner: "Do the tasks as one chain: 54, 55, 56").
- 2026-10-19: Implemented: one check in `WorkflowService._write` plus template import. Review REV-0051, QA QA-0051 (pass). PR open; not merged.
- 2026-10-19: Merged in PR #62 (owner: "Merge PR #62, #63, #64 in turn").

## Handoff Notes

- TASK-0055 uses `Me.permissions` to show the code read-only and to hide Test with sample state for users without `code.write`.
