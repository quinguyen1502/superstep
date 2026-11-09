"""Async Redis clients for code that runs on the event loop: no blocking socket calls on the loop.

redis.asyncio connections belong to the loop that created them, so one client is kept per running loop
(one per process in production; tests start several loops)."""
import asyncio, weakref

_clients: "weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, dict]" = weakref.WeakKeyDictionary()


def async_redis(url: str):
    import redis.asyncio as aredis
    loop = asyncio.get_running_loop()
    per_loop = _clients.setdefault(loop, {})
    if url not in per_loop:
        per_loop[url] = aredis.Redis.from_url(url, decode_responses=True, socket_connect_timeout=2, socket_timeout=2)
    return per_loop[url]
