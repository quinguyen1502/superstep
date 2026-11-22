"""The public OpenAPI spec for workflow triggers, Chat v1 and Dataset Connected v1.

Served at GET /openapi.public.json (Swagger view at /docs/public) and committed as docs/api/openapi.public.json by
scripts/gen_public_openapi.py; the SDKs and the handbook API reference are built from that file.
"""
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from ..schemas.dataset_public import DatasetConnectedRequest
from .routes.datasets import execute_connected, router as datasets_router
from .routes.hooks import PUBLIC_TAG, router as hooks_router
from .routes.public_chat import CHAT_TAG, v1_router

TITLE, VERSION = "Superstep public API", "1.2.0"
DESCRIPTION = """Start workflow runs from other services, manage that workflow's schedules, talk to a published chat, and work with Dataset rows.

Authenticate with a **workflow token** (`wft_…`) in `X-Workflow-Token` or `Authorization: Bearer`. The workflow owner
creates tokens in the editor under **⋯ → API**; each token acts on one workflow only. A schedule it creates runs as
the token's owner.

Every response is an envelope: `{"success": true, "data": …, "error": null}` or
`{"success": false, "data": null, "error": {"code", "message", "details"}}`. `code` is the stable contract.

**Chat API v1** (`/api/public/v1/chat/{slug}`): the published chat page of a workflow. An anonymous visitor is identified
by a visitor token: send `X-Chat-Visitor: new` once, keep the `visitor_token` of the answer and send it back in
`X-Chat-Visitor`. Messages are sent over the WebSocket `/ws/public/v1/chat/{slug}`. Clients must ignore fields they do
not know: v1 only grows.

**Dataset Connected v1** (`/api/datasets/{dataset_id}/connected`): run row operations with a scoped Dataset token
(`dsat_…`) issued under **Datasets → Access → Dataset API tokens**.
"""
CHAT_DESCRIPTION = "Chat API v1: a published chat page, its chats, files and ratings (anonymous visitor, studio sign-in or a third-party HS256 user token)."


DATASET_TAG = "Datasets"
DATASET_DESCRIPTION = "Dataset Connected v1: typed row queries and writes with a dataset-scoped token."
DATASET_BEARER = "DatasetBearer"
DATASET_OPERATION_DESCRIPTION = """Send the explicit binding (`columns`) and field projection (`fields`) with each operation.
The server checks current column kinds, requirements, defaults, uniqueness, options, validation rules and Formula definitions.
Include keys used in filters, sorts, writes and unique targets in the binding. Search requires a binding for every
searchable column. Use flat filters or a filter tree. Aggregate requires its summary and grouping keys in `fields`.

| Operation | Token capability | Result in `data` |
| --- | --- | --- |
| `find_rows` | Read | Projected rows, `next_offset`, and `schema_revision`. Omit `arguments` for the first page with defaults. |
| `aggregate_rows` | Read | Summary groups, `group_by`, and `truncated`. |
| `get_row` | Read | One projected row. |
| `insert_row` | Write | `row` and `inserted`. |
| `upsert_row` | Write | `row` and `inserted`. The unique `key` must have a non-null entry in `values`. |
| `delete_row` | Allow row deletion (independent of Read and Write) | `row_id` and `deleted`. |

Insert and Upsert with a write-only token require `fields: []`. An empty field list on either operation always returns
only the row ID and revision in `row`. Other operations require at least one field.
Keep `operation_id` and the body identical when retrying Insert, Upsert or Delete. The receipt is scoped to the
token record and survives token rotation. During retention (30 days by default), an exact retry preserves the row ID
and original insert or delete outcome. A readable write replay sees the current projected row when it exists and
identifiers only after deletion. Reusing the identity with different arguments returns `DATASET_RECEIPT_CONFLICT`.
"""


def _dataset_operation(spec: dict, path: str) -> None:
    components = spec["components"]
    request = DatasetConnectedRequest.model_json_schema(ref_template="#/components/schemas/{model}")
    schemas = components["schemas"]
    schemas.update(request.pop("$defs"))
    schemas["DatasetConnectedRequest"] = request
    del schemas["DatasetConnectedInput"]

    op = spec["paths"][path]["post"]
    op.update(
        operationId="executeDatasetOperation", tags=[DATASET_TAG],
        description=DATASET_OPERATION_DESCRIPTION, security=[{DATASET_BEARER: []}],
    )
    op["parameters"] = [
        parameter for parameter in op["parameters"]
        if (parameter["in"], parameter["name"]) != ("header", "authorization")
    ]
    op["parameters"][0]["description"] = "ID of the Dataset for which the token was issued."
    content = op["requestBody"]["content"]["application/json"]
    content["schema"] = {"$ref": "#/components/schemas/DatasetConnectedRequest"}

    binding = {"version": 1, "columns": [{"key": "ticket", "kind": "text", "unique": True, "required": True}],
               "fields": ["ticket"]}
    content["examples"] = {
        operation: {"value": {**binding, "operation": operation, **payload}}
        for operation, payload in {
            "find_rows": {"arguments": {"limit": 10}},
            "aggregate_rows": {"arguments": {"summaries": {"ticket": "count"}}},
            "get_row": {"arguments": {"row_id": "row_123"}},
            "insert_row": {"fields": [], "arguments": {"values": {"ticket": "T-42"}},
                           "operation_id": "import:T-42"},
            "upsert_row": {"arguments": {"key": "ticket", "values": {"ticket": "T-42"}},
                           "operation_id": "sync:T-42"},
            "delete_row": {"arguments": {"key": "ticket", "value": "T-42"},
                           "operation_id": "delete:T-42"},
        }.items()
    }
    components["securitySchemes"][DATASET_BEARER] = {
        "type": "http", "scheme": "bearer", "bearerFormat": "dsat_…",
        "description": "Dataset API token scoped to one Dataset. Create it in the Dataset's Access tab.",
    }


def public_openapi() -> dict:
    dataset_route = next(route for route in datasets_router.routes if route.endpoint is execute_connected)
    spec = get_openapi(title=TITLE, version=VERSION, description=DESCRIPTION,
                       routes=[*hooks_router.routes, *v1_router.routes, dataset_route],
                       tags=[{"name": PUBLIC_TAG, "description": "Workflow-trigger API for external callers (workflow token): runs and schedules."},
                             {"name": CHAT_TAG, "description": CHAT_DESCRIPTION},
                             {"name": DATASET_TAG, "description": DATASET_DESCRIPTION}])
    schemes = spec["components"].setdefault("securitySchemes", {})
    schemes["ChatUserToken"] = {"type": "http", "scheme": "bearer", "bearerFormat": "JWT",
        "description": "HS256 user token signed server-side with a chat app key. aud=superstep-chat:<slug>; lifetime at most 1 hour. Never send the app secret to a client."}
    schemes["ChatVisitor"] = {"type": "apiKey", "in": "header", "name": "X-Chat-Visitor", "description": "Anonymous visitor token, or new to create one."}
    for item in spec["paths"].values():
        for op in item.values():
            if op.get("tags") == [CHAT_TAG]: op["security"] = [{"ChatUserToken": []}, {"ChatVisitor": []}, {}]
    _dataset_operation(spec, dataset_route.path)
    return spec


def install_public_docs(app: FastAPI) -> None:
    spec = public_openapi()

    @app.get("/openapi.public.json", include_in_schema=False)
    def public_spec(): return JSONResponse(spec)  # plain JSON (not an envelope), like /openapi.json

    @app.get("/docs/public", include_in_schema=False)
    def public_swagger(): return get_swagger_ui_html(openapi_url="/openapi.public.json", title=TITLE)
