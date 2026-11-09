"""workflow test suites compared with an earlier version, run against a stored version, suite history, a draft
case from a run, stale checks and permissions."""
import json, time, uuid
from app.api.deps import run_service
from app.models import Run
from tests.test_hitl import APPROVAL
from tests.test_workflow_tests import H, add, by_name, c, run_all, save, user  # noqa: F401 (c: fixture)


def renamed_route(wf):
    """APPROVAL with its Condition node `route` renamed to `route2`: a check on `route` goes stale."""
    wf = json.loads(json.dumps(wf).replace('"route"', '"route2"')); return wf


def ws(c, tok, msg):
    with c.websocket_connect(f"/ws/run?token={tok}") as w:
        w.send_json(msg)
        while True:
            e = w.receive_json()
            if e["type"] in ("run_summary", "error"): return e


def test_compare_with_an_earlier_version_and_run_against_a_version(c):
    u = user(c); wid = save(c, u, APPROVAL)
    a = add(c, u, wid, name="A", answers={"ask": ["approved"]}, checks=[{"kind": "node", "node": "route", "ran": True}])["data"]
    add(c, u, wid, name="B", answers={"ask": ["approved"]}, checks=[{"kind": "node", "node": "route2", "ran": True}])
    s1 = run_all(c, u, wid)
    assert s1["version"] == 1 and s1["compare"] is None and {n: r["status"] for n, r in by_name(s1).items()} == {"A": "passed", "B": "failed"}
    assert by_name(s1)["B"]["checks"][0]["reason"] == "node_missing"

    wf = c.get(f"/api/workflows/{wid}", headers=H(u["token"])).json()["data"]
    c.post("/api/workflows", json=renamed_route(wf), headers=H(u["token"]))  # version 2
    c.put(f"/api/workflows/{wid}/tests/{a['id']}", json={**{k: a[k] for k in ("input", "answers", "checks")}, "name": "A edited"}, headers=H(u["token"]))
    add(c, u, wid, name="C", answers={"ask": ["approved"]})
    s2 = run_all(c, u, wid)
    got = by_name(s2)
    assert s2["version"] == 2 and s2["compare"]["version"] == 1 and s2["compare"]["suite_id"] == s1["id"]
    assert s2["compare"]["counts"] == {"regression": 1, "fixed": 1, "still_failing": 0, "still_passing": 0, "new": 1}
    assert (got["A edited"]["change"], got["B"]["change"], got["C"]["change"]) == ("regression", "fixed", "new")  # an edited case is the same case
    assert got["A edited"]["checks"][0]["reason"] == "node_missing"  # the stale check fails with its reason

    # run against version 1: its snapshot runs, and the result names it
    s3 = run_all(c, u, wid, version=1)
    assert s3["version"] == 1 and {r["version"] for r in s3["results"]} == {1} and by_name(s3)["A edited"]["status"] == "passed"
    assert c.post(f"/api/workflows/{wid}/tests/run", json={"version": 99}, headers=H(u["token"])).json()["error"]["code"] == "VERSION_NOT_FOUND"
    assert c.post(f"/api/workflows/{wid}/tests/run", json={"version": "1"}, headers=H(u["token"])).json()["error"]["code"] == "VERSION_NOT_FOUND"
    # the version 2 suite is now compared with the newest finished suite run on an earlier version
    assert c.get(f"/api/workflows/{wid}/tests/runs/{s2['id']}", headers=H(u["token"])).json()["data"]["compare"]["suite_id"] == s3["id"]

    hist = c.get(f"/api/workflows/{wid}/tests/runs", headers=H(u["token"])).json()["data"]["items"]
    assert [h["id"] for h in hist] == [s3["id"], s2["id"], s1["id"]] and [h["version"] for h in hist] == [1, 2, 1]
    assert hist[0]["by"] == u["email"] and (hist[1]["passed"], hist[1]["failed"]) == (2, 1)

    # viewers see the history and the comparison, but cannot run against a version
    other = user(c)
    c.put(f"/api/workflows/{wid}/shares", json={"email": other["email"], "role": "viewer"}, headers=H(u["token"]))
    assert len(c.get(f"/api/workflows/{wid}/tests/runs", headers=H(other["token"])).json()["data"]["items"]) == 3
    assert c.get(f"/api/workflows/{wid}/tests/runs/{s2['id']}", headers=H(other["token"])).json()["data"]["compare"]["version"] == 1
    assert c.post(f"/api/workflows/{wid}/tests/run", json={"version": 1}, headers=H(other["token"])).json()["error"]["code"] == "WORKFLOW_FORBIDDEN"


