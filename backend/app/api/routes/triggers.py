"""API / webhook triggers (TASK-0007).

Owner (JWT): manage per-workflow tokens under /api/workflows/{wid}/tokens and cron schedules (TASK-0046) under
/api/workflows/{wid}/schedules; POST /api/schedules/preview lists the next times of an expression; chat triggers
(TASK-0074) under /api/workflows/{wid}/chat-triggers.
The public routes that external callers use with those tokens live in `hooks.py`.
"""
from fastapi import APIRouter, Depends
from ...schemas.trigger import ChatTriggerIn, ChatTriggerPatch, ScheduleIn, SchedulePatch, SchedulePreview, TokenIn
from ..deps import chat_trigger_service, current_user, delivery_service, schedule_service, trigger_service

router = APIRouter(prefix="/api", tags=["triggers"])


@router.get("/workflows/{wid}/tokens")
def list_tokens(wid: str, user=Depends(current_user), svc=Depends(trigger_service)): return svc.list_tokens(wid, user["id"])

@router.post("/workflows/{wid}/tokens")
def create_token(wid: str, body: TokenIn, user=Depends(current_user), svc=Depends(trigger_service)): return svc.create_token(wid, user["id"], body.name)

@router.post("/workflows/{wid}/tokens/{tid}/rotate-secret")
def rotate_secret(wid: str, tid: str, user=Depends(current_user), svc=Depends(trigger_service)): return svc.rotate_secret(wid, tid, user["id"])

@router.get("/workflows/{wid}/deliveries")
def list_deliveries(wid: str, user=Depends(current_user), svc=Depends(delivery_service)): return svc.list(wid, user["id"])

@router.post("/workflows/{wid}/deliveries/{did}/redeliver")
def redeliver(wid: str, did: str, user=Depends(current_user), svc=Depends(delivery_service)): return svc.redeliver(wid, did, user["id"])

@router.delete("/workflows/{wid}/tokens/{tid}")
def revoke_token(wid: str, tid: str, user=Depends(current_user), svc=Depends(trigger_service)): return svc.revoke_token(wid, tid, user["id"])


# ---- cron schedules (TASK-0046) ----
@router.get("/workflows/{wid}/schedules")
def list_schedules(wid: str, user=Depends(current_user), svc=Depends(schedule_service)): return svc.list(wid, user["id"])

@router.post("/workflows/{wid}/schedules")
def create_schedule(wid: str, body: ScheduleIn, user=Depends(current_user), svc=Depends(schedule_service)):
    return svc.create(wid, user["id"], body.name, body.cron, body.timezone, body.input, body.enabled)

@router.patch("/workflows/{wid}/schedules/{sid}")
def update_schedule(wid: str, sid: str, body: SchedulePatch, user=Depends(current_user), svc=Depends(schedule_service)):
    return svc.update(wid, sid, user["id"], **body.model_dump())

@router.delete("/workflows/{wid}/schedules/{sid}")
def delete_schedule(wid: str, sid: str, user=Depends(current_user), svc=Depends(schedule_service)): return svc.delete(wid, sid, user["id"])

@router.post("/schedules/preview")
def preview_schedule(body: SchedulePreview, user=Depends(current_user), svc=Depends(schedule_service)): return svc.preview(body.cron, body.timezone)


# ---- chat triggers (TASK-0074) ----
@router.get("/workflows/{wid}/chat-triggers")
def list_chat_triggers(wid: str, user=Depends(current_user), svc=Depends(chat_trigger_service)): return svc.list(wid, user["id"])

@router.post("/workflows/{wid}/chat-triggers")
def create_chat_trigger(wid: str, body: ChatTriggerIn, user=Depends(current_user), svc=Depends(chat_trigger_service)):
    return svc.create(wid, user["id"], body.model_dump())

@router.patch("/workflows/{wid}/chat-triggers/{tid}")
def update_chat_trigger(wid: str, tid: str, body: ChatTriggerPatch, user=Depends(current_user), svc=Depends(chat_trigger_service)):
    return svc.update(wid, tid, user["id"], body.model_dump())

@router.delete("/workflows/{wid}/chat-triggers/{tid}")
def delete_chat_trigger(wid: str, tid: str, user=Depends(current_user), svc=Depends(chat_trigger_service)): return svc.delete(wid, tid, user["id"])
