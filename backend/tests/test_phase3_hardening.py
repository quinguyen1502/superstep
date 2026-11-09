"""teams, ownership transfer, audit log, account deletion, org-resource policy, subgraph dependents and names."""
import json, time, uuid
import pytest
from app.api.deps import channel_service, get_db, run_service
from app.core.errors import AppError
from app.engine.subgraphs import validate_with
from app.models import ApprovalChannel, McpServer
from app.repositories import ApprovalRepository, McpServerRepository, UserRepository, WorkflowRepository
from test_rbac import H, admin_token, c, code, first_wf, register

N = lambda i, t, **d: {"id": i, "type": t, "position": {"x": 0, "y": 0}, "data": {"label": i, **d}}
E = lambda s, t: {"id": f"{s}-{t}", "source": s, "target": t}


def wf(name, *mid):
    ids = ["s"] + [n["id"] for n in mid] + ["e"]
    return {"name": name, "state": [{"name": "message", "type": "string"}, {"name": "out", "type": "string"}],
            "nodes": [N("s", "start"), *mid, N("e", "end")], "edges": [E(a, b) for a, b in zip(ids, ids[1:])]}


def save(u, w): return c.post("/api/workflows", json=w, headers=H(u.token)).json()["data"]["id"]


def audit(adm, **q): return c.get("/api/admin/audit", params=q, headers=H(adm)).json()["data"]


# ---------- teams ----------
def test_teams_and_team_shares():
    adm, a, b = admin_token(), register("ta"), register("tb")
    assert code(c.post("/api/teams", json={"name": "x"}, headers=H(a.token))) == "PERMISSION_DENIED"
    name = f"Support {uuid.uuid4().hex[:4]}"
    t = c.post("/api/teams", json={"name": name}, headers=H(adm)).json()["data"]
    assert code(c.post("/api/teams", json={"name": name.upper()}, headers=H(adm))) == "TEAM_NAME_TAKEN"
    assert code(c.post("/api/teams", json={"name": "  "}, headers=H(adm))) == "TEAM_NAME_REQUIRED"
    assert c.post(f"/api/teams/{t['id']}/members", json={"email": b.email}, headers=H(adm)).json()["data"]["members"][0]["email"] == b.email
    listed = c.get("/api/teams", headers=H(b.token)).json()["data"]
    mine = next(x for x in listed["teams"] if x["id"] == t["id"]); assert mine["mine"] and "member_list" not in mine and not listed["can_manage"]
    wid = first_wf(a)
    assert c.get(f"/api/workflows/{wid}", headers=H(b.token)).status_code == 404
    r = c.put(f"/api/workflows/{wid}/team-shares", json={"team_id": t["id"], "role": "viewer"}, headers=H(a.token)).json()["data"]
    assert r["teams"][0]["name"] == name
    c.put(f"/api/workflows/{wid}/team-shares", json={"team_id": t["id"], "role": "viewer"}, headers=H(a.token))  # unchanged: not audited again
    c.post(f"/api/teams/{t['id']}/members", json={"email": b.email}, headers=H(adm))  # already a member: not audited again
    assert c.get(f"/api/workflows/{wid}", headers=H(b.token)).json()["data"]["access"] == "viewer"
    c.put(f"/api/workflows/{wid}/shares", json={"email": b.email, "role": "editor"}, headers=H(a.token))  # best of direct + team
    assert c.get(f"/api/workflows/{wid}", headers=H(b.token)).json()["data"]["access"] == "editor"
    c.delete(f"/api/workflows/{wid}/shares/{b.id}", headers=H(a.token))
    row = next(w for w in c.get("/api/workflows", headers=H(b.token)).json()["data"] if w["id"] == wid); assert row["access"] == "viewer"
    assert code(c.put(f"/api/workflows/{wid}/team-shares", json={"team_id": "nope", "role": "viewer"}, headers=H(a.token))) == "TEAM_NOT_FOUND"
    c.delete(f"/api/teams/{t['id']}/members/{b.id}", headers=H(adm))
    assert code(c.delete(f"/api/teams/{t['id']}/members/{b.id}", headers=H(adm))) == "TEAM_MEMBER_NOT_FOUND"
    assert c.get(f"/api/workflows/{wid}", headers=H(b.token)).status_code == 404
    assert c.delete(f"/api/teams/{t['id']}", headers=H(adm)).status_code == 200
    acts = [e["action"] for e in audit(adm, q=name)["items"]]
    assert {"team.create", "team.member_add", "team.member_remove", "team.delete"} <= set(acts) and acts.count("team.member_add") == 1
    assert sum(e["action"] == "share.team" and e["details"]["team"] == name for e in audit(adm, category="share", limit=200)["items"]) == 1
    assert any(e["action"] == "share.team" and e["details"]["team"] == name for e in audit(adm, category="share", limit=200)["items"])