def test_draft_from_a_run_replays_it(c):
    u = user(c); wid = save(c, u, APPROVAL)
    rid = ws(c, u["token"], {"workflow_id": wid, "input": {"message": "order A100"}})["run_id"]
    assert ws(c, u["token"], {"resume_run_id": rid, "response": "approved"})["status"] == "ok"
    d = c.post(f"/api/workflows/{wid}/tests/from-run/{rid}", headers=H(u["token"])).json()["data"]
    assert d["input"] == {"message": "order A100"} and d["answers"] == {"ask": ["approved"]} and d["name"] == f"Run {rid}"
    assert d["checks"][0] == {"kind": "status", "value": "ok"}
    assert {"kind": "node", "node": "ask", "ran": True} in d["checks"] and {"kind": "node", "node": "route", "ran": True} in d["checks"]
    assert {"kind": "field", "field": "decision", "op": "equals", "value": "approved"} in d["checks"]
    assert not any(ch.get("node") in ("s", "e") for ch in d["checks"])  # Start and End always run
    assert not any(ch.get("field") == "message" for ch in d["checks"])  # passed through unchanged
    assert c.get(f"/api/workflows/{wid}/tests", headers=H(u["token"])).json()["data"]["items"] == []  # a draft, not saved
    assert add(c, u, wid, **d)["data"]["id"]
    assert run_all(c, u, wid)["results"][0]["status"] == "passed"  # the saved draft passes on the same version


def test_draft_from_a_run_without_answers_and_long_values(c):
    u = user(c); wid = save(c, u, APPROVAL)
    long = "x" * 300
    rid = ws(c, u["token"], {"workflow_id": wid, "input": {"message": long}})["run_id"]
    ws(c, u["token"], {"resume_run_id": rid, "response": long})  # a text answer, longer than the prefill limit
    d = c.post(f"/api/workflows/{wid}/tests/from-run/{rid}", headers=H(u["token"])).json()["data"]
    assert d["answers"] == {"ask": [long]}
    assert {"kind": "field", "field": "decision", "op": "contains", "value": "x" * 200} in d["checks"]

    still = ws(c, u["token"], {"workflow_id": wid, "input": {"message": "m"}})["run_id"]  # waiting: no answer yet
    d = c.post(f"/api/workflows/{wid}/tests/from-run/{still}", headers=H(u["token"])).json()["data"]
    assert d["answers"] == {} and d["checks"][0] == {"kind": "status", "value": "waiting"}


def test_draft_from_a_run_permissions(c):
    u = user(c); wid = save(c, u, APPROVAL); other_wid = save(c, u, APPROVAL)
    rid = ws(c, u["token"], {"workflow_id": wid, "input": {"message": "m"}})["run_id"]
    code = lambda tok, w=wid, r=rid: (c.post(f"/api/workflows/{w}/tests/from-run/{r}", headers=H(tok)).json().get("error") or {}).get("code")  # noqa: E731
    assert code(u["token"], other_wid) == "RUN_NOT_FOUND" and code(u["token"], wid, "nope") == "RUN_NOT_FOUND"
    viewer, editor, stranger = user(c), user(c), user(c)
    c.put(f"/api/workflows/{wid}/shares", json={"email": viewer["email"], "role": "viewer"}, headers=H(u["token"]))
    c.put(f"/api/workflows/{wid}/shares", json={"email": editor["email"], "role": "editor"}, headers=H(u["token"]))
    assert code(viewer["token"]) == "WORKFLOW_FORBIDDEN" and code(stranger["token"]) == "WORKFLOW_NOT_FOUND"
    assert code(editor["token"]) == "RUN_NOT_FOUND"  # an editor sees only their own runs, as in the run history
    mine = ws(c, editor["token"], {"workflow_id": wid, "input": {"message": "e"}})["run_id"]
    assert code(editor["token"], wid, mine) is None


def test_a_recovered_test_run_keeps_its_version(c):
    """A test run on version 1 whose worker died before any node finished restarts on version 1, not on the latest."""
    u = user(c); wid = save(c, u, APPROVAL)
    wf = c.get(f"/api/workflows/{wid}", headers=H(u["token"])).json()["data"]
    c.post("/api/workflows", json=renamed_route(wf), headers=H(u["token"]))  # version 2
    svc = run_service(); rid = uuid.uuid4().hex[:10]
    svc.runs.add(Run(id=rid, workflow_id=wid, input="{}", events="[]", status="running", started=time.time(), owner=u["id"], source="test", workflow_version=1))
    plan = svc.plan_recover(svc.runs.get(rid))
    assert plan.version == 1 and any(n["id"] == "route" for n in plan.workflow["nodes"])
    assert svc.plan(u["id"], {"workflow_id": wid, "input": {}}).version == 2
