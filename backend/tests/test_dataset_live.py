"""Persisted Dataset invalidations, authorization and cross-process delivery."""
import asyncio
import os
import subprocess
import sys
from time import time

import pytest
from alembic import command
from alembic.config import Config
from fastapi import WebSocket, WebSocketDisconnect

from app.api import deps
from app.api.routes import dataset_ws
from app.core.security import SESSION_COOKIE
from app.models import TeamMember, User
from app.models.database import MIGRATIONS_DIR
from app.repositories.datasets import DatasetRepository
from app.services.notification_hub import InMemoryNotificationHub, dataset_changes_channel
from test_dataset_connected import ACTIVE, SCORE, TICKET, dataset, post, request, token
from test_dataset_rows import call, insert
from test_datasets import auth, client, create, error  # noqa: F401
from test_identity_migration import db  # noqa: F401


class RecordingHub(InMemoryNotificationHub):
    def __init__(self, db):
        super().__init__()
        self.repo = DatasetRepository(db)
        self.published = []

    def publish(self, topic, payload):
        if topic.startswith("dataset-changes:"):
            dataset_id = topic.split(":", 1)[1]
            self.published.append((topic, payload, self.repo.revisions("owner", dataset_id)))
        super().publish(topic, payload)


@pytest.fixture
def live_hub(monkeypatch, db):
    hub = RecordingHub(db)
    monkeypatch.setattr(deps, "get_notification_hub", lambda: hub)
    monkeypatch.setattr(dataset_ws, "get_notification_hub", lambda: hub)
    return hub


def revisions(client, base, uid="owner"):
    response = client.get(f"{base}/revisions", headers=auth(uid))
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    return response.json()["data"]


def marker(data_revision, schema_revision=1):
    return {"schema_revision": schema_revision, "data_revision": data_revision}


def socket_headers(uid="owner"):
    token = auth(uid)["Authorization"].removeprefix("Bearer ")
    return {"cookie": f"{SESSION_COOKIE}={token}", "origin": "http://testserver"}


def test_studio_writes_csv_batch_undo_and_rollbacks(client, live_hub, monkeypatch):
    data = dataset(client)
    base = f"/api/datasets/{data['id']}"
    rows = f"{base}/rows"
    assert revisions(client, base) == marker(1)
    row = insert(client, rows, ticket="A", score=2)
    assert revisions(client, base) == marker(2)
    row_url = rows + "/" + row["id"]
    row = call(client, "PATCH", row_url, body={"revision": row["revision"], "values": {"score": 3}})["row"]
    assert revisions(client, base) == marker(3)
    call(client, "POST", rows + "/upsert", body={"key": "ticket", "values": {"ticket": "A", "score": 3}})
    call(client, "PATCH", rows + "/batch", body={"schema_revision": 1, "rows": [
        {"id": row["id"], "revision": row["revision"], "values": {"score": 3}},
    ]})
    assert revisions(client, base) == marker(3)
    error(client.post(rows, json={"values": {"ticket": "A"}}, headers=auth("owner")), 409, "DATASET_UNIQUE_CONFLICT")
    assert revisions(client, base) == marker(3)

    csv = {"dataset_id": data["id"], "schema_revision": 1, "text": "Ticket,Score\nB,4\nC,5\n"}
    call(client, "POST", "/api/datasets/csv/preview", body=csv)
    assert revisions(client, base) == marker(3)
    assert call(client, "POST", "/api/datasets/csv/import", body=csv)["imported"] == 2
    assert revisions(client, base) == marker(4)

    batch = {"schema_revision": 1, "rows": [
        {"id": row["id"], "revision": row["revision"], "values": {"score": 7}},
    ]}
    conflict = client.patch(rows + "/batch", json={**batch, "append": [{"ticket": "B"}]}, headers=auth("owner"))
    error(conflict, 409, "DATASET_BATCH_CONFLICT")
    assert revisions(client, base) == marker(4)
    assert call(client, "GET", row_url) == row
    changed = call(client, "PATCH", rows + "/batch", body={**batch, "append": [{"ticket": "D"}, {"ticket": "E"}]})
    assert revisions(client, base) == marker(5)
    edit, = changed["rows"]
    call(client, "PATCH", rows + "/batch", body={
        "schema_revision": 1,
        "rows": [{"id": edit["id"], "revision": edit["revision"], "values": edit["previous"]}],
        "remove": {item["id"]: item["revision"] for item in changed["added"]},
    })
    assert revisions(client, base) == marker(6)

    # Simulate a schema editor which loaded its definition before another write.
    service = deps.dataset_service()
    stale = service.definition("owner", data["id"])
    call(client, "DELETE", f"{row_url}?revision={edit['revision'] + 1}")
    assert revisions(client, base) == marker(7)
    stale.name = "Renamed"
    service._save("owner", stale, "dataset.update")
    assert revisions(client, base) == marker(8, 2)

    monkeypatch.setenv("STUDIO_ENABLE_DATASET_FORMULAS", "1")
    call(client, "POST", base + "/columns", status=201, body={"revision": 2, "column": {
        "key": "total", "label": "Total", "kind": "number", "formula": {"version": 1, "expression": "[score] * 2"},
    }})
    assert revisions(client, base) == marker(9, 3)
    found = call(client, "POST", rows + "/query", body={"sorts": [{"field": "ticket"}]})["items"]
    assert [(item["values"]["ticket"], item["values"]["total"]) for item in found] == [("B", 8), ("C", 10)]
    call(client, "DELETE", base + "?revision=3")
    error(client.get(base + "/revisions", headers=auth("owner")), 404, "DATASET_NOT_FOUND")
    expected = [(1, i) for i in range(1, 8)] + [(2, 8), (3, 9), None]
    assert live_hub.published == [
        (dataset_changes_channel(data["id"]), {"type": "dataset_changed"}, version) for version in expected
    ]


