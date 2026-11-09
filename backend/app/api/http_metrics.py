"""HTTP metrics: request count and duration by route template, method and status class; open WebSockets.

A plain ASGI middleware on the Telemetry meter. The label is the matched route template (`/api/workflows/{wid}`),
never the raw path or query; requests that match no route count as `unmatched`. With metrics off it only checks a
flag and passes the request on.
"""
from __future__ import annotations
import time
from typing import Callable


def route_of(scope) -> str:
    route = scope.get("route")
    return getattr(route, "path", None) or "unmatched"


class HttpMetrics:
    def __init__(self, app, telemetry: Callable):
        self.app, self.telemetry = app, telemetry

    async def __call__(self, scope, receive, send):
        t = self.telemetry()
        if not t.metrics_enabled or scope["type"] not in ("http", "websocket"): return await self.app(scope, receive, send)
        if scope["type"] == "websocket":
            t.websocket(1)
            try: return await self.app(scope, receive, send)
            finally: t.websocket(-1)
        started = time.perf_counter(); status = [500]

        async def capture(message):
            if message["type"] == "http.response.start": status[0] = int(message["status"])
            await send(message)
        try: await self.app(scope, receive, capture)
        finally:
            t.http_request(route_of(scope), scope.get("method") or "GET", status[0], (time.perf_counter() - started) * 1000)
