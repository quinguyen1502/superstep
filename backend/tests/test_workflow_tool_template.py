"""The "Support team" template (TASK-0137, REQ-0073): using it creates the supervisor and its two specialist workflows,
and its test cases pass with the offline mock, child runs included (test rules, the "tool called" check)."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.api.deps import run_service
from tests.test_workflow_tests import H, run_all, user, by_name


@pytest.fixture(scope="module")
def c():
    with TestClient(app) as client: yield client  # lifespan: the worker that runs test runs and their child runs


@pytest.fixture(autouse=True)
def no_key(monkeypatch):
    for k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY"): monkeypatch.delenv(k, raising=False)


def test_the_support_team_template_creates_its_desks_and_its_tests_pass(c):
    u = user(c)
    made = c.post("/api/templates/builtin-support-team/use", json={"name": "My team"}, headers=H(u["token"])).json()["data"]
    assert made["errors"] == []
    names = {w["name"]: w["id"] for w in c.get("/api/workflows", headers=H(u["token"])).json()["data"]}
    assert {"My team", "My team · Order desk", "My team · Refund desk"} <= set(names)
    wf = c.get(f"/api/workflows/{made['id']}", headers=H(u["token"])).json()["data"]
    tools = next(n for n in wf["nodes"] if n["id"] == "agent")["data"]["tools"]
    assert [(t["name"], t["workflow_id"]) for t in tools] == [("order_desk", names["My team · Order desk"]), ("refund_desk", names["My team · Refund desk"])]
    assert all("helper" not in t for t in tools)
    suite = run_all(c, u, made["id"], mock=True)
    results = by_name(suite)
    assert results["Order questions go to the order desk"]["status"] == "passed", results
    assert results["Refund requests go to the refund desk"]["status"] == "passed", results
    # the refund desk's approval was not sent anywhere: the test cancelled it, and nobody's inbox lists it
    assert c.get("/api/approvals/inbox", headers=H(u["token"])).json()["data"] == []
    refund_runs = run_service().runs.list_for_workflow(names["My team · Refund desk"])
    assert refund_runs and all(r.status == "cancelled" and r.source == "tool" for r in refund_runs)
