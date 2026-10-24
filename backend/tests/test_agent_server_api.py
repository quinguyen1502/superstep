"""LangGraph Agent Server API subset at /api/lg, driven by the official `langgraph-sdk` client (its sync client over
the app's TestClient): assistants, threads, runs (create / wait / stream / get / list / join), Human-node interrupts
resumed with `Command(resume=...)`, and who sees what (workflow token vs JWT)."""
import uuid
import pytest
from fastapi.testclient import TestClient
from langgraph_sdk.client import SyncLangGraphClient
from app.main import app
from test_hitl import APPROVAL

SIMPLE = {"name": "Echo", "state": [{"name": "message", "type": "string"}, {"name": "answer", "type": "string"}],
          "nodes": [{"id": "start", "type": "start", "position": {"x": 0, "y": 0}, "data": {"label": "Start"}},
                    {"id": "reply", "type": "llm", "position": {"x": 0, "y": 0}, "data": {"label": "Reply", "prompt": "Say: {{state.message}}", "output_field": "answer"}},
                    {"id": "end", "type": "end", "position": {"x": 0, "y": 0}, "data": {"label": "End"}}],
          "edges": [{"id": "1", "source": "start", "target": "reply"}, {"id": "2", "source": "reply", "target": "end"}]}


@pytest.fixture(scope="module")
def http():
    with TestClient(app) as c: yield c


def H(t): return {"Authorization": f"Bearer {t}"}


def user(http):
    return http.post("/api/auth/register", json={"email": f"lg{uuid.uuid4().hex[:6]}@example.com", "password": "secret12"}).json()["data"]["token"]


def save(http, jwt, wf):
    return http.post("/api/workflows", json={**wf, "name": f"{wf['name']} {uuid.uuid4().hex[:4]}"}, headers=H(jwt)).json()["data"]["id"]


def token(http, jwt, wid):
    return http.post(f"/api/workflows/{wid}/tokens", json={"name": "lg"}, headers=H(jwt)).json()["data"]["token"]


def status(fn, *a, **kw) -> int:
    """The HTTP status a client call fails with (the SDK raises the transport's HTTPStatusError)."""
    with pytest.raises(Exception) as e: fn(*a, **kw)
    return e.value.response.status_code


def sdk(key):
    """The SDK's own client classes over the in-process app (what `get_sync_client(url=…/api/lg, api_key=key)` builds)."""
    c = TestClient(app, base_url="http://testserver/api/lg", headers={"x-api-key": key})
    return SyncLangGraphClient(c)


def test_token_client_runs_the_workflow_on_a_thread(http):
    jwt = user(http); wid = save(http, jwt, SIMPLE); other = save(http, jwt, SIMPLE)
    client = sdk(token(http, jwt, wid))
    assert [a["assistant_id"] for a in client.assistants.search()] == [wid], "a token sees only its workflow"
    a = client.assistants.get(wid)
    assert a["graph_id"] == wid and a["name"].startswith("Echo")
    assert status(client.assistants.get, other) == 404
    g = client.assistants.get_graph(wid)
    assert [n["id"] for n in g["nodes"]] == ["__start__", "reply", "__end__"] and {"source": "__start__", "target": "reply", "conditional": False} in g["edges"]
    assert client.assistants.get_schemas(wid)["input_schema"]["properties"] == {"message": {"type": "string"}, "answer": {"type": "string"}}

    t = client.threads.create(metadata={"customer": "c1"})
    assert t["status"] == "idle" and t["metadata"] == {"customer": "c1"}
    out = client.runs.wait(t["thread_id"], wid, input={"message": "hello"})
    assert out["message"] == "hello" and "hello" in out["answer"]
    st = client.threads.get_state(t["thread_id"])
    assert st["values"] == out and st["next"] == []
    assert client.threads.get(t["thread_id"])["status"] == "idle"

    # a second run starts from the thread's state with the new input on top; stream updates + values
    parts = list(client.runs.stream(t["thread_id"], wid, input={"message": "again"}, stream_mode=["updates", "values"]))
    events = [p.event for p in parts]
    assert events[0] == "metadata" and "updates" in events and "values" in events
    assert {"reply": parts[events.index("updates")].data["reply"]} == parts[events.index("updates")].data
    assert "again" in parts[-1].data["answer"]
    runs = client.runs.list(t["thread_id"])
    assert len(runs) == 2 and all(r["status"] == "success" and r["assistant_id"] == wid for r in runs)
    assert client.runs.get(t["thread_id"], runs[0]["run_id"])["run_id"] == runs[0]["run_id"]
    assert client.runs.join(t["thread_id"], runs[0]["run_id"])["answer"] == parts[-1].data["answer"]
    assert [x["thread_id"] for x in client.threads.search(metadata={"customer": "c1"})] == [t["thread_id"]]

    # the run is an ordinary API run in the workflow's history
    hist = http.get(f"/api/workflows/{wid}/runs", headers=H(jwt)).json()["data"]
    assert {r["id"] for r in hist} >= {r["run_id"] for r in runs} and all(r["source"] == "api" for r in hist)


