# Task

## Metadata

- Project: superstep
- Task ID: TASK-0090
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-24
- Updated: 2026-10-24
- Requirement IDs: REQ-0053
- Design IDs: none
- Architecture IDs: DEC-0058

## Objective

Export a workflow as a runnable LangGraph project.

## Scope

### In Scope

- backend/app/engine/project_export.py, services/workflow_service.py, routes/workflows.py; frontend lib/code-export.ts, editor-code-panel.tsx, locales; tests/test_project_export.py, e2e/code-export.spec.ts; scripts/langgraph_dev_smoke.py; handbook guide/python-export.md, reference/api.md (en+vi); CHANGELOG.

### Out Of Scope

- A LangSmith Studio check (no account).
- Deploying to LangSmith from Superstep.

## Dependencies

- None: based on develop.

## Activity Log

- Branch `feat/langgraph-project-export` (PR #128) predates the owner's switch to the factory workflow on 2026-10-24; it keeps its name, and these artifacts were added as a normal commit on it.
- 2026-10-24: implemented, verified with `factory deps apply` and `factory verify run --profile full` plus e2e and handbook builds (QA-0083); PR into develop.
- 2026-10-24: PR #128 merged into develop (b43dea6); moved to done by TASK-0110.

## Handoff Notes

- Review REV-0083, QA-0083.
