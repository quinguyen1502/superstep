"""RunBus: in-memory and Redis implementations share one contract; cancel via the bus."""
import asyncio, json, os, time, uuid
from types import SimpleNamespace as NS
import pytest
from fastapi.testclient import TestClient
from app.services.run_bus import InMemoryRunBus, RedisRunBus, channel, make_run_bus
from app.services.run_service import RunService


def _redis_bus():
    url = os.environ.get("TEST_REDIS_URL") or os.environ.get("REDIS_URL")
    if url: return RedisRunBus(url)  # real server (CI service / local redis-server)
    import fakeredis
    return RedisRunBus("redis://fake", client=fakeredis.FakeRedis(decode_responses=True))


@pytest.fixture(params=["memory", "redis"])
def bus(request):
    return InMemoryRunBus() if request.param == "memory" else _redis_bus()


def test_factory_picks_implementation():
    assert make_run_bus(None).kind == "memory"
    assert make_run_bus("redis://localhost:1/0").kind == "redis"  # lazy: no connection until used


def test_registry_and_cancel_contract(bus):
    rid = uuid.uuid4().hex[:10]
    assert bus.owner(rid) is None and not bus.is_cancelled(rid) and bus.ping()
    bus.start(rid, "u1"); assert bus.owner(rid) == "u1"
    bus.request_cancel(rid); assert bus.is_cancelled(rid)
    bus.finish(rid); assert bus.owner(rid) is None and not bus.is_cancelled(rid)


def test_redis_publishes_events_on_run_channel():
    b = _redis_bus(); rid = uuid.uuid4().hex[:10]
    sub = b.r.pubsub(); sub.subscribe(channel(rid)); sub.get_message(timeout=1)  # subscribe ack
    b.publish(rid, {"type": "node_started", "node": "a"})
    msg = None
    for _ in range(20):
        msg = sub.get_message(timeout=0.2)
        if msg and msg["type"] == "message": break
    assert json.loads(msg["data"]) == {"type": "node_started", "node": "a"}
    sub.close()


class _Runs:
    def __init__(self): self.rows = []
    def add(self, r): self.rows.append(r)
    def get(self, rid): return next((r for r in self.rows if r.id == rid), None)


def _slow_plan(steps=50):
    def events():
        for i in range(steps): time.sleep(0.02); yield {"type": "node_finished", "node": f"n{i}"}
        yield {"type": "run_finished", "state": {}}
    from app.services.run_service import RunPlan
    plan = RunPlan("w1", {}, {}); plan.events = events
    return plan


def test_cancel_through_bus_stops_run(bus):
    runs = _Runs(); svc = RunService(None, runs, bus=bus); seen = []

    async def send(ev):
        seen.append(ev)
        if ev["type"] == "run_started": svc.cancel(ev["run_id"], "u1")  # e.g. POST /api/runs/{id}/cancel on another worker
        return True

    async def listen(): await asyncio.sleep(30); return "disconnected"

    status = asyncio.run(svc.execute(_slow_plan(), send, listen, "u1"))
    assert status == "cancelled" and seen[-2]["type"] == "run_cancelled" and seen[-2]["reason"] == "api"
    assert seen[-1]["type"] == "run_summary"
    assert runs.rows[0].status == "cancelled"
    assert bus.owner(seen[0]["run_id"]) is None  # unregistered when done


def test_cancel_requires_owner(bus):
    svc = RunService(None, _Runs(), bus=bus); rid = uuid.uuid4().hex[:10]; bus.start(rid, "owner")
    from app.core.errors import AppError
    with pytest.raises(AppError) as e: svc.cancel(rid, "someone-else")
    assert e.value.code == "RUN_NOT_FOUND" and not bus.is_cancelled(rid)
    bus.finish(rid)


def test_cancel_endpoint_unknown_run_is_404():
    from app.main import app
    c = TestClient(app)
    tok = c.post("/api/auth/login", json={"email": "admin@example.com", "password": "admin123"}).json()["data"]["token"]
    r = c.post("/api/runs/nope/cancel", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 404 and r.json()["error"]["code"] == "RUN_NOT_FOUND"
    assert c.post("/api/runs/nope/cancel").status_code == 401
    h = c.get("/api/health").json()["data"]
    assert h["run_bus"] in ("memory", "redis") and h["database"] in ("sqlite", "postgresql")
