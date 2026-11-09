"""notifications (in-app, SMTP, notify webhook), webhook delivery log + backoff + redelivery, signing-secret
rotation, recovery from progress checkpoints, periodic lease reaper, live spans and OTel metrics."""
import asyncio, json, socket, time, uuid
from types import SimpleNamespace as NS
import httpx, pytest
from fastapi.testclient import TestClient
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from app.main import app
from app.core.errors import AppError
from app.engine.examples import EXAMPLE
from app.models import Run
from app.services import job_queue as jq, webhooks
from app.services.run_service import RunPlan, RunService
from app.services.telemetry import Telemetry, waited_s
from tests.test_hitl import APPROVAL


@pytest.fixture(scope="module")
def c():
    with TestClient(app) as client:
        yield client

def H(t): return {"Authorization": f"Bearer {t}"}
def user(c):
    return c.post("/api/auth/register", json={"email": f"d{uuid.uuid4().hex[:6]}@example.com", "password": "secret12"}).json()["data"]["token"]
def example(c, tok): return c.get("/api/workflows", headers=H(tok)).json()["data"][0]["id"]
def ws(c, tok, msg, until=("run_summary", "error")):
    with c.websocket_connect(f"/ws/run?token={tok}") as w:
        w.send_json(msg); evs = []
        while True:
            evs.append(w.receive_json())
            if evs[-1]["type"] in until: return evs
def wait_for(fn, timeout=8.0):
    end = time.time() + timeout
    while time.time() < end:
        if (v := fn()): return v
        time.sleep(0.05)
    raise AssertionError("condition not met")
def approval_wf(c, tok): return c.post("/api/workflows", json={**APPROVAL, "name": f"Approval {uuid.uuid4().hex[:5]}"}, headers=H(tok)).json()["data"]["id"]


# ---------- 1. notifications ----------
def test_in_app_notifications_bell_api(c):
    tok, other = user(c), user(c); wid = approval_wf(c, tok)
    rid = ws(c, tok, {"workflow_id": wid, "input": {"message": "A1"}})[0]["run_id"]
    data = c.get("/api/notifications", headers=H(tok)).json()["data"]
    [n] = data["items"]; assert data["unread"] == 1
    assert n["kind"] == "run_waiting" and n["run_id"] == rid and n["link"] == f"/workflows/{wid}?run={rid}" and not n["read"]
    assert n["params"]["label"] == "Manager approval" and n["params"]["prompt"] == "Approve refund for A1?"
    assert c.post(f"/api/notifications/{n['id']}/read", headers=H(other)).json()["error"]["code"] == "NOTIFICATION_NOT_FOUND"
    assert c.post(f"/api/notifications/{n['id']}/read", headers=H(tok)).json()["data"]["unread"] == 0
    ws(c, tok, {"workflow_id": wid, "input": {"message": "A2"}})
    assert c.get("/api/notifications?unread=true", headers=H(tok)).json()["data"]["unread"] == 1
    c.post("/api/notifications/read-all", headers=H(tok))
    assert c.get("/api/notifications", headers=H(tok)).json()["data"]["unread"] == 0
    assert c.get("/api/notifications", headers=H(other)).json()["data"]["items"] == []


def _free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


def test_email_notification_via_local_smtp_debug_server(c, monkeypatch):
    from aiosmtpd.controller import Controller
    got = []
    class Handler:
        async def handle_DATA(self, server, session, envelope):
            got.append(envelope); return "250 OK"
    port = _free_port(); ctl = Controller(Handler(), hostname="127.0.0.1", port=port); ctl.start()
    try:
        monkeypatch.setenv("SMTP_HOST", "127.0.0.1"); monkeypatch.setenv("SMTP_PORT", str(port)); monkeypatch.setenv("SMTP_STARTTLS", "0")
        monkeypatch.setenv("SMTP_FROM", "studio@test.local"); monkeypatch.setenv("STUDIO_PUBLIC_URL", "http://studio.test")
        tok = user(c); wid = approval_wf(c, tok)
        me = c.get("/api/auth/me", headers=H(tok)).json()
        rid = ws(c, tok, {"workflow_id": wid, "input": {"message": "B1"}})[0]["run_id"]
        env = wait_for(lambda: got and got[0])
        body = env.content.decode()
        assert env.mail_from == "studio@test.local" and env.rcpt_tos[0].endswith("@example.com")
        assert "waiting for your response" in body and "Approve refund for B1?" in body and f"http://studio.test/workflows/{wid}?run={rid}" in body
    finally:
        ctl.stop()


