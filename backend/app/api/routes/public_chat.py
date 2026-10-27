"""The published chat page's API (TASK-0140, REQ-0074, DEC-0067), by slug and without the run right.

GET  /api/public/chat/{slug}                      the page: title, intro, suggestions, access, steps mode
GET  /api/public/chat/{slug}/frame                its frame-ancestors (for the nginx auth_request, TASK-0143)
GET  /api/public/chat/{slug}/sessions             {sessions}: the visitor's chats     POST a new chat ({embed?})
GET  /api/public/chat/{slug}/sessions/{sid}       one of them, in the page's steps mode

An anonymous visitor is the HttpOnly cookie `studio_chat_<hash>`, or the `X-Chat-Visitor` header (the widget, which
sends "new" when it has no token yet and then gets the new token back as `visitor_token`). signed_in uses the studio
session as other routes do.
"""
import hashlib
from typing import Optional
from fastapi import APIRouter, Depends, Request, Response
from fastapi.security import HTTPAuthorizationCredentials
from ...core import config
from ...core.client_ip import client_ip
from ...core.errors import AppError
from ...services.public_chat_service import Visitor
from ..deps import bearer, current_user, public_chat_service

router = APIRouter(prefix="/api/public/chat", tags=["public chat"])
VISITOR_HEADER = "x-chat-visitor"


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


def answer(request: Request, response: Response, slug: str, data, v: Visitor):
    """Keeps a new anonymous visitor: the cookie on a direct visit, `visitor_token` in the answer for the widget."""
    if not v.token: return data
    if request.headers.get(VISITOR_HEADER) is not None:
        return {**data, "visitor_token": v.token}
    secure = config.cookie_secure()  # over HTTPS the cookie also works inside an iframe (Chrome, Firefox: partitioned)
    for path in visitor_paths(slug):
        response.set_cookie(cookie_name(slug), v.token, max_age=400 * 86400, httponly=True, path=path,
                            samesite="none" if secure else "lax", secure=secure, partitioned=secure)
    return data


@router.get("/{slug}")
async def page(slug: str, request: Request, user=Depends(maybe_user), svc=Depends(public_chat_service)):
    await checked(request, svc); return svc.page(slug, user)


@router.get("/{slug}/frame")
def frame(slug: str, response: Response, svc=Depends(public_chat_service)):
    v = svc.frame_ancestors(slug); response.headers["Content-Security-Policy"] = f"frame-ancestors {v}"
    return {"frame_ancestors": v}


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