# ---------- ownership transfer ----------
def test_transfer_rebinds_or_flags_references():
    adm, a, b = admin_token(), register("oa"), register("ob")
    cred = c.post("/api/credentials", json={"name": "A key", "provider": "openai", "api_key": "sk-test-aaaa1111"}, headers=H(a.token)).json()["data"]["id"]
    kb = c.post("/api/knowledge-bases", json={"name": "A docs"}, headers=H(a.token)).json()["data"]["id"]
    child = save(a, wf(f"Child {uuid.uuid4().hex[:4]}", N("x", "llm", prompt="hi", output_field="out")))
    wid = save(a, wf("Handover", N("llm", "llm", prompt="hi", output_field="out", credential_id=cred),
                     N("ret", "retriever", knowledge_base_id=kb, top_k=3, query="{{state.message}}", output_field="out"),
                     N("sub", "subgraph", workflow_id=child)))
    p = c.get(f"/api/workflows/{wid}/transfer", params={"email": b.email}, headers=H(a.token)).json()["data"]
    assert sorted(i["kind"] for i in p["issues"]) == ["credential", "knowledge_base", "subgraph"]
    assert next(i for i in p["issues"] if i["kind"] == "credential")["name"] == "A key"
    bcred = c.post("/api/credentials", json={"name": "B key", "provider": "openai", "api_key": "sk-test-bbbb2222"}, headers=H(b.token)).json()["data"]["id"]
    p = c.get(f"/api/workflows/{wid}/transfer", params={"email": b.email}, headers=H(a.token)).json()["data"]
    assert [o["id"] for o in p["options"]["credential"]] == [bcred]
    assert code(c.post(f"/api/workflows/{wid}/transfer", json={"email": b.email, "rebind": {"llm": cred}}, headers=H(a.token))) == "TRANSFER_REBIND_INVALID"
    assert code(c.post(f"/api/workflows/{wid}/transfer", json={"email": a.email}, headers=H(a.token))) == "TRANSFER_SAME_OWNER"
    v = register("ov"); UserRepository(get_db()).set_role(v.id, "viewer")
    assert code(c.post(f"/api/workflows/{wid}/transfer", json={"email": v.email}, headers=H(a.token))) == "TRANSFER_TARGET_ROLE"
    r = c.post(f"/api/workflows/{wid}/transfer", json={"email": b.email, "rebind": {"llm": bcred}}, headers=H(a.token)).json()["data"]
    assert r["owner_email"] == b.email and sorted(i["kind"] for i in r["flagged"]) == ["knowledge_base", "subgraph"]
    row = WorkflowRepository(get_db()).get(wid); data = json.loads(row.data)
    assert row.owner == b.id and next(n for n in data["nodes"] if n["id"] == "llm")["data"]["credential_id"] == bcred
    got = c.get(f"/api/workflows/{wid}", headers=H(a.token)).json()["data"]; assert got["access"] == "editor"  # previous owner keeps editor
    assert code(c.post(f"/api/workflows/{wid}/transfer", json={"email": v.email}, headers=H(a.token))) == "WORKFLOW_FORBIDDEN"
    vs = c.get(f"/api/workflows/{wid}/versions", headers=H(b.token)).json()["data"]["items"]
    assert vs[0]["note"] == f"Ownership transferred to {b.email}"
    e = audit(adm, category="workflow", q="Handover")["items"][0]
    assert e["action"] == "workflow.transfer" and e["details"]["to"] == b.email and len(e["details"]["flagged"]) == 2


