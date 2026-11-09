"""Readiness (`/api/ready`) versus liveness (`/api/health`), the shared probes, queue depth and worker heartbeats."""
import asyncio, time, uuid
from types import SimpleNamespace as NS

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.main import app
from app.models import Run
from app.repositories import RunRepository
from app.services import job_queue as jq
from app.services.health_probes import Probes
from app.services.run_bus import InMemoryRunBus, RedisRunBus
from app.services.run_worker import RunWorker

c = TestClient(app)


def fake_redis():
    import fakeredis
    return fakeredis.FakeRedis(decode_responses=True)


class DeadDb:
    def ping(self): raise ConnectionError("down")


class SlowDb:
    def ping(self): time.sleep(1); return True


class DeadBus:
    kind = "redis"
    def ping(self): return False


def probes(db=None, jobs=None, bus=None, redis=False, prod=False, timeout=2.0):
    db = db or deps.get_db()
    return Probes(db, RunRepository(deps.get_db()), jobs or jq.InMemoryJobQueue(), bus or InMemoryRunBus(), redis, prod, timeout)


def test_ready_is_ok_with_the_test_database():
    r = c.get("/api/ready"); body = r.json()["data"]
    assert r.status_code == 200 and body["ok"] is True
    assert body["database"]["ok"] is True and body["database"]["latency_ms"] >= 0
    assert body["redis"] == {"configured": False, "ok": None, "latency_ms": None} and body["run_bus"] == "memory"
    assert set(body["queue"]) >= {"ready", "delayed", "processing", "oldest_queued_age_s"} and "heartbeat_age_s" in body["worker"]


def test_database_down_gives_503_while_health_stays_200(monkeypatch):
    monkeypatch.setattr(deps.get_probes(), "db", DeadDb())
    r = c.get("/api/ready"); err = r.json()["error"]
    assert r.status_code == 503 and err["code"] == "SERVICE_NOT_READY" and err["details"]["database"]["ok"] is False
    h = c.get("/api/health"); assert h.status_code == 200 and h.json()["data"]["ok"] is True


def test_database_probe_times_out_quickly():
    started = time.monotonic(); out = probes(db=SlowDb(), timeout=0.1).database()
    assert out == {"ok": False, "latency_ms": None} and time.monotonic() - started < 0.9


def test_configured_redis_down_fails_readiness_and_unset_redis_does_not():
    down = probes(bus=DeadBus(), redis=True).ready()
    assert down["ok"] is False and down["redis"]["configured"] is True and down["redis"]["ok"] is False
    up = probes(bus=RedisRunBus("redis://fake", client=fake_redis()), redis=True).ready()
    assert up["ok"] is True and up["redis"]["ok"] is True and up["redis"]["latency_ms"] is not None
    local = probes().ready()
    assert local["ok"] is True and local["redis"]["ok"] is None and local["run_bus"] == "memory"


def test_in_memory_bus_in_production_is_flagged():
    assert probes(prod=True).ready()["in_memory_in_production"] is True
    assert probes(prod=False).ready()["in_memory_in_production"] is False
    assert probes(bus=RedisRunBus("redis://fake", client=fake_redis()), redis=True, prod=True).ready()["in_memory_in_production"] is False


def test_redis_queue_depth_matches_the_lists():
    r = fake_redis(); q = jq.RedisJobQueue("redis://fake", client=r, worker_id="w1", visibility=30)
    for i in range(3): q.enqueue({"n": i})
    q.enqueue_at({"later": 1}, time.time() + 60); q.enqueue_at({"later": 2}, time.time() + 60)
    taken = q.dequeue(1)
    other = jq.RedisJobQueue("redis://fake", client=r, worker_id="w2", visibility=30); other.dequeue(1)
    assert q.depth() == {"ready": 1, "delayed": 2, "processing": 2}
    q.ack(taken); assert q.depth()["processing"] == 1


def test_memory_queue_depth_counts_jobs_in_flight():
    q = jq.InMemoryJobQueue(); q.enqueue({"a": 1}); q.enqueue({"a": 2}); q.enqueue_at({"b": 1}, time.time() + 60)
    job = q.dequeue(0.1); assert q.depth() == {"ready": 1, "delayed": 1, "processing": 1}
    q.ack(job); assert q.depth()["processing"] == 0


def test_oldest_queued_run_age():
    rid = uuid.uuid4().hex[:10]; repo = RunRepository(deps.get_db())
    repo.add(Run(id=rid, workflow_id="w", events="[]", status="queued", started=time.time() - 120, source="api"))
    try:
        age = probes().queue()["oldest_queued_age_s"]
        assert age is not None and age >= 119
    finally:
        repo.set_status(rid, "cancelled")


def test_worker_heartbeat_is_reported_and_goes_stale(monkeypatch):
    r = fake_redis(); q = jq.RedisJobQueue("redis://fake", client=r, worker_id="w1", visibility=30)
    assert probes(jobs=q).worker() == {"ok": True, "workers": 0, "busy": 0, "capacity": 0, "heartbeat_age_s": None}
    w = RunWorker(q, lambda: None); w.capacity, w.busy = 4, 1
    asyncio.run(w.beat())
    out = probes(jobs=q).worker()
    assert out["workers"] == 1 and out["busy"] == 1 and out["capacity"] == 4 and out["heartbeat_age_s"] < 5
    assert 0 < r.ttl(jq.HEARTBEAT_PREFIX + "w1") <= jq.heartbeat_ttl()
    r.delete(jq.HEARTBEAT_PREFIX + "w1")  # the key expired: the worker stopped
    assert probes(jobs=q).worker()["workers"] == 0
    mem = jq.InMemoryJobQueue(); mem.heartbeat(0, 2)
    monkeypatch.setattr(jq, "heartbeat_ttl", lambda: -1)  # older than the TTL
    assert mem.heartbeats() == []


def test_worker_counts_busy_slots_while_a_job_runs():
    q = jq.InMemoryJobQueue(); seen = []
    w = RunWorker(q, lambda: None)
    async def job(_): seen.append(w.busy)
    w.run_job = job
    asyncio.run(w._with_lease({"kind": "x"}))
    assert seen == [1] and w.busy == 0


def test_responses_carry_no_url_host_or_secret(monkeypatch):
    monkeypatch.setattr(deps.get_probes(), "db", DeadDb())
    texts = c.get("/api/ready").text + c.get("/api/health").text
    for leak in ("sqlite:///", "postgresql", "redis://", "localhost", "JWT", "password"):
        assert leak not in texts
