"""Studio Dataset invalidations. Row and schema results use their existing HTTP APIs."""

import asyncio
from contextlib import suppress

import anyio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from redis.exceptions import RedisError

from ...core.errors import AppError
from ...services.notification_hub import dataset_changes_channel
from ..deps import dataset_service, get_notification_hub, ws_user

router = APIRouter()
HEARTBEAT_SECONDS = 20
SEND_TIMEOUT_SECONDS = 5


@router.websocket("/ws/datasets/{dataset_id}/changes")
async def dataset_changes(ws: WebSocket, dataset_id: str):
    service = dataset_service()

    def authorized_revisions() -> dict[str, int]:
        user = ws_user(ws, session_only=True)
        return service.revisions(user["id"], dataset_id)

    async def close(code: int) -> None:
        with anyio.move_on_after(SEND_TIMEOUT_SECONDS), suppress(WebSocketDisconnect, RuntimeError):
            await ws.close(code=code)

    async def send(message: dict) -> None:
        with anyio.fail_after(SEND_TIMEOUT_SECONDS):
            await ws.send_json(message)

    async def guard(job) -> None:
        try:
            await job()
        except AppError as error:
            await close(4403 if error.code == "DATASET_NOT_FOUND" else 4401)
        except (RedisError, TimeoutError):
            await close(1011)
        except (WebSocketDisconnect, RuntimeError):
            pass

    async def stream() -> None:
        await asyncio.to_thread(authorized_revisions)
        await ws.accept()
        async with get_notification_hub().subscribe(dataset_changes_channel(dataset_id), max_pending=1) as feed:
            initial = await asyncio.to_thread(authorized_revisions)
            last_revision = initial["data_revision"]
            await send({"type": "ready", **initial})
            send_lock = anyio.Lock()

            async def pump() -> None:
                nonlocal last_revision
                async for _ in feed:
                    async with send_lock:
                        revisions = await asyncio.to_thread(authorized_revisions)
                        if revisions["data_revision"] > last_revision:
                            await send({"type": "dataset_changed", **revisions})
                            last_revision = revisions["data_revision"]

            async def heartbeat() -> None:
                while True:
                    await asyncio.sleep(HEARTBEAT_SECONDS)
                    async with send_lock:
                        await asyncio.to_thread(authorized_revisions)
                        await send({"type": "ping"})

            async def drain() -> None:
                while (await ws.receive())["type"] != "websocket.disconnect":
                    pass

            async with anyio.create_task_group() as tasks:
                async def run(job) -> None:
                    try:
                        await guard(job)
                    finally:
                        tasks.cancel_scope.cancel()

                tasks.start_soon(run, pump)
                tasks.start_soon(run, heartbeat)
                await run(drain)

    await guard(stream)
