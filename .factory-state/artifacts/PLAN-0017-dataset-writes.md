# Plan

## Metadata

- Project: superstep
- Plan ID: PLAN-0017
- Status: Planned
- Owner: Thái Quí Nguyễn
- Created: 2026-11-13
- Updated: 2026-11-13
- Related Requirements: REQ-0099
- Related Design: DES-0007
- Related Architecture: ARCH-0003
- Integration baseline: origin/develop at 6a2e43a6

## Objective

Deliver workflow row delete, Agent insert and upsert, and granted Dataset lookup and writes from public entries. Delete stays off those public entries.

## Context Reviewed

- [Requirement](REQ-0099-dataset-writes.md)
- [Dataset requirement](REQ-0097-datasets.md)
- [Design](DES-0007-datasets.md)
- [Architecture](ARCH-0003-datasets.md)
- [Decision](../decisions/DEC-0098-dataset-delete-and-public.md)
- [Prior plan](PLAN-0016-datasets.md)
- Medium task workflow. The requirement already states the rules and acceptance criteria, so no separate analysis artifact is added.
- DES-0007 still governs layout, theme tokens, and keyboard behavior. REQ-0099 specifies the Access control, Delete row mapping, and Agent operation checks, so no new design artifact is added.
- DEC-0098 records the schema and public matrix. ARCH-0003 is not rewritten.

## Work Breakdown

| Task | Phase | Outcome | Dependencies |
| --- | --- | --- | --- |
| [TASK-0324](../tasks/done/TASK-0324-dataset-delete-capability.md) | Access | `allow_delete` on grants and tokens, and the Access control | — |
| [TASK-0325](../tasks/todo/TASK-0325-dataset-delete-runtime.md) | Runtime | `delete_row` receipts, locks, and connected token execution | TASK-0324 |
| [TASK-0326](../tasks/todo/TASK-0326-dataset-delete-editor.md) | Studio | Dataset node Delete row mapping | TASK-0325 |
| [TASK-0327](../tasks/todo/TASK-0327-dataset-agent-write.md) | Runtime | Agent insert and upsert, including its settings | — |
| [TASK-0328](../tasks/todo/TASK-0328-dataset-public-entry.md) | Runtime | Public lookup and writes; public delete and demo mode stay denied | TASK-0325, TASK-0327 |
| [TASK-0329](../tasks/todo/TASK-0329-dataset-export-python-delete.md) | Export | Python standalone delete and Agent writes | TASK-0325, TASK-0327 |
| [TASK-0330](../tasks/todo/TASK-0330-dataset-export-typescript-delete.md) | Export | TypeScript standalone delete and Agent writes | TASK-0325, TASK-0327 |
| [TASK-0331](../tasks/todo/TASK-0331-dataset-writes-acceptance.md) | Acceptance | Handbook and one end-to-end path | TASK-0326, TASK-0328, TASK-0329, TASK-0330 |

## Sequence

1. TASK-0324 and TASK-0327 can proceed on separate branches from `develop`.
2. TASK-0325 starts after TASK-0324 has merged. TASK-0326 starts after TASK-0325 has merged.
3. TASK-0328, TASK-0329, and TASK-0330 start after both TASK-0325 and TASK-0327 have merged. The two export tasks may proceed in parallel and must edit only their own language section of `docs/dataset-export.md`.
4. TASK-0331 starts after the editor, public-entry, and both export tasks have merged.

## Risks

- Public entries gain insert and upsert. Grants, configured fields, receipts, and audit without cell values remain the controls.
- Studio delete can merge before standalone delete. Acceptance is not complete until both export tasks pass.
- Existing grants and tokens stay non-deleting. The migration is additive and keeps the permission values.

## Approval Needs

- The owner confirms this set before `task-start`.
- Each task uses its own branch and Draft PR. Merge only after the owner asks and required CI is green.
- No task in this plan covers the later Dataset selections or the deferred items named in REQ-0099.

## Assumptions

- Studio chat remains a public entry, so it can look up and write when granted and cannot delete.
- One logical Agent tool call has a stable receipt identity. A later call in the same run is a new write.
- Untracked copies of TASK-0310 through TASK-0322 under `.factory-state/tasks/todo/` are stale local files. They are not tasks in this plan.

## Open Questions

- None.

## Completion Criteria

- Every task meets its acceptance criteria and is integrated.
- A granted Agent can insert and upsert. A granted workflow can delete from Studio Run and a schedule.
- Studio chat, public chat, and the API trigger can find and upsert, and cannot delete. Demo mode cannot use Dataset operations.
- Python and TypeScript exports pass the same cases on the Superstep API, SQLite, and PostgreSQL.
- The English and Vietnamese handbook states the delete capability, Agent writes, and the entries that cannot delete.
