import asyncio
import json

from app.api import deps
from app.core.errors import AppError
from app.engine import agents
from test_agent_node import call as tool_call
from test_agent_node import final, script, wf
from test_dataset_rows import call
from test_dataset_runtime import dataset_fixture, grant, graph, run, save
from test_datasets import auth, client, create, error  # noqa: F401
from test_identity_migration import db  # noqa: F401


def dataset_tool(did, **overrides):
    return {"name": "find_records", "source": "dataset", "dataset_id": did,
            "fields": ["ticket"], "filter_ops": {"ticket": ["eq"]}, "limit": 1, **overrides}


def test_agent_dataset_reads_only_configured_fields_and_filters(client, monkeypatch):
    did = dataset_fixture(client)
    rows = f"/api/datasets/{did}/rows"
    call(client, "POST", rows, body={"values": {"ticket": "A", "score": 123456789}}, status=201)
    call(client, "POST", rows, body={"values": {"ticket": "B", "score": 123456789}}, status=201)
    tool = dataset_tool(did)
    wid = save(client, wf(tools=[tool], steps_field="steps"))
    grant(client, did, wid, "read_write")
    lookup = {"filters": [{"field": "ticket", "op": "eq", "value": "A"}]}
    rejected = [
        {"operation": "upsert_row", "values": {"ticket": "Unexpected"}},
        {"fields": ["score"]},
        {"dataset_id": "another"},
        {"filters": [{"field": "score", "op": "eq", "value": 123456789}]},
        {"filters": [{"field": "ticket", "op": "ne", "value": "B"}]},
        {"filters": lookup["filters"] * 13},
        {"limit": 100},
    ]
    calls = [tool_call(tool["name"], args, f"request-{i}") for i, args in enumerate([lookup, *rejected])]
    seen = script(monkeypatch, [("", calls), ("Finished", [])])
    events = run(client, {"workflow_id": wid, "input": {"message": "Find the record"}})
    state = final(events)
    assert state["answer"] == "Finished"
    assert [step["status"] for step in state["steps"]] == ["ok", *(["error"] * len(rejected))]
    assert state["steps"][0]["dataset"] == {"count": 1}
    assert all(step["args"] == {} and "rows" not in step.get("result", "") for step in state["steps"])
    messages = [msg["content"] for msg in seen[1][0] if msg["role"] == "tool"]
    assert json.loads(messages[0]) == {"rows": [{"ticket": "A"}], "truncated": False}
    assert all("The tool failed" in message for message in messages[1:])
    assert "123456789" not in json.dumps(events)
    schema = seen[0][1][0]["parameters"]
    assert schema["additionalProperties"] is False
    assert schema["properties"]["filters"]["items"]["properties"]["field"]["enum"] == ["ticket"]
    assert [item["values"]["ticket"] for item in call(client, "POST", rows + "/query", body={})["items"]] == ["A", "B"]

    limited = script(monkeypatch, [("", [tool_call(tool["name"], {})]), ("Finished", [])])
    run(client, {"workflow_id": wid})
    response = next(message["content"] for message in limited[1][0] if message["role"] == "tool")
    assert json.loads(response) == {"rows": [{"ticket": "A"}], "truncated": True}


def test_agent_dataset_checks_grants_on_each_tool_call(client, monkeypatch):
    did = dataset_fixture(client)
    call(client, "POST", f"/api/datasets/{did}/rows", body={"values": {"ticket": "A"}}, status=201)
    tool = dataset_tool(did)
    child = save(client, wf(tools=[tool], steps_field="steps"))
    parent = save(client, graph("Parent", {"id": "child", "type": "subgraph", "data": {"workflow_id": child}}))
    grant(client, did, parent, "read")
    replies = [("", [tool_call(tool["name"], {})]), ("Finished", [])]
    denied = script(monkeypatch, replies)
    events = run(client, {"workflow_id": parent})
    assert final(events)["steps"][0]["status"] == "error"
    assert "grant" in denied[-1][0][-1]["content"].lower()

    grant(client, did, child, "read")
    rounds = iter(range(3))

    def model(*args, **kwargs):
        round_no = next(rounds)
        if round_no == 1:
            call(client, "DELETE", f"/api/datasets/{did}/access/grants/{child}")
        if round_no < 2:
            return "", [tool_call(tool["name"], {}, f"r{round_no}")]
        return "Finished", []

    monkeypatch.setattr(agents, "call_agent", model)
    steps = final(run(client, {"workflow_id": parent}))["steps"]
    assert [step["status"] for step in steps] == ["ok", "error"]
    assert [step["dataset"]["count"] for step in steps] == [1, None]


def test_agent_dataset_authoring_validates_projection_and_operator_kind(client):
    did = dataset_fixture(client)
    denied = client.post("/api/workflows", headers=auth("other"), json=wf(tools=[dataset_tool(did)]))
    error(denied, 404, "DATASET_NOT_FOUND")
    invalid = client.post("/api/workflows", headers=auth("owner"),
                          json=wf(tools=[dataset_tool(did, filter_ops={"done": ["contains"]})]))
    error(invalid, 400, "DATASET_FILTER_INVALID")
    invalid = call(client, "POST", "/api/workflows", body=wf(tools=[dataset_tool(did, limit=21)]))
    assert [issue["code"] for issue in invalid["issues"]] == ["AGENT_TOOL_DATASET"]


