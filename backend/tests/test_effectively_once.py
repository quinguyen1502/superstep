"""TASK-0021: idempotency keys + node-result ledger, LangGraph superstep checkpoints (fan-out, imported graphs),
fencing tokens, export of lost trace segments, live notification push, HTML e-mail and notification preferences."""
import asyncio, email, http.server, json, os, socket, threading, time, uuid
from types import SimpleNamespace as NS
import pytest
from fastapi.testclient import TestClient
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode
from app.main import app
from app.engine.effects import Effects, idempotency_key
from app.engine.runtime import run_stream
from app.engine.tools import register_tool
from app.models import Run
from app.repositories import NodeResultRepository, RunRepository, StaleLease, WorkflowRepository
from app.services.notification_hub import InMemoryNotificationHub
from app.services.run_service import RunService
from app.services.telemetry import Telemetry
from tests.test_deferred import H, approval_wf, example, user, ws, wait_for, _free_port


@pytest.fixture(scope="module")
def c():
    with TestClient(app) as client:
        yield client

CALLS: dict = {}

@register_tool("t21_count")
def t21_count(state, idempotency_key=None):
    CALLS.setdefault("count", []).append(idempotency_key); return f"done {len(CALLS['count'])}"

@register_tool("t21_a")
def t21_a(state): CALLS.setdefault("a", []).append(1); return "A"

@register_tool("t21_b")
def t21_b(state): CALLS.setdefault("b", []).append(1); return "B"


def wf(nodes, edges, state=("message", "x", "a", "b")):
    return {"name": "t21", "state": [{"name": n, "type": "string"} for n in state],
            "nodes": [{"id": "s", "type": "start", "position": {"x": 0, "y": 0}, "data": {"label": "Start"}}]
                     + [{"id": i, "type": t, "position": {"x": 0, "y": 0}, "data": {"label": i, **d}} for i, t, d in nodes]
                     + [{"id": "e", "type": "end", "position": {"x": 0, "y": 0}, "data": {"label": "End"}}],
            "edges": [{"id": f"x{k}", "source": a, "target": b} for k, (a, b) in enumerate(edges)]}

def tool(fn, out): return {"mode": "function", "function": fn, "output_field": out}
FAN = wf([("a", "tool", tool("t21_a", "a")), ("b", "tool", tool("t21_b", "b"))], [("s", "a"), ("s", "b"), ("a", "e"), ("b", "e")])


class DictLedger:
    def __init__(self): self.rows = {}
    def get(self, nid, it): return self.rows.get((nid, it), (None,))[0]
    def put(self, nid, it, delta, key): self.rows.setdefault((nid, it), (delta, key))


