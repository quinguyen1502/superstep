"""TASK-0186 (REQ-0081, DEC-0075): the `approval.auto` policy, its validation, who may turn auto on, the kill switches
and the migration."""
import copy, os, uuid
from types import SimpleNamespace as NS
from fastapi.testclient import TestClient
from app.engine import approval_policy as AP
from app.engine.validator import validate
from app.main import app

c = TestClient(app)
H = lambda t: {"Authorization": f"Bearer {t}"}
def code(r): return r.json()["error"]["code"]
def data(r): assert r.status_code == 200, r.text; return r.json()["data"]


def register():
    email = f"aa{uuid.uuid4().hex[:6]}@example.com"
    d = c.post("/api/auth/register", json={"email": email, "password": "secret12"}).json()["data"]
    return NS(token=d["token"], id=d["user"]["id"], email=email)


def admin(): return NS(token=c.post("/api/auth/login", json={"email": "admin@example.com", "password": "admin123"}).json()["data"]["token"])


def auto(mode="auto", **kw):
    return {"mode": mode, "rules": [{"field": "args.amount", "op": "gt", "value": 100, "effect": "human"}],
            "judge": {"credential_id": "cred1", "model": "gpt-x", "instructions": "Small refunds are fine."}, **kw}


def wf(policy=None, name=None):
    human = {"label": "Approve", "prompt": "Refund?", "output_field": "message", **({"approval": {"auto": policy}} if policy else {})}
    return {"name": name or f"aa-{uuid.uuid4().hex[:6]}", "state": [{"name": "message", "type": "string"}],
            "nodes": [{"id": "s", "type": "start", "position": {"x": 0, "y": 0}, "data": {"label": "s"}},
                      {"id": "h", "type": "human", "position": {"x": 100, "y": 0}, "data": human},
                      {"id": "e", "type": "end", "position": {"x": 200, "y": 0}, "data": {"label": "e"}}],
            "edges": [{"id": "1", "source": "s", "target": "h"}, {"id": "2", "source": "h", "target": "e"}]}


def codes(w): return {e.code for e in validate(w)}


# ---- the policy ----
def test_parse_defaults_and_off():
    assert AP.parse({}) is None and AP.parse({"approval": {"auto": {"mode": "off"}}}) is None
    p = AP.parse({"approval": {"auto": auto("suggest")}})
    assert p["mode"] == "suggest" and p["min_confidence"] == 0.8 and p["max_per_day"] == 50 and p["notify"] is True
    assert AP.parse({"approval": {"auto": {"mode": "auto"}}}) is None  # invalid (no judge): never reviews, people are asked
    assert AP.policy_hash(p) == AP.policy_hash(copy.deepcopy(p)) and AP.policy_hash(None) is None


def test_validation_issues():
    assert not codes(wf(auto()))
    assert "AUTO_APPROVAL_MODE" in codes(wf({"mode": "always"}))
    assert "AUTO_APPROVAL_JUDGE_REQUIRED" in codes(wf({"mode": "suggest"}))
    assert "AUTO_APPROVAL_RULE_INVALID" in codes(wf(auto(rules=[{"field": "args.x", "op": "approx", "value": 1, "effect": "human"}])))
    assert "AUTO_APPROVAL_RULE_INVALID" in codes(wf(auto(rules=[{"field": "secret.x", "op": "equals", "value": 1, "effect": "human"}])))
    assert "AUTO_APPROVAL_RULE_INVALID" in codes(wf(auto(rules=[{"field": "args.x", "op": "equals", "value": 1, "effect": "approve"}])))  # rules never approve
    assert "AUTO_APPROVAL_RULE_INVALID" in codes(wf(auto(rules=[{"field": "args.x", "op": "matches", "value": "(", "effect": "human"}])))
    assert "AUTO_APPROVAL_CONFIDENCE" in codes(wf(auto(min_confidence=1.5)))
    assert "AUTO_APPROVAL_CAP" in codes(wf(auto(max_per_day=0)))
    assert not codes(wf({"mode": "off", "rules": "junk"}))  # off is never checked


