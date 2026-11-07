# Task

## Metadata

- Project: superstep
- Task ID: TASK-0270
- Title: Export Retriever adapter
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-07
- Updated: 2026-11-07
- Requirement IDs: REQ-0089
- Architecture IDs: DEC-0088
- Plan: PLAN-0009

## Objective

Replace the Retriever stub (node and Agent knowledge tool) in Python and TypeScript exports with a real search through the Superstep knowledge base API, configured by `SUPERSTEP_URL`, `SUPERSTEP_TOKEN` and `KNOWLEDGE_BASE_<n>_ID`, per DEC-0088. Split from TASK-0266.

## Acceptance Criteria

- Configured: the studio's hits are returned; path, Bearer token, query and top_k sent as the API expects; a studio error code stops the run (Python and Deno).
- Unconfigured: offline announced mock; live run refused naming the missing variables.
- No knowledge base id or token in the generated file.

## Related Artifacts

- Review: `.factory-state/artifacts/REV-0252-TASK-0270-export-retriever-adapter.md`
- QA: `.factory-state/artifacts/QA-0252-TASK-0270-export-retriever-adapter.md`

## Activity Log

- 2026-11-07: Created (split from TASK-0266) and implemented.
