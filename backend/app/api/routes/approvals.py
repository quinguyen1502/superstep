"""Approval through external channels (TASK-0022, DEC-0019).

User (JWT): channel connections (personal; org-wide ones need an admin), own channel identities (link, one-time code, verify), audit log.
Platforms (no JWT; verified by signature / secret header): POST /api/approvals/callback/{kind}/{channel_id}, or the
shared POST /api/approvals/callback/slack routed by team_id. GET on the same URL answers WhatsApp's verification.
Link channels (e-mail, Teams, TASK-0047): GET /api/approvals/link?token= shows the request, POST /api/approvals/link
records the signed-in user's decision.
Approvals inbox (TASK-0065, DEC-0043): GET /api/approvals/inbox lists the waiting steps the user owns or may answer,
POST /api/approvals/inbox/{run_id} {response} answers one.
AI review kill switches (TASK-0186, REQ-0081): GET/PUT /api/approvals/auto (organisation, admin), GET /api/approvals/auto/workflows (the user's workflows with AI review, TASK-0188), GET/PUT /api/approvals/auto/workflows/{wid} (owner or admin).
"""
import asyncio
from typing import Optional
from urllib.parse import urlencode
from fastapi import APIRouter, Body, Depends, Request
from fastapi.responses import PlainTextResponse, RedirectResponse
from ...core import config
from ...core.errors import AppError
from ...core.client_ip import client_ip
from ...core import permissions as P
from ..deps import approval_service, auto_approval_service, channel_service, current_user, identity_service, inbox_service, need, slack_oauth_service

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


@router.get("/channels")
def list_channels(user=Depends(current_user), svc=Depends(channel_service)): return svc.list(user["id"])

@router.post("/channels")
def create_channel(body=Body(None), user=Depends(need(P.RESOURCES_MANAGE)), svc=Depends(channel_service)): return svc.create(user["id"], body)

@router.put("/channels/{cid}")
def update_channel(cid: str, body=Body(None), user=Depends(need(P.RESOURCES_MANAGE)), svc=Depends(channel_service)): return svc.update(user["id"], cid, body)

@router.delete("/channels/{cid}")
def delete_channel(cid: str, user=Depends(need(P.RESOURCES_MANAGE)), svc=Depends(channel_service)): return svc.delete(user["id"], cid)

@router.post("/channels/{cid}/test")
def test_channel(cid: str, user=Depends(need(P.RESOURCES_MANAGE)), svc=Depends(channel_service)): return svc.test(user["id"], cid)

@router.post("/channels/{cid}/register-webhook")
def register_webhook(cid: str, user=Depends(need(P.RESOURCES_MANAGE)), svc=Depends(channel_service)): return svc.register_webhook(user["id"], cid)

# ---- Add to Slack (TASK-0014) ----
@router.get("/slack/oauth")
def slack_oauth_info(user=Depends(current_user), svc=Depends(slack_oauth_service)): return svc.info()

@router.post("/slack/oauth/start")
def slack_oauth_start(body=Body(None), user=Depends(need(P.RESOURCES_MANAGE)), svc=Depends(slack_oauth_service)):
    return svc.start(user["id"], (body or {}).get("scope") or "user")

@router.get("/slack/oauth/callback")
def slack_oauth_callback(code: str = "", state: str = "", error: str = "", svc=Depends(slack_oauth_service)):
    """Slack redirects the browser here (no JWT; the signed state names the user). Back to Settings → Channels with
    ?slack=installed or ?slack_error=CODE (translated by the UI)."""
    try:
        if error: raise AppError("SLACK_OAUTH_FAILED", reason=error[:60])
        svc.finish(code, state); q = {"slack": "installed"}
    except AppError as e: q = {"slack_error": e.code}
    return RedirectResponse(f"{config.public_url()}/settings/channels?{urlencode(q)}", status_code=303)


@router.get("/identities")
def get_identities(user=Depends(current_user), svc=Depends(identity_service)): return svc.get(user["id"])

@router.put("/identities")
def put_identities(body=Body(None), user=Depends(current_user), svc=Depends(identity_service)): return svc.link(user["id"], body)

