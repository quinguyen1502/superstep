"""All-in-one image: the built frontend (Vite `dist/`) served by the API on the same origin, so one port carries the UI,
/api and /ws (PaaS platforms route one port per service). Unknown non-API paths get index.html (SPA routes); unknown
/api and /ws paths keep the API's 404 envelope.

Frames (TASK-0143, DEC-0067 decision 6): no page of the studio may be framed by another site, except a published chat
page /c/{slug}, which the sites in its `embed_origins` may frame. nginx does the same in Compose."""
import os, re
from typing import Callable
from fastapi import FastAPI
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException
from starlette.staticfiles import StaticFiles

API_PREFIXES = ("api/", "ws/")


class SPAStaticFiles(StaticFiles):
    async def __call__(self, scope, receive, send):
        if scope["type"] == "websocket":  # an unknown WebSocket path: refuse instead of StaticFiles' http-only assert
            await send({"type": "websocket.close", "code": 1008}); return
        await super().__call__(scope, receive, send)

    async def get_response(self, path: str, scope):
        try: return await super().get_response(path, scope)
        except HTTPException as e:
            if e.status_code != 404 or path.startswith(API_PREFIXES) or path in ("api", "ws"): raise
            return await super().get_response("index.html", scope)


CHAT_PAGE = re.compile(r"^/c/([a-z0-9-]+)/?$")
DENY = [(b"x-frame-options", b"DENY"), (b"content-security-policy", b"frame-ancestors 'none'")]


class FrameHeaders:
    """ASGI middleware: the deny headers on every HTTP response, or the chat page's own `frame-ancestors`."""
    def __init__(self, app, ancestors: Callable[[str], str]):
        self.app, self.ancestors = app, ancestors

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http": return await self.app(scope, receive, send)
        m = CHAT_PAGE.match(scope.get("path") or "")
        extra = [(b"content-security-policy", f"frame-ancestors {await run_in_threadpool(self.ancestors, m.group(1))}".encode())] if m else DENY

        async def with_headers(message):
            if message["type"] == "http.response.start":
                names = {k for k, _ in extra}
                message = {**message, "headers": [h for h in message.get("headers", []) if h[0].lower() not in names] + extra}
            await send(message)
        await self.app(scope, receive, with_headers)


def no_frames(slug: str) -> str: return "'none'"


def mount_frontend(app: FastAPI, directory: str, ancestors: Callable[[str], str] = no_frames) -> None:
    if directory and os.path.isfile(os.path.join(directory, "index.html")):
        app.mount("/", SPAStaticFiles(directory=directory, html=True), name="frontend")
        app.add_middleware(FrameHeaders, ancestors=ancestors)
