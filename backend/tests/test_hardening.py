"""TASK-0019: phase-2 hardening (HITL active time + expiry, signed/pinned/rate-limited webhooks, reliable queue,
sync wait cap, version pagination/retention/no-op restore/retry, migration lock, price override, LangSmith dedupe, async Redis)."""
import asyncio, json, os, socket, threading, time, uuid
import httpx, pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core import config
from app.core.errors import AppError
from app.services import job_queue as jq, rate_limit, telemetry, webhooks
from app.services.telemetry import summarize, waited_s
from tests.test_hitl import APPROVAL

REDIS = os.environ.get("REDIS_URL")


@pytest.fixture(scope="module")
def c():
    with TestClient(app) as client:
        yield client

def H(t): return {"Authorization": f"Bearer {t}"}
def user(c):
    return c.post("/api/auth/register", json={"email": f"z{uuid.uuid4().hex[:6]}@example.com", "password": "secret12"}).json()["data"]["token"]
def example(c, tok): return c.get("/api/workflows", headers=H(tok)).json()["data"][0]["id"]
def ws(c, tok, msg, until=("run_summary", "error")):
    with c.websocket_connect(f"/ws/run?token={tok}") as w:
        w.send_json(msg); evs = []
        while True:
            evs.append(w.receive_json())
            if evs[-1]["type"] in until: return evs


# ---------- HITL ----------
def test_waited_time_excluded_from_duration_unit():
    evs = [{"type": "run_started", "ts": 0}, {"type": "run_waiting", "ts": 1}, {"type": "run_resumed", "ts": 101}, {"type": "run_finished", "ts": 102}]
    assert waited_s(evs, 102) == 100 and summarize(evs, 0, 102)["duration_ms"] == 2000
    assert summarize(evs[:2], 0, 1)["duration_ms"] == 1000  # still waiting: active time so far
    cancelled = evs[:2] + [{"type": "run_cancelled", "ts": 50}]
    assert summarize(cancelled, 0, 50)["duration_ms"] == 1000


def test_resumed_run_duration_is_active_time(c):
    tok = user(c); wid = c.post("/api/workflows", json=APPROVAL, headers=H(tok)).json()["data"]["id"]
    rid = ws(c, tok, {"workflow_id": wid, "input": {"message": "x"}})[0]["run_id"]
    time.sleep(1.2)
    ws(c, tok, {"resume_run_id": rid, "response": "approved"})
    [h] = c.get(f"/api/workflows/{wid}/runs", headers=H(tok)).json()["data"]
    assert h["status"] == "ok" and h["metrics"]["duration_ms"] < 1000 < (h["ended"] - h["started"]) * 1000


def test_waiting_runs_expire(c, monkeypatch):
    tok = user(c); wid = c.post("/api/workflows", json=APPROVAL, headers=H(tok)).json()["data"]["id"]
    a = ws(c, tok, {"workflow_id": wid, "input": {"message": "a"}})[0]["run_id"]
    b = ws(c, tok, {"workflow_id": wid, "input": {"message": "b"}})[0]["run_id"]
    monkeypatch.setenv("STUDIO_WAIT_TTL", "0.3"); time.sleep(0.5)
    err = ws(c, tok, {"resume_run_id": a, "response": "approved"})[-1]  # lazily on access
    assert err["type"] == "error" and err["error"]["code"] == "RUN_EXPIRED"
    assert c.get("/api/runs/pending", headers=H(tok)).json()["data"] == []  # the sweep expired b too
    hist = {h["id"]: h for h in c.get(f"/api/workflows/{wid}/runs", headers=H(tok)).json()["data"]}
    assert hist[a]["status"] == hist[b]["status"] == "expired" and hist[b]["events"][-1]["type"] == "run_expired"
    monkeypatch.setenv("STUDIO_WAIT_TTL", "0")  # 0 = never expire
    cnew = ws(c, tok, {"workflow_id": wid, "input": {"message": "c"}})[0]["run_id"]; time.sleep(0.1)
    assert [p["id"] for p in c.get("/api/runs/pending", headers=H(tok)).json()["data"]] == [cnew]
    assert c.post(f"/api/runs/{cnew}/cancel", headers=H(tok)).status_code == 200


