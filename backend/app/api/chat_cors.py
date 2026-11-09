"""Public chat CORS is token-only, independent of the studio's global CORS configuration."""
from __future__ import annotations
import re
from urllib.parse import urlsplit
from starlette.datastructures import MutableHeaders
from starlette.requests import Request
from starlette.responses import Response
from ..core import config
from ..core.client_ip import client_ip
from ..core.errors import AppError
from .error_handlers import respond

CHAT_PATH = re.compile(r"^/api/public/(?:v1/)?chat/([^/]+)(?:/|$)")
METHODS = "GET, POST, PUT, DELETE, OPTIONS"
HEADERS = "Authorization, Content-Type, X-Requested-With, X-Chat-Visitor"


def _matches_chat_origin(connection, origin: str) -> bool:
    try:
        parsed = urlsplit(origin)
        if parsed.scheme not in ("http", "https") or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment: return False
        scheme = {"ws": "http", "wss": "https"}.get(connection.url.scheme, connection.url.scheme)
        expected = urlsplit(f"{scheme}://{connection.headers.get('host', '')}")
        own = parsed.scheme == expected.scheme and parsed.hostname == expected.hostname and (parsed.port or (443 if parsed.scheme == "https" else 80)) == (expected.port or (443 if scheme == "https" else 80))
        # The configured public URL describes a trusted reverse proxy's external origin.
        return own or bool(config.public_url() and origin.rstrip("/") == config.public_url())
    except ValueError: return False


def same_chat_origin(connection) -> bool:
    origin = connection.headers.get("origin")
    # Native/server clients send no Origin; app keys still enforce their origin policy.
    return not origin or _matches_chat_origin(connection, origin)


def chat_request_origin(request) -> str | None:
    """Browsers omit Origin on same-origin GETs. Accept only their own verified referrer.

    Cross-site requests still require Origin. Neither a parent-origin claim nor an
    arbitrary Referer can grant an app key access to a different site's origin.
    """
    origin = request.headers.get("origin")
    if origin is not None: return origin
    if request.headers.get("sec-fetch-site") != "same-origin": return None
    try:
        referrer = urlsplit(request.headers.get("referer", ""))
        if referrer.scheme not in ("http", "https") or not referrer.netloc or referrer.username or referrer.password: return None
        candidate = f"{referrer.scheme}://{referrer.netloc}"
        return candidate if _matches_chat_origin(request, candidate) else None
    except ValueError: return None


def request_ip(connection) -> str:
    return client_ip(connection.client.host if connection.client else None, connection.headers.get("x-forwarded-for"))


class ChatCors:
    def __init__(self, app, public): self.app, self.public = app, public

    async def __call__(self, scope, receive, send):
        match = CHAT_PATH.match(scope.get("path", "")) if scope["type"] == "http" else None
        if not match: return await self.app(scope, receive, send)
        request = Request(scope)
        if same_chat_origin(request): return await self.app(scope, receive, send)
        origin = request.headers.get("origin", "")
        headers = {"Access-Control-Allow-Origin": origin, "Vary": "Origin"}
        if request.method == "OPTIONS":
            asked = {h.strip().lower() for h in request.headers.get("access-control-request-headers", "").split(",") if h.strip()}
            allowed = {h.strip().lower() for h in HEADERS.split(",")}
            if "authorization" not in asked or not asked <= allowed or request.headers.get("access-control-request-method") not in METHODS.split(", "):
                return await respond(AppError("CHAT_TOKEN_REQUIRED"))(scope, receive, send)
            headers.update({"Access-Control-Allow-Methods": METHODS, "Access-Control-Allow-Headers": HEADERS, "Access-Control-Max-Age": "300"})
            return await Response(status_code=204, headers=headers)(scope, receive, send)
        svc = self.public()
        try:
            await svc.check_read(request_ip(request)); request.state.chat_read_checked = True
            scheme, _, token = request.headers.get("authorization", "").partition(" ")
            request.state.chat_app_user = await svc.authenticate(match[1], token if scheme.lower() == "bearer" else "", origin, request_ip(request))
        except AppError as e:
            response = respond(e)
            # These errors occur only after a valid signature and the key's origin check: clients can refresh safely.
            if e.code in ("CHAT_TOKEN_EXPIRED", "CHAT_APP_KEY_REVOKED"): response.headers.update(headers)
            return await response(scope, receive, send)

        async def cors_send(message):
            if message["type"] == "http.response.start":
                message["headers"] = [(k, v) for k, v in message.get("headers", []) if not k.lower().startswith(b"access-control-")]
                out = MutableHeaders(scope=message)
                out["Access-Control-Allow-Origin"] = origin
                out.add_vary_header("Origin")
                out["Access-Control-Expose-Headers"] = "Retry-After, Content-Disposition"
            await send(message)
        await self.app(scope, receive, cors_send)
