# Requirement

## Metadata

- Project: superstep
- Requirement ID: REQ-0099
- Status: Accepted for planning 2026-11-13
- Owner: Thái Quí Nguyễn
- Created: 2026-11-13
- Updated: 2026-11-13 (note on temporary selection codes added)
- Source: Owner selection on 2026-11-13 of the next Dataset slice: DS2-01 Agent write, DS2-02 workflow row delete, and DS2-03 Dataset use from public entry points. DS2-04, DS2-05, DS2-06, DS2-07, DS2-10, and DS2-17 stay deferred. DS2-08, DS2-09, DS2-11, DS2-12, DS2-13, DS2-14, DS2-15, and DS2-16 stay selected for later requirements.

## Summary

A saved workflow can delete a dataset row, an Agent can insert and upsert rows it is allowed to change, and a granted workflow can look up and write rows from public chat and the workflow API. Delete stays off those public entries.

## Note On Temporary Selection Codes

The `DS2-*` codes in the Source line were temporary codes used while the owner chose the direction for this slice (owner note, 2026-11-13). They are not task or artifact IDs. DS2-01 to DS2-03 are the selected scope above. The codes below are selected for a later requirement; this note defines them only and does not change this requirement's scope or create tasks. The Out Of Scope section names them by product name.

| Code | Name | Meaning |
| --- | --- | --- |
| DS2-08 | Formula columns | A column computed from other columns when the row changes. |
| DS2-09 | Cross-table relations | Foreign keys and lookups from one dataset to another. |
| DS2-11 | Change triggers | Insert, Upsert, or Delete automatically runs a workflow. |
| DS2-12 | Saved views | Save filters, column order, and sorting to reopen. |
| DS2-13 | Calendar view | Plot rows with a date column on a month or week calendar. |
| DS2-14 | Map view | A location column and plotting rows on a map. |
| DS2-15 | MCP exposure | MCP clients read or write datasets within the grant. |
| DS2-16 | Embeddings | Embed dataset rows for semantic search, not just per-cell matching. |

## Problem Or Opportunity

REQ-0097 lets a Dataset node find, get, insert, and upsert rows, and lets an Agent query a read-only binding. Operators still finish two common steps by hand: an Agent cannot file or update a ticket, and a workflow cannot delete a row. The same workflows also stop at public chat and API triggers, because those entries reject every Dataset operation before the grant is checked.

## Scope

### In Scope

- Agent tools may be configured for Find rows, Insert row, and Upsert row on one dataset binding. A tool exposes only the operations, fields, and filter operators selected for it.
- A Dataset node operation, Delete row, removes one row by its id or by one unique key.
- Workflow grants and Dataset API tokens gain a delete capability that is separate from read and write.
- Granted Find, Get, Insert, and Upsert operations, including Agent writes, run from Studio chat, public chat, and the workflow API trigger.
- Python and TypeScript project export implement the same Agent write and Delete row contract on the Superstep API, SQLite, and PostgreSQL bindings.
- English and Vietnamese Studio labels and the Datasets handbook describe the new grant, the Agent operations, and where delete is refused.

### Out Of Scope

- Formula columns, cross-table relations, change triggers, saved views, calendar and map views, MCP exposure, and embeddings.
- Free SQL, external database administration, editing existing customer tables, automatic synchronization, multi-cell clipboard and fill handles, and evaluation datasets.
- Agent delete, and Delete row on Studio chat, public chat, the workflow API trigger, or demo mode.
- Changes to Studio grid deletion, CSV import and export, snapshot seeding, or the four Superstep-owned standalone tables.
- Letting an unsaved workflow run under a dataset grant.

## Stakeholders Or Users

- A dataset owner who grants a workflow or an export token.
- A workflow author who configures a Dataset node or an Agent tool.
- A person or external client who runs that saved workflow from Studio, chat, a schedule, or the API.
- An operator who deploys an exported Python or TypeScript project.

## Current Context

- REQ-0097, DES-0007, ARCH-0003, DEC-0097, and PLAN-0016 are implemented on `develop` at `6a2e43a6`. Dataset nodes support `find_rows`, `get_row`, `insert_row`, and `upsert_row`. Grants are `read`, `write`, or `read_write`. A `write` grant does not allow reads.
- The Agent Dataset tool is fixed to `find_rows`, with a configured field list, allowed filter operators, and a limit of at most 20 rows. Write attempts fail. The trace records the tool outcome and count without a second copy of the row values.
- Studio can already delete one row. That path requires `resources.manage`, uses a confirmation button, and sends a plain DELETE. It is not a workflow operation and has no receipt.
- Insert and upsert use a durable receipt. The same operation identity and arguments return the earlier result. Different arguments for that identity return `DATASET_RECEIPT_CONFLICT`. Test, debug, and unsaved runs simulate writes and leave stored rows unchanged.
- A run is treated as public in demo mode, and when its source is not Studio Run (`ui`), a schedule, or a workflow test. Studio chat, public chat, and the API trigger fall in that public group. Child runs of a workflow tool use the top run's source. Public and unsaved runs raise `DATASET_GRANT_DENIED` before the grant is applied.
- Export bindings list the operations a graph uses. Connected calls use a Dataset token. Standalone setup creates `superstep_dataset_definitions`, `superstep_dataset_rows`, `superstep_dataset_keys`, and `superstep_dataset_receipts`. Row values stay in JSON.

## Desired Behavior

