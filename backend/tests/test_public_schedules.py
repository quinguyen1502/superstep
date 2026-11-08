"""Public schedule routes (TASK-0278): a workflow token manages schedules of its own workflow."""
import uuid
from fastapi.testclient import TestClient
from app.main import app


def H(token): return {"X-Workflow-Token": token}


def test_a_workflow_token_manages_its_schedules():
    with TestClient(app) as client:
        jwt = client.post("/api/auth/register", json={"email": f"ps{uuid.uuid4().hex[:6]}@example.com", "password": "secret12"}).json()["data"]["token"]
        auth = {"Authorization": f"Bearer {jwt}"}
        workflows = client.get("/api/workflows", headers=auth).json()["data"]
        wid = workflows[0]["id"]
        other = client.post("/api/workflows", json={"name": "Other"}, headers=auth).json()["data"]["id"]
        token = client.post(f"/api/workflows/{wid}/tokens", json={"name": "schedules"}, headers=auth).json()["data"]["token"]
        other_token = client.post(f"/api/workflows/{other}/tokens", json={"name": "other"}, headers=auth).json()["data"]["token"]

        denied = client.get(f"/api/hooks/workflows/{wid}/schedules")
        assert denied.status_code == 401 and denied.json()["error"]["code"] == "TRIGGER_TOKEN_INVALID"
        assert client.get(f"/api/hooks/workflows/{wid}/schedules", headers=H(other_token)).json()["error"]["code"] == "TRIGGER_TOKEN_INVALID"

        bad = client.post(f"/api/hooks/workflows/{wid}/schedules", json={"cron": "61 * * * *"}, headers=H(token))
        assert bad.status_code == 400 and bad.json()["error"]["code"] == "SCHEDULE_CRON_INVALID"

        created = client.post(f"/api/hooks/workflows/{wid}/schedules",
                              json={"name": "Morning", "cron": "0 9 * * MON-FRI", "timezone": "Asia/Ho_Chi_Minh", "input": {"message": "hi"}},
                              headers=H(token))
        assert created.status_code == 201
        schedule = created.json()["data"]
        assert schedule["enabled"] is True and schedule["input"] == {"message": "hi"} and schedule["next_runs"]

        studio = client.get(f"/api/workflows/{wid}/schedules", headers=auth).json()["data"]
        assert [item["id"] for item in studio] == [schedule["id"]]

        off = client.patch(f"/api/hooks/workflows/{wid}/schedules/{schedule['id']}", json={"enabled": False}, headers=H(token)).json()["data"]
        assert off["enabled"] is False and off["next_runs"] == []
        missing = client.patch(f"/api/hooks/workflows/{wid}/schedules/missing", json={"enabled": True}, headers=H(token))
        assert missing.status_code == 404 and missing.json()["error"]["code"] == "SCHEDULE_NOT_FOUND"

        preview = client.post(f"/api/hooks/workflows/{wid}/schedules/preview", json={"cron": "@daily", "timezone": "UTC"}, headers=H(token)).json()["data"]
        assert preview["next_runs"] and client.get(f"/api/hooks/workflows/{wid}/schedules", headers=H(token)).json()["data"][0]["id"] == schedule["id"]

        assert client.delete(f"/api/hooks/workflows/{wid}/schedules/{schedule['id']}", headers=H(token)).json()["data"] == {"ok": True}
        assert client.get(f"/api/hooks/workflows/{wid}/schedules", headers=H(token)).json()["data"] == []
