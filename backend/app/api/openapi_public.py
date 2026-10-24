"""The public-only OpenAPI spec: the routes tagged `public` (the workflow-trigger API), nothing else.

Served at GET /openapi.public.json (Swagger view at /docs/public) and committed as docs/api/openapi.public.json by
scripts/gen_public_openapi.py; the SDKs and the handbook API reference are built from that file.
"""
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from .routes.hooks import PUBLIC_TAG, router as hooks_router

TITLE, VERSION = "Superstep public API", "1.0.0"
DESCRIPTION = """Start workflow runs from other services and read their results.

Authenticate with a **workflow token** (`wft_…`) in `X-Workflow-Token` or `Authorization: Bearer`. The workflow owner
creates tokens in the editor under **⋯ → API**; each token starts runs of one workflow only.

Every response is an envelope: `{"success": true, "data": …, "error": null}` or
`{"success": false, "data": null, "error": {"code", "message", "details"}}`. `code` is the stable contract.
"""


def public_openapi() -> dict:
    return get_openapi(title=TITLE, version=VERSION, description=DESCRIPTION, routes=hooks_router.routes,
                       tags=[{"name": PUBLIC_TAG, "description": "Workflow-trigger API for external callers (workflow token)."}])


def install_public_docs(app: FastAPI) -> None:
    spec = public_openapi()

    @app.get("/openapi.public.json", include_in_schema=False)
    def public_spec(): return JSONResponse(spec)  # plain JSON (not an envelope), like /openapi.json

    @app.get("/docs/public", include_in_schema=False)
    def public_swagger(): return get_swagger_ui_html(openapi_url="/openapi.public.json", title=TITLE)