- The dataset Access dialog keeps the current read, write, and read-and-write choice, and adds a separate delete control. The control is off until a manager turns it on. Existing grants and tokens stay non-deleting. Revoking the grant, the token, or the delete control takes effect on the next operation, including a resumed or recovered run.
- A Dataset node can delete one row. The author maps either a row id or one unique field from workflow state. The node reports the deleted row id. Audit records the dataset, row id, workflow, and run, and does not record cell values.
- An Agent tool author chooses Find, Insert, Upsert, or a combination. Insert and Upsert accept only the configured fields. Upsert requires a chosen unique key. The model receives the operation result. The trace still shows the outcome and count without an extra copy of the values.
- From Studio Run or a schedule, each operation runs when the grant allows it. From Studio chat, public chat, or the API trigger, Find, Get, Insert, and Upsert run when the grant allows them, and Delete row is refused. Demo mode refuses every Dataset operation. A workflow test simulates Insert, Upsert, and Delete and leaves stored rows unchanged.
- An exported project performs the same lookups, Agent writes, and deletes against a live Superstep API, SQLite, and PostgreSQL, including one graph that mixes those backends. A connected token needs the delete capability for Delete row. Standalone setup remains repeatable and does not remove existing rows.

## Business Rules

- Read allows Find and Get. Write allows Insert and Upsert. Read-and-write allows those four. None of those permissions allows Delete row.
- Delete is an additional capability on a workflow grant and on a Dataset API token. It allows Delete row only from Studio Run, a schedule, or a simulated workflow test.
- A public entry uses the saved workflow's grant for Find, Get, Insert, and Upsert. Delete row on a public entry returns `DATASET_GRANT_DENIED` even when delete is enabled. Demo mode returns the same denial for every Dataset operation.
- An Agent cannot be given Delete row. A read-only Agent tool rejects Insert and Upsert. An Agent write uses the workflow write grant and the same field, type, unique-key, and row-size rules as the Dataset node.
- Delete addresses one row. A missing row returns `DATASET_ROW_NOT_FOUND` and does not consume the receipt identity. A successful delete's retry, with the same identity and arguments, returns the original result after the row is gone. Different arguments for that identity return `DATASET_RECEIPT_CONFLICT`.
- Insert, Upsert, and Delete share the dataset writer lock. A later operation sees the committed row. Unique-key conflicts and stale schema checks use the existing Dataset error codes.
- Receipts, audit records, and traces carry identifiers, operation names, counts, and outcomes. They do not carry cell values or secrets.
- A person who cannot see the dataset still receives not found from Studio. A workflow without a matching grant receives `DATASET_GRANT_DENIED`. An insufficient or revoked token receives `AUTH_TOKEN_INVALID`.

## Constraints

- Keep the backend layers in `docs/backend-architecture.md`. Add error codes only through the shared catalog, `docs/api-errors.md`, and both locale files.
- Studio UI uses shadcn/ui components and theme tokens. New strings go in the English and Vietnamese catalogs with identical keys.
- The Studio row-delete API stays a plain DELETE with no confirm field. Workflow delete is a Dataset operation, not that API.
- Exported Python and TypeScript keep one binding contract. Destination ids, paths, connection strings, and credentials stay in deployment settings. The default archive still contains no rows and no secrets.
- Preserve the current row, column, byte, and query limits.

## Acceptance Criteria

- An Agent configured for Insert and Upsert writes only its allowed fields, and the row appears in Studio. The same tool rejects a field or an operation that was not configured. A read-only Agent tool still cannot write. Revocation applies to the next call.
- A workflow with delete enabled removes one row by id and one row by unique key. A workflow without delete enabled cannot. Replaying a completed delete returns the first result. A second payload under that identity conflicts. A test run deletes nothing.
- Studio chat, public chat, and an API trigger can find and upsert when the grant allows it, and cannot delete. A Studio Run and a schedule can delete when delete is enabled. Demo mode cannot use Dataset operations. A nested workflow tool follows its top run's entry.
- Python and TypeScript exports pass the same lookup, Agent write, delete, receipt, and denial cases on the Superstep API, SQLite, and PostgreSQL. A token without delete capability cannot delete. Setup run twice keeps the rows that remain.
- The Access dialog, Dataset node, and Agent tool settings are keyboard reachable in English and Vietnamese. The handbook in both languages states the delete capability, the Agent write operations, and the entries that cannot delete.

## Edge Cases

- Two runs delete and upsert the same row at the same time. One committed result wins, and the other sees that result.
- A worker stops after a committed Agent write or delete and retries. The caller receives the original result and no second mutation.
- Delete by a key that is no longer unique, or by a field the schema no longer has, fails with the existing schema error and leaves rows in place.
- An Agent Upsert whose unique value belongs to another row returns `DATASET_UNIQUE_CONFLICT` and does not change that row.
- A public run whose grant is removed during a wait resumes without Dataset access.

## Assumptions

- Studio chat stays in the public entry group because it already shares that run source with public chat. Delete row is refused there. Find, Get, Insert, and Upsert are allowed when granted.
- Agent write identity follows the existing receipt rule: one logical tool call has a stable identity, a retry of that call replays, and a distinct call in the same run is a new write.
- Existing `read`, `write`, and `read_write` values remain unchanged. Delete is stored beside them, not as another value in that set.
- The later Dataset selections stay outside this requirement until the owner asks for their requirements.

## Open Questions

- None.

## Related Artifacts

- [Dataset requirement](REQ-0097-datasets.md)
- [Dataset design](DES-0007-datasets.md)
- [Dataset architecture](ARCH-0003-datasets.md)
- [Dataset decision](../decisions/DEC-0097-dataset-grid-and-export.md)
- [Dataset plan](PLAN-0016-datasets.md)
- [Write plan](PLAN-0017-dataset-writes.md)
- [Delete and public decision](../decisions/DEC-0098-dataset-delete-and-public.md)
- [Dataset export](../../docs/dataset-export.md)
- [English handbook](../../handbook/docs/en/guide/datasets.md)
- [Vietnamese handbook](../../handbook/docs/vi/guide/datasets.md)
