import asyncio
import json
from time import time
from copy import deepcopy

from sqlalchemy import select

from app.api import deps
from app.models import AuditEvent
from test_dataset_rows import call
from test_datasets import auth, client, create, error  # noqa: F401
from test_identity_migration import db  # noqa: F401


def graph(name, node, *, waiting=False):
    nodes = [{"id": "start", "type": "start", "data": {}}, node, {"id": "end", "type": "end", "data": {}}]
    if waiting:
        nodes.insert(1, {"id": "approval", "type": "human", "data": {"prompt": "Proceed?", "output_field": "answer"}})
    state = [{"name": "ticket", "type": "string"}, {"name": "score", "type": "number"}, {"name": "done", "type": "boolean"},
             {"name": "answer", "type": "string"}, {"name": "result", "type": "object"}]
    return {"name": name, "state": state, "nodes": nodes,
            "edges": [{"id": f"edge-{i}", "source": a["id"], "target": b["id"]} for i, (a, b) in enumerate(zip(nodes, nodes[1:]))]}


def dataset_node(did, operation, arguments, fields=None):
    return {"id": "dataset", "type": "dataset", "data": {
        "dataset_id": did, "operation": operation, "arguments": arguments, "fields": fields or ["ticket"],
        "output_field": "result",
    }}


def dataset_fixture(client):
    result = create(client, name="Runtime data", columns=[
        {"key": "ticket", "label": "Ticket", "kind": "text", "unique": True, "required": True},
        {"key": "score", "label": "Score", "kind": "number"},
        {"key": "done", "label": "Done", "kind": "boolean"},
    ])
    return result["id"]


def save(client, workflow):
    result = call(client, "POST", "/api/workflows", body=workflow)
    assert result["errors"] == [], result["errors"]
    return result["id"]


def grant(client, did, wid, permission, allow_delete=False):
    call(client, "PUT", f"/api/datasets/{did}/access/grants/{wid}", body={"permission": permission, "allow_delete": allow_delete})


def run(client, request, uid="owner"):
    token = auth(uid)["Authorization"].removeprefix("Bearer ")
    with client.websocket_connect(f"/ws/run?token={token}") as socket:
        socket.send_json(request)
        events = [socket.receive_json()]
        while events[-1]["type"] != "run_summary" and not (len(events) == 1 and events[-1]["type"] == "error"):
            events.append(socket.receive_json())
        return events


def final(events):
    assert events[-1]["status"] == "ok", events
    return next(event["state"]["result"] for event in reversed(events) if event["type"] == "run_finished")


def assert_error(events, code):
    assert any(event.get("error", {}).get("code") == code for event in events), events


def test_dataset_runtime_write_lookup_permissions_and_dry_run(client):
    did = dataset_fixture(client)
    writer = save(client, graph("Write", dataset_node(did, "upsert_row", {
        "key": "ticket", "values": {"ticket": "{{state.ticket}}", "score": "{{state.score}}", "done": "{{state.done}}"},
    }, ["ticket", "score", "done"])))
    args = {"workflow_id": writer, "input": {"ticket": "A", "score": 0, "done": False}}
    assert_error(run(client, args), "DATASET_GRANT_DENIED")
    grant(client, did, writer, "write")
    output = final(run(client, args))
    assert output["inserted"] is True
    assert output["row"]["values"] == {"ticket": "A", "score": 0, "done": False}
    row_id = output["row"]["id"]
    output = final(run(client, {**args, "input": {"ticket": "A", "score": 2, "done": True}}))
    assert output["inserted"] is False and output["row"]["id"] == row_id

    reader = save(client, graph("Read", dataset_node(did, "find_rows", {
        "filters": [{"field": "ticket", "op": "eq", "value": "{{state.ticket}}"}], "limit": 1,
    })))
    grant(client, did, reader, "read")
    output = final(run(client, {"workflow_id": reader, "input": {"ticket": "A"}}))
    assert len(output["items"]) == 1 and output["items"][0]["values"] == {"ticket": "A"}
    getter = save(client, graph("Get", dataset_node(did, "get_row", {"row_id": row_id}, ["done"])))
    grant(client, did, getter, "read")
    assert final(run(client, {"workflow_id": getter}))["values"] == {"done": True}

    svc = deps.run_service()
    plan = svc.plan("owner", {**args, "input": {"ticket": "Simulation", "score": 0, "done": False}})
    svc.apply_test(plan, {"mock": True})
    events = []
    async def send(event):
        events.append(event)
        return True
    async def listen():
        await asyncio.Future()
    assert asyncio.run(svc.execute(plan, send, listen, "owner")) == "ok"
    assert final(events)["dry_run"] is True

    plan = svc.plan("owner", args)
    plan.source = "api"
    events.clear()
    assert asyncio.run(svc.execute(plan, send, listen, "owner")) == "error"
    assert_error(events, "DATASET_GRANT_DENIED")
    rows = call(client, "POST", f"/api/datasets/{did}/rows/query", body={})
    assert [item["values"]["ticket"] for item in rows["items"]] == ["A"]