def test_stateless_run_and_thread_mismatch(http):
    jwt = user(http); wid = save(http, jwt, SIMPLE); wid2 = save(http, jwt, SIMPLE)
    client = sdk(jwt)  # a signed-in user sees every workflow they may run
    assert {wid, wid2} <= {a["assistant_id"] for a in client.assistants.search(limit=100)}
    assert "hi" in client.runs.wait(None, wid, input={"message": "hi"})["answer"]
    t = client.threads.create(); client.runs.wait(t["thread_id"], wid, input={"message": "x"})
    assert status(client.runs.wait, t["thread_id"], wid2, input={"message": "x"}) == 409
    assert status(client.threads.create, thread_id=t["thread_id"]) == 409
    assert client.threads.create(thread_id=t["thread_id"], if_exists="do_nothing")["thread_id"] == t["thread_id"]
    client.threads.delete(t["thread_id"])
    assert status(client.threads.get, t["thread_id"]) == 404


def test_human_node_interrupts_and_resumes(http):
    jwt = user(http); wid = save(http, jwt, APPROVAL)
    client = sdk(token(http, jwt, wid))
    t = client.threads.create()
    out = client.runs.wait(t["thread_id"], wid, input={"message": "order A100"})
    assert out["__interrupt__"][0]["value"] == {"node": "ask", "question": "Approve refund for order A100?"}
    st = client.threads.get_state(t["thread_id"])
    assert st["next"] == ["ask"] and st["tasks"][0]["interrupts"][0]["value"]["node"] == "ask"
    assert client.threads.get(t["thread_id"])["status"] == "interrupted"
    assert status(client.runs.wait, t["thread_id"], wid, command={"resume": {"not": "text"}}) == 400
    parts = list(client.runs.stream(t["thread_id"], wid, command={"resume": "approved"}, stream_mode="updates"))
    assert {"ask": {"decision": "approved"}} in [p.data for p in parts], "only the resumed segment is streamed"
    assert client.threads.get_state(t["thread_id"])["values"]["decision"] == "approved"
    assert client.threads.get(t["thread_id"])["status"] == "idle"
    assert status(client.runs.wait, t["thread_id"], wid, command={"resume": "approved"}) == 409


def test_isolation_and_auth(http):
    a, b = user(http), user(http); wid = save(http, a, SIMPLE)
    tok = token(http, a, wid)
    t = sdk(tok).threads.create()
    assert status(sdk(a).threads.get, t["thread_id"]) == 404  # the owner's JWT does not see the token's threads
    assert status(sdk(b).assistants.get, wid) == 404
    assert status(sdk(b).runs.wait, None, wid, input={"message": "x"}) == 404
    for key in ("wft_nope", "not-a-jwt"):
        r = http.post("/api/lg/assistants/search", json={}, headers={"x-api-key": key})
        assert r.status_code == 401 and r.json()["error"]["code"] in ("TRIGGER_TOKEN_INVALID", "AUTH_TOKEN_INVALID")
    assert http.post("/api/lg/threads", json={}).json()["error"]["code"] == "AUTH_REQUIRED"
    for h in ({"Authorization": f"Bearer {tok}"}, {"X-Workflow-Token": tok}):
        assert http.post("/api/lg/assistants/search", json={}, headers=h).json()[0]["assistant_id"] == wid
    assert http.get("/api/lg/info").json()["flags"]["assistants"] is True
