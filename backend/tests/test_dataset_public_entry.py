import asyncio
from time import time

from app.api import deps
from app.models import Run
from test_agent_node import call as tool_call
from test_agent_node import script, wf
from test_dataset_rows import call
from test_dataset_runtime import assert_error, dataset_fixture, dataset_node, final, grant, graph, run, save
from test_datasets import client  # noqa: F401
from test_identity_migration import db  # noqa: F401


def execute(source, request, *, run_id=None):
    svc = deps.run_service()
    plan = svc.plan("owner", request)
    plan.source = source
    if run_id:
        plan.run_id = run_id
    events = []

    async def send(event):
        events.append(event)
        return True

    async def listen():
        await asyncio.Future()

    return asyncio.run(svc.execute(plan, send, listen, "owner")), events


def tickets(client, did):
    return sorted(item["values"]["ticket"] for item in call(client, "POST", f"/api/datasets/{did}/rows/query", body={})["items"])


def workflows(client, did):
    finder = save(client, graph("Find", dataset_node(did, "find_rows", {
        "filters": [{"field": "ticket", "op": "eq", "value": "{{state.ticket}}"}], "limit": 1})))
    upserter = save(client, graph("Upsert", dataset_node(did, "upsert_row", {
        "key": "ticket", "values": {"ticket": "{{state.ticket}}", "score": "{{state.score}}"}}, ["ticket", "score"])))
    deleter = save(client, graph("Delete", dataset_node(did, "delete_row", {"key": "ticket", "value": "{{state.ticket}}"})))
    grant(client, did, finder, "read")
    grant(client, did, upserter, "write")
    grant(client, did, deleter, "read_write", allow_delete=True)
    return finder, upserter, deleter


def test_public_entries_find_and_upsert_under_the_grant_but_never_delete(client):
    did = dataset_fixture(client)
    finder, upserter, deleter = workflows(client, did)
    for source in ("chat", "api"):
        ticket = f"{source}-ticket"
        status, events = execute(source, {"workflow_id": upserter, "input": {"ticket": ticket, "score": 3}})
        assert status == "ok" and final(events)["inserted"] is True
        status, events = execute(source, {"workflow_id": finder, "input": {"ticket": ticket}})
        assert status == "ok" and [item["values"] for item in final(events)["items"]] == [{"ticket": ticket}]
        status, events = execute(source, {"workflow_id": deleter, "input": {"ticket": ticket}})
        assert status == "error"
        assert_error(events, "DATASET_GRANT_DENIED")
    assert tickets(client, did) == ["api-ticket", "chat-ticket"]

    status, events = execute("api", {"workflow_id": finder, "input": {"ticket": "x"}})
    assert status == "ok"
    no_grant = save(client, graph("Ungranted", dataset_node(did, "find_rows", {})))
    status, events = execute("chat", {"workflow_id": no_grant})
    assert status == "error"
    assert_error(events, "DATASET_GRANT_DENIED")
    status, events = execute("chat", {"workflow": graph("Unsaved", dataset_node(did, "find_rows", {}))})
    assert status == "error"
    assert_error(events, "DATASET_GRANT_DENIED")

    for source in ("ui", "schedule"):
        ticket = f"{source}-ticket"
        call(client, "POST", f"/api/datasets/{did}/rows", body={"values": {"ticket": ticket}}, status=201)
        status, events = execute(source, {"workflow_id": deleter, "input": {"ticket": ticket}})
        assert status == "ok" and final(events)["deleted"] is True
    assert tickets(client, did) == ["api-ticket", "chat-ticket"]


def test_demo_mode_denies_every_dataset_operation(client, monkeypatch):
    did = dataset_fixture(client)
    call(client, "POST", f"/api/datasets/{did}/rows", body={"values": {"ticket": "A"}}, status=201)
    finder, upserter, deleter = workflows(client, did)
    monkeypatch.setenv("STUDIO_DEMO_MODE", "true")
    for wid in (finder, upserter, deleter):
        for source in ("ui", "schedule", "chat"):
            status, events = execute(source, {"workflow_id": wid, "input": {"ticket": "A", "score": 1}})
            assert status == "error", (wid, source)
            assert_error(events, "DATASET_GRANT_DENIED")
    assert tickets(client, did) == ["A"]