def test_smtp_unset_is_noop_and_failures_never_break_runs(c, monkeypatch):
    monkeypatch.delenv("SMTP_HOST", raising=False)
    from app.api.deps import notification_service
    n = notification_service().run_event("run_waiting", "nobody", "r1", None)
    assert notification_service().dispatch(n) == {}  # no channels configured
    monkeypatch.setenv("SMTP_HOST", "127.0.0.1"); monkeypatch.setenv("SMTP_PORT", str(_free_port()))  # nothing listens
    tok = user(c); wid = approval_wf(c, tok)
    assert ws(c, tok, {"workflow_id": wid, "input": {"message": "x"}})[-1]["status"] == "waiting"


def test_notify_webhook_signed(c, monkeypatch):
    sent = []
    monkeypatch.setattr(webhooks, "http_client", lambda: httpx.Client(transport=httpx.MockTransport(lambda r: sent.append(r) or httpx.Response(200))))
    monkeypatch.setenv("STUDIO_ALLOW_PRIVATE_CALLBACKS", "1"); monkeypatch.setenv("STUDIO_NOTIFY_WEBHOOK_URL", "http://localhost:9/notify")
    monkeypatch.setenv("STUDIO_NOTIFY_WEBHOOK_SECRET", "whsec_notify")
    tok = user(c); wid = approval_wf(c, tok)
    rid = ws(c, tok, {"workflow_id": wid, "input": {"message": "C1"}})[0]["run_id"]
    req = wait_for(lambda: next((r for r in sent if r.url.path == "/notify" and json.loads(r.content).get("run_id") == rid), None))  # not a late one from an earlier test
    body = json.loads(req.content)
    assert req.headers["x-studio-event"] == "notification.created" and body["run_id"] == rid and body["kind"] == "run_waiting"
    assert webhooks.verify_signature("whsec_notify", req.headers["x-studio-signature"], req.content)


# ---------- 2. delivery log, backoff, redelivery, rotation ----------
def _token(c, tok, wid): return c.post(f"/api/workflows/{wid}/tokens", json={"name": "d"}, headers=H(tok)).json()["data"]


def test_delivery_log_backoff_and_redeliver(c, monkeypatch):
    codes = iter([500, 502, 200]); seen = []
    def handler(r): seen.append(r); return httpx.Response(next(codes, 200))
    monkeypatch.setattr(webhooks, "http_client", lambda: httpx.Client(transport=httpx.MockTransport(handler)))
    monkeypatch.setenv("STUDIO_ALLOW_PRIVATE_CALLBACKS", "1"); monkeypatch.setenv("STUDIO_WEBHOOK_BACKOFF_BASE", "0.05")
    monkeypatch.setenv("STUDIO_JOB_REAP_EVERY", "0.2")
    tok = user(c); wid = example(c, tok); t = _token(c, tok, wid)
    c.post(f"/api/hooks/workflows/{wid}/runs", json={"input": {"message": "hi"}, "callback_url": "http://localhost:9/cb"}, headers=H(t["token"]))
    d = wait_for(lambda: next((x for x in c.get(f"/api/workflows/{wid}/deliveries", headers=H(tok)).json()["data"] if x["status"] == "ok"), None), 15)
    assert d["attempts"] == 3 and d["response_code"] == 200 and d["latency_ms"] is not None and d["last_error"] is None
    assert len(seen) == 3 and all(webhooks.verify_signature(t["signing_secret"], r.headers["x-studio-signature"], r.content) for r in seen)
    # redeliver: a fresh round, same payload
    monkeypatch.setattr(webhooks, "http_client", lambda: httpx.Client(transport=httpx.MockTransport(lambda r: seen.append(r) or httpx.Response(204))))
    r = c.post(f"/api/workflows/{wid}/deliveries/{d['id']}/redeliver", headers=H(tok)).json()["data"]
    assert r["status"] == "pending" and r["attempts"] == 0
    d2 = wait_for(lambda: next((x for x in c.get(f"/api/workflows/{wid}/deliveries", headers=H(tok)).json()["data"] if x["status"] == "ok" and x["response_code"] == 204), None))
    assert d2["attempts"] == 1 and seen[-1].content == seen[0].content
    other = user(c)
    assert c.get(f"/api/workflows/{wid}/deliveries", headers=H(other)).json()["error"]["code"] == "WORKFLOW_NOT_FOUND"
    assert c.post(f"/api/workflows/{wid}/deliveries/nope/redeliver", headers=H(tok)).json()["error"]["code"] == "DELIVERY_NOT_FOUND"


