"""Workflow tools run as linked child runs (TASK-0134, REQ-0073, DEC-0066): the parent's tool step starts the child once
per call and waits; the child's end resumes the parent with its result. Cancel, restarts, depth and answers."""
import asyncio, json, uuid
import pytest
from app.api.deps import get_job_queue, run_service, run_worker
from app.core.errors import AppError
from app.models import Run
from tests.test_agent_workflow_tools import STATE, supervisor, tool
from tests.test_hitl import APPROVAL, H, c, user, ws


def specialist(name, *nodes):
    """Start → nodes… → End, in a line; no nodes: the input comes back as the final state."""
    ids = ["start"] + [n["id"] for n in nodes] + ["end"]
    return {"name": name, "state": STATE,
            "nodes": [{"id": "start", "type": "start", "data": {}}, *nodes, {"id": "end", "type": "end", "data": {}}],
            "edges": [{"id": str(i), "source": a, "target": b} for i, (a, b) in enumerate(zip(ids, ids[1:]))]}


def llm(**d): return {"id": "x", "type": "llm", "data": {"label": "Reply", "prompt": "Answer: {{state.message}}", "output_field": "answer", **d}}


def drain():
    """Run every queued job (child runs, then the parents' resumes) in this process, as a worker would."""
    q, w, n = get_job_queue(), run_worker(), 0
    while (job := q.dequeue(0.05)) is not None:
        asyncio.run(w.run_job(job)); n += 1
    return n


def setup(tok, child):
    child_id = c.post("/api/workflows", json={**child, "name": f"{child['name']} {uuid.uuid4().hex[:4]}"}, headers=H(tok)).json()["data"]["id"]
    sup = c.post("/api/workflows", json={**supervisor(tool(wid=child_id)), "name": f"Team {uuid.uuid4().hex[:4]}"}, headers=H(tok)).json()["data"]["id"]
    return child_id, sup


def start(tok, sup, message="Where is order B200?"):
    evs = ws(tok, {"workflow_id": sup, "input": {"message": message}})
    return evs[0]["run_id"], evs


@pytest.fixture(autouse=True)
def no_key(monkeypatch): monkeypatch.delenv("OPENAI_API_KEY", raising=False)


def test_a_supervisor_calls_a_specialist():
    tok = user(); child_id, sup = setup(tok, specialist("Order desk", llm()))
    rid, evs = start(tok, sup)
    waiting = next(e for e in evs if e["type"] == "run_waiting")
    assert evs[-1]["status"] == "waiting" and waiting["wait"]["kind"] == "child" and waiting["tool"] == "desk"
    svc = run_service(); uid = c.get("/api/me", headers=H(tok)).json()["data"]["id"]
    assert all(p["id"] != rid for p in svc.pending(uid))  # nobody is asked anything
    cid = waiting["wait"]["run_id"]; child = svc.runs.get(cid)
    assert (child.parent_run_id, child.source, child.workflow_id, child.status) == (rid, "tool", child_id, "queued")
    assert child.parent_step.endswith("#mock_call_1") and json.loads(child.input) == {"message": "Help: Where is order B200?"}
    assert drain() == 2  # the child, then the parent's resume
    child, parent = svc.runs.get(cid), svc.runs.get(rid)
    assert child.status == "ok" and parent.status == "ok"
    st = json.loads(parent.final_state)
    assert st["steps"][0]["status"] == "ok" and json.loads(st["steps"][0]["result"])["answer"].startswith("[mock:")
    assert "Answer" in st["answer"]
    tool_step = [e for e in json.loads(parent.events) if e.get("type") == "node_finished" and e["node"] == "ag/__tool"][-1]
    assert tool_step["usage"]["provider"] == "workflow" and tool_step["usage"]["tokens"] == (child.tokens_in or 0) + (child.tokens_out or 0) > 0
    assert parent.tokens_in >= child.tokens_in  # the child's tokens count in the parent's totals


def test_time_travel_after_a_call_keeps_its_result():
    tok = user(); _, sup = setup(tok, specialist("Desk", llm()))
    rid, _ = start(tok, sup); drain()
    cps = c.get(f"/api/runs/{rid}/checkpoints", headers=H(tok)).json()["data"]["checkpoints"]
    at = [cp for cp in cps if cp["nodes"] == ["ag/__model"]][-1]  # the model step after the tool call
    evs = ws(tok, {"fork": {"run_id": rid, "checkpoint": at["index"]}})
    assert evs[-1]["status"] == "ok" and not any(e["type"] == "run_waiting" for e in evs)
    assert len(run_service().runs.children(rid)) == 1 and not run_service().runs.children(evs[0]["run_id"])


def test_a_failed_child_gives_the_model_an_error():
    tok = user(); _, sup = setup(tok, specialist("Broken desk", llm(credential_id="missing")))
    rid, _ = start(tok, sup); drain()
    parent = run_service().runs.get(rid)
    step = json.loads(parent.final_state)["steps"][0]
    assert parent.status == "ok" and step["status"] == "error" and "ended with error" in step["result"]


