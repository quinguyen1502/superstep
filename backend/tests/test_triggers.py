"""per-workflow tokens, REST trigger (async + sync), job queue + worker, webhook callback, cancel."""
import json, time, uuid
import httpx, pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services import run_worker as worker_mod, webhooks
from app.services.job_queue import InMemoryJobQueue, RedisJobQueue, make_job_queue
from app.services.trigger_service import check_callback_url
from app.core.errors import AppError


@pytest.fixture(scope="module")
def c():
    with TestClient(app) as client:  # lifespan starts the in-process worker
        yield client

def H(t): return {"Authorization": f"Bearer {t}"}
def user(c):
    return c.post("/api/auth/register", json={"email": f"t{uuid.uuid4().hex[:6]}@example.com", "password": "secret12"}).json()["data"]["token"]
def example(c, tok): return c.get("/api/workflows", headers=H(tok)).json()["data"][0]["id"]
def token_for(c, tok, wid): return c.post(f"/api/workflows/{wid}/tokens", json={"name": "ci"}, headers=H(tok)).json()["data"]
def wait_done(c, wid, rid, secret, timeout=15):
    for _ in range(int(timeout / 0.1)):
        r = c.get(f"/api/hooks/workflows/{wid}/runs/{rid}", headers=H(secret)).json()["data"]
        if r["status"] not in ("queued", "running"): return r
        time.sleep(0.1)
    raise AssertionError("run did not finish")


def test_queue_contract():
    import fakeredis
    for q in (InMemoryJobQueue(), RedisJobQueue("redis://fake", client=fakeredis.FakeRedis(decode_responses=True))):
        assert q.dequeue(0.01) is None
        q.enqueue({"run_id": "a"}); q.enqueue({"run_id": "b"})
        assert [q.dequeue(1)["run_id"], q.dequeue(1)["run_id"]] == ["a", "b"]  # FIFO
    assert make_job_queue(None).kind == "memory" and make_job_queue("redis://x:1/0").kind == "redis"


def test_token_lifecycle_and_auth(c):
    tok = user(c); wid = example(c, tok); t = token_for(c, tok, wid)
    assert t["token"].startswith("wft_") and t["prefix"] == t["token"][:10]
    listed = c.get(f"/api/workflows/{wid}/tokens", headers=H(tok)).json()["data"]
    assert [x["id"] for x in listed] == [t["id"]] and "token" not in listed[0] and "token_hash" not in listed[0]
    other = user(c)  # ownership: someone else cannot list or mint tokens for this workflow
    assert c.get(f"/api/workflows/{wid}/tokens", headers=H(other)).json()["error"]["code"] == "WORKFLOW_NOT_FOUND"
    for bad in ({}, H("wft_nope"), H(tok)):  # missing, unknown, a user JWT
        r = c.post(f"/api/hooks/workflows/{wid}/runs", json={}, headers=bad)
        assert r.status_code == 401 and r.json()["error"]["code"] == "TRIGGER_TOKEN_INVALID"
    assert c.delete(f"/api/workflows/{wid}/tokens/{t['id']}", headers=H(tok)).json()["data"]["ok"]
    r = c.post(f"/api/hooks/workflows/{wid}/runs", json={}, headers=H(t["token"])); assert r.status_code == 401  # revoked
    assert c.delete(f"/api/workflows/{wid}/tokens/nope", headers=H(tok)).json()["error"]["code"] == "TOKEN_NOT_FOUND"


def test_token_is_bound_to_its_workflow(c):
    tok = user(c); wid = example(c, tok); t = token_for(c, tok, wid)
    dup = c.post(f"/api/workflows/{wid}/duplicate", headers=H(tok)).json()["data"]["id"]
    r = c.post(f"/api/hooks/workflows/{dup}/runs", json={}, headers={"X-Workflow-Token": t["token"]})
    assert r.status_code == 401


def test_async_run_via_worker_and_history_source(c):
    tok = user(c); wid = example(c, tok); secret = token_for(c, tok, wid)["token"]
    r = c.post(f"/api/hooks/workflows/{wid}/runs", json={"input": {"message": "where is my order A100"}}, headers=H(secret))
    assert r.status_code == 202 and r.json()["data"]["status"] == "queued"
    rid = r.json()["data"]["run_id"]; res = wait_done(c, wid, rid, secret)
    assert res["status"] == "ok" and res["source"] == "api" and res["final_state"]["intent"] == "order_status" and res["metrics"]["tokens_in"] > 0
    h = next(x for x in c.get(f"/api/workflows/{wid}/runs", headers=H(tok)).json()["data"] if x["id"] == rid)
    assert h["source"] == "api" and h["status"] == "ok" and h["events"][0]["type"] == "run_started"


