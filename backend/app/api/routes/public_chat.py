"""The published chat page's API (TASK-0140, REQ-0074, DEC-0067), by slug and without the run right.

GET  /api/public/chat/{slug}                      the page: title, intro, suggestions, access, steps mode
GET  /api/public/chat/{slug}/sessions             {sessions}: the visitor's chats     POST a new chat ({embed?})
GET  /api/public/chat/{slug}/sessions/{sid}       one of them, in the page's steps mode
GET  /api/public/chat/{slug}/logo?v=<hash>        the chat's logo image (TASK-0145)
POST /api/public/chat/{slug}/sessions/{sid}/attachments        one file (multipart `file`), before the message (TASK-0174)
GET  /api/public/chat/{slug}/sessions/{sid}/attachments/{aid}  download it      DELETE it while unsent
WS   /ws/public/chat/{slug}                       {chat_session_id, message} or {chat_session_id, response, node?}: the run
                                                  streams as public_event()s (TASK-0141); ?visitor= for the widget
GET  /api/public/chat-frame?path=/c/{slug}        the page's frame-ancestors in Content-Security-Policy (TASK-0143):
                                                  nginx asks it with auth_request (X-Original-URI) before serving /c/

An anonymous visitor is the HttpOnly cookie `studio_chat_<hash>`, or the `X-Chat-Visitor` header (the widget, which
sends "new" when it has no token yet and then gets the new token back as `visitor_token`). signed_in uses the studio
session as other routes do.
"""
import hashlib, tempfile
from urllib.parse import quote
from typing import BinaryIO, Optional
from fastapi import APIRouter, Depends, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials
from ...core import config, security
from ...core.client_ip import client_ip
from ...core.errors import AppError
from ...engine import locale
from ...schemas.chat import ChatRatingIn
from ...services.public_chat_service import Visitor, public_event
from ...services.run_service import error_event
from ..static import CHAT_PAGE
from ..deps import _same_origin, bearer, chat_attachment_service, current_user, public_chat_service, run_service, ws_user

router = APIRouter(prefix="/api/public/chat", tags=["public chat"])
root_router = APIRouter()  # the socket and the frame check, outside the prefix
VISITOR_HEADER = "x-chat-visitor"
COOKIE_AGE = 400 * 86400  # browsers keep a cookie at most 400 days


def cookie_name(slug: str) -> str: return "studio_chat_" + hashlib.sha1(slug.encode()).hexdigest()[:10]


def visitor_paths(slug: str) -> tuple[str, str]: return f"/api/public/chat/{slug}", f"/ws/public/chat/{slug}"


def maybe_user(request: Request, cred: Optional[HTTPAuthorizationCredentials] = Depends(bearer)) -> Optional[dict]:
    """The signed-in studio user, or None (an anonymous visitor)."""
    try: return current_user(request, cred)
    except AppError as e:
        if e.code == "AUTH_CSRF": raise
        return None


def token_of(request: Request, slug: str) -> Optional[str]:
    h = request.headers.get(VISITOR_HEADER)
    return h if h is not None else request.cookies.get(cookie_name(slug))


async def checked(request: Request, svc) -> None:
    await svc.check_read(client_ip(request.client.host if request.client else None, request.headers.get("x-forwarded-for")))


def logo_response(logo, versioned: bool, scope: str = "public") -> Response:
    """A chat's logo. With ?v=<hash> its address changes with the image, so it is cached for good."""
    age = "max-age=31536000, immutable" if versioned else "max-age=300"
    return Response(logo.data, media_type=logo.mime, headers={"Cache-Control": f"{scope}, {age}", "X-Content-Type-Options": "nosniff"})


MULTIPART_SLACK = 64 * 1024  # the multipart envelope around one file


UPLOAD_PIECE = 1024 * 1024  # read an upload in pieces of this size (TASK-0200)