def test_two_calls_in_one_round_start_two_children(monkeypatch):
    from app.engine import agents
    replies = iter([("", [{"id": "a", "name": "desk", "args": {"message": "one"}}, {"id": "b", "name": "desk", "args": {"message": "two"}}]),
                    ("done", [])])
    monkeypatch.setattr(agents, "call_agent", lambda *a, **k: next(replies))
    tok = user(); _, sup = setup(tok, specialist("Echo desk"))
    w = c.get(f"/api/workflows/{sup}", headers=H(tok)).json()["data"]
    w["nodes"][1]["data"]["tools"][0]["outputs"] = ["message"]; c.post("/api/workflows", json=w, headers=H(tok))
    rid, _ = start(tok, sup); drain()
    svc = run_service(); kids = svc.runs.children(rid)
    assert sorted(json.loads(k.input)["message"] for k in kids) == ["one", "two"] and len({k.parent_step for k in kids}) == 2
    steps = json.loads(svc.runs.get(rid).final_state)["steps"]
    assert [json.loads(s["result"])["message"] for s in steps] == ["one", "two"]


def test_cancelling_the_parent_cancels_the_child():
    tok = user(); _, sup = setup(tok, specialist("Slow desk", llm()))
    rid, evs = start(tok, sup); cid = next(e for e in evs if e["type"] == "run_waiting")["wait"]["run_id"]
    assert c.post(f"/api/runs/{rid}/cancel", headers=H(tok)).json()["success"]
    svc = run_service()
    assert svc.runs.get(rid).status == "cancelled" and svc.runs.get(cid).status == "cancelled"
    drain()  # the child's job is skipped, and nothing resumes the cancelled parent
    assert svc.runs.get(rid).status == "cancelled"


def test_a_cancelled_child_answers_its_parent():
    tok = user(); _, sup = setup(tok, specialist("Desk", llm()))
    rid, evs = start(tok, sup); cid = next(e for e in evs if e["type"] == "run_waiting")["wait"]["run_id"]
    assert c.post(f"/api/runs/{cid}/cancel", headers=H(tok)).json()["success"]
    drain()
    step = json.loads(run_service().runs.get(rid).final_state)["steps"][0]
    assert step["status"] == "error" and "cancelled" in step["result"]


def test_people_and_children_cannot_answer_for_each_other():
    tok = user(); _, sup = setup(tok, specialist("Desk", llm()))
    rid, evs = start(tok, sup)
    r = c.post("/api/approvals/inbox/" + rid, json={"response": "approved"}, headers=H(tok))
    assert not r.json()["success"]
    svc = run_service(); uid = c.get("/api/me", headers=H(tok)).json()["data"]["id"]
    with pytest.raises(AppError) as e: svc.plan_resume(uid, rid, "approved", via_channel=True)
    assert e.value.code == "RUN_NOT_WAITING"
    human = c.post("/api/workflows", json=APPROVAL, headers=H(tok)).json()["data"]["id"]
    hid = ws(tok, {"workflow_id": human, "input": {"message": "x"}})[0]["run_id"]
    with pytest.raises(AppError) as e: svc.plan_resume(uid, hid, None, via_channel=True, child={"child_run_id": "nope", "status": "ok"})
    assert e.value.code == "RUN_NOT_WAITING"
    drain()


def test_a_call_starts_one_child_and_a_second_settle_resumes_once(monkeypatch):
    tok = user(); _, sup = setup(tok, specialist("Desk", llm()))
    rid, evs = start(tok, sup); cid = next(e for e in evs if e["type"] == "run_waiting")["wait"]["run_id"]
    svc = run_service(); parent = svc.runs.get(rid)
    # a recovered or retried tool step asks again with the same call key: the same child, nothing queued
    starter = svc._child_starter(rid, None, parent.owner)
    q, queued = get_job_queue(), []; enqueue = q.enqueue
    monkeypatch.setattr(q, "enqueue", lambda job: (queued.append(job), enqueue(job)))  # in memory or Redis alike
    assert starter(svc.runs.get(cid).parent_step, {}, None, {}, {}) == cid and queued == []
    drain()
    assert svc.runs.get(rid).status == "ok"
    assert svc.resume_parent(cid) is False  # settled again: the parent is no longer waiting for it


def test_a_child_cut_off_before_its_first_node_restarts_on_the_snapshot():
    tok = user(); child_id, sup = setup(tok, specialist("Desk", llm()))
    rid, evs = start(tok, sup); cid = next(e for e in evs if e["type"] == "run_waiting")["wait"]["run_id"]
    svc = run_service()
    while get_job_queue().dequeue(0.05) is not None: pass  # the child's job is lost with the server
    # the saved child changes meanwhile; the run keeps the version its parent planned
    w = c.get(f"/api/workflows/{child_id}", headers=H(tok)).json()["data"]; w["nodes"][1]["data"]["prompt"] = "Changed: {{state.message}}"
    c.post("/api/workflows", json=w, headers=H(tok))
    assert svc.runs.claim(cid, ("queued",)) is not None  # a worker took it, then died
    assert asyncio.run(run_worker().run_job(svc.recovery_job(svc.runs.get(cid)))) == "ok"
    child = svc.runs.get(cid)
    assert child.status == "ok" and "Changed" not in json.loads(child.final_state)["answer"]
    drain()
    assert svc.runs.get(rid).status == "ok"


def test_the_run_time_depth_limit():
    svc = run_service(); prev = None; ids = []
    for _ in range(6):  # a top run and five nested children: a sixth level is refused
        rid = uuid.uuid4().hex[:10]; ids.append(rid)
        svc.runs.add(Run(id=rid, workflow_id="adhoc", status="waiting", started=0.0, source="tool" if prev else "ui", parent_run_id=prev,
                         parent_step=f"k{rid}" if prev else None))
        prev = rid
    with pytest.raises(AppError) as e: svc._child_starter(prev, None, "u")("key", {}, None, {}, {"workflow_id": "w"})
    assert e.value.code == "WORKFLOW_TOOL_TOO_DEEP"
