"""TASK-0067: workflow test cases and suite runs. Checks, scripted Human answers, no side effects (e-mail, channel,
notification), the mock model option, one suite at a time, cancel, permissions, limits and the run history filter."""
import copy, time, uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.api.deps import approval_service, workflow_test_service
from app.engine import checks as C
from app.models import WorkflowTestSuite
from tests.test_hitl import APPROVAL
from tests.test_email_node import cred, flow, server  # noqa: F401 (fixture)

H = lambda t: {"Authorization": f"Bearer {t}"}  # noqa: E731


@pytest.fixture(scope="module")
def c():
    with TestClient(app) as client: yield client  # lifespan: the worker that runs the test runs


def user(c):
    d = c.post("/api/auth/register", json={"email": f"t{uuid.uuid4().hex[:6]}@example.com", "password": "secret12"}).json()["data"]
    return {"token": d["token"], **d["user"]}


def save(c, u, wf):
    wf = copy.deepcopy(wf); wf["name"] = f"{wf['name']} {uuid.uuid4().hex[:4]}"
    return c.post("/api/workflows", json=wf, headers=H(u["token"])).json()["data"]["id"]


def add(c, u, wid, **case):
    body = {"name": "case", "input": {"message": "order A100"}, "checks": [{"kind": "status", "value": "ok"}], **case}
    return c.post(f"/api/workflows/{wid}/tests", json=body, headers=H(u["token"])).json()


def run_all(c, u, wid, **body):
    r = c.post(f"/api/workflows/{wid}/tests/run", json=body, headers=H(u["token"])).json()
    assert "data" in r, r
    sid = r["data"]["id"]; t0 = time.time()
    while time.time() - t0 < 20:
        s = c.get(f"/api/workflows/{wid}/tests/runs/{sid}", headers=H(u["token"])).json()["data"]
        if s["status"] != "running": return s
        time.sleep(0.05)
    raise AssertionError(f"suite still running: {s}")


def by_name(suite): return {r["name"]: r for r in suite["results"]}


# ---------- checks (engine, pure) ----------
def test_checks_evaluate_every_kind():
    wf = {"state": [{"name": "decision"}, {"name": "note"}, {"name": "data"}], "nodes": [{"id": "a"}, {"id": "b"}]}
    run = {"status": "ok", "final_state": {"decision": "approved", "note": "", "data": {"n": 3}}, "duration_ms": 1500, "cost_usd": None,
           "events": [{"type": "node_finished", "node": "a"}]}
    cs = [{"kind": "status", "value": "ok"}, {"kind": "field", "field": "decision", "op": "equals", "value": "approved"},
          {"kind": "field", "field": "decision", "op": "contains", "value": "prov"}, {"kind": "field", "field": "decision", "op": "not_contains", "value": "rej"},
          {"kind": "field", "field": "decision", "op": "matches", "value": "^app"}, {"kind": "field", "field": "note", "op": "empty"},
          {"kind": "field", "field": "data", "op": "equals", "value": '{"n": 3}'}, {"kind": "node", "node": "a", "ran": True},
          {"kind": "node", "node": "b", "ran": False}, {"kind": "duration", "max": 2}, {"kind": "cost", "max": 0.01}]
    got = C.evaluate(cs, run, wf)
    assert [g["passed"] for g in got] == [True] * 10 + [None] and got[-1]["reason"] == "no_price"
    assert C.passed(cs, got, "ok")
    bad = C.evaluate([{"kind": "field", "field": "decision", "op": "equals", "value": "rejected"}, {"kind": "field", "field": "gone", "op": "empty"},
                      {"kind": "node", "node": "zzz", "ran": True}, {"kind": "duration", "max": 1}], run, wf)
    assert [(g["passed"], g["expected"], g["actual"], g["reason"]) for g in bad] == [
        (False, "rejected", "approved", None), (False, "empty", None, "field_missing"), (False, "ran", None, "node_missing"), (False, "1", "1.5", None)]
    # a run that did not finish: node checks still read the events, the rest is not evaluated, and the case fails
    err = C.evaluate([{"kind": "node", "node": "a", "ran": True}, {"kind": "field", "field": "decision", "op": "not_empty"}], {**run, "status": "error"}, wf)
    assert [g["passed"] for g in err] == [True, None] and not C.passed([{"kind": "node", "node": "a", "ran": True}], err[:1], "error")
    assert C.passed([{"kind": "status", "value": "error"}], C.evaluate([{"kind": "status", "value": "error"}], {**run, "status": "error"}, wf), "error")


