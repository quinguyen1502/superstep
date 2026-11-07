# Task

## Metadata

- Project: superstep
- Task ID: TASK-0268
- Title: Export LLM fallback for messages with attachments
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-07
- Updated: 2026-11-07
- Requirement IDs: REQ-0089
- Architecture IDs: DEC-0088
- Plan: PLAN-0009

## Objective

An LLM node with fallback and attachments calls call_llm_files_fallback / callLlmFilesFallback: same files to the fallback, TASK-0264 failover rules, at most one fallback call.

## Acceptance Criteria

- See REQ-0089 criteria for this item; generated code executed in Python and TypeScript (Deno) against local servers / fakes only.

## Related Artifacts

- Review: `.factory-state/artifacts/REV-0250-TASK-0268-export-fallback-attachments.md`
- QA: `.factory-state/artifacts/QA-0250-TASK-0268-export-fallback-attachments.md`

## Activity Log

- 2026-11-07: Created and implemented.