# ---------- (a) idempotency keys + ledger ----------
def test_http_tool_node_sends_stable_idempotency_key(monkeypatch):
    monkeypatch.setenv("STUDIO_HTTP_TOOL_ALLOW_PRIVATE", "1")  # the receiver is on 127.0.0.1 (TASK-0039 guard)
    seen = []
    class Hd(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            seen.append({k: self.headers[k] for k in ("Idempotency-Key", "X-Studio-Run-Id", "X-Studio-Attempt")})
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(b'{"ok": true}')
        def log_message(self, *a): pass
    srv = http.server.HTTPServer(("127.0.0.1", 0), Hd); threading.Thread(target=srv.serve_forever, daemon=True).start()
    w = wf([("h", "tool", {"mode": "http", "method": "POST", "url": f"http://127.0.0.1:{srv.server_port}/x", "body": "{}", "output_field": "x"})], [("s", "h"), ("h", "e")])
    try:
        list(run_stream(w, {}, effects=Effects("run1", attempt=1)))
        list(run_stream(w, {}, effects=Effects("run1", attempt=2)))  # the same execution retried by a recovered job
    finally: srv.shutdown()
    key = idempotency_key("run1", "h", 1)
    assert [s["Idempotency-Key"] for s in seen] == [key, key] and [s["X-Studio-Attempt"] for s in seen] == ["1", "2"]
    assert seen[0]["X-Studio-Run-Id"] == "run1" and idempotency_key("run1", "h", 2) != key and idempotency_key("run2", "h", 1) != key


def test_ledger_reuses_finished_side_effect_nodes():
    CALLS.clear(); led = DictLedger()
    w = wf([("t", "tool", tool("t21_count", "x"))], [("s", "t"), ("t", "e")])
    first = list(run_stream(w, {}, effects=Effects("r", ledger=led)))
    again = list(run_stream(w, {}, effects=Effects("r", attempt=2, ledger=led)))  # e.g. a restart after a crash
    assert CALLS["count"] == [idempotency_key("r", "t", 1)]  # executed once, with the key passed to the tool
    fin = lambda evs: [e for e in evs if e["type"] == "node_finished" and e["node"] == "t"][0]  # noqa: E731
    assert fin(again).get("reused") is True and "reused" not in fin(first)
    assert first[-1]["state"]["x"] == again[-1]["state"]["x"] == "done 1"


# ---------- (b) checkpoints at fan-out ----------
def test_fan_out_step_is_checkpointed_and_resumable():
    CALLS.clear()
    cps = [e for e in run_stream(FAN, {}) if e["type"] == "_checkpoint"]
    fan = next(c for c in cps if set(c["nodes"]) == {"a", "b"})
    CALLS.clear()
    evs = list(run_stream(FAN, {}, resume={k: fan[k] for k in ("nodes", "state", "counts")}))
    assert evs[-1]["type"] == "run_finished" and evs[-1]["state"]["a"] == "A" and evs[-1]["state"]["b"] == "B"
    assert {e["node"] for e in evs if e["type"] == "node_started"} == {"a", "b", "e"} and CALLS == {"a": [1], "b": [1]}


def test_human_in_parallel_branch_resumes_with_its_sibling():
    w = wf([("a", "tool", tool("t21_a", "a")), ("h", "human", {"prompt": "ok?", "output_field": "b"})], [("s", "a"), ("s", "h"), ("a", "e"), ("h", "e")])
    led = DictLedger(); evs = list(run_stream(w, {}, effects=Effects("p", ledger=led)))
    cp = evs[-1]["checkpoint"]; assert evs[-1]["type"] == "run_waiting" and set(cp["nodes"]) == {"a", "h"}
    CALLS.clear()
    done = list(run_stream(w, {}, resume={**cp, "value": "yes"}, effects=Effects("p", ledger=led)))
    assert done[-1]["state"]["b"] == "yes" and done[-1]["state"]["a"] == "A" and "a" not in CALLS  # sibling reused, not re-run


def test_imported_graph_checkpoint_roundtrip():
    """The sandbox runner's saver helpers: serialize a superstep checkpoint, restore it in a fresh graph, continue."""
    from typing import Optional, TypedDict
    from langgraph.graph import END, START, StateGraph
    from app.engine.sandbox import runner
    class S(TypedDict, total=False):
        a: Optional[str]; b: Optional[str]; c: Optional[str]
    calls = []
    def build():
        g = StateGraph(S)
        for k in "abc": g.add_node(k, (lambda k: lambda s: (calls.append(k), {k: k.upper()})[1])(k))
        g.add_edge(START, "a"); g.add_edge("a", "b"); g.add_edge("a", "c"); g.add_edge("b", END); g.add_edge("c", END)
        return g.compile()
    g = build(); sv = runner.attach_saver(g); cfg = {"configurable": {"thread_id": "studio"}}; blob = None
    for mode, chunk in g.stream({}, cfg, stream_mode=["updates", "checkpoints"], durability="sync"):
        if mode == "checkpoints" and sorted(chunk["next"]) == ["b", "c"]: blob = runner.dump_checkpoint(sv, cfg); break
    assert blob and calls == ["a"]
    g2 = build(); sv2 = runner.attach_saver(g2); runner.load_checkpoint(sv2, blob)
    out = None
    for chunk in g2.stream(None, cfg, stream_mode="values"): out = chunk
    assert sorted(calls) == ["a", "b", "c"] and out == {"a": "A", "b": "B", "c": "C"}
    assert runner.attach_saver(g2) is None  # a graph that already has a checkpointer keeps its own


# ---------- (c) fencing ----------
def _queued_run(svc, wid, owner, status="queued"):
    rid = uuid.uuid4().hex[:10]
    svc.runs.add(Run(id=rid, workflow_id=wid, input="{}", events="[]", status=status, started=time.time(), owner=owner, source="api"))
    return rid


def test_claim_and_fenced_writes(c):
    from app.api.deps import get_db, run_service
    tok = user(c); wid = example(c, tok); svc = run_service(); owner = svc.workflows.get(wid).owner; repo = RunRepository(get_db())
    rid = _queued_run(svc, wid, owner)
    g1 = repo.claim(rid, ("queued",)); assert g1 == 1 and repo.get(rid).status == "running"
    assert repo.claim(rid, ("queued",)) is None  # a second fresh claim loses
    g2 = repo.claim(rid, ("running",)); assert g2 == 2  # a recovered job takes over
    with pytest.raises(StaleLease): repo.save_progress(rid, "[]", "{}", g1)
    with pytest.raises(StaleLease): repo.add(Run(id=rid, status="ok", events="[]"), fence=g1)
    with pytest.raises(StaleLease): NodeResultRepository(get_db()).put(rid, "n", 1, "{}", "k", g1)
    repo.save_progress(rid, "[1]", '{"kind": "progress"}', g2); repo.add(Run(id=rid, status="ok", events="[2]"), fence=g2)
    assert repo.get(rid).status == "ok" and repo.get(rid).lease_gen == 2


def test_stale_worker_is_fenced_out_and_its_run_cancelled(c):
    from app.api.deps import run_service, run_worker
    tok = user(c); svc = run_service(); taken = {}
    @register_tool("t21_takeover")
    def takeover(state):  # while this node runs, the reaper requeued the job and another worker claimed it
        taken["gen"] = svc.runs.claim(taken["rid"], ("running",)); return "late"
    w = wf([("t1", "tool", tool("t21_takeover", "x")), ("t2", "tool", tool("t21_count", "a"))], [("s", "t1"), ("t1", "t2"), ("t2", "e")])
    wid = c.post("/api/workflows", json=w, headers=H(tok)).json()["data"]["id"]; owner = svc.workflows.get(wid).owner
    rid = taken["rid"] = _queued_run(svc, wid, owner); CALLS.clear()
    assert asyncio.run(run_worker().run_job({"run_id": rid, "workflow_id": wid, "owner": owner, "input": {}})) == "fenced"
    row = svc.runs.get(rid)
    assert taken["gen"] == 2 and row.lease_gen == 2 and row.status == "running"  # the new owner's run is untouched
    assert "count" not in CALLS  # the stale worker stopped before its next side effect
    assert not NodeResultRepository(svc.runs.db).for_run(rid)  # and its result of t1 was rejected


# ---------- (d) lost segment root span ----------
def test_recovery_exports_the_lost_segment_root_and_links_it(c):
    from app.api.deps import get_db
    exp = InMemorySpanExporter(); db = get_db()
    svc = RunService(WorkflowRepository(db), RunRepository(db), telemetry=Telemetry(exporters=[exp], sync=True, metric_readers=[]))
    tok = user(c); wid = example(c, tok); owner = svc.workflows.get(wid).owner; rid = _queued_run(svc, wid, owner)
    # the dead worker: its live root span never ended, one node span was exported under it
    dead = svc.telemetry.start_run({"id": rid, "started": time.time() - 5}); svc.telemetry.node(dead, {"type": "node_finished", "node": "s", "ts": time.time() - 4})
    gen = svc.runs.claim(rid, ("queued",))
    svc.runs.save_progress(rid, "[]", json.dumps({"kind": "progress", "workflow": json.loads(svc.workflows.get(wid).data), "ts": time.time() - 3, "trace": dead.ref}), gen)
    gen = svc.runs.claim(rid, ("running",))
    plan = svc.plan_recover(svc.runs.get(rid), gen, 2)
    async def send(ev): return True
    async def listen(): await asyncio.Event().wait()
    assert asyncio.run(svc.execute(plan, send, listen, owner)) == "ok"
    spans = exp.get_finished_spans(); ids = dead.ids
    lost = [s for s in spans if format(s.context.span_id, "016x") == ids["span_id"]]
    assert len(lost) == 1 and lost[0].status.status_code == StatusCode.ERROR and lost[0].attributes["studio.run.lost"]
    node = next(s for s in spans if s.name == "node s" and format(s.parent.span_id, "016x") == ids["span_id"]); assert node
    seg = next(s for s in spans if s.name.startswith("run (") and s.parent and format(s.parent.span_id, "016x") == ids["span_id"])
    assert [format(l.context.span_id, "016x") for l in seg.links] == [ids["span_id"]]
    assert all(format(s.context.trace_id, "032x") == ids["trace_id"] for s in spans)


# ---------- (e) live push, HTML e-mail, preferences ----------
def test_preferences_api(c):
    tok = user(c)
    assert c.get("/api/notifications/preferences", headers=H(tok)).json()["data"] == {"in_app": True, "email": True, "email_configured": False, "lang": "en"}
    assert c.put("/api/notifications/preferences", json={"email": False}, headers=H(tok)).json()["data"]["email"] is False
    for bad in ({"email": "no"}, {"push": True}, [], {}):
        r = c.put("/api/notifications/preferences", json=bad, headers=H(tok))
        assert r.status_code == 422 and r.json()["error"]["code"] == "NOTIFICATION_PREFS_INVALID"
    assert c.get("/api/notifications/preferences", headers=H(tok)).json()["data"]["in_app"] is True


def test_in_app_off_stores_nothing(c):
    tok = user(c); wid = approval_wf(c, tok)
    c.put("/api/notifications/preferences", json={"in_app": False}, headers=H(tok))
    ws(c, tok, {"workflow_id": wid, "input": {"message": "Z"}})
    assert c.get("/api/notifications", headers=H(tok)).json()["data"] == {"items": [], "unread": 0}


def test_live_push_over_websocket(c):
    tok = user(c); wid = approval_wf(c, tok); other = user(c)
    with c.websocket_connect(f"/ws/notifications?token={tok}") as w, c.websocket_connect(f"/ws/notifications?token={other}") as w2:
        assert w.receive_json() == {"type": "ready"} and w2.receive_json() == {"type": "ready"}
        rid = ws(c, tok, {"workflow_id": wid, "input": {"message": "P1"}})[0]["run_id"]
        m = w.receive_json()
        assert m["type"] == "notification" and m["notification"]["run_id"] == rid and m["unread"] == 1
    with pytest.raises(Exception):
        with c.websocket_connect("/ws/notifications?token=bad") as w: w.receive_json()


def test_in_memory_hub_fan_out_is_per_user():
    hub = InMemoryNotificationHub()
    async def go():
        async with hub.subscribe("u1") as feed, hub.subscribe("u2") as feed2:
            threading.Thread(target=lambda: (hub.publish("u2", {"n": 0}), hub.publish("u1", {"n": 1}))).start()
            got = await asyncio.wait_for(feed.__anext__(), 2); got2 = await asyncio.wait_for(feed2.__anext__(), 2)
            return got, got2
    assert asyncio.run(go()) == ({"n": 1}, {"n": 0}) and not any(hub._subs.values())


@pytest.mark.skipif(not os.environ.get("REDIS_URL"), reason="needs REDIS_URL")
def test_redis_hub_pub_sub():
    from app.services.notification_hub import RedisNotificationHub
    hub = RedisNotificationHub(os.environ["REDIS_URL"]); uid = uuid.uuid4().hex
    async def go():
        async with hub.subscribe(uid) as feed:
            await asyncio.sleep(0.1); await asyncio.to_thread(hub.publish, uid, {"hello": 1})
            return await asyncio.wait_for(feed.__anext__(), 5)
    assert asyncio.run(go()) == {"hello": 1}


def test_html_email_and_email_preference(c, monkeypatch):
    from aiosmtpd.controller import Controller
    got = []
    class Handler:
        async def handle_DATA(self, server, session, envelope): got.append(envelope); return "250 OK"
    port = _free_port(); ctl = Controller(Handler(), hostname="127.0.0.1", port=port); ctl.start()
    try:
        for k, v in {"SMTP_HOST": "127.0.0.1", "SMTP_PORT": str(port), "SMTP_STARTTLS": "0", "STUDIO_PUBLIC_URL": "http://studio.test"}.items(): monkeypatch.setenv(k, v)
        tok = user(c); wid = c.post("/api/workflows", json={**json.loads(json.dumps(__import__("tests.test_hitl", fromlist=["APPROVAL"]).APPROVAL)),
                                                             "name": "<b>Refunds</b>"}, headers=H(tok)).json()["data"]["id"]
        ws(c, tok, {"workflow_id": wid, "input": {"message": "A1"}}); wait_for(lambda: got)
        msg = email.message_from_bytes(got[0].content)
        parts = {p.get_content_type(): p.get_payload(decode=True).decode() for p in msg.walk() if not p.is_multipart()}
        assert set(parts) == {"text/plain", "text/html"}
        h = parts["text/html"]
        assert "&lt;b&gt;Refunds&lt;/b&gt;" in h and "<b>Refunds</b>" not in h and f'href="http://studio.test/workflows/{wid}?run=' in h
        assert "Workflow: <b>Refunds</b>" in parts["text/plain"]
        assert c.get("/api/notifications/preferences", headers=H(tok)).json()["data"]["email_configured"] is True
        c.put("/api/notifications/preferences", json={"email": False}, headers=H(tok))
        ws(c, tok, {"workflow_id": wid, "input": {"message": "A2"}}); time.sleep(0.5)
        assert len(got) == 1 and c.get("/api/notifications", headers=H(tok)).json()["data"]["unread"] == 2  # in-app still on
    finally: ctl.stop()


def test_ui_run_paused_in_parallel_branch_does_not_rerun_sibling(c):
    from app.api.deps import get_db
    tok = user(c)
    w = wf([("a", "tool", tool("t21_a", "a")), ("h", "human", {"prompt": "ok?", "output_field": "b"})], [("s", "a"), ("s", "h"), ("a", "e"), ("h", "e")])
    wid = c.post("/api/workflows", json=w, headers=H(tok)).json()["data"]["id"]; CALLS.clear()
    evs = ws(c, tok, {"workflow_id": wid, "input": {}}); rid = evs[0]["run_id"]
    # The Human node pauses by raising, and LangGraph cancels sibling tasks that have not started yet when a task
    # raises (pregel/_runner.py). So `a` may or may not run before the pause; both orders are valid (TASK-0109).
    ran_before = CALLS.get("a", []) == [1]
    assert any(e["type"] == "run_waiting" for e in evs) and CALLS.get("a", []) in ([], [1])
    assert bool(NodeResultRepository(get_db()).for_run(rid)) == ran_before  # recorded in the ledger only if it ran
    done = ws(c, tok, {"resume_run_id": rid, "response": "yes"})
    assert done[-1]["status"] == "ok" and CALLS["a"] == [1]  # the sibling ran exactly once across both segments
    reused = any(e.get("reused") for e in done if e["type"] == "node_finished" and e.get("node") == "a")
    assert reused == ran_before  # when it ran before the pause, the resume took its result from the ledger
    assert not NodeResultRepository(get_db()).for_run(rid)  # purged once the run finished
