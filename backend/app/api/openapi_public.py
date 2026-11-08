"""The public-only OpenAPI spec: the routes tagged `public` (the workflow-trigger API) and the Chat API v1 (tag `Chat`,
TASK-0215), nothing else.

Served at GET /openapi.public.json (Swagger view at /docs/public) and committed as docs/api/openapi.public.json by
scripts/gen_public_openapi.py; the SDKs and the handbook API reference are built from that file.
"""
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from .routes.hooks import PUBLIC_TAG, router as hooks_router
from .routes.public_chat import CHAT_TAG, v1_router

TITLE, VERSION = "Superstep public API", "1.2.0"
DESCRIPTION = """Start workflow runs from other services, manage that workflow's schedules, and talk to a published chat.

Authenticate with a **workflow token** (`wft_…`) in `X-Workflow-Token` or `Authorization: Bearer`. The workflow owner
creates tokens in the editor under **⋯ → API**; each token acts on one workflow only. A schedule it creates runs as
the token's owner.

Every response is an envelope: `{"success": true, "data": …, "error": null}` or
`{"success": false, "data": null, "error": {"code", "message", "details"}}`. `code` is the stable contract.

**Chat API v1** (`/api/public/v1/chat/{slug}`): the published chat page of a workflow. An anonymous visitor is identified
by a visitor token: send `X-Chat-Visitor: new` once, keep the `visitor_token` of the answer and send it back in
`X-Chat-Visitor`. Messages are sent over the WebSocket `/ws/public/v1/chat/{slug}`. Clients must ignore fields they do
not know: v1 only grows.
"""
CHAT_DESCRIPTION = "Chat API v1: a published chat page, its chats, files and ratings (anonymous visitor, studio sign-in or a third-party HS256 user token)."


def public_openapi() -> dict:
    spec = get_openapi(title=TITLE, version=VERSION, description=DESCRIPTION, routes=hooks_router.routes + v1_router.routes,
                       tags=[{"name": PUBLIC_TAG, "description": "Workflow-trigger API for external callers (workflow token): runs and schedules."},
                             {"name": CHAT_TAG, "description": CHAT_DESCRIPTION}])
    schemes = spec["components"].setdefault("securitySchemes", {})
    schemes["ChatUserToken"] = {"type": "http", "scheme": "bearer", "bearerFormat": "JWT",
        "description": "HS256 user token signed server-side with a chat app key. aud=superstep-chat:<slug>; lifetime at most 1 hour. Never send the app secret to a client."}
    schemes["ChatVisitor"] = {"type": "apiKey", "in": "header", "name": "X-Chat-Visitor", "description": "Anonymous visitor token, or new to create one."}
    for item in spec["paths"].values():
        for op in item.values():
            if op.get("tags") == [CHAT_TAG]: op["security"] = [{"ChatUserToken": []}, {"ChatVisitor": []}, {}]
    return spec



def install_public_docs(app: FastAPI) -> None:
    spec = public_openapi()

    @app.get("/openapi.public.json", include_in_schema=False)
    def public_spec(): return JSONResponse(spec)  # plain JSON (not an envelope), like /openapi.json

    @app.get("/docs/public", include_in_schema=False)
    def public_swagger(): return get_swagger_ui_html(openapi_url="/openapi.public.json", title=TITLE)