def test_workflow_delete_requires_the_separate_capability(client, db):
    did = dataset_fixture(client)
    created = call(client, "POST", f"/api/datasets/{did}/rows", body={"values": {"ticket": "A", "score": 1}}, status=201)
    row_id = created["row"]["id"]
    rows = f"/api/datasets/{did}/rows/query"
    by_id = save(client, graph("Delete id", dataset_node(did, "delete_row", {"row_id": row_id})))
    grant(client, did, by_id, "write")
    assert_error(run(client, {"workflow_id": by_id}), "DATASET_GRANT_DENIED")
    grant(client, did, by_id, "read", allow_delete=True)

    svc = deps.run_service()
    plan = svc.plan("owner", {"workflow_id": by_id})
    svc.apply_test(plan, {"mock": True})
    events = []

    async def send(event):
        events.append(event)
        return True

    async def listen():
        await asyncio.Future()

    assert asyncio.run(svc.execute(plan, send, listen, "owner")) == "ok"
    assert final(events) == {"row_id": row_id, "deleted": True, "dry_run": True}
    assert [item["id"] for item in call(client, "POST", rows, body={})["items"]] == [row_id]

    assert final(run(client, {"workflow_id": by_id})) == {"row_id": row_id, "deleted": True}
    assert call(client, "POST", rows, body={})["items"] == []
    assert_error(run(client, {"workflow_id": by_id}), "DATASET_ROW_NOT_FOUND")

    call(client, "POST", f"/api/datasets/{did}/rows", body={"values": {"ticket": "B"}}, status=201)
    by_key = save(client, graph("Delete key", dataset_node(did, "delete_row", {"key": "ticket", "value": "{{state.ticket}}"})))
    grant(client, did, by_key, "read", allow_delete=True)
    deleted = final(run(client, {"workflow_id": by_key, "input": {"ticket": "B"}}))
    assert deleted["deleted"] is True
    assert call(client, "POST", rows, body={})["items"] == []

    kept = call(client, "POST", f"/api/datasets/{did}/rows", body={"values": {"ticket": "C"}}, status=201)["row"]["id"]
    plan = svc.plan("owner", {"workflow_id": by_key, "input": {"ticket": "C"}})
    plan.source = "api"
    events.clear()
    assert asyncio.run(svc.execute(plan, send, listen, "owner")) == "error"
    assert_error(events, "DATASET_GRANT_DENIED")
    assert [item["id"] for item in call(client, "POST", rows, body={})["items"]] == [kept]

    response = client.post("/api/workflows", headers=auth("owner"), json=graph(
        "Bad key", dataset_node(did, "delete_row", {"key": "score", "value": "1"}),
    ))
    assert response.status_code == 400 and response.json()["error"]["code"] == "DATASET_UPSERT_KEY_INVALID"
    assert [item["id"] for item in call(client, "POST", rows, body={})["items"]] == [kept]

    with db.session() as session:
        audits = list(session.scalars(select(AuditEvent).where(AuditEvent.action == "dataset.row_delete")))
    assert audits and all("A" not in event.details and "B" not in event.details for event in audits)
    assert all(json.loads(event.details)["row_id"] for event in audits)


def test_dataset_nested_scope_and_revocation_before_resume(client):
    did = dataset_fixture(client)
    call(client, "POST", f"/api/datasets/{did}/rows", body={"values": {"ticket": "A"}}, status=201)
    child = save(client, graph("Child", dataset_node(did, "find_rows", {})))
    parent = save(client, graph("Parent", {"id": "sub", "type": "subgraph", "data": {"workflow_id": child}}, waiting=True))
    grant(client, did, parent, "read")
    paused = run(client, {"workflow_id": parent})
    assert paused[-1]["status"] == "waiting"
    assert_error(run(client, {"resume_run_id": paused[0]["run_id"], "response": "yes"}), "DATASET_GRANT_DENIED")

    grant(client, did, child, "read")
    paused = run(client, {"workflow_id": parent})
    result = final(run(client, {"resume_run_id": paused[0]["run_id"], "response": "yes"}))
    assert result["items"][0]["values"] == {"ticket": "A"}

    paused = run(client, {"workflow_id": parent})
    call(client, "DELETE", f"/api/datasets/{did}/access/grants/{child}")
    assert_error(run(client, {"resume_run_id": paused[0]["run_id"], "response": "yes"}), "DATASET_GRANT_DENIED")


