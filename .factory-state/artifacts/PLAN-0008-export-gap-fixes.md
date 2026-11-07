# Plan

- Plan ID: PLAN-0008
- Project: superstep
- Status: owner-authorised implementation (TASK-0263..0265); TASK-0266 proposal awaiting owner decision
- Created/Updated: 2026-11-07
- Related: REQ-0088, DEC-0087

| Task | Purpose | Size |
| --- | --- | --- |
| TASK-0263 | service stubs fail fast in live runs; missing targets fail when reached; docs | S |
| TASK-0264 | export LLM model fallback (Python + TypeScript), executed tests | M |
| TASK-0265 | HTTP Tool safeguards and idempotency in exports, executed tests | M |
| TASK-0266 | proposal: cross-language code, advanced approvals, per-node providers, real service adapters | — |

One PR per task, merged only with all required CI green. Edits stay outside browser export code paths to avoid collision with TASK-0261/0262.