def test_csv_create_initializes_one_revision_and_one_invalidation(client, live_hub):
    result = call(client, "POST", "/api/datasets/csv/import", body={
        "text": "Ticket\nA\nB\n", "create": {"name": "From CSV", "columns": [{**TICKET, "label": "Ticket"}]},
    })
    assert result["imported"] == 2
    did = result["dataset"]["id"]
    assert revisions(client, f"/api/datasets/{did}") == marker(1)
    assert live_hub.published == [(dataset_changes_channel(did), {"type": "dataset_changed"}, (1, 1))]


def test_connected_receipts_and_no_op_writes(client, live_hub):
    data = dataset(client)
    base = f"/api/datasets/{data['id']}"
    secret = token(client, base, allow_delete=True)["token"]
    first = request("insert_row", operation_id="insert", arguments={"values": {"ticket": "A", "score": 1}})
    response = post(client, base, secret, first)
    assert response.status_code == 200
    rid = response.json()["data"]["row"]["id"]
    assert revisions(client, base) == marker(2)
    assert post(client, base, secret, first).json() == response.json()
    same = request("upsert_row", operation_id="no-op", arguments={"key": "ticket", "values": {"ticket": "A", "score": 1}})
    assert post(client, base, secret, same).status_code == 200
    error(post(client, base, secret, {**first, "arguments": {"values": {"ticket": "B"}}}), 409, "DATASET_RECEIPT_CONFLICT")
    assert revisions(client, base) == marker(2)
    gone = request("delete_row", operation_id="delete", arguments={"row_id": rid})
    assert post(client, base, secret, gone).status_code == 200
    assert post(client, base, secret, gone).status_code == 200
    assert revisions(client, base) == marker(3)
    assert [event[2] for event in live_hub.published] == [(1, 1), (1, 2), (1, 3)]


def test_revision_migration_preserves_dataset_and_rows(client, db):
    data = dataset(client)
    base = f"/api/datasets/{data['id']}"
    row = insert(client, base + "/rows", ticket="Before migration")
    cfg = Config()
    cfg.set_main_option("script_location", MIGRATIONS_DIR)
    with db.engine.begin() as connection:
        cfg.attributes["connection"] = connection
        command.downgrade(cfg, "0072_dataset_formulas")
    db.migrate()
    assert call(client, "GET", base) == data
    assert call(client, "GET", f"{base}/rows/{row['id']}") == row
    assert revisions(client, base) == marker(1)
    insert(client, base + "/rows", ticket="After migration")
    assert revisions(client, base) == marker(2)


def test_socket_visibility_and_revoked_membership(client, db, live_hub):
    data = create(client, name="Team Dataset", team_id="support",
                  columns=[{**column, "label": column["key"].title()} for column in (TICKET, SCORE, ACTIVE)])
    base = f"/api/datasets/{data['id']}"
    path = f"/ws/datasets/{data['id']}/changes"
    outsider = socket_headers("other")
    foreign_origin = {**socket_headers(), "origin": "https://foreign.invalid"}
    other_port = {**socket_headers(), "origin": "http://testserver:8899"}
    url_token = auth("owner")["Authorization"].removeprefix("Bearer ")
    pat = call(client, "POST", "/api/me/tokens", body={"name": "Revision reader"})["token"]
    pat_cookie = {**socket_headers(), "cookie": f"{SESSION_COOKIE}={pat}"}
    for target, headers, code in (
        (path, {}, 4401), (path + "?token=" + url_token, {}, 4401),
        (path, outsider, 4403), (path, pat_cookie, 4401), (path, foreign_origin, 4401), (path, other_port, 4401),
    ):
        with pytest.raises(WebSocketDisconnect) as rejected:
            with client.websocket_connect(target, headers=headers) as ws:
                ws.receive_json()
        assert rejected.value.code == code
    error(client.get(base + "/revisions", headers=auth("other")), 404, "DATASET_NOT_FOUND")

    with client.websocket_connect(path, headers=socket_headers("member")) as ws:
        assert ws.receive_json() == {"type": "ready", **marker(1)}
        row = insert(client, base + "/rows", ticket="A", score=8)
        assert ws.receive_json() == {"type": "dataset_changed", **marker(2)}
        assert call(client, "GET", f"{base}/rows/{row['id']}", uid="member") == row
        with db.session() as session:
            session.delete(session.get(TeamMember, ("support", "member")))
            session.commit()
        insert(client, base + "/rows", ticket="B")
        with pytest.raises(WebSocketDisconnect) as closed:
            ws.receive_json()
        assert closed.value.code == 4403
    assert dataset_changes_channel(data["id"]) not in live_hub._subs
    error(client.get(base + "/revisions", headers=auth("member")), 404, "DATASET_NOT_FOUND")