def test_rule_operators():
    req = {"tool": "refund", "args": {"amount": 120, "note": "Duplicate CHARGE", "tags": ["vip"]}, "prompt": "", "state": {}}
    def m(op, field, value=None): return AP.matches({"field": field, "op": op, "value": value, "effect": "human"}, req)
    assert m("gt", "args.amount", 100) and not m("lt", "args.amount", 100) and not m("gt", "args.note", 1)
    assert m("equals", "tool", "Refund") and m("not_equals", "tool", "delete")
    assert m("contains", "args.note", "charge") and m("not_contains", "args.note", "fraud") and m("contains", "args.tags", "vip")
    assert m("matches", "args.note", r"^Dup") and m("empty", "args.missing") and m("empty", "prompt") and not m("empty", "tool")
    rules = [{"field": "args.amount", "op": "gt", "value": 100, "effect": "human"}, {"field": "args.note", "op": "contains", "value": "charge", "effect": "reject"}]
    assert AP.check(rules, req) == ("reject", [1, 2])
    assert AP.check(rules[:1], req) == ("human", [1]) and AP.check(rules[:1], {"args": {"amount": 5}}) == (None, [])


# ---- who may turn auto on (owner decision 3) ----
def shared(u):
    a = admin(); w = wf()
    wid = data(c.post("/api/workflows", json=w, headers=H(a.token)))["id"]
    data(c.put(f"/api/workflows/{wid}/shares", json={"email": u.email, "role": "editor"}, headers=H(a.token)))
    return a, {**w, "id": wid}


def test_editor_may_suggest_but_not_auto():
    u = register(); a, w = shared(u)
    sug = wf(auto("suggest")); sug["id"] = w["id"]; sug["name"] = w["name"]
    assert data(c.post("/api/workflows", json=sug, headers=H(u.token)))["id"] == w["id"]
    on = copy.deepcopy(sug); on["nodes"][1]["data"]["approval"]["auto"]["mode"] = "auto"
    r = c.post("/api/workflows", json=on, headers=H(u.token))
    assert r.status_code == 403 and code(r) == "AUTO_APPROVAL_FORBIDDEN"
    assert data(c.get(f"/api/workflows/{w['id']}", headers=H(u.token)))["nodes"][1]["data"]["approval"]["auto"]["mode"] == "suggest"  # nothing stored
    assert data(c.post("/api/workflows", json=on, headers=H(a.token)))["id"] == w["id"]  # an admin may
    moved = copy.deepcopy(on); moved["nodes"][1]["position"] = {"x": 300, "y": 40}
    assert data(c.post("/api/workflows", json=moved, headers=H(u.token)))["id"] == w["id"]  # an unchanged auto policy is fine
    changed = copy.deepcopy(moved); changed["nodes"][1]["data"]["approval"]["auto"]["min_confidence"] = 0.5
    assert code(c.post("/api/workflows", json=changed, headers=H(u.token))) == "AUTO_APPROVAL_FORBIDDEN"
    off = copy.deepcopy(moved); off["nodes"][1]["data"]["approval"]["auto"]["mode"] = "off"
    assert data(c.post("/api/workflows", json=off, headers=H(u.token)))["id"] == w["id"]  # turning it off is always allowed


def test_owner_may_turn_auto_on():
    u = register()
    assert data(c.post("/api/workflows", json=wf(auto()), headers=H(u.token)))["id"]


