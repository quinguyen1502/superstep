# Plan

## Metadata

- Project: superstep
- Plan ID: PLAN-0018
- Status: Accepted 2026-11-13 (Asia/Saigon) by the owner (owner chat, "accept"), with REQ-0100. DEC-0099 and DEC-0100 accepted (pt287u). TASK-0332 is in todo; the other tasks stay in backlog until their dependencies merge.
- Owner: Thái Quí Nguyễn
- Created: 2026-11-13
- Updated: 2026-11-13
- Related Requirements: REQ-0100
- Related Design: DES-0007
- Related Architecture: ARCH-0003
- Related Decisions: DEC-0099, DEC-0100
- Integration baseline: origin/develop at b12fa14f

## Objective

Close the Datasets phase 1 review findings, starting with the P0 write-only read leak before public entries gain Dataset writes.

## Context Reviewed

- [Fix requirement](REQ-0100-dataset-phase1-fixes.md)
- [Dataset requirement](REQ-0097-datasets.md), [Write requirement](REQ-0099-dataset-writes.md), [Write plan](PLAN-0017-dataset-writes.md)
- [Design](DES-0007-datasets.md), [Architecture](ARCH-0003-datasets.md)
- [DEC-0097](../decisions/DEC-0097-dataset-grid-and-export.md), [DEC-0098](../decisions/DEC-0098-dataset-delete-and-public.md), [DEC-0099](../decisions/DEC-0099-dataset-write-only-results.md), [DEC-0100](../decisions/DEC-0100-team-dataset-authority.md)
- Review of `develop` at `b12fa14f`: 42 screenshots and probes (local SQLite stack).
- DES-0007 still governs layout; the UI tasks bring the implementation back to it (sibling views, delete naming, explained states). No new design artifact.

## Work Breakdown

| Task | Priority | Outcome | Dependencies |
| --- | --- | --- | --- |
| [TASK-0332](../tasks/review/TASK-0332-dataset-write-only-results.md) | P0 | Write-only callers get identifiers only; no-op writes keep the revision | DEC-0099 (accepted); after #383 (TASK-0327), before TASK-0328 |
| [TASK-0333](../tasks/backlog/TASK-0333-dataset-receipt-minimization.md) | P1 | Identifier-only receipts, migration, retention | TASK-0332 |
| [TASK-0334](../tasks/done/TASK-0334-dataset-filter-semantics.md) | P1 | Null-safe `ne`; case-insensitive contains, search, sort | — |
| [TASK-0335](../tasks/done/TASK-0335-dataset-team-authority.md) | P1 | Team dataset management authority; rotate keeps issuer | DEC-0100 (accepted) |
| [TASK-0336](../tasks/done/TASK-0336-dataset-unique-later.md) | P1 | Make an existing column unique after a duplicate check | — |
| [TASK-0337](../tasks/backlog/TASK-0337-dataset-error-clarity.md) | P1 (token scope P2) | Specific codes for team, sharing, filter, token scope | — |
| [TASK-0338](../tasks/done/TASK-0338-dataset-schema-limits.md) | P2 | Active-column limit, removed values cleared, required default backfill | — |
| [TASK-0339](../tasks/done/TASK-0339-dataset-csv-fidelity.md) | P2 | Leading zeros, formula guard round trip, DELETE revision | — |
| [TASK-0340](../tasks/backlog/TASK-0340-dataset-studio-states.md) | P1 | Viewer, empty, not-found states; delete names the row; CSV issue list | — |
| [TASK-0341](../tasks/backlog/TASK-0341-dataset-grid-usability.md) | P2 | Layout persistence, page size, totals, widths, dates, tabs | TASK-0340 |
| [TASK-0342](../tasks/backlog/TASK-0342-dataset-run-feedback.md) | P2 | Trace summary, real-write notice, Grant shortcut | TASK-0341 |
| [TASK-0343](../tasks/backlog/TASK-0343-dataset-export-fix-parity.md) | P1 | Python and TypeScript parity for the fixes | TASK-0329, TASK-0330, TASK-0332, TASK-0333, TASK-0334, TASK-0337 |
| [TASK-0344](../tasks/backlog/TASK-0344-dataset-fixes-acceptance.md) | P1 | Regression suite, screenshots, handbook | TASK-0332 to TASK-0343 |

## P0 Ordering Against The Phase 2 Chain

The phase 2 chain (REQ-0099, PLAN-0017) is in flight: PR #382 (TASK-0326) and PR #383 (TASK-0327) are open, and TASK-0328 to TASK-0331 are being pushed. TASK-0327 lets an Agent write through the write grant and TASK-0328 lets public chat and the API trigger write. Both reuse the upsert result that leaks values.

1. #382 (TASK-0326, Delete row editor) is unaffected and may merge whenever the owner approves.
2. #383 (TASK-0327) may merge as is. Until TASK-0332 merges, no `main` release may include TASK-0327; `develop` is not deployed publicly.
3. TASK-0332 branches from `develop` after #383 merges, so one change fixes the node, Agent, connected-token, and dry-run paths together, including Agents without Find.
4. TASK-0328 (public entries) merges only after TASK-0332. It rebases onto `develop` and its tests then expect identifier-only results for write-only public writes. This is the hard gate: public writes must never ship with the leak.
5. TASK-0329 and TASK-0330 (exports) may merge before or after TASK-0332; connected bindings get the fix from the server. Standalone parity follows in TASK-0343.
6. TASK-0331 (phase 2 acceptance) runs after TASK-0328 and therefore already covers the fixed behavior.

Alternative if the owner prefers not to merge #383 first: hold #383, merge TASK-0332 (node, token, dry-run), then rebase #383 to use the shared result function. This delays Agent writes by one review cycle and is not recommended.

No PLAN-0017 task file is edited by this plan.

## Sequence

1. TASK-0332 as above. In parallel, from `develop`: TASK-0334, TASK-0336, TASK-0338, TASK-0339, TASK-0340.
2. TASK-0335 after DEC-0100 is accepted. TASK-0337 after TASK-0335 if both touch the access service (rebase, no shared branch).
3. TASK-0333 after TASK-0332. TASK-0341 after TASK-0340; TASK-0342 after TASK-0341.
4. TASK-0343 after the phase 2 export tasks and the server fixes it mirrors.
5. TASK-0344 last.

## Risks

- TASK-0333 changes replay responses (values re-read from the current row). Clients that compared replay bodies byte for byte must accept current values; documented in `docs/dataset-export.md`.
- TASK-0334 changes result sets for existing filters (`ne` now includes empty cells; contains ignores case). Saved workflows may return more rows; the handbook and changelog state it.
- TASK-0337 and TASK-0339 change API contracts (403 scope, required DELETE revision); changelog entries.
- The phase 2 executor works concurrently; tasks touching `dataset_access.py` and `dataset_rows.py` must rebase on whatever of TASK-0328 to TASK-0331 has merged.

## Approval Needs

- Done: the owner accepted REQ-0100 and this plan, DEC-0099 Option A, DEC-0100 Option A, 30-day receipt retention, `403 DATASET_TOKEN_SCOPE`, and required Studio DELETE revisions on 2026-11-13.
- Each task uses its own branch and Draft PR into `develop`. Merge only after the owner asks and required CI is green.

## Completion Criteria

- Every REQ-0100 finding is covered by a merged task and a passing test or screenshot recorded in the TASK-0344 QA artifact.
