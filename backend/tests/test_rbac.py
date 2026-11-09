"""roles, per-workflow sharing, admin user management, STUDIO_ADMIN_EMAILS bootstrap, Add to Slack."""
import json, time, uuid
from types import SimpleNamespace as NS
from urllib.parse import parse_qs, urlparse
import httpx, pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from app.api.deps import get_db, run_service
from app.core import permissions as P
from app.core.errors import AppError
from app.main import app
from app.models.database import Database
from app.repositories import UserRepository, WorkflowRepository
from app.services import slack_oauth
from app.services.approval_channels import ADAPTERS
from app.services.seed import bootstrap
from app.services.user_service import UserService
from test_identity_migration import db, upgrade  # noqa: F401  (SQLite + Postgres migration fixture)

c = TestClient(app)
H = lambda t: {"Authorization": f"Bearer {t}"}


def register(prefix="u"):
    email = f"{prefix}{uuid.uuid4().hex[:6]}@example.com"
    d = c.post("/api/auth/register", json={"email": email, "password": "secret12"}).json()["data"]
    return NS(token=d["token"], id=d["user"]["id"], email=email, user=d["user"])


def admin_token():
    return c.post("/api/auth/login", json={"email": "admin@example.com", "password": "admin123"}).json()["data"]["token"]


def code(r): return r.json()["error"]["code"]


def first_wf(u): return c.get("/api/workflows", headers=H(u.token)).json()["data"][0]["id"]


# ---------- model ----------
def test_permission_matrix():
    assert P.can("admin", P.USERS_MANAGE) and not P.can("editor", P.USERS_MANAGE) and not P.can("viewer", P.WORKFLOWS_CREATE)
    assert P.workflow_role("editor", True, None) == "owner" and P.workflow_role("admin", False, None) == "owner"
    assert P.workflow_role("editor", False, "editor") == "editor" and P.workflow_role("viewer", False, "editor") == "viewer"  # capped
    assert P.workflow_role("editor", False, None) is None
    m = P.matrix(); assert [r["role"] for r in m["roles"]] == ["admin", "editor", "viewer"]
    assert {a["access"]: a["actions"] for a in m["workflow_access"]}["viewer"] == ["view", "run"]


def test_migration_backfills_admins_from_is_admin(db):  # noqa: F811
    upgrade(db, "0020_mcp_servers")
    with db.engine.begin() as cx:
        cx.execute(text("INSERT INTO users (id, email, password, created, is_admin) VALUES ('a', 'a@x.io', 'p', 1, :t), ('b', 'b@x.io', 'p', 2, :f)"),
                   {"t": True, "f": False})
    upgrade(db, "head")
    with db.engine.connect() as cx:
        rows = dict(cx.execute(text("SELECT id, role FROM users ORDER BY id")).all())
        assert rows == {"a": "admin", "b": "editor"}
        assert cx.execute(text("SELECT count(*) FROM users WHERE active = :t"), {"t": True}).scalar() == 2
        assert cx.execute(text("SELECT count(*) FROM workflow_shares")).scalar() == 0