def test_tool_called_check():
    """TASK-0119: whether an Agent node's model called a tool and the call ran, read from the step summaries of the run."""
    def step(tool, status="ok", result="done", node="ag/__tool"):
        return {"type": "node_finished", "node": node, "agent": {"kind": "tool", "tool": tool, "status": status, "result": result}}
    run = {"status": "ok", "final_state": {}, "events": [
        {"type": "node_finished", "node": "ag/__model", "agent": {"kind": "model", "tool_calls": [{"name": "refund"}]}},
        step("lookup"), step("refund", "rejected", "Rejected by a reviewer"), step("broken", "error", "The tool failed: boom"),
        step("typo", "error", "Invalid arguments for typo: missing argument(s): a"), step("other", node="b/__tool")]}
    wf = {"nodes": [{"id": "ag"}, {"id": "b"}]}
    cases = [("lookup", True, True), ("refund", False, True), ("broken", True, True), ("typo", False, True), ("other", False, True),
             ("never", False, True), ("lookup", False, False), ("refund", True, False)]
    got = C.evaluate([{"kind": "tool", "node": "ag", "tool": t, "called": want} for t, want, _ in cases], run, wf)
    assert [g["passed"] for g in got] == [ok for _, _, ok in cases]
    assert (got[1]["expected"], got[1]["actual"]) == ("not_called", "not_called") and (got[6]["expected"], got[6]["actual"]) == ("not_called", "called")
    assert C.evaluate([{"kind": "tool", "node": "zz", "tool": "x", "called": True}], run, wf)[0]["reason"] == "node_missing"
    # like node checks, it reads the events of a run that did not finish
    assert C.evaluate([{"kind": "tool", "node": "ag", "tool": "lookup", "called": True}], {**run, "status": "error"}, wf)[0]["passed"] is True
    assert C.errors([{"kind": "tool", "node": "", "tool": "x", "called": True}, {"kind": "tool", "node": "ag", "called": "yes"}]) == [
        "check 1: choose an Agent node", "check 2: choose a tool", "check 2: called must be true or false"]


def test_check_validation():
    assert C.errors([]) == ["add at least one check"]
    assert C.errors([{"kind": "x"}]) == ["check 1: unknown kind"]
    assert C.errors([{"kind": "field", "field": "a", "op": "matches", "value": "("}])[0].startswith("check 1: invalid pattern")
    assert C.errors([{"kind": "node", "node": "a", "ran": "yes"}, {"kind": "duration", "max": 0}]) == [
        "check 1: ran must be true or false", "check 2: the limit must be a positive number"]
    assert C.errors([{"kind": "field", "field": "a", "op": "empty"}, {"kind": "status", "value": "waiting"}]) == []


