# Dataset exports

A Python or TypeScript project that uses Dataset nodes or Agent tools includes `datasets.json`. It lists each deployment binding, the field contract, and the operations the workflow uses. Multiple nodes and tools that use the same dataset share one binding. Display labels, Studio dataset IDs, row snapshots, and token values are absent from the contract.

## Superstep API

For a connected binding, set `_BACKEND` to `superstep`. Set `_API_URL` to the base URL of the destination Superstep server, `_ID` to the destination dataset ID, and `_API_TOKEN` to a Dataset token issued for that dataset. The token needs read permission for Find rows and Get row, and write permission for Insert row and Upsert row. Delete row also needs a token issued with delete allowed. An Agent tool uses read permission for Find rows and write permission when it may insert or upsert rows.

A valid token without the permission for the requested operation gets `403 DATASET_TOKEN_SCOPE`. Invalid or revoked tokens and tokens issued for another dataset get `401 AUTH_TOKEN_INVALID`. A token with write but not read permission receives identifiers only. Insert row and Upsert row then return `{"row": {"id": "...", "revision": 1}, "inserted": true}` with no `values`, including when a receipt is replayed. Such a token must send `"fields": []`; a non-empty `fields` list returns `403 DATASET_GRANT_DENIED` and nothing is written. `fields` may be empty only for Insert row and Upsert row, where it asks for identifiers only for any token. Upsert still reports `inserted: false` when the key exists, so a write-only token can learn whether a key value is present; use Insert row when that must stay hidden. An upsert that leaves every value unchanged keeps the row's `revision` and `updated` time. Use an HTTPS server URL for deployments and a separate destination dataset when running write examples.

### Wire format

Send `POST /api/datasets/{id}/connected` with a Bearer Dataset token and a JSON body. The request contains `version: 1`, one of `find_rows`, `get_row`, `insert_row`, `upsert_row`, and `delete_row` in `operation`, the binding's `columns`, an explicit `fields` projection, and operation-specific `arguments`. The schema uses stable keys with `kind`, `required`, `unique`, `default`, and `options`. The server checks the contract against the destination before accessing rows. Additional destination columns are allowed when they are compatible with the operation.

Find accepts typed filters, sorting and paging. Get accepts `row_id`. Insert and Upsert accept a `values` object, and Upsert also requires its unique `key`. Delete accepts either `row_id`, or a unique `key` with its `value`, and returns `{row_id, deleted}`. Write and delete requests carry an `operation_id` of at most 128 characters. Scope is the token record, which stays the same when its secret is rotated. Retry an uncertain write with the same identity and arguments. During the receipt window, an exact retry returns the original row ID and insert outcome. If the row still exists, readable callers receive its current revision and projected values. After deletion, a retry returns the stored identifiers and never recreates the row while the receipt is retained. The Studio worker expires receipts after 30 days by default (`STUDIO_DATASET_RECEIPT_DAYS`). An expired identity can be processed as a new write. A different payload with that identity returns `DATASET_RECEIPT_CONFLICT`. The adapters reuse the same body on a transport retry.

Responses use the standard Superstep API envelope. `AUTH_TOKEN_INVALID` covers invalid, revoked, differently scoped, or insufficient tokens. `DATASET_BINDING_SCHEMA_MISMATCH` identifies the first incompatible field. `DATASET_SCHEMA_CONFLICT` means the destination changed during the request. In generated code, `DATASET_BINDING_MISSING` names the environment variables to set, `DATASET_BINDING_INVALID` reports invalid connection settings, and `DATASET_TRANSPORT_ERROR` indicates that the response could not be used.


### Grouped filters in the connected API

Find rows accepts either the existing `filters` and `filter_mode` arguments or a
`filter_tree`. A group has `type: "group"`, `conjunction: "and" | "or"`, and
`children`. A rule has `type: "rule"`, `field`, `op`, and `value`. A tree
supports three group levels and 20 rules. The `in` and `not_in` operators
take 1 to 50 values of the field's type. Null cells match `not_in` and
`not_contains`, and `not_contains` ignores case. Code export reports
`DATASET_EXPORT_FILTER_UNSUPPORTED` for these filters until both generated
runtimes support them.

## Python standalone

Choose the backend for each binding independently. An exported Python project can read a connected dataset and write to a standalone database in the same run.

| Backend | Settings for each binding |
| --- | --- |
| `sqlite` | `_SQLITE_PATH` for the SQLite file and `_ID` for a stable dataset name in that file |
| `postgresql` | `_POSTGRES_DSN` for an existing PostgreSQL database and `_ID` for a stable dataset name in it |