def test_dataset_authoring_and_untrusted_scope(client):
    did = dataset_fixture(client)
    node = dataset_node(did, "find_rows", {})
    original = graph("Authorized", node)
    child = save(client, original)
    grant(client, did, child, "read")
    forbidden = client.post("/api/workflows", headers=auth("other"), json=original)
    error(forbidden, 404, "DATASET_NOT_FOUND")

    spoofed = deepcopy(original)
    spoofed["name"] = "Spoofed"
    spoofed["nodes"][1]["data"]["_dataset_workflow"] = child
    wid = save(client, spoofed)
    stored = call(client, "GET", f"/api/workflows/{wid}")
    assert "_dataset_workflow" not in stored["nodes"][1]["data"]
    assert_error(run(client, {"workflow_id": wid, "workflow": spoofed}), "DATASET_GRANT_DENIED")
    assert_error(run(client, {"workflow": original}), "DATASET_GRANT_DENIED")


def test_worker_replays_dataset_write_after_commit_before_progress(client, db, monkeypatch):
    from app.models import Run
    from app.repositories.runs import StaleLease

    did = dataset_fixture(client)
    writer = graph("Scheduled", dataset_node(did, "insert_row", {"values": {"ticket": "{{state.ticket}}"}}))
    wid = save(client, writer)
    grant(client, did, wid, "write")
    svc = deps.run_service()
    request = {"workflow_id": wid, "input": {"ticket": "A"}}
    initial = svc.plan("owner", request)
    original_version = initial.version
    with db.session() as session:
        session.add(Run(id="dataset-worker-replay", workflow_id=wid, status="running", owner="owner",
                        source="schedule", lease_gen=1, started=time(), input='{"ticket":"A"}'))
        session.commit()
    initial.run_id, initial.source, initial.fence, initial.checkpointing = "dataset-worker-replay", "schedule", 1, True
    real_execute = svc.dataset_runtime.execute

    def stop_after_commit(**args):
        real_execute(**args)
        raise StaleLease(args["run_id"])
    monkeypatch.setattr(svc.dataset_runtime, "execute", stop_after_commit)
    events = []
    async def send(event):
        events.append(event)
        return True
    async def listen():
        await asyncio.Future()

    assert asyncio.run(svc.execute(initial, send, listen, "owner")) == "fenced"
    url = f"/api/datasets/{did}/rows/query"
    row = call(client, "POST", url, body={})["items"][0]
    edited = deepcopy(writer)
    edited["id"] = wid
    edited["nodes"][1]["data"]["arguments"]["values"]["ticket"] = "Changed workflow"
    assert save(client, edited) == wid

    stored = svc.runs.get(initial.run_id)
    assert svc.runs.claim(initial.run_id, ("running",)) == 2
    resumed = svc.plan_recover(stored, 2)
    assert resumed.version == original_version
    monkeypatch.setattr(svc.dataset_runtime, "execute", real_execute)
    events.clear()
    assert asyncio.run(svc.execute(resumed, send, listen, "owner")) == "ok"
    assert final(events)["row"]["id"] == row["id"]
    assert call(client, "POST", url, body={})["items"] == [row]


def test_debug_run_keeps_dry_run_after_human_resume(client):
    did = dataset_fixture(client)
    wid = save(client, graph("Debug writer", dataset_node(did, "insert_row", {"values": {"ticket": "Debug"}}), waiting=True))
    grant(client, did, wid, "write")
    paused = run(client, {"workflow_id": wid, "steps": 1})
    assert paused[-1]["status"] == "waiting"
    assert final(run(client, {"resume_run_id": paused[0]["run_id"], "response": "yes"}))["dry_run"] is True
    assert call(client, "POST", f"/api/datasets/{did}/rows/query", body={})["items"] == []


def test_dataset_node_filters_ignore_case_and_ne_matches_empty_cells(client):
    did = dataset_fixture(client)
    for values in ({"ticket": "\u0110\u01a1n-A", "score": 5}, {"ticket": "\u0111\u01a1n-b", "score": 1}, {"ticket": "\u0110\u01a0N-C"}, {"ticket": "Other"}):
        call(client, "POST", f"/api/datasets/{did}/rows", body={"values": values}, status=201)
    reader = save(client, graph("Read", dataset_node(did, "find_rows", {
        "filters": [{"field": "ticket", "op": "contains", "value": "{{state.ticket}}"},
                    {"field": "score", "op": "ne", "value": 5}], "limit": 10,
    })))
    grant(client, did, reader, "read")
    output = final(run(client, {"workflow_id": reader, "input": {"ticket": "\u0110\u01a0N"}}))
    assert [item["values"]["ticket"] for item in output["items"]] == ["\u0111\u01a1n-b", "\u0110\u01a0N-C"]