# ---------- test cases ----------
def test_cases_save_validate_and_obey_limits_and_permissions(c, monkeypatch):
    owner, other = user(c), user(c); wid = save(c, owner, APPROVAL)
    t = add(c, owner, wid, name="Approved", answers={"ask": ["approved"]})["data"]
    assert t["answers"] == {"ask": ["approved"]} and t["last"] is None
    assert add(c, owner, wid, checks=[{"kind": "field", "field": "x", "op": "matches", "value": "("}])["error"]["code"] == "TEST_CASE_INVALID"
    assert add(c, owner, wid, name="")["error"]["code"] == "TEST_CASE_INVALID"
    assert add(c, owner, wid, answers={"ask": [1]})["error"]["code"] == "TEST_CASE_INVALID"
    u = c.put(f"/api/workflows/{wid}/tests/{t['id']}", json={**t, "name": "Renamed"}, headers=H(owner["token"])).json()["data"]
    assert u["name"] == "Renamed"
    monkeypatch.setenv("STUDIO_TEST_CASES_MAX", "1")
    assert add(c, owner, wid)["error"]["code"] == "TEST_CASES_LIMIT"
    monkeypatch.delenv("STUDIO_TEST_CASES_MAX")
    # others: nothing; a viewer reads but cannot change or run
    assert c.get(f"/api/workflows/{wid}/tests", headers=H(other["token"])).json()["error"]["code"] == "WORKFLOW_NOT_FOUND"
    c.put(f"/api/workflows/{wid}/shares", json={"email": other["email"], "role": "viewer"}, headers=H(owner["token"]))
    seen = c.get(f"/api/workflows/{wid}/tests", headers=H(other["token"])).json()["data"]
    assert [x["name"] for x in seen["items"]] == ["Renamed"] and seen["can_edit"] is False
    assert add(c, other, wid)["error"]["code"] == "WORKFLOW_FORBIDDEN"
    assert c.post(f"/api/workflows/{wid}/tests/run", json={}, headers=H(other["token"])).json()["error"]["code"] == "WORKFLOW_FORBIDDEN"
    assert c.delete(f"/api/workflows/{wid}/tests/{t['id']}", headers=H(owner["token"])).json()["data"] == {"ok": True}
    assert c.get(f"/api/workflows/{wid}/tests", headers=H(owner["token"])).json()["data"]["items"] == []


# ---------- suite runs ----------
def test_suite_answers_human_nodes_and_reports_each_check(c):
    owner = user(c); wid = save(c, owner, APPROVAL)
    ok = [{"kind": "field", "field": "decision", "op": "equals", "value": "approved"}, {"kind": "node", "node": "e", "ran": True}]
    add(c, owner, wid, name="Approved", answers={"ask": ["approved"]}, checks=ok)
    add(c, owner, wid, name="Wrong", answers={"ask": ["rejected"]}, checks=ok[:1])
    add(c, owner, wid, name="Nobody answers")
    s = run_all(c, owner, wid)
    assert s["status"] == "done" and (s["total"], s["passed"], s["failed"]) == (3, 1, 2) and s["version"] == 1
    r = by_name(s)
    assert r["Approved"]["status"] == "passed" and [x["passed"] for x in r["Approved"]["checks"]] == [True, True]
    assert r["Approved"]["checks"][0] == {**ok[0], "passed": True, "expected": "approved", "actual": "approved", "reason": None}
    assert r["Wrong"]["status"] == "failed" and r["Wrong"]["checks"][0]["actual"] == "rejected"
    assert (r["Nobody answers"]["status"], r["Nobody answers"]["reason"], r["Nobody answers"]["detail"]) == ("failed", "no_answer", "ask")
    runs = c.get(f"/api/workflows/{wid}/runs?tests=true", headers=H(owner["token"])).json()["data"]
    approved = next(x for x in runs if x["id"] == r["Approved"]["run_id"])
    assert approved["source"] == "test" and approved["status"] == "ok" and approved["version"] == 1
    assert next(e for e in approved["events"] if e["type"] == "run_resumed")["by"] == {"channel": "test"}
    assert next(x for x in runs if x["id"] == r["Nobody answers"]["run_id"])["status"] == "cancelled"
    # test runs stay out of the normal history and the waiting list; nothing reached the inbox or the bell
    assert c.get(f"/api/workflows/{wid}/runs", headers=H(owner["token"])).json()["data"] == []
    assert c.get("/api/runs/pending", headers=H(owner["token"])).json()["data"] == []
    assert all(approval_service().repo.latest_wait(x["id"]) is None for x in runs)
    assert [n for n in c.get("/api/notifications", headers=H(owner["token"])).json()["data"]["items"] if n["run_id"] in {x["id"] for x in runs}] == []
    # the case list shows each case's last result; recording a settled run again changes nothing
    items = {x["name"]: x for x in c.get(f"/api/workflows/{wid}/tests", headers=H(owner["token"])).json()["data"]["items"]}
    assert items["Approved"]["last"]["status"] == "passed" and items["Wrong"]["last"]["status"] == "failed"
    workflow_test_service().on_settled(r["Approved"]["run_id"])
    assert c.get(f"/api/workflows/{wid}/tests/runs/{s['id']}", headers=H(owner["token"])).json()["data"]["passed"] == 1
    # run one case
    one = run_all(c, owner, wid, test_ids=[r["Approved"]["test_id"]])
    assert (one["total"], one["passed"]) == (1, 1)


