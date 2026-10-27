"""Agent node tool approval (TASK-0117, REQ-0072, DEC-0063 decision 7): the run waits before a call to a tool that needs
approval, through the Human node's path (the inbox, the channels, the deadlines, workflow test answers); approve runs the
call once, reject tells the model. The restart cases are in test_durable_restart.py."""
import http.server, json, threading, uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.api.deps import approval_service
from app.engine import agents
from app.engine.effects import Effects
from app.engine.ports import Ports
from app.engine.runtime import run_stream
from app.engine.validator import validate
from app.services.chat_session_service import answered_by
from tests.test_agent_node import BUILTIN, call, final, script, wf
from tests.test_approval_channels import api, connect, until  # noqa: F401 (api: fake Slack/Telegram, inline sends)

REFUND = {"name": "send_refund", "description": "Refund an order", "source": "http", "method": "POST", "url": "https://pay.example/refund", "approval": True,
          "parameters": {"type": "object", "properties": {"order": {"type": "string"}, "amount": {"type": "number"}}, "required": ["order", "amount"]}}
ARGS = {"order": "B200", "amount": 20}
H = lambda t: {"Authorization": f"Bearer {t}"}  # noqa: E731


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)  # the Agent node uses the offline mock


@pytest.fixture
def refunds(monkeypatch):
    """A local payment API: the request bodies it received. REFUND tools are pointed at it."""
    got, reply = [], {"body": b"{}"}
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            got.append(json.loads(self.rfile.read(int(self.headers["Content-Length"])))); self.send_response(200)
            self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(reply["body"])
        def log_message(self, *a): pass
    srv = http.server.HTTPServer(("127.0.0.1", 0), Handler); threading.Thread(target=srv.serve_forever, daemon=True).start()
    monkeypatch.setenv("STUDIO_HTTP_TOOL_ALLOW_PRIVATE", "1"); monkeypatch.setitem(REFUND, "url", f"http://127.0.0.1:{srv.server_port}/refund")
    yield got, reply
    srv.shutdown()


def waiting_at(evs):
    w = next(e for e in evs if e["type"] == "run_waiting")
    assert not any(e["type"] == "run_finished" for e in evs)
    return w


def resume(w, value, flow, **kw):
    cp = w["checkpoint"]
    return list(run_stream(flow, {}, resume={"node": cp["node"], "nodes": cp["nodes"], "state": cp["state"], "counts": cp["counts"], "value": value}, **kw))


# ---- engine -----------------------------------------------------------------------------------

def test_approve_runs_the_call_once(monkeypatch, refunds):
    got, reply = refunds; reply["body"] = b'{"refunded": true}'
    seen = script(monkeypatch, [("", [call("send_refund", ARGS)]), ("Refunded.", [])])
    flow = wf(tools=[REFUND], steps_field="steps")
    w = waiting_at(list(run_stream(flow, {"message": "Refund B200"}, effects=Effects("r1"))))
    assert (w["node"], w["label"], w["tool"], w["arguments"]) == ("ag/__tool/1", "Helper › send_refund", "send_refund", ARGS)
    assert "Helper wants to call send_refund" in w["prompt"] and '"amount": 20' in w["prompt"]
    assert got == [] and "agent:ag" not in w["state"]
    st = final(resume(w, "approved", flow, effects=Effects("r1")))
    assert got == [ARGS]
    assert st["answer"] == "Refunded." and st["steps"][0] | {"ms": 0} == {"tool": "send_refund", "args": ARGS, "result": '{"refunded": true}',
                                                                           "status": "ok", "ms": 0, "approval": "approved"}
    assert seen[1][0][-1] == {"role": "tool", "tool_call_id": "c1", "name": "send_refund", "content": '{"refunded": true}'}


@pytest.mark.parametrize("answer, told", [("rejected", "Rejected by a reviewer"), ("Too much, offer 10", "Rejected by a reviewer: Too much, offer 10")])
def test_reject_tells_the_model_and_the_loop_goes_on(monkeypatch, refunds, answer, told):
    seen = script(monkeypatch, [("", [call("send_refund", ARGS)]), ("I could not refund it.", [])])
    flow = wf(tools=[REFUND], steps_field="steps")
    st = final(resume(waiting_at(list(run_stream(flow, {"message": "x"}))), answer, flow))
    assert refunds[0] == [] and st["answer"] == "I could not refund it."
    assert seen[1][0][-1]["content"] == told and (st["steps"][0]["status"], st["steps"][0]["approval"]) == ("rejected", "rejected")


