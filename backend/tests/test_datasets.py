from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api import deps
from app.core.security import make_token
from app.main import app
from app.models import AuditEvent, Dataset, DatasetColumn, Team, TeamMember, User
from app.repositories.teams import TeamRepository
from app.repositories.user_data import UserDataRepository
from test_identity_migration import db, upgrade  # noqa: F401


@pytest.fixture
def client(db, monkeypatch):
    upgrade(db, "0062_usage_budgets")
    with db.session() as session:
        session.add_all([
            User(id=uid, email=f"{uid}@example.com", role=role)
            for uid, role in (("owner", "editor"), ("member", "viewer"), ("other", "editor"))
        ])
        session.add(Team(id="support", name="Support", created=1, created_by="owner"))
        session.commit()
        session.add_all([
            TeamMember(team_id="support", user_id=uid, added=1)
            for uid in ("owner", "member")
        ])
        session.commit()
    db.migrate()
    monkeypatch.setattr(deps, "get_db", lambda: db)
    return TestClient(app)


def auth(uid):
    return {"Authorization": f"Bearer {make_token(uid, f'{uid}@example.com')}"}


def error(response, status, code):
    assert response.status_code == status, response.text
    assert response.json()["error"]["code"] == code


def create(client, **payload):
    response = client.post("/api/datasets", json=payload, headers=auth("owner"))
    assert response.status_code == 201, response.text
    return response.json()["data"]


def test_dataset_visibility_and_lifecycle(client, db):
    private = create(client, name="Tickets", columns=[{"key": "subject", "label": "Subject", "kind": "text"}])
    shared = create(client, name="Tickets", team_id="support",
                    columns=[{"key": "email", "label": "Email", "kind": "email"}])
    personal_url = f"/api/datasets/{private['id']}"
    team_url = f"/api/datasets/{shared['id']}"
    error(client.get(personal_url), 401, "AUTH_REQUIRED")
    error(client.get(personal_url, headers=auth("member")), 404, "DATASET_NOT_FOUND")
    error(client.get(team_url, headers=auth("other")), 404, "DATASET_NOT_FOUND")
    assert client.get("/api/datasets", headers=auth("other")).json()["data"]["items"] == []
    assert client.get(team_url, headers=auth("member")).json()["data"] == shared
    error(client.put(team_url, headers=auth("member"), json={"name": "New", "revision": 1}),
          403, "PERMISSION_DENIED")
    error(client.post("/api/datasets", headers=auth("other"), json={"name": "Guess", "team_id": "support"}),
          404, "DATASET_NOT_FOUND")
    page = client.get("/api/datasets?limit=1", headers=auth("owner")).json()["data"]
    assert len(page["items"]) == 1 and page["next_offset"] == 1
    error(client.post("/api/datasets", headers=auth("owner"), json={"name": " tickets "}),
          409, "DATASET_NAME_TAKEN")
    renamed = client.put(personal_url, headers=auth("owner"), json={"name": "Incidents", "revision": 1})
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["data"]["revision"] == 2
    assert client.delete(f"{personal_url}?revision=2", headers=auth("owner")).status_code == 200
    TeamRepository(db).delete("support")
    with db.session() as session:
        assert list(session.scalars(select(Dataset))) == []
        assert list(session.scalars(select(DatasetColumn))) == []
        audit = list(session.scalars(select(AuditEvent).where(AuditEvent.target_id == private["id"]).order_by(AuditEvent.ts)))
        assert [event.action for event in audit] == ["dataset.create", "dataset.update", "dataset.delete"]
        assert all(event.target_label is None and event.details is None for event in audit)


def test_dataset_schema_types_and_revisions(client):
    columns = [
        {"key": "label", "label": "Label", "kind": "text", "default": ""},
        {"key": "count", "label": "Count", "kind": "number", "default": 0},
        {"key": "done", "label": "Done", "kind": "boolean", "default": False},
        {"key": "day", "label": "Day", "kind": "date", "default": "2024-02-29"},
        {"key": "at", "label": "At", "kind": "datetime", "default": "2024-02-29T01:00:00+01:00"},
        {"key": "email", "label": "Email", "kind": "email", "unique": True, "default": " A@Example.COM "},
        {"key": "status", "label": "Status", "kind": "select", "options": ["Open", "Closed"], "default": "Open"},
    ]
    created = create(client, name="Typed", columns=columns)
    defaults = [column["default"] for column in created["columns"]]
    assert defaults == ["", 0, False, "2024-02-29", "2024-02-29T00:00:00.000Z", "a@example.com", "Open"]
    assert defaults[2] is False
    url = f"/api/datasets/{created['id']}/columns"
    headers = auth("owner")
    error(client.post(url, headers=headers, json={"revision": 1, "column": columns[0]}),
          409, "DATASET_COLUMN_KEY_TAKEN")
    error(client.post(url, headers=headers, json={
        "revision": 1, "column": {"key": "invalid", "label": "Invalid", "kind": "number", "default": True},
    }), 400, "DATASET_VALUE_INVALID")
    status = {**columns[-1], "label": "State", "options": ["Open", "Closed", "Waiting"]}
    edited = client.put(f"{url}/status", headers=headers, json={"revision": 1, "column": status})
    assert edited.status_code == 200, edited.text
    assert edited.json()["data"]["columns"][-1]["label"] == "State"
    assert edited.json()["data"]["columns"][-1]["key"] == "status"
    error(client.put(f"{url}/status", headers=headers, json={"revision": 1, "column": status}),
          409, "DATASET_SCHEMA_CONFLICT")
    error(client.put(f"{url}/status", headers=headers, json={
        "revision": 2, "column": {**status, "options": ["Open", "Waiting"]},
    }), 409, "DATASET_SCHEMA_INCOMPATIBLE")
    assert client.delete(f"{url}/status?revision=2", headers=headers).status_code == 200
    error(client.post(url, headers=headers, json={"revision": 3, "column": status}),
          409, "DATASET_COLUMN_KEY_TAKEN")
    added = client.post(url, headers=headers, json={
        "revision": 3, "column": {"key": "notes", "label": "Notes", "kind": "text"},
    })
    assert added.status_code == 201, added.text
    assert [column["key"] for column in added.json()["data"]["columns"]][-1] == "notes"


def test_concurrent_schema_updates_and_account_cleanup(client, db):
    personal = create(client, name="Concurrent", columns=[{"key": "key", "label": "Key", "kind": "text"}])
    shared = create(client, name="Shared", team_id="support")

    def rename(name):
        return client.put(f"/api/datasets/{personal['id']}", headers=auth("owner"),
                          json={"name": name, "revision": 1})

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(rename, ["First", "Second"]))
    assert sorted(response.status_code for response in responses) == [200, 409]
    UserDataRepository(db).purge("owner", runs=False)
    with db.session() as session:
        assert list(session.scalars(select(Dataset.id))) == [shared["id"]]
        assert list(session.scalars(select(DatasetColumn))) == []