def test_test_run_sends_no_email(c, server):  # noqa: F811
    owner = user(c); cid = cred(owner["token"], server["port"])
    wid = save(c, owner, flow(credential_id=cid))
    add(c, owner, wid, name="Mail", input={"email": "ann@example.com", "name": "Ann", "emails": [], "sent": {}},
        checks=[{"kind": "field", "field": "sent", "op": "contains", "value": '"dry_run": true'}])
    s = run_all(c, owner, wid)
    assert s["passed"] == 1, s
    assert server["got"] == []


def test_mock_option_runs_llm_nodes_offline(c, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test"); monkeypatch.setenv("OPENAI_BASE_URL", "http://127.0.0.1:9/v1")  # unreachable
    owner = user(c)
    wf = {"name": "LLM", "state": [{"name": "message"}, {"name": "reply"}],
          "nodes": [{"id": "s", "type": "start", "data": {}}, {"id": "llm", "type": "llm", "data": {"prompt": "Answer: {{state.message}}", "output_field": "reply"}},
                    {"id": "e", "type": "end", "data": {}}],
          "edges": [{"id": "1", "source": "s", "target": "llm"}, {"id": "2", "source": "llm", "target": "e"}]}
    wid = save(c, owner, wf)
    add(c, owner, wid, name="Mock", checks=[{"kind": "field", "field": "reply", "op": "contains", "value": "[mock:"}])
    assert run_all(c, owner, wid, mock=True)["passed"] == 1
    real = run_all(c, owner, wid)  # the real model is unreachable here
    assert real["failed"] == 1 and real["results"][0]["reason"] == "run_status" and real["results"][0]["detail"] == "error"


def test_one_suite_at_a_time_and_cancel(c):
    owner = user(c); wid = save(c, owner, APPROVAL); add(c, owner, wid, answers={"ask": ["approved"]})
    stuck = WorkflowTestSuite(id=uuid.uuid4().hex[:12], workflow_id=wid, version=1, owner=owner["id"], status="running", total=0, passed=0, failed=0,
                              started=time.time())
    assert workflow_test_service().repo.start_suite(stuck, [])
    assert c.post(f"/api/workflows/{wid}/tests/run", json={}, headers=H(owner["token"])).json()["error"]["code"] == "TEST_SUITE_RUNNING"
    done = c.post(f"/api/workflows/{wid}/tests/runs/{stuck.id}/cancel", headers=H(owner["token"])).json()["data"]
    assert done["status"] == "cancelled"
    assert run_all(c, owner, wid)["passed"] == 1


def test_deleting_a_workflow_deletes_its_tests(c):
    owner = user(c); wid = save(c, owner, APPROVAL); add(c, owner, wid)
    run_all(c, owner, wid)
    svc = workflow_test_service()
    assert svc.repo.count_for_workflow(wid) == 1 and svc.repo.suites(wid)
    c.delete(f"/api/workflows/{wid}", headers=H(owner["token"]))
    assert svc.repo.count_for_workflow(wid) == 0 and svc.repo.suites(wid) == []
