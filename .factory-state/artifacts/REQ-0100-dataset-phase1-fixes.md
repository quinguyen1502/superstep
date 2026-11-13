# Requirement

## Metadata

- Project: superstep
- Requirement ID: REQ-0100
- Status: Proposed 2026-11-13 (Asia/Saigon); awaiting owner acceptance of this requirement, PLAN-0018, DEC-0099 and DEC-0100
- Owner: Thái Quí Nguyễn
- Created: 2026-11-13
- Updated: 2026-11-13
- Source: Owner chat 2026-11-13 (pt286u, asking for a fix plan after the Datasets phase 1 review of `develop` at `b12fa14f`). Review evidence: 42 Studio screenshots and probe notes taken on a local SQLite stack.
- Related: REQ-0097, REQ-0099, DES-0007, ARCH-0003, DEC-0097, DEC-0098, DEC-0099, DEC-0100, PLAN-0016, PLAN-0017, PLAN-0018, TASK-0332 to TASK-0344

## Why A New Requirement

REQ-0097 (phase 1) and REQ-0099 (phase 2 writes) are accepted and their tasks are merged or in flight. The review found behavior that contradicts their rules (a `write` grant reads row values, team datasets are managed by any editor, receipts keep row values after delete) and gaps they did not specify (filter null semantics, case sensitivity, schema changes after creation, Studio states). This requirement collects the corrections without reopening the accepted phase scope. Where it changes an accepted rule, the change is named below.

## Summary

Close the phase 1 review findings: no row values reach a caller without read access, receipts keep identifiers only, filters behave predictably with empty cells and letter case, team datasets follow a clear management authority, schema and CSV edge cases keep data intact, errors name the real cause, and Studio explains every state it shows.

## Findings Covered

| Priority | Finding | Evidence on `b12fa14f` | Task |
| --- | --- | --- | --- |
| P0 | A `write` grant or token reads a whole row: upsert with only the key returns every projected field of the existing row; dry-run does the same. A no-op upsert still bumps the revision. | `services/dataset_access.py` `_allows`; `services/dataset_rows.py` upsert result and dry-run branch; probe: write-only token 401 on `find_rows`, 200 with 9 values on `upsert_row` | TASK-0332 |
| P1 | Write receipts store a full copy of the row, are never removed, and survive row deletion. | `repositories/dataset_rows.py` receipt `result`; `models/dataset_receipt.py` | TASK-0333 |
| P1 | `ne` uses SQL `!=` and drops empty cells. Search, `contains`, and text sort are case-sensitive (`instr`/`strpos`, collation `C`/`BINARY`). | `repositories/dataset_rows.py` `_predicate`, `query`; probe: "Webhook" 3 rows, "webhook" 0 | TASK-0334 |
| P1 | Team datasets: any user with global `resources.manage` who is in the team may delete the dataset, revoke grants, and rotate another member's token. Rotation moves the token's issuer to the rotating user. Team membership has no role. | `services/dataset_service.py` `editable_definition`; `services/dataset_access.py` `rotate`; `models/team.py` `TeamMember` | TASK-0335 |
| P1 | A column cannot become unique after creation, so a CSV-imported dataset without a key cannot be upserted. | `services/dataset_service.py` `update_column` | TASK-0336 |
| P1 | Misleading errors: create for a team the caller is not in returns `DATASET_NOT_FOUND`; granting a team dataset to a workflow not shared with the team says the grant is missing; an empty filter value fails the run without naming the node or filter. | `dataset_service.py` `prepare_create`; `dataset_access.py` scope check; `dataset_rows.py` filter parsing | TASK-0337 |
| P2 | A valid token without the operation gets `401 AUTH_TOKEN_INVALID`, the same as a wrong token. | `dataset_access.py` `token_dataset` | TASK-0337 |
| P2 | Removed (archived) columns count toward the 100-column limit and keep their values in rows. A required column with a default cannot be added once rows exist. | `dataset_service.py` `add_column`, `remove_column` | TASK-0338 |
| P2 | CSV type inference turns `00123` into a number. The export formula guard's leading `'` survives re-import (for example `'+84...`). Studio row and dataset DELETE skip the conflict check when `revision` is omitted. | `services/dataset_csv.py`; `api/routes/datasets.py` delete routes | TASK-0339 |
| P1 (UI) | Viewers see controls disappear with no explanation; the empty state shows "No datasets yet" and "Select a dataset" with no Create or Import; not found is red text with a Retry that cannot help; the row delete confirmation does not name the row; the CSV issue list shows keys, is unsorted, hides the bad value, has no alert icon, and existing-dataset import has no preview. | `frontend/src/pages/Datasets.tsx`, `components/datasets/dataset-grid.tsx`, CSV dialog | TASK-0340 |
| P2 (UI) | Breadcrumb order reversed; Schema and Access open as dialogs while DES-0007 specifies sibling views; grid layout not kept; fixed page size of 50; no total; prev/next only; narrow default widths; sticky actions column covers the last sort icon; long text edits in a one-line input; mixed date formats. | `Datasets.tsx`, `dataset-grid.tsx` | TASK-0341 |
| P2 (UI) | Run trace for a Dataset node shows raw JSON with epoch timestamps; Studio Run gives no notice that it writes real rows; the missing-grant hint offers no direct Grant action to a manager. | Dataset node trace and validation UI | TASK-0342 |

