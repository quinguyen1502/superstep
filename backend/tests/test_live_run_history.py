"""TASK-0256: persisted-history invalidations keep the existing workflow/run visibility boundary."""
import asyncio
import json
import os
import subprocess
import sys
import threading
import uuid

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.api.deps import get_notification_hub, run_service
from app.main import app
from app.services.run_service import RunPlan


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def user(c):
    return c.post("/api/auth/register", json={"email": f"live-{uuid.uuid4().hex[:10]}@example.com", "password": "secret12"}).json()["data"]


def headers(u): return {"Authorization": f"Bearer {u['token']}"}


def workflow(c, u):
    return c.post("/api/workflows", headers=headers(u), json={"name": "Live history", "state": [],
        "nodes": [{"id": "s", "type": "start", "position": {"x": 0, "y": 0}, "data": {}},
                  {"id": "e", "type": "end", "position": {"x": 100, "y": 0}, "data": {}}],
        "edges": [{"id": "a", "source": "s", "target": "e"}]}).json()["data"]["id"]


def run(c, u, wid):
    with c.websocket_connect(f"/ws/run?token={u['token']}") as ws:
        ws.send_json({"workflow_id": wid, "input": {}})
        events = []
        while True:
            events.append(ws.receive_json())
            if events[-1]["type"] == "run_summary": return events[0]["run_id"]


def test_history_socket_requires_auth_and_workflow_access(client):
    owner, outsider = user(client), user(client)
    wid = workflow(client, owner)
    for query, code in (("", 4401), ("?token=bad", 4401), (f"?token={outsider['token']}", 4403)):
        with pytest.raises(WebSocketDisconnect) as error:
            with client.websocket_connect(f"/ws/workflows/{wid}/runs{query}") as ws: ws.receive_json()
        assert error.value.code == code


def test_terminal_push_is_content_free_and_after_persistence(client):
    owner = user(client); wid = workflow(client, owner)
    with client.websocket_connect(f"/ws/workflows/{wid}/runs?token={owner['token']}") as ws:
        assert ws.receive_json() == {"type": "ready"}
        rid = run(client, owner, wid)
        assert ws.receive_json() == {"type": "runs_changed"}
        row = next(r for r in client.get(f"/api/workflows/{wid}/runs", headers=headers(owner)).json()["data"] if r["id"] == rid)
        assert row["status"] == "ok" and row["events"]


def test_shared_viewer_only_observes_own_runs(client):
    owner, viewer = user(client), user(client)
    wid = workflow(client, owner); other = workflow(client, owner)
    client.put(f"/api/workflows/{wid}/shares", headers=headers(owner), json={"email": viewer["user"]["email"], "role": "viewer"})
    owners_run = run(client, owner, wid); viewers_run = run(client, viewer, wid); other_run = run(client, owner, other)
    svc = run_service()
    assert svc.watch_history(wid, owner["user"]["id"], owners_run)
    assert not svc.watch_history(wid, viewer["user"]["id"], owners_run)
    assert svc.watch_history(wid, viewer["user"]["id"], viewers_run)
    assert not svc.watch_history(wid, owner["user"]["id"], other_run)
    assert not svc.watch_history(wid, owner["user"]["id"], "missing")
    with client.websocket_connect(f"/ws/workflows/{wid}/runs?token={viewer['token']}") as ws:
        assert ws.receive_json() == {"type": "ready"}
        svc.history_changed(wid, viewers_run)
        assert ws.receive_json() == {"type": "runs_changed"}


def test_open_subscription_rechecks_revoked_share(client):
    owner, viewer = user(client), user(client); wid = workflow(client, owner)
    client.put(f"/api/workflows/{wid}/shares", headers=headers(owner), json={"email": viewer["user"]["email"], "role": "viewer"})
    rid = run(client, viewer, wid)
    with client.websocket_connect(f"/ws/workflows/{wid}/runs?token={viewer['token']}") as ws:
        assert ws.receive_json() == {"type": "ready"}
        assert client.delete(f"/api/workflows/{wid}/shares/{viewer['user']['id']}", headers=headers(owner)).status_code == 200
        run_service().history_changed(wid, rid)
        with pytest.raises(WebSocketDisconnect) as error: ws.receive_json()
        assert error.value.code == 4403


def test_reconnect_can_resnapshot_changes_missed_offline(client):
    owner = user(client); wid = workflow(client, owner)
    path = f"/ws/workflows/{wid}/runs?token={owner['token']}"
    with client.websocket_connect(path) as ws: assert ws.receive_json() == {"type": "ready"}
    rid = run(client, owner, wid)
    with client.websocket_connect(path) as ws:
        assert ws.receive_json() == {"type": "ready"}
        rows = client.get(f"/api/workflows/{wid}/runs", headers=headers(owner)).json()["data"]
        assert any(row["id"] == rid for row in rows)