# ---------- sharing ----------
def test_share_viewer_editor_and_isolation():
    a, b, x = register("own"), register("sh"), register("out")
    wid = first_wf(a)
    assert c.get(f"/api/workflows/{wid}", headers=H(b.token)).status_code == 404
    r = c.put(f"/api/workflows/{wid}/shares", json={"email": b.email.upper(), "role": "viewer"}, headers=H(a.token))
    assert r.status_code == 200 and [s["email"] for s in r.json()["data"]["shares"]] == [b.email]
    # viewer: listed with owner, opens, cannot change anything
    row = next(w for w in c.get("/api/workflows", headers=H(b.token)).json()["data"] if w["id"] == wid)
    assert row["access"] == "viewer" and row["mine"] is False and row["owner_email"] == a.email
    wf = c.get(f"/api/workflows/{wid}", headers=H(b.token)).json()["data"]; assert wf["access"] == "viewer"
    assert code(c.post("/api/workflows", json={**wf, "name": "Hijack"}, headers=H(b.token))) == "WORKFLOW_FORBIDDEN"
    assert code(c.patch(f"/api/workflows/{wid}", json={"name": "x"}, headers=H(b.token))) == "WORKFLOW_FORBIDDEN"
    assert code(c.delete(f"/api/workflows/{wid}", headers=H(b.token))) == "WORKFLOW_FORBIDDEN"
    assert code(c.get(f"/api/workflows/{wid}/tokens", headers=H(b.token))) == "WORKFLOW_FORBIDDEN"
    assert code(c.put(f"/api/workflows/{wid}/shares", json={"email": x.email, "role": "viewer"}, headers=H(b.token))) == "WORKFLOW_FORBIDDEN"
    assert c.get(f"/api/workflows/{wid}", headers=H(x.token)).status_code == 404  # not shared: not disclosed
    # editor: saves in place, the owner does not change; the response-only fields are not stored
    c.put(f"/api/workflows/{wid}/shares", json={"email": b.email, "role": "editor"}, headers=H(a.token))
    r = c.post("/api/workflows", json={**wf, "name": "Edited by B"}, headers=H(b.token)); assert r.status_code == 200
    row = WorkflowRepository(get_db()).get(wid)
    assert row.owner == a.id and row.name == "Edited by B" and "access" not in json.loads(row.data)
    assert code(c.delete(f"/api/workflows/{wid}", headers=H(b.token))) == "WORKFLOW_FORBIDDEN"
    # share errors
    assert code(c.put(f"/api/workflows/{wid}/shares", json={"email": a.email, "role": "viewer"}, headers=H(a.token))) == "SHARE_OWNER"
    assert code(c.put(f"/api/workflows/{wid}/shares", json={"email": "nobody@example.com", "role": "viewer"}, headers=H(a.token))) == "SHARE_USER_NOT_FOUND"
    assert code(c.put(f"/api/workflows/{wid}/shares", json={"email": b.email, "role": "owner"}, headers=H(a.token))) == "SHARE_ROLE_INVALID"
    # the shared user may leave; then it is gone again
    assert c.delete(f"/api/workflows/{wid}/shares/{b.id}", headers=H(b.token)).status_code == 200
    assert code(c.delete(f"/api/workflows/{wid}/shares/{b.id}", headers=H(a.token))) == "SHARE_NOT_FOUND"
    assert c.get(f"/api/workflows/{wid}", headers=H(b.token)).status_code == 404


def test_shared_runs_use_the_stored_graph_and_owner_resources():
    a, b = register("own"), register("vw")
    wid = first_wf(a)
    c.put(f"/api/workflows/{wid}/shares", json={"email": b.email, "role": "viewer"}, headers=H(a.token))
    svc = run_service(); stored = json.loads(WorkflowRepository(get_db()).get(wid).data)
    plan = svc.plan(b.id, {"workflow_id": wid, "workflow": {"name": "evil", "nodes": [], "edges": []}, "input": {}})
    assert plan.workflow["nodes"] == stored["nodes"]  # viewers can't run unsaved JSON
    assert svc.resources_of(wid, b.id) == a.id
    UserRepository(get_db()).set_role(b.id, "viewer")
    with pytest.raises(AppError) as e: svc.plan(b.id, {"workflow": stored, "input": {}})  # ad-hoc graphs: not for viewers
    assert e.value.code == "PERMISSION_DENIED"
    assert svc.plan(b.id, {"workflow_id": wid, "input": {}}).workflow_id == wid  # a viewer still runs the shared workflow
    # run history: the owner sees every run, others only their own
    for u in (a, b):
        with c.websocket_connect(f"/ws/run?token={u.token}") as ws:
            ws.send_json({"workflow_id": wid, "input": {"message": "hi"}})
            while ws.receive_json()["type"] not in ("run_finished", "error"): pass
    time.sleep(0.2)
    own = c.get(f"/api/workflows/{wid}/runs", headers=H(a.token)).json()["data"]
    mine = c.get(f"/api/workflows/{wid}/runs", headers=H(b.token)).json()["data"]
    assert len(own) == 2 and len(mine) == 1