async def read_upload(request: Request) -> tuple[str, BinaryIO]:
    """(file name, file) of a one-file multipart upload. A body that says it is larger than the operator's ceiling is
    refused before it is read (TASK-0174, DEC-0072 decision 3). The multipart parser then spools the whole part to a
    temporary file before the ceiling is checked, so a body without a Content-Length (chunked) is only bounded by the
    proxy in front (nginx client_max_body_size, which also buffers it and sends a length); the file is then copied in
    pieces and refused past the ceiling, so it is never one bytes object (TASK-0200, corrected in TASK-0203). The
    caller closes the file."""
    ceiling = config.chat_attachment_max_mb() * 1024 * 1024
    too_large = AppError("CHAT_ATTACHMENT_TOO_LARGE", max_mb=config.chat_attachment_max_mb())
    try: declared = int(request.headers.get("content-length") or 0)
    except ValueError: declared = 0
    if declared > ceiling + MULTIPART_SLACK: raise too_large
    form = await request.form(max_files=1, max_fields=1)
    try:
        f = form.get("file")
        if f is None or isinstance(f, str): raise AppError("CHAT_ATTACHMENT_TYPE", allowed="")
        out, size = tempfile.SpooledTemporaryFile(max_size=UPLOAD_PIECE), 0
        try:
            while piece := await f.read(UPLOAD_PIECE):
                size += len(piece)
                if size > ceiling: raise too_large
                out.write(piece)
        except BaseException:
            out.close(); raise
        out.seek(0)
        return f.filename or "", out
    finally:
        await form.close()


def file_response(a, chunks) -> Response:
    """A chat file, always as a download that the browser must not sniff or render (REQ-0077). The bytes are streamed
    from the attachment storage through the backend, whatever the backend: never a bucket URL (DEC-0074 decision 3)."""
    ascii_name = a.name.encode("ascii", "ignore").decode().replace('"', "") or "file"
    return StreamingResponse(chunks, media_type=a.mime, headers={
        "Content-Disposition": f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(a.name)}", "Content-Length": str(a.size),
        "X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store", "Content-Security-Policy": "sandbox"})


def answer(request: Request, response: Response, slug: str, data, v: Visitor):
    """Keeps a new anonymous visitor: the cookie on a direct visit, `visitor_token` in the answer for the widget."""
    if not v.token: return data
    if request.headers.get(VISITOR_HEADER) is not None:
        return {**data, "visitor_token": v.token}
    # over HTTPS the cookie also works inside an iframe (Chrome, Firefox: partitioned). Written by hand: Starlette's
    # partitioned= needs Python 3.14, and the token is [0-9a-f.] only, so nothing needs quoting
    flags = "SameSite=None; Secure; Partitioned" if config.cookie_secure() else "SameSite=Lax"
    for path in visitor_paths(slug):
        response.headers.append("set-cookie", f"{cookie_name(slug)}={v.token}; Max-Age={COOKIE_AGE}; Path={path}; HttpOnly; {flags}")
    return data


@router.get("/{slug}")
async def page(slug: str, request: Request, user=Depends(maybe_user), svc=Depends(public_chat_service)):
    await checked(request, svc); return svc.page(slug, user)


@router.get("/{slug}/logo")
async def logo(slug: str, request: Request, v: Optional[str] = None, svc=Depends(public_chat_service)):
    await checked(request, svc); return logo_response(svc.logo(slug), v is not None)


@router.get("/{slug}/sessions")
async def sessions(slug: str, request: Request, response: Response, user=Depends(maybe_user), svc=Depends(public_chat_service)):
    await checked(request, svc); rows, v = svc.sessions(slug, token_of(request, slug), user)
    return answer(request, response, slug, {"sessions": rows}, v)


@router.post("/{slug}/sessions")
async def create(slug: str, request: Request, response: Response, user=Depends(maybe_user), svc=Depends(public_chat_service)):
    await checked(request, svc)
    try: body = await request.json()
    except ValueError: body = {}
    s, v = svc.create(slug, token_of(request, slug), user, embed=bool(isinstance(body, dict) and body.get("embed")))
    return answer(request, response, slug, s, v)


@router.get("/{slug}/sessions/{sid}")
async def session(slug: str, sid: str, request: Request, response: Response, user=Depends(maybe_user), svc=Depends(public_chat_service)):
    await checked(request, svc); s, v = svc.get(slug, sid, token_of(request, slug), user)
    return answer(request, response, slug, s, v)


@router.post("/{slug}/sessions/{sid}/attachments")
async def upload(slug: str, sid: str, request: Request, response: Response, user=Depends(maybe_user), svc=Depends(chat_attachment_service)):
    await checked(request, svc.pub)
    name, data = await read_upload(request)
    with data:
        ip = client_ip(request.client.host if request.client else None, request.headers.get("x-forwarded-for"))
        out, v = await svc.public_upload(slug, sid, token_of(request, slug), user, ip, name, data)
    return answer(request, response, slug, out, v)


