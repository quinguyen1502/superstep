"""HTTP server spans (STUDIO_OTEL_INSTRUMENT=1 with a traces exporter): one span per request or WebSocket, named by
method and route template, never the raw path or query; the probe routes are not traced. The span is current while
the request runs, so SQL and Redis spans of the request become its children. Off, it only checks a flag."""
from __future__ import annotations
from typing import Callable
from .http_metrics import route_of


class HttpSpans:
    def __init__(self, app, telemetry: Callable):
        self.app, self.telemetry = app, telemetry

    async def __call__(self, scope, receive, send):
        t = self.telemetry()
        handle = t.open_http(scope) if t.instrumented else None
        if handle is None: return await self.app(scope, receive, send)
        status = [None if scope["type"] == "websocket" else 500]

        async def capture(message):
            if message["type"] == "http.response.start": status[0] = int(message["status"])
            await send(message)
        try: await self.app(scope, receive, capture)
        finally: t.close_http(handle, route_of(scope), status[0])