def test_public_run_is_visible_and_progresses_before_finishing(client, monkeypatch):
    """Hold actual public-socket execution open; waiting until terminal persistence cannot pass."""
    owner = user(client); wid = workflow(client, owner)
    wf = client.get(f"/api/workflows/{wid}", headers=headers(owner)).json()["data"]
    wf["state"] = [{"name": "message", "type": "string"}, {"name": "answer", "type": "string"}]
    wf["nodes"].insert(1, {"id": "slow", "type": "llm", "position": {"x": 50, "y": 0},
        "data": {"prompt": "{{state.message}}", "output_field": "answer"}})
    wf["edges"] = [{"id": "a", "source": "s", "target": "slow"}, {"id": "b", "source": "slow", "target": "e"}]
    client.post("/api/workflows", headers=headers(owner), json=wf)
    settings = client.put(f"/api/workflows/{wid}/chat", headers=headers(owner), json={"enabled": True,
        "access": "anonymous", "input_field": "message", "reply_field": "answer", "steps": "full"}).json()["data"]
    slug = settings["slug"]
    session = client.post(f"/api/public/v1/chat/{slug}/sessions", headers={"X-Chat-Visitor": "new"}).json()["data"]
    finish_node, finish_run = threading.Event(), threading.Event()
    original = RunPlan.events

    def slow(plan):
        if plan.workflow_id != wid: yield from original(plan); return
        yield {"type": "node_started", "node": "slow", "node_type": "llm", "label": "Slow", "input": plan.input}
        if not finish_node.wait(8): raise TimeoutError("test did not release node")
        yield {"type": "node_finished", "node": "slow", "node_type": "llm", "label": "Slow", "delta": {"answer": "done"}, "duration_ms": 1}
        if not finish_run.wait(8): raise TimeoutError("test did not release run")
        yield {"type": "run_finished", "state": {"message": "hello", "answer": "done"}}

    monkeypatch.setattr(RunPlan, "events", slow)
    try:
        with client.websocket_connect(f"/ws/workflows/{wid}/runs?token={owner['token']}") as observer:
            assert observer.receive_json() == {"type": "ready"}
            with client.websocket_connect(f"/ws/public/v1/chat/{slug}") as guest:
                assert guest.receive_json()["type"] == "ready"
                guest.send_json({"type": "auth", "visitor": session["visitor_token"]})
                guest.send_json({"type": "message", "chat_session_id": session["id"], "text": "hello"})
                started = guest.receive_json(); assert started["type"] == "run_started"
                rid = started["run_id"]
                assert observer.receive_json() == {"type": "runs_changed"}
                row = next(r for r in client.get(f"/api/workflows/{wid}/runs", headers=headers(owner)).json()["data"] if r["id"] == rid)
                assert row["status"] == "running" and row["ended"] is None and row["source"] == "chat"
                assert row["events"][0]["type"] == "run_started"
                assert json.loads(run_service().runs.get(rid).checkpoint)["kind"] == "live_history"
                finish_node.set()
                while True:
                    frame = guest.receive_json()
                    if frame["type"] == "step" and frame["event"] == "finished": break
                row = next(r for r in client.get(f"/api/workflows/{wid}/runs", headers=headers(owner)).json()["data"] if r["id"] == rid)
                assert row["status"] == "running" and any(e["type"] == "node_finished" for e in row["events"])
                finish_run.set()
                while guest.receive_json()["type"] != "done": pass
                assert run_service().runs.get(rid).checkpoint is None
    finally: finish_node.set(); finish_run.set()


def test_history_socket_cleanup_releases_subscriptions(client):
    hub = get_notification_hub()
    if hub.kind != "memory": pytest.skip("memory subscriber registry contract")
    owner = user(client); wid = workflow(client, owner)
    from app.services.notification_hub import workflow_runs_channel
    for _ in range(3):
        with client.websocket_connect(f"/ws/workflows/{wid}/runs?token={owner['token']}") as ws:
            assert ws.receive_json() == {"type": "ready"}
    assert not hub._subs.get(workflow_runs_channel(wid))


def test_display_snapshot_is_cancelled_not_reexecuted_after_restart(client, monkeypatch):
    from app.services import job_queue, run_worker
    owner = user(client); wid = workflow(client, owner); svc = run_service()
    plan = svc.plan(owner["user"]["id"], {"workflow_id": wid, "input": {}}); plan.source = "chat"
    rid = uuid.uuid4().hex[:10]
    svc._save_live_history(rid, plan, [{"type": "run_started", "run_id": rid, "ts": 1}], 1, owner["user"]["id"])
    row = svc.runs.get(rid)
    monkeypatch.setattr(svc.runs, "list_resumes", lambda: [])
    monkeypatch.setattr(svc.runs, "list_unfinished", lambda: [row])
    monkeypatch.setattr(run_worker, "_recovered", False)
    queue = job_queue.InMemoryJobQueue()
    worker = run_worker.RunWorker(queue, lambda: svc)
    assert asyncio.run(worker.recover_unfinished()) == 0
    assert queue.dequeue(0.01) is None
    assert svc.runs.get(rid).status == "cancelled"
    assert svc.runs.get(rid).checkpoint is None


@pytest.mark.skipif(not os.environ.get("REDIS_URL"), reason="needs REDIS_URL")
def test_invalidation_from_a_separate_process_reaches_the_socket(client):
    owner = user(client); wid = workflow(client, owner); rid = run(client, owner, wid)
    with client.websocket_connect(f"/ws/workflows/{wid}/runs?token={owner['token']}") as ws:
        assert ws.receive_json() == {"type": "ready"}
        script = "from app.services.notification_hub import RedisNotificationHub,workflow_runs_channel; import os,sys; RedisNotificationHub(os.environ['REDIS_URL']).publish(workflow_runs_channel(sys.argv[1]), {'type':'runs_changed','run_id':sys.argv[2]})"
        subprocess.run([sys.executable, "-c", script, wid, rid], check=True, timeout=10)
        assert ws.receive_json() == {"type": "runs_changed"}