def write_tool(did, **overrides):
    return dataset_tool(did, **{"name": "file_ticket", "operations": ["find_rows", "insert_row", "upsert_row"],
                                "fields": ["ticket", "score"], "write_fields": ["ticket", "score"], "key": "ticket", **overrides})


def rows_of(client, did):
    items = call(client, "POST", f"/api/datasets/{did}/rows/query", body={})["items"]
    return sorted((item["values"] for item in items), key=lambda values: values["ticket"])


def test_agent_dataset_writes_only_configured_operations_and_fields(client, monkeypatch):
    did = dataset_fixture(client)
    tool = write_tool(did)
    wid = save(client, wf(tools=[tool], steps_field="steps"))
    grant(client, did, wid, "read")
    insert = {"operation": "insert_row", "values": {"ticket": "A", "score": 424242}}
    denied = script(monkeypatch, [("", [tool_call(tool["name"], insert)]), ("Finished", [])])
    steps = final(run(client, {"workflow_id": wid}))["steps"]
    assert steps[0]["status"] == "error" and "grant" in denied[-1][0][-1]["content"].lower()
    assert rows_of(client, did) == []

    grant(client, did, wid, "read_write")
    accepted = [insert, {"operation": "upsert_row", "values": {"ticket": "A", "score": 7}}]
    rejected = [
        {"operation": "insert_row", "values": {"ticket": "B", "done": True}},
        {"operation": "delete_row", "values": {"ticket": "A"}},
        {"operation": "upsert_row", "values": {"score": 1}},
        {"operation": "insert_row", "values": {"ticket": {"nested": True}}},
        {"operation": "insert_row", "values": {}},
        {"operation": "find_rows", "values": {"ticket": "A"}},
    ]
    calls = [tool_call(tool["name"], args, f"write-{i}") for i, args in enumerate([*accepted, *rejected])]
    seen = script(monkeypatch, [("", calls[:2]), ("", calls[2:]), ("Finished", [])])
    events = run(client, {"workflow_id": wid})
    steps = final(events)["steps"]
    assert [step["status"] for step in steps] == ["ok", "ok", *(["error"] * len(rejected))]
    assert steps[0]["dataset"] == {"count": 1, "operation": "insert_row"}
    assert steps[1]["dataset"] == {"count": 1, "operation": "upsert_row"}
    assert all(step["args"] == {} for step in steps)
    assert "424242" not in json.dumps(events)
    messages = [json.loads(msg["content"]) for msg in seen[1][0] if msg["role"] == "tool"]
    assert messages[0]["inserted"] is True and messages[0]["values"] == {"ticket": "A", "score": 424242}
    assert messages[1]["inserted"] is False and messages[1]["row_id"] == messages[0]["row_id"]
    assert rows_of(client, did) == [{"ticket": "A", "score": 7, "done": None}]
    schema = seen[0][1][0]["parameters"]
    assert schema["required"] == ["operation"]
    assert schema["properties"]["operation"]["enum"] == ["find_rows", "insert_row", "upsert_row"]
    assert set(schema["properties"]["values"]["properties"]) == {"ticket", "score"}
    assert schema["properties"]["values"]["additionalProperties"] is False

    reader = dataset_tool(did, name="lookup_ticket")
    assert "operation" not in agents.parameters(reader)["properties"]
    only_insert = write_tool(did, name="insert_only", operations=["insert_row"], key=None)
    assert agents.parameters(only_insert)["properties"]["operation"]["enum"] == ["insert_row"]
    assert "filters" not in agents.parameters(only_insert)["properties"]


def test_agent_dataset_write_replays_one_call_and_writes_distinct_calls(client, monkeypatch):
    from app.services.dataset_runtime import DatasetRuntimeService
    did = dataset_fixture(client)
    tool = write_tool(did, operations=["insert_row"], key=None)
    wid = save(client, wf(tools=[tool], steps_field="steps"))
    grant(client, did, wid, "write")
    original = DatasetRuntimeService.execute
    keys = []

    def retried(self, **kwargs):
        first = original(self, **kwargs)
        keys.append(kwargs["operation_id"])
        assert original(self, **kwargs) == first  # the same logical call replays its receipt
        changed = {**kwargs, "arguments": {"values": {"ticket": "Other"}}}
        try:
            original(self, **changed)
        except AppError as exc:
            assert exc.code == "DATASET_RECEIPT_CONFLICT"
        else:
            raise AssertionError("a changed payload must not reuse the receipt")
        return first

    monkeypatch.setattr(DatasetRuntimeService, "execute", retried)
    calls = [tool_call(tool["name"], {"operation": "insert_row", "values": {"ticket": ticket}}, f"call-{ticket}") for ticket in "BC"]
    script(monkeypatch, [("", calls), ("Finished", [])])
    steps = final(run(client, {"workflow_id": wid}))["steps"]
    assert [step["status"] for step in steps] == ["ok", "ok"]
    assert len(set(keys)) == 2 and all(key.endswith(("#call-B", "#call-C")) for key in keys)
    assert [values["ticket"] for values in rows_of(client, did)] == ["B", "C"]