def test_sync_run_returns_final_state(c):
    tok = user(c); wid = example(c, tok); secret = token_for(c, tok, wid)["token"]
    r = c.post(f"/api/hooks/workflows/{wid}/runs", json={"input": {"message": "refund please"}, "mode": "sync"}, headers=H(secret))
    d = r.json()["data"]
    assert r.status_code == 200 and d["status"] == "ok" and d["final_state"]["intent"] == "refund" and d["run_id"]


def test_sync_run_reports_errors(c):
    tok = user(c); wid = example(c, tok); secret = token_for(c, tok, wid)["token"]
    d = c.post(f"/api/hooks/workflows/{wid}/runs", json={"input": {"message": 5}, "mode": "sync"}, headers=H(secret)).json()["data"]
    assert d["status"] == "error" and d["error"]["code"] == "WORKFLOW_INVALID"


def test_input_and_callback_validation(c, monkeypatch):
    tok = user(c); wid = example(c, tok); secret = token_for(c, tok, wid)["token"]
    r = c.post(f"/api/hooks/workflows/{wid}/runs", json={"input": {}, "callback_url": "ftp://x"}, headers=H(secret))
    assert r.json()["error"]["code"] == "CALLBACK_URL_INVALID"
    monkeypatch.delenv("STUDIO_ALLOW_PRIVATE_CALLBACKS", raising=False)
    for url in ("http://127.0.0.1/hook", "http://localhost:8000/x", "http://10.0.0.5/x", "http://169.254.169.254/latest"):
        with pytest.raises(AppError): check_callback_url(url)  # SSRF guard
    monkeypatch.setenv("STUDIO_ALLOW_PRIVATE_CALLBACKS", "1"); assert check_callback_url("http://127.0.0.1/hook")


def test_webhook_callback_receives_result(c, monkeypatch):
    got = []
    def handler(req): got.append((req.headers["x-studio-event"], json.loads(req.content), req)); return httpx.Response(204)
    monkeypatch.setattr(webhooks, "http_client", lambda: httpx.Client(transport=httpx.MockTransport(handler)))
    monkeypatch.setenv("STUDIO_ALLOW_PRIVATE_CALLBACKS", "1")
    tok = user(c); wid = example(c, tok); created = token_for(c, tok, wid); secret = created["token"]
    rid = c.post(f"/api/hooks/workflows/{wid}/runs", json={"input": {"message": "hi"}, "callback_url": "http://localhost:9/hook"}, headers=H(secret)).json()["data"]["run_id"]
    wait_done(c, wid, rid, secret)
    for _ in range(50):
        if got: break
        time.sleep(0.1)
    event, body, req = got[0]
    #: connected to the pinned resolved IP, Host kept; HMAC-signed with the token's signing secret
    assert req.url.host in ("127.0.0.1", "::1") and req.headers["host"] == "localhost:9"
    assert created["signing_secret"].startswith("whsec_")
    assert webhooks.verify_signature(created["signing_secret"], req.headers["x-studio-signature"], req.content)
    assert not webhooks.verify_signature("whsec_wrong", req.headers["x-studio-signature"], req.content)
    assert event == "run.finished" and body["run_id"] == rid and body["status"] == "ok" and body["final_state"]["intent"] == "general"


def test_result_is_scoped_to_the_token(c):
    tok = user(c); wid = example(c, tok); secret = token_for(c, tok, wid)["token"]
    other = user(c); owid = example(c, other); osecret = token_for(c, other, owid)["token"]
    rid = c.post(f"/api/hooks/workflows/{wid}/runs", json={"input": {"message": "x"}}, headers=H(secret)).json()["data"]["run_id"]
    assert c.get(f"/api/hooks/workflows/{owid}/runs/{rid}", headers=H(osecret)).json()["error"]["code"] == "RUN_NOT_FOUND"


def test_cancel_queued_run_is_skipped(c):
    """Without the worker running, a queued run can be cancelled and the worker then skips it.
    Uses the module client: a second TestClient would start the shared worker on another event loop."""
    import asyncio
    from app.api.deps import run_service, trigger_service
    from app.services.run_worker import RunWorker
    q = InMemoryJobQueue(); trig = trigger_service(); trig.jobs = q
    tok = user(c); wid = example(c, tok); secret = token_for(c, tok, wid)["token"]
    uid = c.get("/api/me", headers=H(tok)).json()["data"]["id"]
    t = trig.authenticate(wid, secret); rid = trig.start(t, {"message": "x"}, None)
    run_service().cancel(rid, uid)
    assert asyncio.run(RunWorker(q, run_service).run_job(q.dequeue(1))) is None
    assert run_service().runs.get(rid).status == "cancelled"