def test_heartbeat_rechecks_password_revocation(client, db, live_hub, monkeypatch):
    monkeypatch.setattr(dataset_ws, "HEARTBEAT_SECONDS", 0.025)
    data = dataset(client)
    with client.websocket_connect(f"/ws/datasets/{data['id']}/changes", headers=socket_headers()) as ws:
        assert ws.receive_json() == {"type": "ready", **marker(1)}
        assert ws.receive_json() == {"type": "ping"}
        with db.session() as session:
            session.get(User, "owner").password_changed = time() + 2
            session.commit()
        with pytest.raises(WebSocketDisconnect) as closed:
            while ws.receive_json() == {"type": "ping"}:
                pass
        assert closed.value.code == 4401


def test_missed_notification_can_be_recovered_on_reconnect(client, live_hub, monkeypatch):
    data = dataset(client)
    base = f"/api/datasets/{data['id']}"
    path = f"/ws/datasets/{data['id']}/changes"
    with client.websocket_connect(path, headers=socket_headers()) as ws:
        assert ws.receive_json() == {"type": "ready", **marker(1)}

    def fail_publish(*args):
        raise OSError("notification hub unavailable")

    monkeypatch.setattr(live_hub, "publish", fail_publish)
    row = insert(client, base + "/rows", ticket="Recovered")
    assert revisions(client, base) == marker(2)
    with client.websocket_connect(path, headers=socket_headers()) as ws:
        assert ws.receive_json() == {"type": "ready", **marker(2)}
        assert call(client, "GET", f"{base}/rows/{row['id']}") == row


def test_slow_socket_releases_subscription(client, live_hub, monkeypatch):
    send_json = WebSocket.send_json

    async def stalled(ws, message, mode="text"):
        if message.get("type") == "dataset_changed":
            await asyncio.Event().wait()
        else:
            await send_json(ws, message, mode=mode)

    monkeypatch.setattr(dataset_ws, "SEND_TIMEOUT_SECONDS", 0.05)
    monkeypatch.setattr(WebSocket, "send_json", stalled)
    data = dataset(client)
    with client.websocket_connect(f"/ws/datasets/{data['id']}/changes", headers=socket_headers()) as ws:
        assert ws.receive_json() == {"type": "ready", **marker(1)}
        insert(client, f"/api/datasets/{data['id']}/rows", ticket="A")
        with pytest.raises(WebSocketDisconnect) as closed:
            ws.receive_json()
        assert closed.value.code == 1011
    assert dataset_changes_channel(data["id"]) not in live_hub._subs


def test_memory_hub_keeps_only_latest_pending_invalidation():
    async def exercise():
        hub = InMemoryNotificationHub()
        topic = dataset_changes_channel("demo")
        async with hub.subscribe(topic, max_pending=1) as feed:
            for number in range(20):
                hub.publish(topic, {"number": number})
            await asyncio.sleep(0)
            assert await anext(feed) == {"number": 19}
        assert not hub._subs

    asyncio.run(exercise())


@pytest.mark.skipif(not os.environ.get("REDIS_URL"), reason="needs REDIS_URL")
def test_commit_from_another_process_reaches_socket(client, db):
    data = dataset(client)
    did = data["id"]
    with client.websocket_connect(f"/ws/datasets/{did}/changes", headers=socket_headers()) as ws:
        assert ws.receive_json() == {"type": "ready", **marker(1)}
        script = """
import sys
from app.api.deps import dataset_row_service
dataset_row_service().save("owner", sys.argv[1], schema_revision=1, values={"ticket": "Worker"})
"""
        env = {**os.environ, "DATABASE_URL": db.engine.url.render_as_string(hide_password=False)}
        subprocess.run([sys.executable, "-c", script, did], env=env, check=True, timeout=20)
        assert ws.receive_json() == {"type": "dataset_changed", **marker(2)}
        found = call(client, "POST", f"/api/datasets/{did}/rows/query", body={})
        assert [item["values"]["ticket"] for item in found["items"]] == ["Worker"]
