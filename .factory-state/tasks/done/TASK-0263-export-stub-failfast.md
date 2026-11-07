# Task

## Metadata

- Project: superstep
- Task ID: TASK-0263
- Title: Export: service stubs fail fast in live runs; missing targets fail when reached
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-07
- Updated: 2026-11-07
- Requirement IDs: REQ-0088
- Architecture IDs: DEC-0087
- Plan: PLAN-0008

## Objective

Shared offline_service/offlineService helper; subgraph/workflow-tool/function missing targets raise; handbook en/vi matrix.

## Acceptance Criteria

- See REQ-0088 criteria for this item; generated code executed in Python and TypeScript (Deno).

## Related Artifacts

- Review: `.factory-state/artifacts/REV-0246-TASK-0263-export-stub-failfast.md`
- QA: `.factory-state/artifacts/QA-0246-TASK-0263-export-stub-failfast.md`

## Activity Log

- 2026-11-07: Created.
- 2026-11-07: Implemented in python_export.py / typescript_export.py stub and missing-target sections only (no browser export code touched). New tests/test_export_service_stubs.py executes generated files (Python subprocess, Deno). Export test suites: 136 + 6 passed locally with Deno.
