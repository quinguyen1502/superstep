import time
from fastapi import APIRouter, Depends, Request, Response
from ...core import config, permissions as P, security
from ...core.client_ip import client_ip
from ...schemas.auth import Credentials, DeviceDecision, DeviceStart, PasswordChange, ResetConfirm, ResetRequest, TokenName
from ..deps import auth_service, current_user, need, pat_service

router = APIRouter(prefix="/api", tags=["auth"])


def _signed_in(session: dict, response: Response) -> dict:
    """The browser keeps the JWT in an HttpOnly cookie (TASK-0045). The body still has `token` for API clients."""
    response.set_cookie(security.SESSION_COOKIE, session["token"], max_age=max(1, session["expires_at"] - int(time.time())),
                        httponly=True, samesite="lax", secure=config.cookie_secure(), path="/")
    return session


@router.post("/auth/register")
def register(cr: Credentials, response: Response, svc=Depends(auth_service)): return _signed_in(svc.register(cr.email, cr.password), response)

@router.post("/auth/login")
def login(cr: Credentials, response: Response, svc=Depends(auth_service)): return _signed_in(svc.login(cr.email, cr.password), response)

@router.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie(security.SESSION_COOKIE, path="/", httponly=True, samesite="lax", secure=config.cookie_secure())
    return {"ok": True}

@router.get("/auth/options")
def options(svc=Depends(auth_service)): return svc.options()

@router.post("/auth/password-reset")
def request_reset(body: ResetRequest, svc=Depends(auth_service)): return svc.request_reset(body.email)

@router.post("/auth/password-reset/confirm")
def confirm_reset(body: ResetConfirm, svc=Depends(auth_service)): return svc.confirm_reset(body.token, body.password)

@router.post("/admin/users/{target}/password-reset")
def admin_reset_link(target: str, user=Depends(need(P.USERS_MANAGE)), svc=Depends(auth_service)):
    return svc.admin_reset_link(user["id"], target)

@router.get("/me")
def me(user=Depends(current_user)): return user

@router.get("/me/tokens")
def list_tokens(user=Depends(current_user), svc=Depends(pat_service)): return svc.list(user["id"])

@router.post("/me/tokens")
def create_token(body: TokenName, user=Depends(current_user), svc=Depends(pat_service)): return svc.create(user["id"], body.name)

@router.delete("/me/tokens/{tid}")
def revoke_token(tid: str, user=Depends(current_user), svc=Depends(pat_service)): return svc.revoke(user["id"], tid)

@router.post("/auth/cli/devices")
async def start_cli_device(body: DeviceStart, request: Request, svc=Depends(pat_service)):
    return await svc.start_device_from(client_ip(request.client.host if request.client else None, request.headers.get("x-forwarded-for")), body.name)

@router.get("/auth/cli/devices/{device_code}")
def poll_cli_device(device_code: str, svc=Depends(pat_service)): return svc.poll(device_code)

@router.post("/auth/cli/devices/approve")
def approve_cli_device(body: DeviceDecision, user=Depends(current_user), svc=Depends(pat_service)):
    return svc.approve(user["id"], body.user_code, body.name)

@router.post("/auth/cli/devices/deny")
def deny_cli_device(body: DeviceDecision, user=Depends(current_user), svc=Depends(pat_service)):
    return svc.deny(body.user_code)

@router.post("/me/password")
def change_password(body: PasswordChange, response: Response, user=Depends(current_user), svc=Depends(auth_service)):
    """TASK-0052: a new session for this browser; every other session of the account is signed out."""
    return _signed_in(svc.change_password(user["id"], body.current_password, body.new_password), response)
