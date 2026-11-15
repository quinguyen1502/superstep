"""In-app notifications: the header bell. Live push + preferences."""
import asyncio
from fastapi import APIRouter, Body, Depends, WebSocket, WebSocketDisconnect
from ...core.errors import AppError
from ..deps import current_user, get_notification_hub, notification_service, ws_user

router = APIRouter(prefix="/api/notifications", tags=["notifications"])
ws_router = APIRouter()


@router.get("")
def list_notifications(unread: bool = False, user=Depends(current_user), svc=Depends(notification_service)):
    return svc.list(user["id"], unread_only=unread)

@router.get("/preferences")
def get_preferences(user=Depends(current_user), svc=Depends(notification_service)): return svc.preferences(user["id"])

@router.put("/preferences")
def put_preferences(body=Body(None), user=Depends(current_user), svc=Depends(notification_service)): return svc.set_preferences(user["id"], body)

@router.post("/read-all")
def read_all(user=Depends(current_user), svc=Depends(notification_service)): return svc.mark_all_read(user["id"])

@router.post("/{nid}/read")
def read_one(nid: str, user=Depends(current_user), svc=Depends(notification_service)): return svc.mark_read(user["id"], nid)


@ws_router.websocket("/ws/notifications")
async def ws_notifications(ws: WebSocket):
    """Connect with the session cookie (same origin) or ?token=JWT. Server pushes {"type": "notification", notification, unread} for each new in-app
    notification of this user (and {"type": "ready"} once subscribed). Clients keep polling when the socket is down."""
    try: uid = ws_user(ws)["id"]
    except AppError: await ws.close(code=4401); return
    await ws.accept()
    async with get_notification_hub().subscribe(uid) as feed:
        await ws.send_json({"type": "ready"})
        async def pump():
            async for payload in feed: await ws.send_json(payload)
        async def drain():  # returns when the client goes away
            try:
                while True: await ws.receive_text()
            except (WebSocketDisconnect, RuntimeError): return
        tasks = [asyncio.create_task(pump()), asyncio.create_task(drain())]
        try: await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        finally:
            for t in tasks: t.cancel()
