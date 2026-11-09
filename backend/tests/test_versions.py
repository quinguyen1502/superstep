"""workflow versions (save → version), diff, restore, run ↔ version tagging, migration backfill."""
import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.workflow_diff import diff_workflows, same_content


@pytest.fixture(scope="module")
def c():
    with TestClient(app) as client:
        yield client

def H(t): return {"Authorization": f"Bearer {t}"}
def user(c):
    return c.post("/api/auth/register", json={"email": f"v{uuid.uuid4().hex[:6]}@example.com", "password": "secret12"}).json()["data"]["token"]
def example(c, tok): return c.get("/api/workflows", headers=H(tok)).json()["data"][0]["id"]
def get(c, tok, path): return c.get(path, headers=H(tok)).json()["data"]
def run_ws(c, tok, msg):
    with c.websocket_connect(f"/ws/run?token={tok}") as w:
        w.send_json(msg)
        while True:
            e = w.receive_json()
            if e["type"] in ("run_summary", "error"): return e


def test_seeded_workflow_has_v1(c):
    tok = user(c); wid = example(c, tok)
    vs = get(c, tok, f"/api/workflows/{wid}/versions")["items"]
    assert [v["version"] for v in vs] == [1] and vs[0]["current"] and vs[0]["author_email"].endswith("@example.com")


def test_save_creates_versions_only_on_change(c):
    tok = user(c); wid = example(c, tok); wf = get(c, tok, f"/api/workflows/{wid}")
    c.post("/api/workflows", json=wf, headers=H(tok))  # unchanged → no new version
    assert len(get(c, tok, f"/api/workflows/{wid}/versions")["items"]) == 1
    wf["nodes"].append({"id": "extra", "type": "end", "position": {"x": 1, "y": 1}, "data": {}})
    c.post("/api/workflows", json=wf, headers=H(tok))
    c.patch(f"/api/workflows/{wid}", json={"name": f"Renamed {uuid.uuid4().hex[:4]}"}, headers=H(tok))
    vs = get(c, tok, f"/api/workflows/{wid}/versions")["items"]
    assert [v["version"] for v in vs] == [3, 2, 1] and [v["current"] for v in vs] == [True, False, False]
    v2 = get(c, tok, f"/api/workflows/{wid}/versions/2")["workflow"]
    assert any(n["id"] == "extra" for n in v2["nodes"])


def test_diff_and_restore(c):
    tok = user(c); wid = example(c, tok); wf = get(c, tok, f"/api/workflows/{wid}")
    first = wf["nodes"][0]["id"]
    wf["nodes"] = wf["nodes"][1:] + [{"id": "new1", "type": "end", "position": {"x": 0, "y": 0}, "data": {}}]
    c.post("/api/workflows", json=wf, headers=H(tok))
    d = get(c, tok, f"/api/workflows/{wid}/versions/diff?a=1&b=2")
    assert [n["id"] for n in d["nodes"]["added"]] == ["new1"] and [n["id"] for n in d["nodes"]["removed"]] == [first]
    assert not d["identical"]
    r = c.post(f"/api/workflows/{wid}/versions/1/restore", headers=H(tok)).json()["data"]
    assert r["version"] == 3 and any(n["id"] == first for n in r["workflow"]["nodes"])
    vs = get(c, tok, f"/api/workflows/{wid}/versions")["items"]
    assert vs[0]["note"] == "Restored from v1" and len(vs) == 3  # history kept, restore is a new version
    assert get(c, tok, f"/api/workflows/{wid}/versions/diff?a=1&b=3")["identical"]
    assert get(c, tok, f"/api/workflows/{wid}")["nodes"] == get(c, tok, f"/api/workflows/{wid}/versions/1")["workflow"]["nodes"]


def test_errors_and_ownership(c):
    a, b = user(c), user(c); wid = example(c, a)
    r = c.get(f"/api/workflows/{wid}/versions/99", headers=H(a))
    assert r.status_code == 404 and r.json()["error"]["code"] == "VERSION_NOT_FOUND"
    assert c.post(f"/api/workflows/{wid}/versions/99/restore", headers=H(a)).json()["error"]["code"] == "VERSION_NOT_FOUND"
    for path in (f"/api/workflows/{wid}/versions", f"/api/workflows/{wid}/versions/1", f"/api/workflows/{wid}/versions/diff?a=1&b=1"):
        assert c.get(path, headers=H(b)).json()["error"]["code"] == "WORKFLOW_NOT_FOUND"
    assert c.post(f"/api/workflows/{wid}/versions/1/restore", headers=H(b)).status_code == 404


