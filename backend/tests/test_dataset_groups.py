from test_dataset_filter_groups import group, rule
from test_dataset_rows import call, insert, rows  # noqa: F401
from test_datasets import auth, client, error  # noqa: F401
from test_identity_migration import db  # noqa: F401


def test_groups_page_and_rows_use_the_same_predicates(client, rows):
    insert(client, rows, ticket="A", title="Open", score=3)
    insert(client, rows, ticket="B", title="Open", score=4)
    insert(client, rows, ticket="C", title="Closed", score=5)
    insert(client, rows, ticket="D", title=None, score=6)
    insert(client, rows, ticket="E", title="Open", score=1)
    tree = group("or", rule("score", "gte", 3), rule("ticket", "eq", "missing"))
    base = {"group_by": "title", "filter_tree": tree}
    result = call(client, "POST", f"{rows}/groups", uid="member", body={
        **base, "summaries": {"score": "avg"}, "limit": 2,
    })
    assert result["groups"] == [
        {"group": "Open", "total": 2, "values": {"score": 3.5}},
        {"group": "Closed", "total": 1, "values": {"score": 5}},
    ]
    assert result["next_offset"] == 2
    result = call(client, "POST", f"{rows}/groups", uid="member", body={**base, "offset": 2})
    assert result["groups"] == [{"group": None, "total": 1, "values": {}}]
    assert result["next_offset"] is None
    result = call(client, "POST", f"{rows}/groups/query", uid="member", body={
        **base, "group": "Open", "limit": 1, "offset": 1,
    })
    assert result["total"] == 2
    assert [row["values"]["ticket"] for row in result["items"]] == ["B"]
    result = call(client, "POST", f"{rows}/groups/query", body={**base, "group": None})
    assert [row["values"]["ticket"] for row in result["items"]] == ["D"]
    error(client.post(f"{rows}/groups", headers=auth("other"), json=base), 404, "DATASET_NOT_FOUND")
    error(client.post(f"{rows}/groups", headers=auth("member"), json={"group_by": "score"}), 400, "DATASET_FILTER_INVALID")
