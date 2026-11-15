from app.engine import dataset_nodes
from test_agent_node import call as tool_call, final as agent_final, script, wf
from test_dataset_agent_tool import dataset_tool
from test_dataset_rows import call, insert
from test_dataset_runtime import dataset_fixture, dataset_node, final, grant, graph, run, save
from test_datasets import auth, client, error  # noqa: F401
from test_identity_migration import db  # noqa: F401


def rule(field, op, value):
    return {"type": "rule", "field": field, "op": op, "value": value}


def group(conjunction, *children):
    return {"type": "group", "conjunction": conjunction, "children": list(children)}


def seed(client):
    did = dataset_fixture(client)
    path = f"/api/datasets/{did}/rows"
    for ticket, score, done in [("A", 5, True), ("B", 1, False), ("C", 5, False), ("D", None, False)]:
        insert(client, path, ticket=ticket, score=score, done=done)
    return did, path


def test_grouped_filter_in_api_node_and_agent(client, monkeypatch):
    did, path = seed(client)
    tree = group("and", rule("ticket", "in", ["A", "B", "C"]),
                 group("or", rule("done", "eq", True), rule("score", "lt", 3)))
    arguments = {"filter_tree": tree}
    expected = [{"ticket": "A"}, {"ticket": "B"}]
    api_rows = call(client, "POST", f"{path}/query", body={**arguments, "fields": ["ticket"]})
    assert [item["values"] for item in api_rows["items"]] == expected
    assert api_rows["total"] == 2

    mapped = group("and", rule("ticket", "in", ["{{state.ticket}}", "B", "C"]), *tree["children"][1:])
    wid = save(client, graph("Grouped query", dataset_node(did, "find_rows", {"filter_tree": mapped})))
    grant(client, did, wid, "read")
    result = final(run(client, {"workflow_id": wid, "input": {"ticket": "A"}}))
    assert [item["values"] for item in result["items"]] == expected

    tool = dataset_tool(did, filter_ops={"ticket": ["in"], "done": ["eq"], "score": ["lt"]}, limit=10)
    agent = save(client, wf(tools=[tool], steps_field="steps"))
    grant(client, did, agent, "read")
    seen = script(monkeypatch, [("", [tool_call(tool["name"], arguments)]), ("Finished", [])])
    steps = agent_final(run(client, {"workflow_id": agent}))["steps"]
    assert steps[0]["dataset"] == {"count": 2}
    assert any('"ticket": "A"' in item.get("content", "") and '"ticket": "B"' in item.get("content", "")
               for item in seen[1][0] if item["role"] == "tool")
    assert dataset_nodes.agent_parameters(tool)["properties"]["filter_tree"]["type"] == "object"


def test_negated_membership_and_text_filters_include_null(client):
    did, path = seed(client)
    options = {"filter_tree": group("and", rule("score", "not_in", [1, 5]), rule("ticket", "not_contains", "a"))}
    rows = call(client, "POST", f"{path}/query", body=options)["items"]
    assert [item["values"]["ticket"] for item in rows] == ["D"]
    legacy = call(client, "POST", f"{path}/query", body={"filters": [{"field": "ticket", "op": "eq", "value": "A"}]})
    assert [item["values"]["ticket"] for item in legacy["items"]] == ["A"]


def test_group_and_list_limits_and_mapped_rule_error(client):
    did, path = seed(client)
    valid = rule("ticket", "eq", "A")
    too_deep = group("and", group("and", group("and", group("and", valid))))
    too_many = group("and", group("or", *([valid] * 11)), group("or", *([valid] * 10)))
    too_many_values = group("and", rule("ticket", "in", ["A"] * 51))
    for tree, limit in [(too_deep, "3"), (too_many, "20"), (too_many_values, "50")]:
        response = client.post(f"{path}/query", headers=auth("owner"), json={"filter_tree": tree})
        error(response, 422, "VALIDATION_ERROR")
        assert limit in response.text
    tree = group("and", group("or", rule("score", "lt", "{{state.ticket}}")))
    wid = save(client, graph("Mapped query", dataset_node(did, "find_rows", {"filter_tree": tree})))
    grant(client, did, wid, "read")
    events = run(client, {"workflow_id": wid, "input": {"ticket": ""}})
    fault = next(event["error"] for event in events if event.get("error", {}).get("code") == "DATASET_FILTER_INVALID")
    assert fault["details"] == {"node": "dataset", "group": "1", "position": 1, "field": "score", "state_key": "ticket"}