def test_delivery_gives_up_after_max_attempts_and_on_refused_address(monkeypatch):
    from app.api.deps import get_db
    from app.repositories import WebhookDeliveryRepository
    from app.services.delivery_service import DeliveryService, backoff
    q = jq.InMemoryJobQueue(); svc = DeliveryService(WebhookDeliveryRepository(get_db()), None, q)
    monkeypatch.setenv("STUDIO_WEBHOOK_MAX_ATTEMPTS", "2"); monkeypatch.setenv("STUDIO_WEBHOOK_BACKOFF_BASE", "10"); monkeypatch.setenv("STUDIO_WEBHOOK_BACKOFF_MAX", "15")
    assert [backoff(n) for n in (1, 2, 3)] == [10, 15, 15]
    monkeypatch.setattr(webhooks, "post", lambda *a, **k: webhooks.Attempt(False, 500, 1.0, "HTTP 500"))
    did = svc.create("w", "r", None, "http://x.example/cb", {"a": 1}); q.dequeue(0.1)
    assert svc.attempt(did) == "retrying" and q._delayed and svc.attempt(did) == "failed"
    row = svc.repo.get(did); assert row.attempts == 2 and row.response_code == 500 and row.next_attempt is None
    monkeypatch.setattr(webhooks, "post", lambda *a, **k: webhooks.Attempt(False, None, None, "address not allowed", retryable=False))
    did2 = svc.create("w", "r", None, "http://10.0.0.1/cb", {}); assert svc.attempt(did2) == "failed" and svc.repo.get(did2).attempts == 1


def test_signing_secret_rotation_with_grace(c, monkeypatch):
    from app.api.deps import trigger_service
    tok = user(c); wid = example(c, tok); t = _token(c, tok, wid); old = t["signing_secret"]
    r = c.post(f"/api/workflows/{wid}/tokens/{t['id']}/rotate-secret", headers=H(tok)).json()["data"]
    new = r["signing_secret"]; assert new.startswith("whsec_") and new != old and r["grace_until"] > time.time() and r["secret_rotated"]
    secrets = trigger_service().signing_secrets(t["id"]); assert secrets == [new, old]
    header = webhooks.sign(secrets, b"{}")
    assert header.count("v1=") == 2 and webhooks.verify_signature(old, header, b"{}") and webhooks.verify_signature(new, header, b"{}")
    monkeypatch.setenv("STUDIO_SECRET_GRACE", "0")  # grace over: only the new secret signs
    assert trigger_service().signing_secrets(t["id"]) == [new]
    assert not webhooks.verify_signature(old, webhooks.sign(trigger_service().signing_secrets(t["id"]), b"{}"), b"{}")
    assert c.post(f"/api/workflows/{wid}/tokens/nope/rotate-secret", headers=H(tok)).json()["error"]["code"] == "TOKEN_NOT_FOUND"
    assert c.post(f"/api/workflows/{wid}/tokens/{t['id']}/rotate-secret", headers=H(user(c))).json()["error"]["code"] == "WORKFLOW_NOT_FOUND"


