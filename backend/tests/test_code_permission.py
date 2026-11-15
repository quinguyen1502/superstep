"""only `code.write` (admins by default) may add a Code node or change its source, on every graph write."""
import copy, uuid
from types import SimpleNamespace as NS
from fastapi.testclient import TestClient
from app.core import permissions as P
from app.engine import templates as T
from app.main import app

c = TestClient(app)
H = lambda t: {"Authorization": f"Bearer {t}"}
def code(r): return r.json()["error"]["code"]
def data(r): assert r.status_code == 200, r.text; return r.json()["data"]


def register():
    email = f"cw{uuid.uuid4().hex[:6]}@example.com"
    d = c.post("/api/auth/register", json={"email": email, "password": "secret12"}).json()["data"]
    return NS(token=d["token"], id=d["user"]["id"], email=email)


def admin(): return NS(token=c.post("/api/auth/login", json={"email": "admin@example.com", "password": "admin123"}).json()["data"]["token"])


def wf(src="def main(state):\n    return 1\n", name=None, mode="code"):
    d = {"label": "c", "mode": mode, "output_field": "out", **({"code": src} if mode == "code" else {"function": "lookup_order"})}
    return {"name": name or f"cw-{uuid.uuid4().hex[:6]}", "state": [{"name": "message", "type": "string"}, {"name": "out", "type": "string"}],
            "nodes": [{"id": "s", "type": "start", "position": {"x": 0, "y": 0}, "data": {"label": "s"}},
                      {"id": "c", "type": "tool", "position": {"x": 100, "y": 0}, "data": d},
                      {"id": "e", "type": "end", "position": {"x": 200, "y": 0}, "data": {"label": "e"}}],
            "edges": [{"id": "1", "source": "s", "target": "c"}, {"id": "2", "source": "c", "target": "e"}]}


def admin_workflow_shared_with(u, src="def main(state):\n    return 1\n"):
    a = admin(); w = wf(src)
    wid = data(c.post("/api/workflows", json=w, headers=H(a.token)))["id"]
    data(c.put(f"/api/workflows/{wid}/shares", json={"email": u.email, "role": "editor"}, headers=H(a.token)))
    return a, wid, {**w, "id": wid}


def test_only_admins_hold_code_write():
    assert P.can("admin", P.CODE_WRITE) and not P.can("editor", P.CODE_WRITE) and not P.can("viewer", P.CODE_WRITE)
    assert P.CODE_WRITE in P.matrix()["permissions"]
    u = register()
    assert P.CODE_WRITE not in data(c.get("/api/me", headers=H(u.token)))["permissions"]
    assert P.CODE_WRITE in data(c.get("/api/me", headers=H(admin().token)))["permissions"]


def test_code_written_compares_sources_per_node():
    a, b = wf("def main(s): return 1"), wf("def main(s): return 2")
    assert P.code_written({}, a) and P.code_written(a, b) and not P.code_written(a, copy.deepcopy(a))
    moved = copy.deepcopy(a); moved["nodes"][1]["position"] = {"x": 9, "y": 9}; moved["nodes"][1]["data"]["label"] = "renamed"
    assert not P.code_written(a, moved)
    gone = copy.deepcopy(a); gone["nodes"].pop(1)
    assert not P.code_written(a, gone) and not P.code_written(a, wf(mode="function"))  # delete, or switch away from code
    assert not P.code_written({}, wf(mode="function"))


def test_editor_cannot_save_new_code_and_nothing_is_stored():
    u = register(); w = wf()
    r = c.post("/api/workflows", json=w, headers=H(u.token))
    assert r.status_code == 403 and code(r) == "CODE_WRITE_FORBIDDEN"
    assert all(x["name"] != w["name"] for x in data(c.get("/api/workflows", headers=H(u.token))))
    assert data(c.post("/api/workflows", json=wf(mode="function"), headers=H(u.token)))["id"]  # other Tool modes are fine


def test_editor_uses_but_cannot_change_shared_code():
    u = register(); a, wid, w = admin_workflow_shared_with(u)
    moved = copy.deepcopy(w); moved["nodes"][1]["position"] = {"x": 300, "y": 40}; moved["nodes"][1]["data"]["label"] = "Renamed"
    assert data(c.post("/api/workflows", json=moved, headers=H(u.token)))["id"] == wid  # move and rename
    changed = copy.deepcopy(moved); changed["nodes"][1]["data"]["code"] = "def main(state):\n    return 2\n"
    assert code(c.post("/api/workflows", json=changed, headers=H(u.token))) == "CODE_WRITE_FORBIDDEN"
    added = copy.deepcopy(moved); added["nodes"].append({**copy.deepcopy(moved["nodes"][1]), "id": "c2"})
    assert code(c.post("/api/workflows", json=added, headers=H(u.token))) == "CODE_WRITE_FORBIDDEN"
    stored = data(c.get(f"/api/workflows/{wid}", headers=H(u.token)))
    assert stored["nodes"][1]["data"]["code"] == w["nodes"][1]["data"]["code"] and len(stored["nodes"]) == 3
    assert data(c.post(f"/api/workflows/{wid}/duplicate", headers=H(u.token)))["id"] != wid  # a copy writes no new code
    removed = copy.deepcopy(moved); removed["nodes"].pop(1); removed["edges"] = [{"id": "1", "source": "s", "target": "e"}]
    assert data(c.post("/api/workflows", json=removed, headers=H(u.token)))["id"] == wid  # deleting the node is fine
    assert data(c.post("/api/workflows", json=changed, headers=H(a.token)))["id"] == wid  # admins may change code


def test_version_restore_that_brings_back_other_code_is_refused():
    u = register(); a, wid, w = admin_workflow_shared_with(u, "def main(state):\n    return 'v1'\n")
    v2 = copy.deepcopy(w); v2["nodes"][1]["data"]["code"] = "def main(state):\n    return 'v2'\n"
    data(c.post("/api/workflows", json=v2, headers=H(a.token)))
    assert code(c.post(f"/api/workflows/{wid}/versions/1/restore", headers=H(u.token))) == "CODE_WRITE_FORBIDDEN"
    assert data(c.post(f"/api/workflows/{wid}/versions/1/restore", headers=H(a.token)))["workflow"]["nodes"][1]["data"]["code"].endswith("'v1'\n")


def test_templates_with_code():
    u, a = register(), admin()
    payload = {"format": T.FORMAT, "version": T.VERSION, "name": "Code tpl", "description": "", "workflow": wf()}
    assert code(c.post("/api/templates/import", json={"file": payload}, headers=H(u.token))) == "CODE_WRITE_FORBIDDEN"
    t = data(c.post("/api/templates/import", json={"file": payload, "scope": "org"}, headers=H(a.token)))
    assert code(c.post(f"/api/templates/{t['id']}/use", headers=H(u.token))) == "CODE_WRITE_FORBIDDEN"
    assert data(c.post(f"/api/templates/{t['id']}/use", headers=H(a.token)))["id"]
