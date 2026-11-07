# Task

## Metadata

- Project: superstep
- Task ID: TASK-0266
- Title: Proposal: remaining export gaps needing owner decision
- Status: backlog (proposal; real MCP/retriever/SMTP adapters split out and owner-authorised as TASK-0269..0271 under REQ-0089; the rest still needs an owner decision)
- Owner: Thái Quí Nguyễn
- Created: 2026-11-07
- Updated: 2026-11-07
- Requirement IDs: REQ-0088, REQ-0089
- Architecture IDs: DEC-0087
- Plan: PLAN-0008

## Objective

Cross-language code nodes (TS export cannot run Python code/server functions; Python export cannot run TS code) would need an embedded runtime or transpiler; approval channels, deadlines and AI review need Studio services; per-node provider credentials need a multi-provider env convention; real MCP/retriever/SMTP adapters need dependency and configuration choices. Each needs an owner decision before work.

## Acceptance Criteria

- See REQ-0088 criteria for this item; generated code executed in Python and TypeScript (Deno).

## Activity Log

- 2026-11-07: Created.
- 2026-11-07: Owner "Làm đi" (REQ-0089): adapters split into TASK-0269 (MCP), TASK-0270 (Retriever), TASK-0271 (Send email). Cross-language code, advanced approvals, per-node providers and managed connections remain proposals here.
