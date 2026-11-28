import csv
import io

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.core import config, security
from app.core.errors import AppError
from app.main import create_app
from app.models.database import Database
from app.services import demo_dataset, demo_service, seed


def _data(response, status=200):
    assert response.status_code == status, response.text
    return response.json()["data"]


def _auth(uid, email):
    return {"Authorization": f"Bearer {security.make_token(uid, email)}"}


def test_demo_dataset_is_readable_but_immutable_for_old_and_new_visitors(tmp_path, monkeypatch):
    db = Database(f"sqlite:///{tmp_path}/demo-dataset.db")
    monkeypatch.setattr(deps, "get_db", lambda: db)
    monkeypatch.setattr("app.main.get_db", lambda: db)
    monkeypatch.setenv("STUDIO_DEMO_MODE", "false")
    seed.bootstrap(db)
    admin = _auth("admin", config.DEMO_EMAIL)
    path = f"/api/datasets/{demo_dataset.DATASET_ID}"

    with TestClient(create_app(), base_url="https://testserver") as studio:
        assert _data(studio.get("/api/datasets", headers=admin))["items"] == []
        private = _data(studio.post("/api/datasets", headers=admin, json={"name": "Private"}), 201)
    old_visitor = demo_service.start_visit(db)

    monkeypatch.setenv("STUDIO_DEMO_MODE", "true")
    with TestClient(create_app(), base_url="https://testserver") as client:
        sample = _data(client.get(path, headers=admin))
        first_page = _data(client.post(f"{path}/rows/query", headers=admin, json={"limit": 10}))
        assert first_page["total"] == 125
        assert first_page["next_offset"] == 10
        assert first_page["items"][0]["values"]["ticket_id"] == 1
        seed.bootstrap(db)
        assert _data(client.post(f"{path}/rows/query", headers=admin, json={"limit": 10})) == first_page

        for visitor in (_auth(old_visitor, "visitor@example.org"), None):
            if visitor is None:
                login = _data(client.post("/api/auth/login", json=demo_service.options()))
                assert login["user"]["role"] == "viewer"
                visitor = {"Authorization": f"Bearer {login['token']}"}
            listed = _data(client.get("/api/datasets", headers=visitor))
            assert [item["id"] for item in listed["items"]] == [sample["id"]]
            assert _data(client.get(path, headers=visitor)) == sample
            exported = client.get(f"{path}/csv", headers=visitor)
            assert exported.status_code == 200
            assert len(list(csv.DictReader(io.StringIO(exported.text)))) == 125
            hidden = client.post(f"/api/datasets/{private['id']}/rows/query", json={}, headers=visitor)
            assert hidden.status_code == 404 and hidden.json()["error"]["code"] == "DATASET_NOT_FOUND"

            result = _data(client.post(f"{path}/rows/query", headers=visitor, json={
                "filters": [{"field": "status", "op": "eq", "value": "Open"}],
                "sort": "ticket_id", "descending": True, "limit": 10,
            }))
            assert result["total"] == 42
            assert [row["values"]["ticket_id"] for row in result["items"][:2]] == [124, 121]
            summary = _data(client.post(f"{path}/rows/summary", headers=visitor, json={
                "summaries": {"priority": "sum"},
            }))
            assert summary["total"] == 125 and summary["values"]["priority"] == 375
            groups = _data(client.post(f"{path}/rows/groups", headers=visitor, json={"group_by": "team"}))
            assert len(groups["groups"]) == 3
            team_rows = _data(client.post(f"{path}/rows/groups/query", headers=visitor, json={
                "group_by": "team", "group": "Support",
            }))
            assert team_rows["items"] and all(row["values"]["team"] == "Support" for row in team_rows["items"])

            for method, endpoint, body in (
                ("POST", f"{path}/rows", {"values": {"subject": "Should fail"}}),
                ("PUT", path, {"name": "Should fail", "revision": sample["revision"]}),
            ):
                response = client.request(method, endpoint, json=body, headers=visitor)
                assert response.status_code == 403 and response.json()["error"]["code"] == "DEMO_READ_ONLY"

    with pytest.raises(AppError) as error:
        deps.dataset_access_service().for_workflow(old_visitor, "example", sample["id"], "read", demo=True)
    assert error.value.code == "DATASET_GRANT_DENIED"


def test_demo_boot_uses_active_admin_after_development_account_is_disabled(tmp_path, monkeypatch):
    from app.repositories import UserRepository
    from app.repositories.datasets import DatasetRepository

    db = Database(f"sqlite:///{tmp_path}/demo-upgrade.db")
    monkeypatch.setenv("STUDIO_DEMO_MODE", "false")
    seed.bootstrap(db)

    monkeypatch.setattr(config, "IS_PROD", True)
    monkeypatch.setenv("STUDIO_ADMIN_EMAILS", "operator@example.org")
    monkeypatch.setenv("STUDIO_ADMIN_PASSWORD", "demo-test-1234")
    monkeypatch.setenv("STUDIO_DEMO_MODE", "true")
    seed.bootstrap(db)
    users = UserRepository(db)
    assert not users.get_by_email(config.DEMO_EMAIL).active
    operator = users.get_by_email("operator@example.org")
    dataset = DatasetRepository(db).get(operator.id, demo_dataset.DATASET_ID)
    assert dataset is not None and dataset.team_owner_id == operator.id
