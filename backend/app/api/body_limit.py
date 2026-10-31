"""Request body ceilings, enforced by the app whatever proxy is in front (TASK-0207).

nginx bounds bodies in Compose; the all-in-one image and PaaS deploys have no nginx, and an unauthenticated route that
reads the whole body (`await request.body()`) before any check would otherwise take whatever it is sent. A body that
says it is too large is refused before it is read; one without a length is counted and refused once it passes.
- the chat platform and approval callbacks (no sign-in): 1 MB;
- the upload routes (chat attachments, workflow import, knowledge documents): their own ceilings plus multipart room;
- everything else: STUDIO_MAX_BODY_MB (default 10).
"""
from __future__ import annotations
import json, re
from ..core import config
from ..core.errors import AppError

MB = 1024 * 1024
SLACK = MB  # multipart boundaries and headers
CALLBACK_MAX = MB
IMPORT_MAX = 50 * MB  # services.import_service.ZIP_MAX
KB_MAX = 10 * MB      # services.knowledge_service.MAX_BYTES
CALLBACK = re.compile(r"^/api/(approvals/callback|channels/events)/[^/]+(/[^/]+)?/?$")
UPLOADS = re.compile(r"^/api/(chat/sessions/[^/]+/attachments|public/chat/[^/]+/sessions/[^/]+/attachments|import|knowledge-bases/[^/]+/documents)/?$")


def limit_for(path: str) -> int:
    if CALLBACK.match(path): return CALLBACK_MAX
    if UPLOADS.match(path): return max(config.chat_attachment_max_mb() * MB, IMPORT_MAX, KB_MAX) + SLACK
    return config.max_body_mb() * MB


class BodyLimit:
    """ASGI middleware: 413 PAYLOAD_TOO_LARGE in the error envelope past the route's ceiling."""
    def __init__(self, app): self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("method") in ("GET", "HEAD", "OPTIONS"): return await self.app(scope, receive, send)
        limit = limit_for(scope.get("path") or "")
        length = dict(scope.get("headers") or []).get(b"content-length")
        try: declared = int(length) if length is not None else None
        except ValueError: declared = None
        if declared is not None and declared > limit: return await self._refuse(send)
        seen = 0
        async def counted():
            nonlocal seen
            msg = await receive()
            if msg.get("type") == "http.request":
                seen += len(msg.get("body") or b"")
                if seen > limit: raise AppError("PAYLOAD_TOO_LARGE")
            return msg
        return await self.app(scope, counted, send)

    @staticmethod
    async def _refuse(send):
        body = json.dumps({"success": False, "data": None, "error": AppError("PAYLOAD_TOO_LARGE").to_dict()}).encode()
        await send({"type": "http.response.start", "status": 413, "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]})
        await send({"type": "http.response.body", "body": body})