# ---------- roles ----------
def test_admin_manages_users_and_viewer_role_is_enforced():
    adm, b = admin_token(), register("rv")
    assert code(c.get("/api/admin/users", headers=H(b.token))) == "PERMISSION_DENIED"
    users = c.get("/api/admin/users", headers=H(adm)).json()["data"]
    me = next(u for u in users["users"] if u["email"] == "admin@example.com"); assert me["role"] == "admin" and users["roles"]
    assert code(c.patch(f"/api/admin/users/{me['id']}", json={"role": "viewer"}, headers=H(adm))) == "USER_SELF_CHANGE"
    assert code(c.patch(f"/api/admin/users/{b.id}", json={"role": "boss"}, headers=H(adm))) == "USER_ROLE_INVALID"
    assert code(c.patch("/api/admin/users/nope", json={"role": "viewer"}, headers=H(adm))) == "USER_NOT_FOUND"
    assert c.patch(f"/api/admin/users/{b.id}", json={"role": "viewer"}, headers=H(adm)).json()["data"]["role"] == "viewer"
    m = c.get("/api/me", headers=H(b.token)).json()["data"]; assert m["role"] == "viewer" and m["permissions"] == []
    assert code(c.post("/api/workflows", json={"name": "New", "nodes": [], "edges": []}, headers=H(b.token))) == "PERMISSION_DENIED"
    assert code(c.post("/api/credentials", json={"name": "k", "provider": "openai", "api_key": "sk-x"}, headers=H(b.token))) == "PERMISSION_DENIED"
    assert code(c.post(f"/api/workflows/{first_wf(b)}/duplicate", headers=H(b.token))) == "PERMISSION_DENIED"
    # admins see and act on every workflow
    assert c.get(f"/api/workflows/{first_wf(b)}", headers=H(adm)).json()["data"]["access"] == "owner"
    assert any(w["id"] == first_wf(b) for w in c.get("/api/workflows?all=1", headers=H(adm)).json()["data"])
    # deactivation is immediate: existing tokens, login and sockets
    assert c.patch(f"/api/admin/users/{b.id}", json={"active": False}, headers=H(adm)).status_code == 200
    assert code(c.get("/api/me", headers=H(b.token))) == "AUTH_ACCOUNT_DISABLED"
    assert code(c.post("/api/auth/login", json={"email": b.email, "password": "secret12"})) == "AUTH_ACCOUNT_DISABLED"
    with pytest.raises(Exception):
        with c.websocket_connect(f"/ws/run?token={b.token}") as ws: ws.receive_json()
    c.patch(f"/api/admin/users/{b.id}", json={"active": True, "role": "editor"}, headers=H(adm))
    assert c.get("/api/me", headers=H(b.token)).json()["data"]["role"] == "editor"


def test_last_admin_guard(tmp_path):
    d = Database(f"sqlite:///{tmp_path}/r.db"); d.migrate(); users = UserRepository(d)
    users.add("a", "a@x.io", "p", 1); users.set_admin("a"); users.add("b", "b@x.io", "p", 2)
    allow = NS(require=lambda uid, perm: None)  # a racing second admin: the guard still holds
    with pytest.raises(AppError) as e: UserService(users, allow).update("b", "a", role="editor")
    assert e.value.code == "USER_LAST_ADMIN"
    with pytest.raises(AppError) as e: UserService(users, allow).update("b", "a", active=False)
    assert e.value.code == "USER_LAST_ADMIN"