def test_agent_dataset_write_revocation_and_test_runs(client, monkeypatch):
    did = dataset_fixture(client)
    call(client, "POST", f"/api/datasets/{did}/rows", body={"values": {"ticket": "Owned", "score": 1}}, status=201)
    tool = write_tool(did, operations=["upsert_row"])
    wid = save(client, wf(tools=[tool], steps_field="steps"))
    grant(client, did, wid, "write")
    rounds = iter(range(4))

    def model(*args, **kwargs):
        round_no = next(rounds)
        if round_no == 1:
            grant(client, did, wid, "read")
        if round_no < 2:
            return "", [tool_call(tool["name"], {"operation": "upsert_row", "values": {"ticket": f"R{round_no}"}}, f"r{round_no}")]
        return "Finished", []

    monkeypatch.setattr(agents, "call_agent", model)
    steps = final(run(client, {"workflow_id": wid}))["steps"]
    assert [step["status"] for step in steps] == ["ok", "error"]
    assert [values["ticket"] for values in rows_of(client, did)] == ["Owned", "R0"]

    grant(client, did, wid, "write")
    script(monkeypatch, [("", [tool_call(tool["name"], {"operation": "upsert_row", "values": {"ticket": "R0", "score": 5}})]),
                         ("Finished", [])])
    assert final(run(client, {"workflow_id": wid}))["steps"][0]["status"] == "ok"
    assert {values["ticket"]: values["score"] for values in rows_of(client, did)} == {"Owned": 1, "R0": 5}

    svc = deps.run_service()
    plan = svc.plan("owner", {"workflow_id": wid})
    svc.apply_test(plan, {"mock": True})
    simulated = script(monkeypatch, [("", [tool_call(tool["name"], {"operation": "upsert_row", "values": {"ticket": "Simulated"}})]),
                                     ("Finished", [])])
    events = []

    async def send(event):
        events.append(event)
        return True

    async def listen():
        await asyncio.Future()

    assert asyncio.run(svc.execute(plan, send, listen, "owner")) == "ok"
    message = json.loads(next(msg["content"] for msg in simulated[1][0] if msg["role"] == "tool"))
    assert message["simulated"] is True and message["inserted"] is True
    assert "Simulated" not in [values["ticket"] for values in rows_of(client, did)]


def test_agent_dataset_upsert_unique_conflict_leaves_the_other_row(client, monkeypatch):
    did = create(client, name="Two unique", columns=[
        {"key": "ticket", "label": "Ticket", "kind": "text", "unique": True, "required": True},
        {"key": "email", "label": "Email", "kind": "email", "unique": True},
    ])["id"]
    tool = dataset_tool(did, name="update_ticket", operations=["upsert_row"], fields=["ticket", "email"],
                        write_fields=["ticket", "email"], key="ticket")
    wid = save(client, wf(tools=[tool], steps_field="steps"))
    grant(client, did, wid, "write")
    base = f"/api/datasets/{did}/rows"
    call(client, "POST", base, body={"values": {"ticket": "A", "email": "a@example.com"}}, status=201)
    call(client, "POST", base, body={"values": {"ticket": "B", "email": "b@example.com"}}, status=201)
    conflict = {"operation": "upsert_row", "values": {"ticket": "A", "email": "b@example.com"}}
    seen = script(monkeypatch, [("", [tool_call(tool["name"], conflict)]), ("Finished", [])])
    assert final(run(client, {"workflow_id": wid}))["steps"][0]["status"] == "error"
    assert "unique" in next(msg["content"] for msg in seen[1][0] if msg["role"] == "tool").lower()
    items = call(client, "POST", base + "/query", body={})["items"]
    assert sorted((item["values"]["ticket"], item["values"]["email"]) for item in items) == [
        ("A", "a@example.com"), ("B", "b@example.com")]


def test_agent_dataset_write_authoring_checks_write_access_and_keys(client):
    did = dataset_fixture(client)
    viewer = client.post("/api/workflows", headers=auth("other"), json=wf(tools=[write_tool(did)]))
    error(viewer, 404, "DATASET_NOT_FOUND")
    invalid = client.post("/api/workflows", headers=auth("owner"), json=wf(tools=[write_tool(did, write_fields=["score"], key="score")]))
    error(invalid, 400, "DATASET_UPSERT_KEY_INVALID")
    missing = client.post("/api/workflows", headers=auth("owner"), json=wf(tools=[write_tool(did, write_fields=["gone"], key="gone")]))
    error(missing, 404, "DATASET_COLUMN_NOT_FOUND")
    for bad in ({"operations": ["delete_row"]}, {"operations": []}, {"write_fields": []}, {"key": "done"}):
        result = call(client, "POST", "/api/workflows", body=wf(tools=[write_tool(did, **bad)]))
        assert [issue["code"] for issue in result["issues"]] == ["AGENT_TOOL_DATASET"], bad