# ---------- 3. recovery from the last checkpoint ----------
def test_recovered_job_continues_from_last_checkpoint(c):
    from app.api.deps import run_service, run_worker
    tok = user(c); wid = example(c, tok); svc = run_service(); owner = svc.workflows.get(wid).owner
    inp = {"message": "where is my order A100"}
    # a reference run with checkpointing, capturing each progress checkpoint
    saved = []; real = svc.runs.save_progress
    svc.runs.save_progress = lambda rid, ev, cp, fence=None: (saved.append((ev, cp)), real(rid, ev, cp, fence))
    ref = uuid.uuid4().hex[:10]; svc.runs.add(Run(id=ref, workflow_id=wid, input=json.dumps(inp), events="[]", status="running", started=time.time(), owner=owner, source="api"))
    plan = svc.plan(owner, {"workflow_id": wid, "input": inp}); plan.run_id, plan.checkpointing = ref, True
    async def send(ev): return True
    async def listen(): await asyncio.Event().wait()
    assert asyncio.run(svc.execute(plan, send, listen, owner)) == "ok" and len(saved) >= 2
    ref_row = svc.runs.get(ref); assert ref_row.checkpoint is None  # cleared once recorded
    # a "crashed" run: worker died right after the 2nd checkpoint
    events, cp = saved[1]; cpd = json.loads(cp)
    rid = uuid.uuid4().hex[:10]; svc.runs.add(Run(id=rid, workflow_id=wid, input=json.dumps(inp), events="[]", status="running", started=ref_row.started, owner=owner, source="api"))
    real(rid, events, cp); time.sleep(1.0)  # the dead worker's gap
    job = {"run_id": rid, "workflow_id": wid, "owner": owner, "input": inp, "recovered": True}
    assert asyncio.run(run_worker().run_job(job)) == "ok"
    row = svc.runs.get(rid); evs = json.loads(row.events); types = [e["type"] for e in evs]
    rec = types.index("run_recovered"); assert evs[rec]["node"] == cpd["node"]
    before = [e["node"] for e in evs[:rec] if e["type"] == "node_finished"]; after = [e["node"] for e in evs[rec:] if e["type"] == "node_finished"]
    assert not set(before) & set(after)  # nodes finished before the crash are not run again
    assert json.loads(row.final_state) == json.loads(ref_row.final_state)
    assert row.duration_ms < (row.ended - row.started) * 1000 - 900  # the dead worker's gap is not active time


def test_recovered_job_without_checkpoint_restarts(c):
    from app.api.deps import run_service, run_worker
    tok = user(c); wid = example(c, tok); svc = run_service(); owner = svc.workflows.get(wid).owner
    rid = uuid.uuid4().hex[:10]; svc.runs.add(Run(id=rid, workflow_id=wid, input="{}", events="[]", status="running", started=time.time(), owner=owner, source="api"))
    assert asyncio.run(run_worker().run_job({"run_id": rid, "workflow_id": wid, "owner": owner, "input": {"message": "hi"}, "recovered": True})) == "ok"
    assert json.loads(svc.runs.get(rid).events)[0]["type"] == "run_started"


def test_waited_s_excludes_recovery_gap():
    evs = [{"type": "run_started", "ts": 0}, {"type": "node_finished", "ts": 1}, {"type": "run_recovered", "ts": 61}, {"type": "run_finished", "ts": 62}]
    assert waited_s(evs, 62) == 60


# ---------- 4. periodic lease reaper ----------
def test_worker_reaps_expired_leases_periodically(monkeypatch):
    import fakeredis
    from app.services.run_worker import RunWorker
    monkeypatch.setenv("STUDIO_JOB_REAP_EVERY", "0.1")
    r = fakeredis.FakeRedis(decode_responses=True); q = jq.RedisJobQueue("redis://fake", client=r, worker_id="me", visibility=30)
    r.lpush(jq.PROCESSING_PREFIX + "gone", json.dumps({"run_id": "orphan"}))  # taken by a dead worker, lease long gone
    q.enqueue_at({"run_id": "later"}, time.time() + 0.2)
    w = RunWorker(q, lambda: None)
    async def go():
        t = asyncio.create_task(w.maintain()); await asyncio.sleep(1.2); w._stop = True; t.cancel()
    asyncio.run(go())
    queued = [json.loads(x) for x in r.lrange(jq.QUEUE_KEY, 0, -1)]
    assert {"run_id": "orphan", "recovered": True, "attempt": 2} in queued and {"run_id": "later"} in queued and r.zcard(jq.DELAYED_KEY) == 0


