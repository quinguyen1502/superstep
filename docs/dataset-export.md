# Connected Dataset exports

A Python or TypeScript project that uses Dataset nodes or Agent tools includes `datasets.json`. It lists each deployment binding, the field contract, and the operations the workflow uses. Multiple nodes and tools that use the same dataset share one binding. Display labels, Studio dataset IDs, row snapshots, and token values are absent from the contract.

Set each binding's `_BACKEND` to `superstep`. Set `_API_URL` to the base URL of the destination Superstep server, `_ID` to the destination dataset ID, and `_API_TOKEN` to a Dataset token issued for that dataset. The token needs read permission for Find rows and Get row, and write permission for Insert row and Upsert row. The Agent tool uses read permission. Use an HTTPS server URL for deployments and a separate destination dataset when running write examples.

## Wire format

Send `POST /api/datasets/{id}/connected` with a Bearer Dataset token and a JSON body. The request contains `version: 1`, one of `find_rows`, `get_row`, `insert_row`, and `upsert_row` in `operation`, the binding's `columns`, an explicit `fields` projection, and operation-specific `arguments`. The schema uses stable keys with `kind`, `required`, `unique`, `default`, and `options`. The server checks the contract against the destination before accessing rows. Additional destination columns are allowed when they are compatible with the operation.

Find accepts typed filters, sorting and paging. Get accepts `row_id`. Insert and Upsert accept a `values` object, and Upsert also requires its unique `key`. Write requests carry an `operation_id` of at most 128 characters. Scope is the token record, which stays the same when its secret is rotated. Retry an uncertain write with the same identity and arguments. An exact retry returns the original projected outcome. A different payload with that identity returns `DATASET_RECEIPT_CONFLICT`. The adapters reuse the same body on a transport retry.

Responses use the standard Superstep API envelope. `AUTH_TOKEN_INVALID` covers invalid, revoked, differently scoped, or insufficient tokens. `DATASET_BINDING_SCHEMA_MISMATCH` identifies the first incompatible field. `DATASET_SCHEMA_CONFLICT` means the destination changed during the request. In generated code, `DATASET_BINDING_MISSING` names the environment variables to set, `DATASET_BINDING_INVALID` reports invalid connection settings, and `DATASET_TRANSPORT_ERROR` indicates that the response could not be used.
