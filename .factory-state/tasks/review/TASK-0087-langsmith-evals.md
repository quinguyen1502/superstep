# Task

## Metadata

- Project: superstep
- Task ID: TASK-0087
- Status: review (PR)
- Owner: Thái Quí Nguyễn
- Created: 2026-10-24
- Updated: 2026-10-24
- Requirement IDs: REQ-0050
- Design IDs: none
- Architecture IDs: DEC-0056

## Objective

LangSmith evals and trace links.

## Scope

### In Scope

- backend/app/services/langsmith.py, migration 0037, models run/workflow_test, repositories/workflow_tests, services/{workflow_test_service,run_worker,run_service,telemetry,trigger_service,agent_server_service}, routes users/workflow_tests, schemas/rbac, deps; frontend UsersSection LangSmith card, editor-tests-panel; locales; e2e phase3 card test; handbook run/tests, operate/observability, reference/api (en+vi).

### Out Of Scope

- A real LangSmith account check (none available).
- Per-team settings (one studio-wide admin setting).

## Dependencies

- Stacked on #129 (`feat/agent-server-api`): migration 0037 chains after 0036_agent_threads.

## Activity Log

- 2026-10-24: implemented, verified with `factory deps apply` and `factory verify run --profile full` plus e2e and handbook builds (QA-0080); PR into develop.

## Handoff Notes

- Review REV-0080, QA-0080.