## Business Rules

- A caller without read permission on a dataset never receives cell values from that dataset, from any entry: Dataset node, Agent tool, public chat or API trigger, connected token, dry-run, or receipt replay. The permission model is set by DEC-0099.
- An insert or upsert that would leave every stored value unchanged does not change the revision, does not update `updated`, and records no row-update audit event. It still returns a normal result and still stores its receipt.
- Receipts store the operation identity, fingerprint, row id, inserted flag, and resulting revision only. They expire after a retention window (default 30 days after creation; configurable). Deleting a row does not delete its receipts, because a retried insert must still replay instead of inserting again.
- `ne` and "is not" match empty cells. `contains`, free-text search, and text sort ignore letter case and treat Vietnamese letters consistently on SQLite and PostgreSQL. `eq` and unique keys stay exact.
- Team dataset management (schema, delete, grants, tokens) follows DEC-0100. Rotating a token keeps its issuer.
- A token valid for the dataset but lacking the operation returns `403` with a dedicated scope code. A wrong, revoked, or other-dataset token keeps `401 AUTH_TOKEN_INVALID`. This supersedes the REQ-0099 rule "an insufficient or revoked token receives `AUTH_TOKEN_INVALID`" for the insufficient case only.
- Studio row and dataset DELETE require the current revision. A stale revision returns the existing conflict code. Workflow `delete_row` is unchanged (DEC-0098).

## Acceptance Criteria

- Security tests prove that a `write` grant, a `write` token, and an Agent tool without Find never receive cell values from insert, upsert, dry-run, or replay, on SQLite and PostgreSQL.
- A migration rewrites existing receipts to the identifier-only shape; no receipt holds a cell value afterwards; expired receipts are removed by the existing maintenance path.
- Filter, search, and sort tests cover empty cells, mixed case, and Vietnamese text on both databases.
- Team-role tests cover dataset delete, grant revoke, token rotate, and token revoke by the owner, an admin, and another team member.
- Every Studio state named above has an explanation and the action that can resolve it, in English and Vietnamese, in both themes.
- Python and TypeScript exports keep the same contract for every rule above that reaches an exported project (TASK-0343).

## Out Of Scope

- New Dataset features (phase 3, REQ-0101).
- Team-level roles for workflows or other resources. DEC-0100 applies to datasets only.
- Changing `delete_row`, `allow_delete`, or the public-entry matrix of DEC-0098.

## Constraints

- Backend layers in `docs/backend-architecture.md`; Alembic migrations, additive where possible; error codes through `core/errors.py` `CATALOG`, `docs/api-errors.md`, and both locale files.
- shadcn/ui and theme tokens; identical en/vi locale keys; `ConfirmDeleteDialog` for deletions (dataset row deletion keeps the confirmation click of DEC-0025).
- Preserve the row, column, byte, and query limits of REQ-0097 except where TASK-0338 changes how removed columns count.

## Open Questions

- DEC-0099: keep write-only and return identifiers only (recommended), or remove standalone write.
- DEC-0100: who manages a team dataset (recommended: its owner and global admins).
- Receipt retention: 30 days by default (recommended), or tie it to run retention.
- Requiring a revision on Studio DELETE changes the Dataset REST contract for PAT clients. Recommended: require it, documented in the changelog.