def test_admin_emails_bootstrap_and_default_role(tmp_path, monkeypatch):
    d = Database(f"sqlite:///{tmp_path}/b.db"); bootstrap(d); users = UserRepository(d)
    assert users.get_by_email("admin@example.com").role == "admin"
    users.add("z", "boss@x.io", "p", 5)
    monkeypatch.setenv("STUDIO_ADMIN_EMAILS", "boss@x.io")
    bootstrap(d); assert users.get_by_email("boss@x.io").role == "editor"  # an admin exists: no change
    users.set_role(users.get_by_email("admin@example.com").id, "editor")
    bootstrap(d); assert users.get_by_email("boss@x.io").role == "admin"  # lockout recovery
    monkeypatch.setenv("STUDIO_DEFAULT_ROLE", "viewer")
    v = register("dv"); assert v.user["role"] == "viewer"
    assert c.get("/api/workflows", headers=H(v.token)).json()["data"] == []  # viewers get no example copy
    monkeypatch.setenv("STUDIO_ADMIN_EMAILS", "boot@example.com")
    r = c.post("/api/auth/register", json={"email": "boot@example.com", "password": "secret12"})
    assert r.status_code == 409 or r.json()["data"]["user"]["role"] == "admin"


# ---------- Add to Slack ----------
def test_add_to_slack_oauth(monkeypatch):
    u = register("sl")
    assert c.get("/api/approvals/slack/oauth", headers=H(u.token)).json()["data"]["enabled"] is False
    assert code(c.post("/api/approvals/slack/oauth/start", json={}, headers=H(u.token))) == "SLACK_OAUTH_NOT_CONFIGURED"
    for k, v in {"SLACK_CLIENT_ID": "1.2", "SLACK_CLIENT_SECRET": "cs", "SLACK_SIGNING_SECRET": "ab" * 16, "STUDIO_PUBLIC_URL": "https://studio.example"}.items():
        monkeypatch.setenv(k, v)
    url = c.post("/api/approvals/slack/oauth/start", json={"scope": "user"}, headers=H(u.token)).json()["data"]["url"]
    q = parse_qs(urlparse(url).query); state = q["state"][0]
    assert q["client_id"] == ["1.2"] and q["redirect_uri"] == ["https://studio.example/api/approvals/slack/oauth/callback"]
    assert code(c.post("/api/approvals/slack/oauth/start", json={"scope": "org"}, headers=H(u.token))) == "CHANNEL_ADMIN_REQUIRED"
    seen = []
    def fake(req: httpx.Request):
        seen.append(req.url.path)
        if req.url.path.endswith("oauth.v2.access"):
            assert b"code=abc" in req.content and req.headers["authorization"].startswith("Basic ")
            return httpx.Response(200, json={"ok": True, "access_token": "xoxb-1234-5678-abcdefgh", "team": {"id": "T9", "name": "Acme"}})
        return httpx.Response(200, json={"ok": True, "team": "Acme", "team_id": "T9"})
    monkeypatch.setattr(ADAPTERS["slack"], "transport", httpx.MockTransport(fake), raising=False)
    r = c.get(f"/api/approvals/slack/oauth/callback?code=abc&state={state}", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "https://studio.example/settings/channels?slack=installed"
    ch = c.get("/api/approvals/channels", headers=H(u.token)).json()["data"]["channels"]
    assert any(x["kind"] == "slack" and x["team_id"] == "T9" and x["scope"] == "user" for x in ch)
    bad = c.get(f"/api/approvals/slack/oauth/callback?code=abc&state={state[:-2]}xx", follow_redirects=False)
    assert bad.headers["location"].endswith("slack_error=SLACK_OAUTH_STATE_INVALID")
    old = slack_oauth.make_state(u.id, "user", now=time.time() - 3600)
    assert c.get(f"/api/approvals/slack/oauth/callback?code=abc&state={old}", follow_redirects=False).headers["location"].endswith("SLACK_OAUTH_STATE_INVALID")
    denied = c.get("/api/approvals/slack/oauth/callback?error=access_denied", follow_redirects=False)
    assert denied.headers["location"].endswith("slack_error=SLACK_OAUTH_FAILED")