def test_workflow_tool_child_follows_its_top_run_entry(client, db):
    did = dataset_fixture(client)
    _, _, deleter = workflows(client, did)
    call(client, "POST", f"/api/datasets/{did}/rows", body={"values": {"ticket": "Nested"}}, status=201)
    for top_source, expected in (("chat", "error"), ("ui", "ok")):
        parent, child = f"top-{top_source}", f"child-{top_source}"
        with db.session() as session:
            session.add(Run(id=parent, workflow_id=deleter, status="waiting", owner="owner", source=top_source, started=time()))
            session.add(Run(id=child, workflow_id=deleter, status="queued", owner="owner", source="tool",
                            parent_run_id=parent, started=time()))
            session.commit()
        status, events = execute("tool", {"workflow_id": deleter, "input": {"ticket": "Nested"}}, run_id=child)
        assert status == expected, events
        if expected == "error":
            assert_error(events, "DATASET_GRANT_DENIED")
            assert tickets(client, did) == ["Nested"]
    assert tickets(client, did) == []


def test_public_run_resumes_without_a_grant_removed_while_it_waited(client, db):
    did = dataset_fixture(client)
    call(client, "POST", f"/api/datasets/{did}/rows", body={"values": {"ticket": "A"}}, status=201)
    wid = save(client, graph("Waiting upsert", dataset_node(did, "upsert_row", {
        "key": "ticket", "values": {"ticket": "{{state.ticket}}"}}), waiting=True))
    grant(client, did, wid, "write")

    def paused_chat_run():
        events = run(client, {"workflow_id": wid, "input": {"ticket": "Resumed"}})
        assert events[-1]["status"] == "waiting"
        with db.session() as session:
            session.get(Run, events[0]["run_id"]).source = "chat"
            session.commit()
        return events[0]["run_id"]

    rid = paused_chat_run()
    assert final(run(client, {"resume_run_id": rid, "response": "yes"}))["inserted"] is True
    rid = paused_chat_run()
    call(client, "DELETE", f"/api/datasets/{did}/access/grants/{wid}")
    assert_error(run(client, {"resume_run_id": rid, "response": "yes"}), "DATASET_GRANT_DENIED")
    assert tickets(client, did) == ["A", "Resumed"]


def test_agent_write_follows_the_same_entry_rule(client, monkeypatch):
    did = dataset_fixture(client)
    tool = {"name": "file_ticket", "source": "dataset", "dataset_id": did, "operations": ["upsert_row"],
            "fields": ["ticket"], "write_fields": ["ticket"], "key": "ticket", "filter_ops": {}, "limit": 1}
    wid = save(client, wf(tools=[tool], steps_field="steps"))
    grant(client, did, wid, "write")
    script(monkeypatch, [("", [tool_call(tool["name"], {"operation": "upsert_row", "values": {"ticket": "From chat"}})]),
                         ("Finished", [])])
    status, events = execute("chat", {"workflow_id": wid})
    steps = next(event for event in events if event["type"] == "run_finished")["state"]["steps"]
    assert status == "ok" and steps[0]["status"] == "ok"
    assert tickets(client, did) == ["From chat"]
    grant(client, did, wid, "read")
    script(monkeypatch, [("", [tool_call(tool["name"], {"operation": "upsert_row", "values": {"ticket": "Denied"}})]),
                         ("Finished", [])])
    status, events = execute("chat", {"workflow_id": wid})
    steps = next(event for event in events if event["type"] == "run_finished")["state"]["steps"]
    assert steps[0]["status"] == "error"
    assert tickets(client, did) == ["From chat"]


def test_api_trigger_upserts_and_finds_but_cannot_delete(client):
    from fastapi.testclient import TestClient
    from app.main import app
    from test_datasets import auth
    did = dataset_fixture(client)
    finder, upserter, deleter = workflows(client, did)
    with TestClient(app) as live:  # the lifespan starts the in-process worker that runs triggered jobs
        def trigger(wid, payload):
            secret = live.post(f"/api/workflows/{wid}/tokens", json={"name": "ci"}, headers=auth("owner")).json()["data"]["token"]
            response = live.post(f"/api/hooks/workflows/{wid}/runs", json={"input": payload, "mode": "sync"},
                                 headers={"Authorization": f"Bearer {secret}"})
            assert response.status_code == 200, response.text
            return response.json()["data"]

        upserted = trigger(upserter, {"ticket": "API", "score": 2})
        assert upserted["status"] == "ok" and upserted["final_state"]["result"]["inserted"] is True
        found = trigger(finder, {"ticket": "API"})
        assert found["status"] == "ok" and found["final_state"]["result"]["items"][0]["values"] == {"ticket": "API"}
        denied = trigger(deleter, {"ticket": "API"})
        assert denied["status"] == "error" and "DATASET_GRANT_DENIED" in str(denied)
    assert tickets(client, did) == ["API"]
