# Task

## Metadata

- Project: superstep
- Task ID: TASK-0267
- Title: Export HTTP Tool connects to the checked address
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-07
- Updated: 2026-11-07
- Requirement IDs: REQ-0089
- Architecture IDs: DEC-0088
- Plan: PLAN-0009

## Objective

HTTP Tool requests resolve once and connect to the checked address (Python httpx IP URL + Host + sni_hostname; TypeScript node:http(s) with a pinned lookup and servername), per DEC-0088.

## Acceptance Criteria

- See REQ-0089 criteria for this item; generated code executed in Python and TypeScript (Deno) against local servers / fakes only.

## Related Artifacts

- Review: `.factory-state/artifacts/REV-0249-TASK-0267-export-http-pinning.md`
- QA: `.factory-state/artifacts/QA-0249-TASK-0267-export-http-pinning.md`

## Activity Log

- 2026-11-07: Created and implemented.
