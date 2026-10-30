"""GET and list report the latest version. version and updated are not stored in the graph (TASK-0168)."""
import json
import uuid

from fastapi.testclient import TestClient

from app.main import app


def test_version_and_updated_are_response_fields_only():
    with TestClient(app) as client:
        token = client.post("/api/auth/register", json={"email": f"v{uuid.uuid4().hex[:8]}@example.com", "password": "secret12"}).json()["data"]["token"]
        headers = {"Authorization": f"Bearer {token}"}
        listed = client.get("/api/workflows", headers=headers).json()["data"]
        wid = listed[0]["id"]
        assert listed[0]["version"] == 1 and "updated" in listed[0]

        got = client.get(f"/api/workflows/{wid}", headers=headers).json()["data"]
        assert got["version"] == 1 and isinstance(got["updated"], (int, float))

        from app.api.deps import get_db
        from app.repositories import WorkflowRepository, WorkflowVersionRepository
        repo = WorkflowRepository(get_db())
        before = json.loads(repo.get(wid).data)
        assert "version" not in before and "updated" not in before
        saved = client.post("/api/workflows", json={**got, "version": 99, "updated": 123.0}, headers=headers)
        assert saved.status_code == 200, saved.text
        after = json.loads(repo.get(wid).data)
        assert after == before and "version" not in after and "updated" not in after
        again = client.get(f"/api/workflows/{wid}", headers=headers).json()["data"]
        assert again["version"] == 1 and again["updated"] != 123.0
        assert [item["version"] for item in client.get(f"/api/workflows/{wid}/versions", headers=headers).json()["data"]["items"]] == [1]

        repo.save("nover", "No version", json.dumps({"name": "No version", "nodes": [], "edges": [], "state": []}), 42.0, repo.get(wid).owner)
        assert WorkflowVersionRepository(get_db()).latest("nover") is None
        bare = client.get("/api/workflows/nover", headers=headers).json()["data"]
        assert bare["version"] == 0 and bare["updated"] == 42.0 and bare["name"] == "No version"
        row = next(item for item in client.get("/api/workflows", headers=headers).json()["data"] if item["id"] == "nover")
        assert row["version"] == 0 and row["updated"] == 42.0