def test_calls_before_the_approval_run_once_and_the_rest_after_the_answer(monkeypatch, refunds):
    looked = []
    monkeypatch.setattr(agents, "call_tool", lambda fn, state, key, locale: looked.append(state["message"]) or "found")
    script(monkeypatch, [("", [call("lookup_order", {"message": "B200"}, "a"), call("send_refund", ARGS, "b"), call("lookup_order", {"message": "C3"}, "c")]),
                         ("Done.", [])])
    flow = wf(tools=[BUILTIN, REFUND], steps_field="steps")
    class Ledger:
        def __init__(self): self.rows = {}
        def get(self, nid, it): return self.rows.get((nid, it), (None,))[0]
        def put(self, nid, it, delta, key): self.rows.setdefault((nid, it), (delta, key))
    effects = Effects("r-wave", ledger=Ledger())  # finished siblings of the approval come back from the ledger
    w = waiting_at(list(run_stream(flow, {"message": "x"}, effects=effects)))
    assert "B200" in looked and set(looked) <= {"B200", "C3"} and w["tool"] == "send_refund"
    st = final(resume(w, "approved", flow, effects=effects))
    assert sorted(looked) == ["B200", "C3"] and refunds[0] == [ARGS]
    assert [(s["tool"], s["status"]) for s in st["steps"]] == [("lookup_order", "ok"), ("send_refund", "ok"), ("lookup_order", "ok")]


def test_the_answer_is_used_once_and_a_later_call_asks_again(monkeypatch, refunds):
    script(monkeypatch, [("", [call("send_refund", ARGS)]), ("", [call("send_refund", {**ARGS, "amount": 5}, "c2")]), ("Done.", [])])
    flow = wf(tools=[REFUND])
    again = waiting_at(resume(waiting_at(list(run_stream(flow, {"message": "x"}))), "approved", flow))
    assert again["arguments"]["amount"] == 5 and final(resume(again, "rejected", flow))["answer"] == "Done."


def test_no_approval_is_asked_for_a_call_that_cannot_run(monkeypatch):
    script(monkeypatch, [("", [call("send_refund", {"order": "B200"})]), ("Sorry.", [])])
    st = final(list(run_stream(wf(tools=[REFUND], steps_field="steps"), {"message": "x"})))
    assert st["steps"][0]["status"] == "error" and "missing argument(s): amount" in st["steps"][0]["result"] and "approval" not in st["steps"][0]


def test_prompt_in_vietnamese(monkeypatch):
    script(monkeypatch, [("", [call("send_refund", ARGS)])])
    w = waiting_at(list(run_stream(wf(tools=[REFUND]), {"message": "x"}, ports=Ports(locale="vi"))))
    assert w["prompt"].startswith("Helper muốn gọi công cụ send_refund")


def test_expansion_copies_the_approval_settings_and_the_validator_checks_the_deadline():
    flow = wf(tools=[REFUND], approval={"approvers": ["a@example.com"]}, deadline={"after": "1h", "on_timeout": "reject"})
    step = next(n for n in agents.expand(flow)["nodes"] if n["id"] == "ag/__tool/1")
    assert step["data"]["approval"] == {"approvers": ["a@example.com"]} and step["data"]["deadline"]["after"] == "1h"
    assert validate(flow) == []
    assert any("deadline must be a duration" in e for e in validate(wf(tools=[REFUND], deadline={"after": "soon"})))
    assert validate(wf(tools=[BUILTIN], deadline={"after": "soon"})) == []  # no tool needs approval: the settings are not used
    assert answered_by(step["data"]) == "reviewer" and answered_by({"answered_by": "visitor"}) == "visitor"
    assert agents.agent_of_step("ag/__tool/1") == "ag" and agents.agent_of_step("ag/__join") == "ag" and agents.agent_of_step("ag") is None


# ---- through the services ---------------------------------------------------------------------

@pytest.fixture(scope="module")
def c():
    with TestClient(app) as client: yield client  # lifespan: the worker that resumes answered runs


def user(c):
    d = c.post("/api/auth/register", json={"email": f"g{uuid.uuid4().hex[:6]}@example.com", "password": "secret12"}).json()["data"]
    return {"token": d["token"], **d["user"]}


