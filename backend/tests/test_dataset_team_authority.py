import json

import pytest
from sqlalchemy import select, text

from app.models import AuditEvent, DatasetApiToken, TeamMember, User
from test_dataset_rows import call
from test_datasets import auth, client, create, error  # noqa: F401
from test_identity_migration import db, upgrade  # noqa: F401

COLUMNS = [{"key": "ticket", "label": "Ticket", "kind": "text", "unique": True, "required": True},
           {"key": "note", "label": "Note", "kind": "text"}]


@pytest.fixture
def team(client, db):
    with db.session() as session:
        session.add_all([User(id="admin", email="admin@example.com", role="admin"),
                         User(id="peer", email="peer@example.com", role="editor")])
        session.flush()
        session.add_all([TeamMember(team_id="support", user_id=uid, added=1) for uid in ("admin", "peer")])
        session.commit()
    return create(client, name="Support data", team_id="support", columns=COLUMNS)


def management(base, revision):
    column = {"key": "extra", "label": "Extra", "kind": "text"}
    return [
        ("PUT", base, {"name": "Renamed", "description": None, "revision": revision}),
        ("POST", f"{base}/columns", {"revision": revision, "column": column}),
        ("PUT", f"{base}/columns/note", {"revision": revision, "column": {"key": "note", "label": "Notes", "kind": "text"}}),
        ("DELETE", f"{base}/columns/note?revision={revision}", None),
        ("GET", f"{base}/access", None),
        ("PUT", f"{base}/access/grants/flow", {"permission": "read"}),
        ("DELETE", f"{base}/access/grants/flow", None),
        ("POST", f"{base}/access/tokens", {"name": "Export", "permission": "read"}),
        ("POST", f"{base}/access/tokens/missing/rotate", None),
        ("DELETE", f"{base}/access/tokens/missing", None),
        ("DELETE", f"{base}?revision={revision}", None),
    ]


def send(client, method, url, uid, body):
    return client.request(method, url, headers=auth(uid), **({"json": body} if body is not None else {}))


@pytest.mark.parametrize("uid,status,code", [
    ("peer", 403, "DATASET_MANAGE_DENIED"), ("member", 403, "PERMISSION_DENIED"), ("other", 404, "DATASET_NOT_FOUND"),
])
def test_members_without_management_cannot_change_a_team_dataset(client, team, uid, status, code):
    base = f"/api/datasets/{team['id']}"
    for method, url, body in management(base, team["revision"]):
        error(send(client, method, url, uid, body), status, code)
    assert call(client, "GET", base)["revision"] == team["revision"]


def test_team_editors_edit_rows_and_managers_manage(client, team, db):
    base = f"/api/datasets/{team['id']}"
    row = call(client, "POST", f"{base}/rows", uid="peer", body={"values": {"ticket": "A"}}, status=201)["row"]
    row = call(client, "PATCH", f"{base}/rows/{row['id']}", uid="peer", body={"revision": 1, "values": {"note": "Seen"}})["row"]
    imported = call(client, "POST", "/api/datasets/csv/import", uid="peer", body={
        "text": "ticket\nB\n", "dataset_id": team["id"], "schema_revision": team["revision"], "mapping": ["ticket"],
    })
    assert imported["imported"] == 1
    assert call(client, "DELETE", f"{base}/rows/{row['id']}?revision={row['revision']}", uid="peer") == {"ok": True}
    for uid in ("owner", "admin"):
        current = call(client, "GET", base)
        renamed = call(client, "PUT", base, uid=uid, body={"name": f"By {uid}", "description": None, "revision": current["revision"]})
        assert renamed["name"] == f"By {uid}" and renamed["team_owner_id"] == "owner"
        added = call(client, "POST", f"{base}/columns", uid=uid, status=201, body={
            "revision": renamed["revision"], "column": {"key": f"{uid}_field", "label": uid, "kind": "text"}})
        call(client, "DELETE", f"{base}/columns/{uid}_field?revision={added['revision']}", uid=uid)
        issued = call(client, "POST", f"{base}/access/tokens", uid=uid, status=201, body={"name": uid, "permission": "read"})
        call(client, "DELETE", f"{base}/access/tokens/{issued['id']}", uid=uid)
        assert call(client, "GET", f"{base}/access", uid=uid)["tokens"] == []
    current = call(client, "GET", base)
    assert call(client, "DELETE", f"{base}?revision={current['revision']}", uid="admin") == {"ok": True}