Set `_BACKEND` to the chosen value. Install the requirements, export the environment variables, and run `python agent.py --setup-datasets`. Setup creates the project tables and initializes each standalone binding with its exported schema. Repeating setup with the same schema preserves rows and receipt identities. Run setup after upgrading an existing standalone export to strip cell snapshots from old receipts. Older receipts start their retention window at migration because their original timestamps were unavailable. The PostgreSQL account needs table creation privileges for setup and read/write privileges on the project tables at runtime.

The startup check reports `DATASET_SETUP_REQUIRED` when a database or binding has not been initialized. `DATASET_BINDING_SCHEMA_MISMATCH` identifies a binding whose stored schema differs from the export. Setup rejects incompatible changes and preserves the stored schema and rows. Standalone retries with the same operation ID and arguments return the previously stored result.

Delete row takes the same writer lock as Insert row and Upsert row, removes the row and its unique keys, and stores a receipt. A row that is already gone returns `DATASET_ROW_NOT_FOUND` and stores no receipt. An Agent tool that may insert or upsert rows sends only its configured write fields, and it receives row values only when it can also Find rows. Otherwise the model gets the row id and whether the row was inserted. Each model call gets its own operation ID, so a retried graph step replays the call and a later call writes again.

## TypeScript standalone

Choose the backend for each binding independently. An exported TypeScript project can read a connected dataset and write to a standalone database in the same run. The settings are the same as for Python: `_SQLITE_PATH` or `_POSTGRES_DSN`, plus `_ID` and `_BACKEND`.

SQLite uses the runtime's built-in `node:sqlite` module. Node.js 22.13 or newer includes it. Node.js 22.5 through 22.12 also need `NODE_OPTIONS=--experimental-sqlite`. Deno 2.2 or newer includes the same module. PostgreSQL uses the `pg` package, which the project `package.json` declares. The single-file export imports it as `npm:pg@^8` so Deno can fetch it.

Install the project dependencies, export the environment variables, and run `npx tsx agent.ts --setup-datasets` or `deno run --allow-env --allow-read --allow-write --allow-net --allow-sys=homedir agent.ts --setup-datasets`. Setup creates the project tables and initializes each standalone binding with its exported schema. Repeating setup with the same schema preserves rows and receipt identities. Run setup after upgrading an existing standalone export to strip cell snapshots from old receipts. Older receipts start their retention window at migration because their original timestamps were unavailable. The PostgreSQL account needs table creation privileges for setup and read/write privileges on the project tables at runtime.

The startup check reports `DATASET_SETUP_REQUIRED` when a database or binding has not been initialized. `DATASET_BINDING_SCHEMA_MISMATCH` identifies a binding whose stored schema differs from the export. `DATASET_STORAGE_ERROR` reports that SQLite is unavailable or the database could not be opened. Setup rejects incompatible changes and preserves the stored schema and rows. Standalone retries with the same operation ID and arguments return the previously stored result.

Delete row, Agent insert and Agent upsert behave as in Python. Delete takes the writer lock, removes the row and its unique keys, and stores a receipt, while a row that is already gone returns `DATASET_ROW_NOT_FOUND` without a receipt. An Agent write sends only its configured write fields, with one operation ID for each model call.

The project download can prefill `_BACKEND` for a binding. The generated graph still reads the backend from the environment, so a deployment can change it without a new export. A snapshot is off unless that binding is explicitly selected and its backend is SQLite or PostgreSQL. The caller needs read access to the dataset. A snapshot holds at most 1,000 rows in `dataset-snapshots.json` and is the only row data in the archive. Setup imports a snapshot row when its id is not already stored. An existing row is left unchanged, including its values. A snapshot whose schema does not match the binding is rejected.

Standalone Dataset writes keep identifier-only receipts for 30 days by default. Both runtimes use `STUDIO_DATASET_RECEIPT_DAYS` and expire old receipts before writes. Replaying a retained receipt projects current values when the row still exists, or returns identifiers after deletion. An unchanged upsert retains the revision and update time. Find uses case-insensitive contains, search and text sorting, and `ne` includes null cells.

### Scalar and system column types

Studio supports `long_text` (multiline text up to 16,384 characters, without a
unique constraint) and `url` (an absolute HTTP or HTTPS URL). The editable
columns are available to Studio, Dataset nodes, Agent tools, and CSV import.
`created_time` and `updated_time` are UTC timestamps derived from row metadata,
including for existing rows. Reads, filters, sorting, and CSV export can use
these fields. CSV import leaves the system fields unmapped, and attempts to
write them through a row operation fail with `DATASET_COLUMN_READ_ONLY`.

Code export currently rejects dataset bindings whose schema includes these
new kinds. Python and TypeScript support will land with their parity tasks.
