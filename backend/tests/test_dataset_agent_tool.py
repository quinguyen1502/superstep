import json

from app.engine import agents
from test_agent_node import call as tool_call
from test_agent_node import final, script, wf
from test_dataset_rows import call
from test_dataset_runtime import dataset_fixture, grant, graph, run, save
from test_datasets import auth, client, error  # noqa: F401
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


def test_agent_dataset_filters_ignore_case_and_ne_matches_empty_cells(client, monkeypatch):
    did = dataset_fixture(client)
    rows = f"/api/datasets/{did}/rows"
    for values in ({"ticket": "Webhook-1", "score": 5}, {"ticket": "WEBHOOK-2"}, {"ticket": "Other", "score": 1}):
        call(client, "POST", rows, body={"values": values}, status=201)
    tool = dataset_tool(did, filter_ops={"ticket": ["contains"], "score": ["ne"]}, limit=10)
    wid = save(client, wf(tools=[tool], steps_field="steps"))
    grant(client, did, wid, "read")
    lookup = {"filters": [{"field": "ticket", "op": "contains", "value": "webhook"}, {"field": "score", "op": "ne", "value": 5}]}
    seen = script(monkeypatch, [("", [tool_call(tool["name"], lookup)]), ("Finished", [])])
    run(client, {"workflow_id": wid, "input": {"message": "Find"}})
    response = next(message["content"] for message in seen[1][0] if message["role"] == "tool")
    assert json.loads(response) == {"rows": [{"ticket": "WEBHOOK-2"}], "truncated": False}
    op = seen[0][1][0]["parameters"]["properties"]["filters"]["items"]["properties"]["op"]
    assert "ignores letter case" in op["description"] and "empty cells" in op["description"]