@router.post("/identities/{kind}/send-code")
def send_code(kind: str, body=Body(None), user=Depends(current_user), svc=Depends(identity_service)): return svc.send_code(user["id"], kind, body)

@router.post("/identities/{kind}/verify")
def verify_identity(kind: str, body=Body(None), user=Depends(current_user), svc=Depends(identity_service)): return svc.verify(user["id"], kind, body)

@router.get("/audit")
def audit(user=Depends(current_user), svc=Depends(approval_service)): return svc.audit_log(user["id"])


def request_ip(request: Request) -> str:
    """The caller's IP (STUDIO_TRUSTED_PROXIES / STUDIO_TRUST_PROXY, see core/client_ip)."""
    return client_ip(request.client.host if request.client else None, request.headers.get("x-forwarded-for"))


async def _callback(kind: str, cid: Optional[str], request: Request, svc):
    body = await request.body()
    await svc.check_rate(request_ip(request), kind, cid, body)  # 429 RATE_LIMITED
    return await asyncio.to_thread(svc.handle_callback, kind, cid, dict(request.headers), body)


@router.post("/callback/{kind}")
async def shared_callback(kind: str, request: Request, svc=Depends(approval_service)):
    """One URL for every connection of the kind (Slack: routed by the payload's team.id, then the signature)."""
    return await _callback(kind, None, request, svc)


@router.post("/callback/{kind}/{cid}")
async def callback(kind: str, cid: str, request: Request, svc=Depends(approval_service)):
    """Slack interactivity / Telegram webhook. Refusals (expired, not allowed, ...) are answered in the channel and
    return 200 so the platform does not retry; only an unauthenticated request gets 401."""
    return await _callback(kind, cid, request, svc)


@router.get("/callback/{kind}/{cid}")
async def callback_challenge(kind: str, cid: str, request: Request, svc=Depends(approval_service)):
    """WhatsApp (Meta) checks a webhook URL with GET ?hub.mode=subscribe&hub.verify_token=…&hub.challenge=…; the body
    must be the challenge itself, so this answer is plain text, not the JSON envelope."""
    await svc.check_rate(request_ip(request), kind, cid, b"")
    return PlainTextResponse(await asyncio.to_thread(svc.challenge, kind, cid, dict(request.query_params)))


# ---- link channels (TASK-0047) ----
@router.get("/link")
def link_info(token: str, user=Depends(current_user), svc=Depends(approval_service)): return svc.link_info(token, user["id"])

@router.post("/link")
def decide_link(body: dict = Body(...), user=Depends(current_user), svc=Depends(approval_service)):
    return svc.decide_link(str(body.get("token") or ""), user["id"])


# ---- the Approvals inbox (TASK-0065) ----
@router.get("/inbox")
def inbox(user=Depends(current_user), svc=Depends(inbox_service)): return svc.list(user["id"])

@router.post("/inbox/{run_id}")
def answer(run_id: str, body=Body(None), user=Depends(current_user), svc=Depends(inbox_service)):
    data = body if isinstance(body, dict) else {}
    node = data.get("node")
    return svc.answer(user["id"], run_id, data.get("response"), node if isinstance(node, str) and node else None)


# ---- AI review of approvals: kill switches (TASK-0186, REQ-0081) ----
@router.get("/auto")
def auto_status(user=Depends(current_user), svc=Depends(auto_approval_service)): return svc.status(user["id"])

@router.put("/auto")
def auto_set_org(body=Body(None), user=Depends(current_user), svc=Depends(auto_approval_service)):
    return svc.set_org_paused(user["id"], bool((body or {}).get("paused")))

@router.get("/auto/workflows")
def auto_workflows(user=Depends(current_user), svc=Depends(auto_approval_service)): return svc.reviewed_workflows(user["id"])

@router.get("/auto/workflows/{wid}")
def auto_workflow(wid: str, user=Depends(current_user), svc=Depends(auto_approval_service)): return svc.workflow_status(user["id"], wid)

@router.put("/auto/workflows/{wid}")
def auto_set_workflow(wid: str, body=Body(None), user=Depends(current_user), svc=Depends(auto_approval_service)):
    return svc.set_workflow_paused(user["id"], wid, bool((body or {}).get("paused")))