# ---------- account deletion ----------
def test_delete_or_anonymise_accounts():
    adm, a, b = admin_token(), register("da"), register("db")
    c.post("/api/credentials", json={"name": "k", "provider": "openai", "api_key": "sk-test-cccc3333"}, headers=H(a.token))
    wid = first_wf(a)
    me = c.get("/api/me", headers=H(adm)).json()["data"]["id"]
    assert code(c.request("DELETE", f"/api/admin/users/{me}", json={}, headers=H(adm))) == "USER_SELF_CHANGE"
    r = c.request("DELETE", f"/api/admin/users/{a.id}", json={"mode": "anonymize"}, headers=H(adm))
    assert code(r) == "USER_HAS_WORKFLOWS" and r.json()["error"]["details"]["count"] == 1
    assert code(c.request("DELETE", f"/api/admin/users/{a.id}", json={"mode": "wipe"}, headers=H(adm))) == "USER_DELETE_MODE_INVALID"
    r = c.request("DELETE", f"/api/admin/users/{a.id}", json={"mode": "anonymize", "reassign_to": b.email}, headers=H(adm)).json()["data"]
    assert r["reassigned"] == [wid] and WorkflowRepository(get_db()).get(wid).owner == b.id
    u = UserRepository(get_db()).get_by_id(a.id)
    assert u.email == f"deleted-{a.id}@deleted.invalid" and not u.active and u.password is None
    assert code(c.get("/api/me", headers=H(a.token))) == "AUTH_ACCOUNT_DISABLED"
    assert c.get("/api/credentials", headers=H(b.token)).json()["data"] == []  # b has none; a's key was purged with the account
    assert all(x["id"] != a.id for x in c.get("/api/admin/users", headers=H(adm)).json()["data"]["users"])
    # hard delete: a user with no workflows left
    d = register("dd"); c.delete(f"/api/workflows/{first_wf(d)}", headers=H(d.token))
    assert c.request("DELETE", f"/api/admin/users/{d.id}", json={"mode": "delete"}, headers=H(adm)).json()["data"]["mode"] == "delete"
    assert UserRepository(get_db()).get_by_id(d.id) is None and code(c.get("/api/me", headers=H(d.token))) == "AUTH_TOKEN_INVALID"
    assert {"user.anonymize", "user.delete"} <= {e["action"] for e in audit(adm, category="user")["items"]}


# ---------- org resource policy ----------
def test_org_resource_policy_defaults_to_editors_and_admins():
    adm, v = admin_token(), register("pv")
    UserRepository(get_db()).set_role(v.id, "viewer")
    assert c.get("/api/admin/policy", headers=H(adm)).json()["data"]["org_resources_roles"] == ["admin", "editor"]
    sid = uuid.uuid4().hex[:10]
    McpServerRepository(get_db()).save(McpServer(id=sid, owner="admin", scope="org", name="Org", transport="http", url="https://mcp.example/mcp", created=time.time()))
    with pytest.raises(AppError) as e: run_service().ports(v.id, v.id).mcp_call(sid, "add", {})
    assert e.value.code == "ORG_RESOURCE_NOT_ALLOWED"
    assert c.get("/api/mcp/servers", headers=H(v.token)).json()["data"]["org_usable"] is False
    cid = uuid.uuid4().hex[:10]
    ApprovalRepository(get_db()).save_channel(ApprovalChannel(id=cid, owner="admin", kind="slack", scope="org", team_id=f"T{cid}", name="Org", secrets="x", hint="x", created=time.time()))
    ch = channel_service(); cfg = {"channel_id": cid}
    assert ch.org_denied(v.id, cfg) and ch.for_node(v.id, cfg) is None
    assert code(c.put("/api/admin/policy", json={"org_resources_roles": ["boss"]}, headers=H(adm))) == "USER_ROLE_INVALID"
    assert code(c.put("/api/admin/policy", json={"org_resources_roles": []}, headers=H(v.token))) == "PERMISSION_DENIED"
    r = c.put("/api/admin/policy", json={"org_resources_roles": ["editor", "viewer"]}, headers=H(adm)).json()["data"]
    assert r["org_resources_roles"] == ["admin", "editor", "viewer"]
    ch = channel_service(); assert not ch.org_denied(v.id, cfg) and ch.for_node(v.id, cfg).id == cid
    c.put("/api/admin/policy", json={"org_resources_roles": ["editor"]}, headers=H(adm))
    assert audit(adm, category="policy")["items"][0]["details"]["after"] == ["admin", "editor"]


