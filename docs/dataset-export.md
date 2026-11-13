# Dataset exports

A Python or TypeScript project that uses Dataset nodes or Agent tools includes `datasets.json`. It lists each deployment binding, the field contract, and the operations the workflow uses. Multiple nodes and tools that use the same dataset share one binding. Display labels, Studio dataset IDs, row snapshots, and token values are absent from the contract.

## Superstep API

For a connected binding, set `_BACKEND` to `superstep`. Set `_API_URL` to the base URL of the destination Superstep server, `_ID` to the destination dataset ID, and `_API_TOKEN` to a Dataset token issued for that dataset. The token needs read permission for Find rows and Get row, and write permission for Insert row and Upsert row. The Agent tool uses read permission. Use an HTTPS server URL for deployments and a separate destination dataset when running write examples.

### Wire format

Send `POST /api/datasets/{id}/connected` with a Bearer Dataset token and a JSON body. The request contains `version: 1`, one of `find_rows`, `get_row`, `insert_row`, and `upsert_row` in `operation`, the binding's `columns`, an explicit `fields` projection, and operation-specific `arguments`. The schema uses stable keys with `kind`, `required`, `unique`, `default`, and `options`. The server checks the contract against the destination before accessing rows. Additional destination columns are allowed when they are compatible with the operation.

Find accepts typed filters, sorting and paging. Get accepts `row_id`. Insert and Upsert accept a `values` object, and Upsert also requires its unique `key`. Write requests carry an `operation_id` of at most 128 characters. Scope is the token record, which stays the same when its secret is rotated. Retry an uncertain write with the same identity and arguments. An exact retry returns the original projected outcome. A different payload with that identity returns `DATASET_RECEIPT_CONFLICT`. The adapters reuse the same body on a transport retry.

Responses use the standard Superstep API envelope. `AUTH_TOKEN_INVALID` covers invalid, revoked, differently scoped, or insufficient tokens. `DATASET_BINDING_SCHEMA_MISMATCH` identifies the first incompatible field. `DATASET_SCHEMA_CONFLICT` means the destination changed during the request. In generated code, `DATASET_BINDING_MISSING` names the environment variables to set, `DATASET_BINDING_INVALID` reports invalid connection settings, and `DATASET_TRANSPORT_ERROR` indicates that the response could not be used.


## Python standalone

Choose the backend for each binding independently. An exported Python project can read a connected dataset and write to a standalone database in the same run.

| Backend | Settings for each binding |
| --- | --- |
| `sqlite` | `_SQLITE_PATH` for the SQLite file and `_ID` for a stable dataset name in that file |
| `postgresql` | `_POSTGRES_DSN` for an existing PostgreSQL database and `_ID` for a stable dataset name in it |

Set `_BACKEND` to the chosen value. Install the requirements, export the environment variables, and run `python agent.py --setup-datasets`. Setup creates the project tables and initializes each standalone binding with its exported schema. Repeating setup with the same schema preserves rows and write receipts. The PostgreSQL account needs table creation privileges for setup and read/write privileges on the project tables at runtime.

The startup check reports `DATASET_SETUP_REQUIRED` when a database or binding has not been initialized. `DATASET_BINDING_SCHEMA_MISMATCH` identifies a binding whose stored schema differs from the export. Setup rejects incompatible changes and preserves the stored schema and rows. Standalone retries with the same operation ID and arguments return the previously stored result.

## TypeScript standalone

Choose the backend for each binding independently. An exported TypeScript project can read a connected dataset and write to a standalone database in the same run. The settings are the same as for Python: `_SQLITE_PATH` or `_POSTGRES_DSN`, plus `_ID` and `_BACKEND`.

SQLite uses the runtime's built-in `node:sqlite` module. Node.js 22.13 or newer includes it. Node.js 22.5 through 22.12 also need `NODE_OPTIONS=--experimental-sqlite`. Deno 2.2 or newer includes the same module. PostgreSQL uses the `pg` package, which the project `package.json` declares. The single-file export imports it as `npm:pg@^8` so Deno can fetch it.

Install the project dependencies, export the environment variables, and run `npx tsx agent.ts --setup-datasets` or `deno run --allow-env --allow-read --allow-write --allow-net --allow-sys=homedir agent.ts --setup-datasets`. Setup creates the project tables and initializes each standalone binding with its exported schema. Repeating setup with the same schema preserves rows and write receipts. The PostgreSQL account needs table creation privileges for setup and read/write privileges on the project tables at runtime.

The startup check reports `DATASET_SETUP_REQUIRED` when a database or binding has not been initialized. `DATASET_BINDING_SCHEMA_MISMATCH` identifies a binding whose stored schema differs from the export. `DATASET_STORAGE_ERROR` reports that SQLite is unavailable or the database could not be opened. Setup rejects incompatible changes and preserves the stored schema and rows. Standalone retries with the same operation ID and arguments return the previously stored result.
