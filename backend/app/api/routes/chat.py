"""Chat triggers: the platform's events URL (no JWT; verified by the connection's signing secret).

POST /api/channels/events/slack  Slack Events API (url_verification, app_mention, message.im), one URL for every
                                 workspace, routed by team_id. Telegram messages arrive on the approval webhook.
"""
import asyncio
from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse
from ..deps import approval_service, chat_run_service
from .approvals import request_ip

router = APIRouter(prefix="/api/channels", tags=["chat"])


@router.post("/events/{kind}")
async def events(kind: str, request: Request, svc=Depends(chat_run_service), approvals=Depends(approval_service)):
    """Answers at once: the run starts on the worker. Retries of the same event start nothing (dedupe by event id)."""
    body = await request.body()
    await approvals.check_rate(request_ip(request), kind, None, body)  # the callbacks' limits (per IP, per workspace)
    out = await asyncio.to_thread(svc.events, kind, dict(request.headers), body)
    return PlainTextResponse(out) if isinstance(out, str) else out  # url_verification: the challenge as plain text
