# Plan

- Plan ID: PLAN-0007
- Project: superstep
- Status: Proposed — implementation waits for owner acceptance of REQ-0087 and a DEC-0086 choice
- Created/Updated: 2026-11-06
- Related: REQ-0087, DES-0005, DEC-0086

| Task | Purpose | Size | Depends |
| --- | --- | --- | --- |
| [TASK-0259](../tasks/backlog/TASK-0259-expose-local-studio-handbook.md) | en/vi handbook page "Expose a local studio" + channels.md cross-link | S | acceptance |
| [TASK-0260](../tasks/backlog/TASK-0260-contextual-handbook-links.md) | handbook URL helper + Channels "Learn more" and connection-helper links | S | TASK-0259 merged, DEC-0086 |

Each task: own branch from develop, own PR, REV/QA, full Factory verify/validate, all required CI (including E2E and handbook strict build) green before merge under the owner's standing green-merge instruction. Independent of TASK-0251/0252 (assigned elsewhere) and of #318.
