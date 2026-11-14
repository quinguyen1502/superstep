import asyncio
import json

from app.api import deps
from test_agent_node import call as tool_call, final as agent_final, script, wf
from test_dataset_agent_tool import dataset_tool
from test_dataset_filter_groups import group, rule
from test_dataset_rows import insert
from test_dataset_runtime import assert_error, dataset_fixture, dataset_node, final, grant, graph, run, save
from test_datasets import client  # noqa: F401
from test_identity_migration import db  # noqa: F401


def test_read_grant_and_public_entry_for_aggregate_node(client):
    did = dataset_fixture(client)
    path = f"/api/datasets/{did}/rows"
    for ticket, done, score in [("A", True, 5), ("B", True, 3), ("C", False, 4), ("D", False, None)]:
        insert(client, path, ticket=ticket, done=done, score=score)
    arguments = {"filter_tree": group("and", rule("score", "not_null", None)),
                 "summaries": {"ticket": "count", "score": "sum"}, "group_by": "done"}
    wid = save(client, graph("Aggregate", dataset_node(did, "aggregate_rows", arguments, ["ticket", "score", "done"])))
    request = {"workflow_id": wid}
    grant(client, did, wid, "write")
    assert_error(run(client, request), "DATASET_GRANT_DENIED")
    grant(client, did, wid, "read")
    expected = {
        "group_by": "done", "groups": [
            {"group": True, "total": 2, "values": {"ticket": 2, "score": 8}},
            {"group": False, "total": 1, "values": {"ticket": 1, "score": 4}},
        ], "truncated": False,
    }
    events = run(client, request)
    assert final(events) == expected
    trace = next(event["dataset"] for event in events if event.get("dataset") and event["type"] == "node_finished")
    assert trace == {"id": did, "operation": "aggregate_rows", "count": 2, "outcome": "completed"}

    svc = deps.run_service()
    plan = svc.plan("owner", request)
    plan.source = "api"
    events.clear()

    async def send(event):
        events.append(event)
        return True

    async def listen():
        await asyncio.Future()

    assert asyncio.run(svc.execute(plan, send, listen, "owner")) == "ok"
    assert final(events) == expected


def test_agent_aggregate_is_opt_in_and_respects_fields_and_grants(client, monkeypatch):
    did = dataset_fixture(client)
    path = f"/api/datasets/{did}/rows"
    insert(client, path, ticket="Support Alpha", done=False, score=5)
    insert(client, path, ticket="Support Beta", done=False, score=4)
    insert(client, path, ticket="Support Gamma", done=True, score=5)
    args = {"operation": "aggregate_rows", "summaries": {"ticket": "count"},
            "group_by": "done", "filter_tree": group("and", rule("score", "gte", 4))}
    tool = dataset_tool(did, operations=["aggregate_rows"], fields=["ticket", "done"], filter_ops={"score": ["gte"]})

    def one_call(tool, permission, args):
        wid = save(client, wf(tools=[tool], steps_field="steps"))
        grant(client, did, wid, permission)
        seen = script(monkeypatch, [("", [tool_call(tool["name"], args)]), ("Finished", [])])
        output = agent_final(run(client, {"workflow_id": wid}))
        return output["steps"][0], next(message["content"] for message in seen[1][0] if message["role"] == "tool")

    step, message = one_call(tool, "read", args)
    assert step["dataset"] == {"operation": "aggregate_rows", "count": 2}
    assert step["args"] == {} and "result" not in step
    assert json.loads(message)["groups"] == [
        {"group": False, "total": 2, "values": {"ticket": 2}},
        {"group": True, "total": 1, "values": {"ticket": 1}},
    ]
    for binding, grant_type, query in [
        (dataset_tool(did), "read", args), (tool, "write", args),
        (tool, "read", {**args, "group_by": "score"}),
    ]:
        step, message = one_call(binding, grant_type, query)
        assert step["status"] == "error"
        assert "The tool failed" in message


def test_aggregate_group_limit_and_stable_order(client):
    did = dataset_fixture(client)
    path = f"/api/datasets/{did}/rows"
    for key in range(25):
        insert(client, path, ticket=f"T-{key:02}")
    wid = save(client, graph("Limited groups", dataset_node(did, "aggregate_rows", {
        "summaries": {"ticket": "count"}, "group_by": "ticket",
    })))
    grant(client, did, wid, "read")
    result = final(run(client, {"workflow_id": wid}))
    assert result["truncated"] is True
    assert [group["group"] for group in result["groups"]] == [f"T-{key:02}" for key in range(20)]