# ---- kill switches ----
def test_workflow_kill_switch_owner_or_admin():
    u = register(); a, w = shared(u)
    assert code(c.put(f"/api/approvals/auto/workflows/{w['id']}", json={"paused": True}, headers=H(u.token))) == "AUTO_APPROVAL_FORBIDDEN"
    assert data(c.put(f"/api/approvals/auto/workflows/{w['id']}", json={"paused": True}, headers=H(a.token)))["paused"] is True
    assert data(c.get(f"/api/approvals/auto/workflows/{w['id']}", headers=H(u.token)))["paused"] is True
    o = register(); wid = data(c.post("/api/workflows", json=wf(), headers=H(o.token)))["id"]
    assert data(c.put(f"/api/approvals/auto/workflows/{wid}", json={"paused": True}, headers=H(o.token)))["paused"] is True
    assert code(c.get(f"/api/approvals/auto/workflows/{wid}", headers=H(u.token))) == "WORKFLOW_NOT_FOUND"


def test_org_kill_switch_admin_only(monkeypatch):
    u = register(); a = admin()
    assert code(c.put("/api/approvals/auto", json={"paused": True}, headers=H(u.token))) == "PERMISSION_DENIED"
    try:
        assert data(c.put("/api/approvals/auto", json={"paused": True}, headers=H(a.token)))["org_paused"] is True
        assert data(c.get("/api/approvals/auto", headers=H(u.token))) == {"enabled": True, "org_paused": True, "can_manage": False}
    finally: data(c.put("/api/approvals/auto", json={"paused": False}, headers=H(a.token)))
    monkeypatch.setenv("STUDIO_AUTO_APPROVAL", "off")
    assert code(c.put("/api/approvals/auto", json={"paused": True}, headers=H(a.token))) == "AUTO_APPROVAL_DISABLED"
    assert data(c.get("/api/approvals/auto", headers=H(a.token)))["enabled"] is False


def test_service_paused_combines_switches(monkeypatch):
    from app.services.auto_approval_service import AutoApprovalService
    store = {}
    svc = AutoApprovalService(NS(get=lambda k, d=None: store.get(k, d), set=lambda k, v, u, t: store.__setitem__(k, v)))
    assert not svc.paused("w1")
    store["auto_approval_paused:w1"] = True; assert svc.paused("w1") and not svc.paused("w2")
    store.clear(); store["auto_approval_paused"] = True; assert svc.paused("w2")
    store.clear(); monkeypatch.setenv("STUDIO_AUTO_APPROVAL", "off"); assert svc.paused("w2")


# ---- the Approvals page list (TASK-0188) ----
def test_reviewed_workflows_lists_own_with_ai_review():
    u = register(); other = register()
    on = data(c.post("/api/workflows", json=wf(auto("suggest")), headers=H(u.token)))["id"]
    off = data(c.post("/api/workflows", json=wf(), headers=H(u.token)))["id"]
    theirs = data(c.post("/api/workflows", json=wf(auto("suggest")), headers=H(other.token)))["id"]
    rows = data(c.get("/api/approvals/auto/workflows", headers=H(u.token)))
    ids = [r["workflow_id"] for r in rows]
    assert on in ids and off not in ids and theirs not in ids
    row = next(r for r in rows if r["workflow_id"] == on)
    assert row["modes"] == ["suggest"] and row["paused"] is False and row["stats"]["agreement"] is None
    assert theirs in [r["workflow_id"] for r in data(c.get("/api/approvals/auto/workflows", headers=H(admin().token)))]


# ---- exports (TASK-0188): a note, never the judge's credential or instructions ----
def test_exports_note_ai_review_without_secrets():
    from app.engine import python_export, typescript_export, project_export
    w = wf(auto())
    py, ts = python_export.to_python(w, "AA").code, typescript_export.to_typescript(w, "AA").code
    for code in (py, ts):
        assert "AI review" in code and "cred1" not in code and "Small refunds" not in code
    assert "AI review" not in python_export.to_python(wf(), "AA").code
    assert "AI review" in project_export._readme("AA", "aa", "agent.py", True)


def test_sanitize_keeps_the_policy_without_the_credential():
    from app.engine.templates import sanitize
    a = sanitize(wf(auto()))["nodes"][1]["data"]["approval"]["auto"]
    assert a["mode"] == "auto" and a["rules"] and a["judge"]["credential_id"] == "" and a["judge"]["model"] == "gpt-x"