def agent_flow(**d):
    """The offline mock calls lookup_order (it matches "order"), which needs approval here."""
    flow = wf(tools=[{**BUILTIN, "approval": True}], steps_field="steps", **d)
    for n in flow["nodes"]: n["position"] = {"x": 0, "y": 0}
    flow["name"] = f"Agent approval {uuid.uuid4().hex[:4]}"
    return flow


def start(c, owner, flow):
    wid = c.post("/api/workflows", json=flow, headers=H(owner["token"])).json()["data"]["id"]
    with c.websocket_connect(f"/ws/run?token={owner['token']}") as w:
        w.send_json({"workflow_id": wid, "input": {"message": "Where is order B200?"}}); evs = []
        while (evs := evs + [w.receive_json()])[-1]["type"] != "run_summary": pass
    assert evs[-1]["status"] == "waiting", evs[-3:]
    return wid, evs[0]["run_id"]


def run_row(c, owner, wid, rid): return next(r for r in c.get(f"/api/workflows/{wid}/runs", headers=H(owner["token"])).json()["data"] if r["id"] == rid)


def test_inbox_lists_the_tool_call_and_an_approver_answers(c):
    owner, approver = user(c), user(c)
    wid, rid = start(c, owner, agent_flow(approval={"approvers": [approver["email"]]}))
    row = next(x for x in c.get("/api/approvals/inbox", headers=H(approver["token"])).json()["data"] if x["run_id"] == rid)
    assert (row["node"], row["label"]) == ("ag/__tool/1", "Helper › lookup_order") and "lookup_order" in row["prompt"] and "Where is order B200?" in row["prompt"]
    assert c.post(f"/api/approvals/inbox/{rid}", json={"response": "approved"}, headers=H(approver["token"])).status_code == 200
    done = until(lambda: (r := run_row(c, owner, wid, rid))["status"] == "ok" and r)
    assert "In transit" in done["final_state"]["answer"] and done["final_state"]["steps"][0]["approval"] == "approved"
    assert next(e for e in done["events"] if e["type"] == "run_waiting")["tool"] == "lookup_order"


def test_slack_message_names_the_tool(c, api):  # noqa: F811
    owner = user(c); connect(c, owner, "slack")
    wid, rid = start(c, owner, agent_flow(approval={"channel": "slack", "target": "C0AGENT"}))
    post = until(lambda: api.requests())[0]
    text = post["blocks"][0]["text"]["text"]
    assert post["channel"] == "C0AGENT" and "Helper › lookup_order" in text and "Helper wants to call lookup_order" in text


def test_deadline_rejects_and_the_model_is_told(c):
    owner = user(c)
    wid, rid = start(c, owner, agent_flow(deadline={"after": "1h", "on_timeout": "reject"}))
    w = approval_service().repo.latest_wait(rid)
    assert w.due_at == pytest.approx(w.created + 3600)
    assert approval_service().fire_deadlines(w.created + 3601) == 1
    done = until(lambda: (r := run_row(c, owner, wid, rid))["status"] == "ok" and r)
    step = done["final_state"]["steps"][0]
    assert (step["status"], step["result"]) == ("rejected", "Rejected by a reviewer") and "Rejected by a reviewer" in done["final_state"]["answer"]


def test_workflow_test_answers_the_agent_by_its_id(c):
    from tests.test_workflow_tests import add, by_name, run_all, save
    owner = user(c); wid = save(c, owner, agent_flow())
    ran = [{"kind": "field", "field": "answer", "op": "contains", "value": "In transit"}]
    add(c, owner, wid, name="Approved", input={"message": "Where is order B200?"}, answers={"ag": ["approved"]}, checks=ran)
    add(c, owner, wid, name="Rejected", input={"message": "Where is order B200?"}, answers={"ag": ["rejected"]},
        checks=[{"kind": "field", "field": "answer", "op": "contains", "value": "Rejected by a reviewer"}])
    add(c, owner, wid, name="No answer", input={"message": "Where is order B200?"})
    r = by_name(run_all(c, owner, wid, mock=True))
    assert r["Approved"]["status"] == "passed" and r["Rejected"]["status"] == "passed", r
    assert (r["No answer"]["status"], r["No answer"]["reason"], r["No answer"]["detail"]) == ("failed", "no_answer", "ag/__tool/1")
    draft = c.post(f"/api/workflows/{wid}/tests/from-run/{r['Approved']['run_id']}", headers=H(owner["token"])).json()
    assert draft.get("data", {}).get("answers") == {"ag": ["approved"]}, draft