def test_rotation_keeps_the_issuer_and_the_token_still_authorizes(client, team, db):
    base = f"/api/datasets/{team['id']}"
    call(client, "POST", f"{base}/rows", body={"values": {"ticket": "A"}}, status=201)
    issued = call(client, "POST", f"{base}/access/tokens", status=201, body={"name": "Export", "permission": "read"})
    rotated = call(client, "POST", f"{base}/access/tokens/{issued['id']}/rotate", uid="admin")
    with db.session() as session:
        assert session.get(DatasetApiToken, issued["id"]).issuer_id == "owner"
    columns = [{"key": "ticket", "kind": "text", "required": True, "unique": True}, {"key": "note", "kind": "text"}]
    reply = client.post(f"{base}/connected", headers={"Authorization": f"Bearer {rotated['token']}"}, json={
        "version": 1, "operation": "find_rows", "columns": columns, "fields": ["ticket"], "arguments": {}})
    assert reply.status_code == 200, reply.text
    assert [item["values"] for item in reply.json()["data"]["items"]] == [{"ticket": "A"}]
    error(client.post(f"{base}/connected", headers={"Authorization": f"Bearer {issued['token']}"}, json={
        "version": 1, "operation": "find_rows", "columns": columns, "fields": ["ticket"], "arguments": {}}), 401, "AUTH_TOKEN_INVALID")


def test_admins_transfer_team_dataset_ownership(client, team, db):
    base = f"/api/datasets/{team['id']}"
    owner_url = f"{base}/owner"
    revision = team["revision"]
    error(send(client, "PUT", owner_url, "owner", {"user_id": "peer", "revision": revision}), 403, "PERMISSION_DENIED")
    error(send(client, "PUT", owner_url, "peer", {"user_id": "peer", "revision": revision}), 403, "PERMISSION_DENIED")
    for target in ("other", "member", "missing"):
        error(send(client, "PUT", owner_url, "admin", {"user_id": target, "revision": revision}), 400, "DATASET_OWNER_INVALID")
    error(send(client, "PUT", owner_url, "admin", {"user_id": "peer", "revision": revision + 1}), 409, "DATASET_SCHEMA_CONFLICT")
    moved = call(client, "PUT", owner_url, uid="admin", body={"user_id": "peer", "revision": revision})
    assert moved["team_owner_id"] == "peer" and moved["revision"] == revision + 1
    with db.session() as session:
        event = session.scalars(select(AuditEvent).where(AuditEvent.action == "dataset.transfer")).one()
    assert event.actor_id == "admin" and json.loads(event.details) == {"from_user": "owner", "to_user": "peer"}
    error(send(client, "PUT", base, "owner", {"name": "Old owner", "description": None, "revision": moved["revision"]}),
          403, "DATASET_MANAGE_DENIED")
    assert call(client, "PUT", base, uid="peer", body={"name": "New owner", "description": None, "revision": moved["revision"]})["name"] == "New owner"
    personal = create(client, name="Mine")
    error(send(client, "PUT", f"/api/datasets/{personal['id']}/owner", "admin", {"user_id": "peer", "revision": 1}),
          404, "DATASET_NOT_FOUND")


def test_existing_team_datasets_take_the_creator_as_owner(db):
    upgrade(db, "0067_dataset_delete_capability")
    with db.engine.begin() as conn:
        conn.execute(text("INSERT INTO users (id, email) VALUES ('maker', 'maker@example.com')"))
        conn.execute(text("INSERT INTO teams (id, name, created, created_by) VALUES ('t', 'T', 1, 'maker')"))
        for dataset_id, team_id, owner_id in (("tracked", "t", None), ("untracked", "t", None), ("personal", None, "maker")):
            conn.execute(text(
                "INSERT INTO datasets (id, owner_id, team_id, name, name_key, revision, created, updated) "
                "VALUES (:id, :owner, :team, :id, :id, 1, 1, 1)"), {"id": dataset_id, "owner": owner_id, "team": team_id})
        for dataset_id in ("tracked", "personal"):
            conn.execute(text(
                "INSERT INTO audit_events (id, ts, actor_id, action, target_type, target_id) "
                "VALUES (:id, 1, 'maker', 'dataset.create', 'dataset', :target)"), {"id": f"e-{dataset_id}", "target": dataset_id})
    upgrade(db, "head")
    with db.engine.connect() as conn:
        owners = dict(conn.execute(text("SELECT id, team_owner_id FROM datasets")).all())
    assert owners == {"tracked": "maker", "untracked": None, "personal": None}