# ---------- webhooks: signature, DNS pinning ----------
def test_signature_roundtrip_and_tolerance():
    body = b'{"a":1}'; h = webhooks.sign("whsec_x", body, ts=1000)
    assert h.startswith("t=1000,v1=") and webhooks.verify_signature("whsec_x", h, body, now=1100)
    assert not webhooks.verify_signature("whsec_x", h, body, now=1000 + webhooks.TOLERANCE_S + 1)  # replay window
    assert not webhooks.verify_signature("whsec_x", h, b'{"a":2}', now=1000) and not webhooks.verify_signature("whsec_x", "garbage", body)


def test_pinned_request_keeps_host_and_sni():
    url, headers, ext = webhooks.pinned_request("https://hooks.example.com:8443/x?y=1", "2001:db8::1")
    assert url == "https://[2001:db8::1]:8443/x?y=1" and headers["Host"] == "hooks.example.com:8443" and ext == {"sni_hostname": "hooks.example.com"}
    url, headers, ext = webhooks.pinned_request("http://a.example/x", "93.184.216.34")
    assert url == "http://93.184.216.34/x" and headers["Host"] == "a.example" and ext == {}


def test_dns_rebinding_is_refused(monkeypatch):
    monkeypatch.delenv("STUDIO_ALLOW_PRIVATE_CALLBACKS", raising=False)
    answers = iter(["93.184.216.34", "10.0.0.5"])  # public when queued, private at delivery (rebinding)
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (next(answers), 80))])
    sent = []
    monkeypatch.setattr(webhooks, "http_client", lambda: httpx.Client(transport=httpx.MockTransport(lambda r: sent.append(r) or httpx.Response(200))))
    assert webhooks.check_callback_url("http://rebind.example/hook")
    assert webhooks.deliver("http://rebind.example/hook", {"x": 1}, "whsec_s") is False and sent == []
    # a stable public answer is delivered to that exact IP
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 80))])
    assert webhooks.deliver("http://ok.example/hook", {"x": 1}, "whsec_s") and sent[0].url.host == "93.184.216.34"
    assert webhooks.verify_signature("whsec_s", sent[0].headers["x-studio-signature"], sent[0].content)


# ---------- rate limit + sync wait cap ----------
def test_memory_rate_limiter_window():
    rl = rate_limit.InMemoryRateLimiter()
    async def go(): return [await rl.hit("k", 2, 60) for _ in range(3)]
    res = asyncio.run(go())
    assert [ok for ok, _ in res] == [True, True, False] and 0 < res[2][1] <= 60


@pytest.mark.skipif(not REDIS, reason="needs REDIS_URL")
def test_redis_rate_limiter_shared_counter():
    key = uuid.uuid4().hex
    async def go():
        a, b = rate_limit.RedisRateLimiter(REDIS), rate_limit.RedisRateLimiter(REDIS)  # two "processes"
        return [await a.hit(key, 2, 60), await b.hit(key, 2, 60), await a.hit(key, 2, 60)]
    assert [ok for ok, _ in asyncio.run(go())] == [True, True, False]