def test_delete_removes_versions(c):
    tok = user(c); wid = example(c, tok)
    c.delete(f"/api/workflows/{wid}", headers=H(tok))
    from app.api.deps import get_db
    from app.repositories import WorkflowVersionRepository
    assert WorkflowVersionRepository(get_db()).latest(wid) is None


def test_runs_record_version(c):
    tok = user(c); wid = example(c, tok); wf = get(c, tok, f"/api/workflows/{wid}")
    run_ws(c, tok, {"workflow_id": wid, "workflow": wf, "input": {"message": "hi"}})
    moved = {**wf, "nodes": [{**n, "position": {"x": 9, "y": 9}} for n in wf["nodes"]]}
    run_ws(c, tok, {"workflow_id": wid, "workflow": moved, "input": {"message": "hi"}})  # layout only: still v1
    edited = {**wf, "nodes": [{**n, "data": {**(n.get("data") or {}), "label": "edited"}} for n in wf["nodes"]]}
    last = run_ws(c, tok, {"workflow_id": wid, "workflow": edited, "input": {"message": "hi"}})  # unsaved edits
    assert last["type"] == "run_summary", last
    import time
    for _ in range(100):  # an "error" event can arrive before the run row is written
        hist = get(c, tok, f"/api/workflows/{wid}/runs")
        if len(hist) == 3: break
        time.sleep(0.05)
    assert sorted([h["version"] for h in hist], key=lambda v: (v is None, v)) == [1, 1, None]


def test_diff_unit():
    a = {"name": "A", "nodes": [{"id": "x", "type": "llm", "data": {"p": 1}, "position": {"x": 0}}, {"id": "y", "type": "end", "position": {"x": 0}}],
         "edges": [{"id": "e1", "source": "x", "target": "y"}], "state": [{"name": "s", "type": "str"}]}
    b = {"name": "B", "nodes": [{"id": "x", "type": "llm", "data": {"p": 2}, "position": {"x": 0}}, {"id": "y", "type": "end", "position": {"x": 5}}],
         "edges": [], "state": [{"name": "s", "type": "int"}, {"name": "t", "type": "str"}]}
    d = diff_workflows(a, b)
    assert d["nodes"]["changed"][0] == {"id": "x", "fields": ["data"], "before": {"data": {"p": 1}}, "after": {"data": {"p": 2}}}
    assert d["nodes"]["moved"] == ["y"] and [e["id"] for e in d["edges"]["removed"]] == ["e1"]
    assert [s["name"] for s in d["state"]["added"]] == ["t"] and d["state"]["changed"][0]["fields"] == ["type"]
    assert d["name"] == {"before": "A", "after": "B"} and not d["identical"] and diff_workflows(a, a)["identical"]
    assert same_content(a, {**a, "name": "other", "nodes": [{**n, "position": {"x": 7}} for n in a["nodes"]]}) and not same_content(a, b)


def test_migration_backfills_v1(tmp_path):
    """Upgrade an 0005 database with workflows in it: each gets a v1 holding its current data."""
    import os
    import sqlalchemy as sa
    from alembic import command
    from alembic.config import Config
    from app.models.database import MIGRATIONS_DIR, Database
    db = Database(f"sqlite:///{tmp_path}/m.db")
    def up(rev):
        cfg = Config(); cfg.set_main_option("script_location", os.path.normpath(MIGRATIONS_DIR))
        with db.engine.begin() as cx:
            cfg.attributes["connection"] = cx; command.upgrade(cfg, rev)
    up("0005_api_triggers")
    with db.engine.begin() as cx:
        cx.execute(sa.text("INSERT INTO workflows (id, name, data, updated, owner) VALUES ('w1', 'One', :d, 5, 'u1')"), {"d": '{"nodes": []}'})
    up("head"); db.migrate()  # idempotent
    with db.engine.begin() as cx:
        row = cx.execute(sa.text("SELECT workflow_id, version, data, author, note FROM workflow_versions")).one()
        assert "workflow_version" in {c["name"] for c in sa.inspect(cx).get_columns("runs")}
    assert tuple(row) == ("w1", 1, '{"nodes": []}', "u1", "Initial version")