@router.get("/{slug}/sessions/{sid}/attachments/{aid}")
async def download(slug: str, sid: str, aid: str, request: Request, user=Depends(maybe_user), svc=Depends(chat_attachment_service)):
    await checked(request, svc.pub)
    a, _v = svc.public_file(slug, sid, aid, token_of(request, slug), user)
    return file_response(a, svc.chunks(a))


@router.delete("/{slug}/sessions/{sid}/attachments/{aid}")
async def remove(slug: str, sid: str, aid: str, request: Request, response: Response, user=Depends(maybe_user), svc=Depends(chat_attachment_service)):
    await checked(request, svc.pub)
    data, v = svc.public_delete(slug, sid, aid, token_of(request, slug), user)
    return answer(request, response, slug, data, v)


@router.put("/{slug}/sessions/{sid}/turns/{tid}/rating")
async def rate(slug: str, sid: str, tid: str, body: ChatRatingIn, request: Request, response: Response, user=Depends(maybe_user), svc=Depends(public_chat_service)):
    await checked(request, svc)
    data, v = svc.rate(slug, sid, tid, token_of(request, slug), user, body.value, body.comment)
    return answer(request, response, slug, data, v)


@router.delete("/{slug}/sessions/{sid}/turns/{tid}/rating")
async def unrate(slug: str, sid: str, tid: str, request: Request, response: Response, user=Depends(maybe_user), svc=Depends(public_chat_service)):
    await checked(request, svc)
    data, v = svc.unrate(slug, sid, tid, token_of(request, slug), user)
    return answer(request, response, slug, data, v)


@root_router.get("/api/public/chat-frame")
def frame(request: Request, response: Response, path: Optional[str] = None, svc=Depends(public_chat_service)):
    """Always 200 (auth_request only passes 2xx through): `frame-ancestors` of the chat page in `path`, or of the page nginx
    is serving (X-Original-URI); 'none' for anything that is not a published chat page."""
    target = (path if path is not None else request.headers.get("x-original-uri") or "").split("?", 1)[0]
    m = CHAT_PAGE.match(target)
    v = svc.frame_ancestors(m.group(1)) if m else "'none'"
    response.headers["Content-Security-Policy"] = f"frame-ancestors {v}"
    return {"frame_ancestors": v}


@root_router.websocket("/ws/public/chat/{slug}")
async def ws_public_chat(ws: WebSocket, slug: str):
    """One message or answer per connection, as /ws/run: the run streams, then the socket closes. Same origin only (the
    page and the embed's iframe are served by the studio); a cancel is {"type": "cancel"}."""
    if not _same_origin(ws.headers.get("origin"), ws.headers.get("host")):
        await ws.close(code=4403); return
    await ws.accept()
    try: req = await ws.receive_json()
    except (WebSocketDisconnect, ValueError, KeyError): return
    svc, runs = public_chat_service(), run_service()
    try: user = ws_user(ws) if ws.cookies.get(security.SESSION_COOKIE) or ws.query_params.get("token") else None
    except AppError: user = None
    try:
        ip = client_ip(ws.client.host if ws.client else None, ws.headers.get("x-forwarded-for"))
        token = ws.query_params.get("visitor") or ws.cookies.get(cookie_name(slug))
        plan, owner, mode, reply = await svc.plan_message(slug, token, user, req, ip, runs.plan)
        if plan.ports is not None: plan.ports.locale = locale.pick(req.get("locale") if isinstance(req, dict) else None, ws.headers.get("accept-language"))
    except AppError as e:
        await ws.send_json(error_event(e.to_dict())); await ws.close(); return

    state = {"connected": True}

    async def send(ev) -> bool:
        out = public_event(ev, mode, reply)
        if out is None: return state["connected"]
        try: await ws.send_json(out); return True
        except Exception: state["connected"] = False; return False

    async def listen() -> str:
        try:
            while True:
                m = await ws.receive_json()
                if isinstance(m, dict) and m.get("type") == "cancel": return "cancelled"
        except (WebSocketDisconnect, RuntimeError, ValueError):
            state["connected"] = False
            return "disconnected"

    await runs.execute(plan, send, listen, owner)
    if state["connected"]:
        try: await ws.close()
        except Exception: pass