# ---------- subgraphs ----------
def test_delete_blocked_by_dependents_and_children_changed_note():
    a = register("sg")
    child = save(a, wf(f"Child {uuid.uuid4().hex[:4]}", N("x", "llm", prompt="hi", output_field="out")))
    parent = save(a, wf("Parent", N("sub", "subgraph", workflow_id=child)))
    r = c.delete(f"/api/workflows/{child}", headers=H(a.token))
    assert code(r) == "WORKFLOW_IN_USE" and r.json()["error"]["details"]["dependents"] == [{"id": parent, "name": "Parent"}]
    assert c.get(f"/api/workflows/{child}/dependents", headers=H(a.token)).json()["data"]["dependents"][0]["id"] == parent
    assert c.get(f"/api/workflows/{parent}/versions", headers=H(a.token)).json()["data"]["children_changed"] == []
    time.sleep(0.01)
    w = c.get(f"/api/workflows/{child}", headers=H(a.token)).json()["data"]; w["nodes"][1]["data"]["prompt"] = "changed"
    c.post("/api/workflows", json=w, headers=H(a.token))
    ch = c.get(f"/api/workflows/{parent}/versions", headers=H(a.token)).json()["data"]["children_changed"]
    assert ch[0]["id"] == child and ch[0]["version"] == 2
    assert c.delete(f"/api/workflows/{child}?force=true", headers=H(a.token)).status_code == 200


def test_errors_inside_subgraphs_name_nodes_by_label():
    child = {"nodes": [N("s", "start"), N("x", "llm", label="Classify"), N("e", "end")], "edges": [E("s", "x"), E("x", "e")], "state": [{"name": "message"}]}
    parent = wf("P", N("sub", "subgraph", label="Triage", workflow_id="c"))
    assert validate_with(parent, lambda r: child) == ['Node "Triage › Classify": output_field is missing']


def test_audit_requires_admin_and_filters():
    adm, b = admin_token(), register("af")
    assert code(c.get("/api/admin/audit", headers=H(b.token))) == "PERMISSION_DENIED"
    c.patch(f"/api/admin/users/{b.id}", json={"role": "viewer"}, headers=H(adm))
    got = audit(adm, category="user", q=b.email, since="24h")
    assert got["total"] >= 1 and got["items"][0]["action"] == "user.role" and got["items"][0]["details"] == {"before": "editor", "after": "viewer"}
    assert audit(adm, category="team", q=b.email)["total"] == 0


from sqlalchemy import inspect as _inspect  # noqa: E402
from test_identity_migration import db, upgrade  # noqa: E402,F401


def test_migration_0022_creates_tables(db):  # noqa: F811
    upgrade(db, "0021_rbac"); upgrade(db, "head")
    have = set(_inspect(db.engine).get_table_names())
    assert {"teams", "team_members", "workflow_team_shares", "audit_events", "studio_settings"} <= have
