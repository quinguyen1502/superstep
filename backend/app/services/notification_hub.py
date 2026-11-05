"""Live notification push (TASK-0021): fan-out of new notifications to each user's open sockets.

- RedisNotificationHub (REDIS_URL set): PUBLISH on `studio:notify:<user>`; every API process subscribes for the users
  connected to it, so a run recorded by a worker process reaches a browser connected to any API process.
- InMemoryNotificationHub (no Redis): process-local fan-out (single process / dev).
`publish` is called from worker threads; `subscribe` is an async iterator used by the WebSocket route.
The bell keeps polling as a fallback, so a lost push only delays a notification.
"""
import asyncio, json, threading
import anyio
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional, Protocol


def channel(uid: str) -> str: return f"studio:notify:{uid}"


def workflow_runs_channel(wid: str) -> str:
    """Separate from personal bell notifications; payloads contain invalidations only, never run data."""
    return f"workflow-runs:{wid}"


class NotificationHub(Protocol):
    kind: str
    def publish(self, uid: str, payload: dict) -> None: ...
    def subscribe(self, uid: str): ...  # async context manager -> async iterator of payloads


class InMemoryNotificationHub:
    kind = "memory"
    def __init__(self): self._subs: dict[str, set] = {}; self._lock = threading.Lock()

    def publish(self, uid, payload):
        with self._lock: subs = list(self._subs.get(uid, ()))
        for loop, q in subs:
            try: loop.call_soon_threadsafe(q.put_nowait, payload)
            except RuntimeError: pass  # that socket's loop is gone

    @asynccontextmanager
    async def subscribe(self, uid) -> AsyncIterator[AsyncIterator[dict]]:
        q: asyncio.Queue = asyncio.Queue(); entry = (asyncio.get_running_loop(), q)
        with self._lock: self._subs.setdefault(uid, set()).add(entry)
        async def it():
            while True: yield await q.get()
        try: yield it()
        finally:
            with self._lock: self._subs.get(uid, set()).discard(entry)


class RedisNotificationHub:
    kind = "redis"
    def __init__(self, url: str, client=None):
        self.url = url
        if client is None:
            import redis
            client = redis.Redis.from_url(url, decode_responses=True, socket_connect_timeout=2, socket_timeout=5)
        self.r = client

    def publish(self, uid, payload): self.r.publish(channel(uid), json.dumps(payload, ensure_ascii=False, default=str))

    @asynccontextmanager
    async def subscribe(self, uid):
        from .redis_async import async_redis
        ps = async_redis(self.url).pubsub(); await ps.subscribe(channel(uid))
        async def it():
            while True:
                m = await ps.get_message(ignore_subscribe_messages=True, timeout=30)
                if m and m.get("type") == "message": yield json.loads(m["data"])
        try: yield it()
        finally:
            # Closing the connection unsubscribes it too. Finish this bounded cleanup
            # even when the owning ASGI cancellation scope is already cancelled.
            with anyio.CancelScope(shield=True):
                try: await ps.aclose()
                except Exception: pass


def make_notification_hub(url: Optional[str]) -> NotificationHub:
    return RedisNotificationHub(url) if url else InMemoryNotificationHub()