def test_memory_queue_delayed_jobs():
    q = jq.InMemoryJobQueue(); q.enqueue_at({"x": 2}, time.time() + 60); q.enqueue_at({"x": 1}, time.time() - 1)
    assert q.promote_due() == 1 and q.dequeue(0.1) == {"x": 1} and q.dequeue(0.01) is None


# ---------- 5. live spans + metrics ----------
def test_node_spans_are_exported_live_and_metrics_recorded():
    exp = InMemorySpanExporter(); reader = InMemoryMetricReader(); runs = []
    svc = RunService(None, NS(add=runs.append), telemetry=Telemetry(exporters=[exp], sync=True, metric_readers=[reader]))
    seen = []
    async def send(ev):
        if ev["type"] == "node_finished":
            done = exp.get_finished_spans(); seen.append((len([s for s in done if s.parent is not None]), any(s.parent is None for s in done)))
        return True
    async def listen(): await asyncio.sleep(3600)
    assert asyncio.run(svc.execute(RunPlan("w1", EXAMPLE, {"message": "where is my order A100"}), send, listen, "u1")) == "ok"
    assert seen and all(n == i + 1 and not root for i, (n, root) in enumerate(seen))  # each node span out before the next node, root still open
    assert sum(1 for s in exp.get_finished_spans() if s.parent is None) == 1
    data = {m.name: m for rm in reader.get_metrics_data().resource_metrics for sm in rm.scope_metrics for m in sm.metrics}
    assert {"studio.runs", "studio.run.duration", "studio.tokens"} <= set(data)
    pt = data["studio.runs"].data.data_points[0]; assert pt.value == 1 and dict(pt.attributes) == {"status": "ok", "source": "ui", "workflow_id": "w1"}


def test_paused_run_keeps_one_trace_across_segments(c):
    from app.api.deps import get_db
    from app.repositories import RunRepository, WorkflowRepository
    tok = user(c); wid = approval_wf(c, tok); db = get_db()
    exp = InMemorySpanExporter(); svc = RunService(WorkflowRepository(db), RunRepository(db), telemetry=Telemetry(exporters=[exp], sync=True, metric_readers=[]))
    uid = svc.workflows.get(wid).owner
    async def send(ev): return True
    async def listen(): await asyncio.sleep(3600)
    p = svc.plan(uid, {"workflow_id": wid, "input": {"message": "T"}}); p.run_id = rid = uuid.uuid4().hex[:10]
    assert asyncio.run(svc.execute(p, send, listen, uid)) == "waiting"
    first = svc.runs.get(rid); assert first.trace_id and json.loads(first.checkpoint)["trace"]["trace_id"] == first.trace_id
    assert asyncio.run(svc.execute(svc.plan_resume(uid, rid, "approved"), send, listen, uid)) == "ok"
    roots = sorted([s for s in exp.get_finished_spans() if s.name.startswith("run")], key=lambda s: s.start_time)
    assert [s.name for s in roots] == ["run", "run (resumed)"] and roots[1].parent.span_id == roots[0].context.span_id
    assert {format(s.context.trace_id, "032x") for s in exp.get_finished_spans()} == {first.trace_id} == {svc.runs.get(rid).trace_id}


def test_metrics_off_without_flag(monkeypatch):
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://127.0.0.1:4318"); monkeypatch.delenv("STUDIO_OTEL_METRICS", raising=False)
    assert Telemetry._metric_readers_from_env() == []
    monkeypatch.setenv("STUDIO_OTEL_METRICS", "1")
    readers = Telemetry._metric_readers_from_env(); assert len(readers) == 1
    for r in readers: r.shutdown()
