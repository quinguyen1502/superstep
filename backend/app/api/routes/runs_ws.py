"""WebSocket run controller: auth + socket I/O only; the run lifecycle lives in RunService."""
import asyncio
import anyio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ...core import config
from ...core.client_ip import client_ip
from ...core.errors import AppError
from ...engine import locale
from ...services.run_service import error_event
from ...services.notification_hub import workflow_runs_channel
from ..deps import demo_service, get_notification_hub, run_service, ws_user

router = APIRouter()


@router.websocket("/ws/workflows/{wid}/runs")
async def ws_workflow_runs(ws: WebSocket, wid: str):
    """Authenticated, read-only invalidations. Clients fetch data via the existing authorised history API."""
    svc = run_service()
    try: user = await asyncio.to_thread(ws_user, ws)
    except AppError: await ws.close(code=4401); return
    try: await asyncio.to_thread(svc.watch_history, wid, user["id"])
    except AppError: await ws.close(code=4403); return
    await ws.accept()

    def allowed(rid=None):
        current = ws_user(ws)  # recheck expiry/deactivation and workflow access on every push/heartbeat
        return svc.watch_history(wid, current["id"], rid)

    async with get_notification_hub().subscribe(workflow_runs_channel(wid)) as feed:
        await ws.send_json({"type": "ready"})  # subscribe before the client takes its initial snapshot

        async def pump():
            async for payload in feed:
                if await asyncio.to_thread(allowed, payload.get("run_id")):
                    await ws.send_json({"type": "runs_changed"})

        async def heartbeat():
            while True:
                await asyncio.sleep(20)
                await asyncio.to_thread(allowed)
                await ws.send_json({"type": "ping"})

        async def drain():
            while True: await ws.receive_text()

        # The ASGI server (and TestClient) owns an AnyIO cancellation scope. Detached
        # asyncio tasks can outlive it or have their cleanup interrupted by repeated
        # cancellation. Keep receive/push/heartbeat in one structured lifetime.
        async with anyio.create_task_group() as tasks:
            async def run(fn):
                try: await fn()
                except AppError: await ws.close(code=4403)
                except (WebSocketDisconnect, RuntimeError): pass
                finally: tasks.cancel_scope.cancel()
            tasks.start_soon(run, pump)
            tasks.start_soon(run, heartbeat)
            await run(drain)


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
