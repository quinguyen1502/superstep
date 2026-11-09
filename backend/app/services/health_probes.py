"""Readiness probes, shared by `GET /api/ready` and the metric gauges so both report the same numbers.

Each probe runs on a small thread pool with a short timeout, so a hung database or Redis makes the probe fail
quickly instead of holding the request. Results carry status, latency and counts only: never a URL, host or secret.
- database: one `SELECT 1` round trip.
- redis: a ping, only when REDIS_URL is set (the in-memory bus needs none).
- queue: ready, delayed and in-flight jobs, and the age of the oldest run still `queued`.
- worker: the live worker heartbeats (busy slots, capacity, age of the newest one).
Readiness fails on the database, or on a configured Redis. Queue and worker values are reported, not judged.
"""
from __future__ import annotations
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Optional

PROBE_TIMEOUT = 2.0  # seconds per probe
_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="probe")


def timed(fn: Callable[[], Any], timeout: float = PROBE_TIMEOUT) -> tuple[bool, Optional[float], Any]:
    """(succeeded, latency in ms, value). A raised exception or a timeout counts as a failure."""
    started = time.perf_counter()
    try: value = _pool.submit(fn).result(timeout=timeout)
    except Exception: return False, None, None
    return True, round((time.perf_counter() - started) * 1000, 2), value


class Probes:
    """`db` needs `ping()`, `runs` needs `oldest_started(status)`, `jobs` is the JobQueue, `bus` the RunBus."""

    def __init__(self, db, runs, jobs, bus, redis_configured: bool, production: bool, timeout: float = PROBE_TIMEOUT):
        self.db, self.runs, self.jobs, self.bus = db, runs, jobs, bus
        self.redis_configured, self.production, self.timeout = redis_configured, production, timeout

    def database(self) -> dict:
        ok, ms, value = timed(self.db.ping, self.timeout)
        return {"ok": ok and value is True, "latency_ms": ms}

    def redis(self) -> dict:
        if not self.redis_configured: return {"configured": False, "ok": None, "latency_ms": None}
        ok, ms, value = timed(self.bus.ping, self.timeout)
        return {"configured": True, "ok": ok and value is True, "latency_ms": ms if ok and value else None}

    def queue(self) -> dict:
        ok, _, depth = timed(self.jobs.depth, self.timeout)
        found, _, oldest = timed(lambda: self.runs.oldest_started("queued"), self.timeout)
        depth = depth if ok else {}
        return {"kind": self.jobs.kind, "ok": ok, "ready": depth.get("ready"), "delayed": depth.get("delayed"),
                "processing": depth.get("processing"),
                "oldest_queued_age_s": round(max(0.0, time.time() - oldest), 1) if found and oldest is not None else None}

    def worker(self) -> dict:
        ok, _, beats = timed(self.jobs.heartbeats, self.timeout)
        beats = beats if ok else []
        newest = max((b.get("ts") or 0 for b in beats), default=None)
        return {"ok": ok, "workers": len(beats), "busy": sum(int(b.get("busy") or 0) for b in beats),
                "capacity": sum(int(b.get("capacity") or 0) for b in beats),
                "heartbeat_age_s": round(max(0.0, time.time() - newest), 1) if newest else None}

    def in_memory_in_production(self) -> bool: return self.bus.kind == "memory" and self.production

    def ready(self) -> dict:
        db, redis = self.database(), self.redis()
        return {"ok": db["ok"] and redis["ok"] is not False, "database": db, "redis": redis, "queue": self.queue(),
                "worker": self.worker(), "run_bus": self.bus.kind, "in_memory_in_production": self.in_memory_in_production()}