def test_trigger_rate_limited_with_retry_after(c, monkeypatch):
    monkeypatch.setenv("STUDIO_TRIGGER_RATE_LIMIT", "2"); monkeypatch.setenv("STUDIO_TRIGGER_RATE_WINDOW", "60")
    import types
    t0 = (time.time() // 60) * 60 + 10  # the windows are fixed: keep all three hits inside one, not across a boundary
    monkeypatch.setattr(rate_limit, "time", types.SimpleNamespace(time=lambda: t0))
    tok = user(c); wid = example(c, tok); secret = c.post(f"/api/workflows/{wid}/tokens", json={"name": "rl"}, headers=H(tok)).json()["data"]["token"]
    codes = [c.post(f"/api/hooks/workflows/{wid}/runs", json={"input": {}}, headers=H(secret)) for _ in range(3)]
    assert [r.status_code for r in codes] == [202, 202, 429]
    assert codes[2].json()["error"]["code"] == "RATE_LIMITED" and 0 < int(codes[2].headers["retry-after"]) <= 60
    assert codes[0].json()["data"]["poll_url"].endswith(f"/api/hooks/workflows/{wid}/runs/{codes[0].json()['data']['run_id']}")
    assert c.get(f"/api/hooks/workflows/{wid}/runs/{codes[0].json()['data']['run_id']}", headers=H(secret)).status_code == 200  # polling is not limited


def test_sync_mode_wait_is_capped(c, monkeypatch):
    monkeypatch.setenv("STUDIO_SYNC_WAIT_MAX", "0")
    tok = user(c); wid = c.post("/api/workflows", json={**APPROVAL, "name": f"A {uuid.uuid4().hex[:4]}"}, headers=H(tok)).json()["data"]["id"]
    secret = c.post(f"/api/workflows/{wid}/tokens", json={}, headers=H(tok)).json()["data"]["token"]
    r = c.post(f"/api/hooks/workflows/{wid}/runs", json={"input": {"message": "x"}, "mode": "sync"}, headers=H(secret))
    d = r.json()["data"]
    assert r.status_code == 202 and d["status"] in ("queued", "running") and r.headers["location"] == d["poll_url"]


# ---------- reliable queue ----------
def _fake():
    import fakeredis
    return fakeredis.FakeRedis(decode_responses=True)


def test_redis_queue_ack_and_lease_reaper():
    """TASK-0020 replaced heartbeats with per-job leases (visibility timeout) reaped periodically."""
    r = _fake()
    dead = jq.RedisJobQueue("redis://fake", client=r, worker_id="dead", visibility=30)
    dead.enqueue({"run_id": "a"}); dead.enqueue({"run_id": "b"})
    ja = dead.dequeue(1); assert ja["run_id"] == "a" and r.llen(dead.processing) == 1
    dead.ack(ja); assert r.llen(dead.processing) == 0 and not list(r.scan_iter(match=jq.LEASE_PREFIX + "*"))
    jb = dead.dequeue(1); assert jb["run_id"] == "b"   # taken, never acked: the worker "crashes"
    alive = jq.RedisJobQueue("redis://fake", client=r, worker_id="alive", visibility=30)
    assert alive.reap() == 0 and alive.reap() == 0      # lease still valid
    for k in r.scan_iter(match=jq.LEASE_PREFIX + "*"): r.delete(k)  # lease expired
    alive.enqueue({"run_id": "c"})
    assert alive.reap() == 0                            # first strike: only suspected
    assert alive.reap() == 1 and r.llen(dead.processing) == 0
    got = alive.dequeue(1); assert got["run_id"] == "b" and got["recovered"] is True  # recovered jobs go first
    assert alive.dequeue(1)["run_id"] == "c"
    assert jq.InMemoryJobQueue().reap() == 0


def test_worker_reexecutes_recovered_running_job(c):
    from app.api.deps import run_service, run_worker
    tok = user(c); wid = example(c, tok); secret = c.post(f"/api/workflows/{wid}/tokens", json={}, headers=H(tok)).json()["data"]["token"]
    from app.models import Run
    svc = run_service(); rid = uuid.uuid4().hex[:10]
    me = {"id": svc.workflows.get(wid).owner}
    svc.runs.add(Run(id=rid, workflow_id=wid, input="{}", events="[]", status="running", started=time.time(), owner=me["id"], source="api"))
    job = {"run_id": rid, "workflow_id": wid, "owner": me["id"], "input": {"message": "hi"}}
    w = run_worker()
    assert asyncio.run(w.run_job(job)) is None                       # running + not recovered: someone else has it
    assert asyncio.run(w.run_job({**job, "recovered": True})) == "ok"  # recovered: executed again
    assert c.get(f"/api/hooks/workflows/{wid}/runs/{rid}", headers=H(secret)).json()["data"]["status"] == "ok"


@pytest.mark.skipif(not REDIS, reason="needs REDIS_URL")
def test_async_run_bus_on_real_redis():
    from app.services.run_bus import RedisRunBus
    bus = RedisRunBus(REDIS); rid = uuid.uuid4().hex[:8]
    async def go():
        await bus.astart(rid, "u1"); await bus.apublish(rid, {"type": "x"}); owner = bus.owner(rid)
        bus.finish(rid); return owner
    assert asyncio.run(go()) == "u1" and bus.owner(rid) is None


# ---------- versions ----------
def _versions(c, tok, wid, q=""): return c.get(f"/api/workflows/{wid}/versions{q}", headers=H(tok)).json()["data"]
def _save_variant(c, tok, wf, i):
    c.post("/api/workflows", json={**wf, "nodes": [{**n, "data": {**(n.get("data") or {}), "label": f"L{i}"}} if k == 0 else n for k, n in enumerate(wf["nodes"])]}, headers=H(tok))


def test_version_pagination(c):
    tok = user(c); wid = example(c, tok); wf = c.get(f"/api/workflows/{wid}", headers=H(tok)).json()["data"]
    for i in range(4): _save_variant(c, tok, wf, i)
    p1 = _versions(c, tok, wid, "?limit=2"); p2 = _versions(c, tok, wid, "?limit=2&offset=2"); p3 = _versions(c, tok, wid, "?limit=2&offset=4")
    assert p1["total"] == 5 and [v["version"] for v in p1["items"]] == [5, 4] and [v["version"] for v in p2["items"]] == [3, 2]
    assert [v["version"] for v in p3["items"]] == [1] and p1["items"][0]["current"] and not p2["items"][0]["current"]
    assert c.get(f"/api/workflows/{wid}/versions?limit=0", headers=H(tok)).json()["error"]["code"] == "VALIDATION_ERROR"


def test_version_retention_keeps_versions_used_by_runs(c, monkeypatch):
    tok = user(c); wid = example(c, tok); wf = c.get(f"/api/workflows/{wid}", headers=H(tok)).json()["data"]
    ws(c, tok, {"workflow_id": wid, "workflow": wf, "input": {"message": "hi"}})  # a run on v1
    monkeypatch.setenv("STUDIO_VERSION_KEEP", "2")
    for i in range(4): _save_variant(c, tok, wf, i)  # v2..v5
    assert [v["version"] for v in _versions(c, tok, wid)["items"]] == [5, 4, 1]  # v1 is referenced by a run
    assert [h["version"] for h in c.get(f"/api/workflows/{wid}/runs", headers=H(tok)).json()["data"]] == [1]


def test_restore_identical_is_noop(c):
    tok = user(c); wid = example(c, tok)
    r = c.post(f"/api/workflows/{wid}/versions/1/restore", headers=H(tok)).json()["data"]
    assert r["unchanged"] is True and r["version"] == 1 and _versions(c, tok, wid)["total"] == 1


def test_version_number_conflict_is_retried():
    from app.api.deps import get_db, workflow_service
    from app.repositories import UserRepository
    svc = workflow_service(); uid = "u-" + uuid.uuid4().hex[:6]
    UserRepository(get_db()).add(uid, f"{uid}@example.com", "x", time.time())
    wid = svc.seed_example(uid)
    real = svc.versions.next_number; calls = []
    def stale(w): calls.append(1); return 1 if len(calls) == 1 else real(w)  # first pick collides with v1 (concurrent save)
    svc.versions.next_number = stale
    svc.rename(wid, f"Renamed {uuid.uuid4().hex[:4]}", uid)
    assert len(calls) == 2 and svc.versions.latest(wid).version == 2


# ---------- migration lock ----------
def test_concurrent_migrations_are_serialised(tmp_path):
    from app.models.database import Database, sqlite_file
    url = f"sqlite:///{tmp_path}/lock.db"; errors = []
    def go():
        try: Database(url).migrate()
        except Exception as e: errors.append(e)
    ts = [threading.Thread(target=go) for _ in range(4)]
    for t in ts: t.start()
    for t in ts: t.join()
    assert errors == [] and os.path.exists(sqlite_file(url) + ".migrate.lock")
    assert sqlite_file("sqlite://") is None and sqlite_file("postgresql+psycopg://x/y") is None


@pytest.mark.skipif(not os.environ.get("TEST_DATABASE_URL", "").startswith("postgres"), reason="needs Postgres")
def test_postgres_migrate_takes_advisory_lock():
    import sqlalchemy as sa
    from app.models.database import MIGRATION_LOCK_KEY, Database
    db = Database(os.environ["TEST_DATABASE_URL"])
    with db.engine.connect() as holder:  # another "replica" holds the lock: migrate must wait for it
        holder.execute(sa.text("SELECT pg_advisory_lock(:k)"), {"k": MIGRATION_LOCK_KEY}); holder.commit()
        t = threading.Thread(target=db.migrate); t.start(); time.sleep(0.5)
        assert t.is_alive()
        holder.execute(sa.text("SELECT pg_advisory_unlock(:k)"), {"k": MIGRATION_LOCK_KEY}); holder.commit()
        t.join(10); assert not t.is_alive()


# ---------- tracing ----------
def test_price_table_override(tmp_path, monkeypatch):
    from app.engine.usage import make_usage, price_for
    assert price_for("gpt-4o") == (2.5, 10.0) and price_for("my-local-model") is None
    f = tmp_path / "prices.json"; f.write_text(json.dumps({"my-local": [1, 2], "gpt-4o": [5, 20], "bad": "x"}))
    monkeypatch.setenv("STUDIO_PRICES_FILE", str(f))
    assert price_for("my-local-model") == (1.0, 2.0) and price_for("gpt-4o") == (5.0, 20.0) and price_for("bad") is None
    monkeypatch.setenv("STUDIO_PRICES", '{"gpt-4o": [7, 7]}')  # env wins over the file
    assert price_for("gpt-4o-2024") == (7.0, 7.0) and price_for("gpt-4o-mini") == (0.15, 0.6)  # longest prefix still wins
    assert make_usage("openai", "my-local-x", 1_000_000, 1_000_000)["cost_usd"] == 3.0
    monkeypatch.setenv("STUDIO_PRICES", "not json")
    assert price_for("gpt-4o") == (5.0, 20.0)  # invalid env ignored, file still applies


def test_langsmith_exporter_disables_langchain_tracer(monkeypatch):
    import langsmith
    from langsmith import utils as ls_utils
    for k in ("LANGSMITH_TRACING_V2", "LANGCHAIN_TRACING_V2", "OTEL_EXPORTER_OTLP_ENDPOINT", "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", "OTEL_SDK_DISABLED"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("LANGSMITH_API_KEY", "lsv2_test"); monkeypatch.setenv("LANGSMITH_TRACING", "true")
    ls_utils.get_env_var.cache_clear()
    try:
        assert ls_utils.tracing_is_enabled() is True          # LangChain would trace natively too...
        exps = telemetry.Telemetry._from_env()
        assert len(exps) == 1                                   # ...our OTLP exporter to LangSmith
        assert ls_utils.tracing_is_enabled() is False           # ...but its own tracer is now off: no duplicates
        assert os.environ["LANGSMITH_TRACING_V2"] == "false"    # inherited by import sandboxes
    finally:
        langsmith.configure(enabled=None); ls_utils.get_env_var.cache_clear()
