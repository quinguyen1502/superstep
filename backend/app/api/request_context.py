"""Request id for log correlation: takes `X-Request-ID` when it is a short safe token, otherwise makes one, keeps it in
a context variable for the request's log lines and echoes it in the response header. WebSockets get an id too."""
from __future__ import annotations
from ..core.logging import request_context, safe_request_id

HEADER = b"x-request-id"


class RequestContext:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket"): return await self.app(scope, receive, send)
        incoming = next((v.decode("latin-1") for k, v in scope.get("headers") or [] if k == HEADER), None)
        rid = safe_request_id(incoming)

        async def echo(message):
            if message["type"] == "http.response.start":
                headers = [(k, v) for k, v in message.get("headers") or [] if k.lower() != HEADER]
                message = {**message, "headers": headers + [(HEADER, rid.encode())]}
            await send(message)
        with request_context(rid):
            return await self.app(scope, receive, echo if scope["type"] == "http" else send)
