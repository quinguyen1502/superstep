"""WebSocket run controller: auth + socket I/O only; the run lifecycle lives in RunService."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ...core import config
from ...core.client_ip import client_ip
from ...core.errors import AppError
from ...engine import locale
from ...services.run_service import error_event
from ..deps import demo_service, run_service, ws_user

router = APIRouter()


@router.websocket("/ws/run")
async def ws_run(ws: WebSocket):
    """Connect with the session cookie (same origin) or ?token=JWT. Client sends {workflow_id, workflow?, input, steps?, until?, locale?}; server streams events.
    steps: 1 pauses after one working superstep (status paused). until: a node id pauses after that node finishes.
    Resume with {resume_run_id, response, node?} (node is the question on screen), or {resume_run_id, steps?} / {resume_run_id, until?} and no response.
    While running, the client may send {"type": "cancel"}; closing the socket also cancels.
    locale (en | vi, else Accept-Language): the language of the mock model's and example tools' offline answers.
    Final status: ok | error | cancelled | timeout | waiting | paused (stored in run history)."""
    try:
        uid = ws_user(ws)["id"]
    except AppError:
        await ws.close(code=4401); return
    await ws.accept()
    try:
        req = await ws.receive_json()
    except (WebSocketDisconnect, ValueError, KeyError):
        return
    svc = run_service()
    try:
        if config.demo_mode(): await demo_service().check_run(client_ip(ws.client.host if ws.client else None, ws.headers.get("x-forwarded-for")))
        plan = svc.plan(uid, req)
        if plan.ports is not None: plan.ports.locale = locale.pick(req.get("locale"), ws.headers.get("accept-language"))  # the UI language
    except AppError as e:
        await ws.send_json(error_event(e.to_dict())); await ws.close(); return

    state = {"connected": True}

    async def send(ev) -> bool:
        try: await ws.send_json(ev); return True
        except Exception: state["connected"] = False; return False

    async def listen() -> str:
        try:
            while True:
                m = await ws.receive_json()
                if isinstance(m, dict) and m.get("type") == "cancel": return "cancelled"
        except (WebSocketDisconnect, RuntimeError, ValueError):
            state["connected"] = False
            return "disconnected"

    await svc.execute(plan, send, listen, uid)
    if state["connected"]:
        try: await ws.close()
        except Exception: pass
