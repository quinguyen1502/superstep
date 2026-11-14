from concurrent.futures import ThreadPoolExecutor

from test_dataset_rows import call, insert
from test_datasets import auth, client, create, error  # noqa: F401
from test_identity_migration import db  # noqa: F401


def test_atomic_batch_validates_every_cell_and_supports_undo(client):
    data = create(client, name="Atomic updates", columns=[
        {"key": "ticket", "label": "Ticket", "kind": "text", "unique": True},
        {"key": "score", "label": "Score", "kind": "number", "validation_rules": {"integer": True}},
    ])
    path = f"/api/datasets/{data['id']}/rows"
    a = insert(client, path, ticket="A", score=5)
    b = insert(client, path, ticket="B", score=10)

    def batch(*rows, status=200):
        response = client.patch(f"{path}/batch", headers=auth("owner"), json={"schema_revision": 1, "rows": rows})
        assert response.status_code == status, response.text
        return response.json()["data" if status == 200 else "error"]

    def edit(row, revision=1, **values):
        return {"id": row["id"], "revision": revision, "values": values}

    invalid = batch(edit(a, score=7), edit(b, score=2.5), status=400)
    assert [(item["id"], item["field"], item["error"]["code"]) for item in invalid["details"]["issues"]] == [
        (b["id"], "score", "DATASET_COLUMN_RULE_VIOLATION"),
    ]
    stale = batch(edit(a, score=7), edit(b, revision=3, score=11), status=409)
    assert stale["details"]["issues"][0]["error"]["code"] == "DATASET_ROW_CONFLICT"
    duplicate = batch(edit(a, ticket="B"), status=409)
    assert duplicate["details"]["issues"][0]["error"]["code"] == "DATASET_UNIQUE_CONFLICT"
    assert call(client, "GET", f"{path}/{a['id']}") == a
    assert call(client, "GET", f"{path}/{b['id']}") == b
    result = batch(edit(a, ticket="B", score=20), edit(b, ticket="A"))
    assert result == {"schema_revision": 1, "rows": [
        {"id": a["id"], "revision": 2, "previous": {"ticket": "A", "score": 5}},
        {"id": b["id"], "revision": 2, "previous": {"ticket": "B"}},
    ]}
    undo = batch(*[{"id": item["id"], "revision": item["revision"], "values": item["previous"]} for item in result["rows"]])
    assert [item["revision"] for item in undo["rows"]] == [3, 3]
    assert call(client, "GET", f"{path}/{a['id']}")["values"] == a["values"]
    assert call(client, "GET", f"{path}/{b['id']}")["values"] == b["values"]


def test_stale_concurrent_batch_never_overwrites_the_winner(client):
    data = create(client, name="Concurrent batch", columns=[{"key": "score", "label": "Score", "kind": "number"}])
    path = f"/api/datasets/{data['id']}/rows"
    row = insert(client, path, score=0)

    def attempt(score):
        return client.patch(f"{path}/batch", headers=auth("owner"), json={"schema_revision": 1, "rows": [
            {"id": row["id"], "revision": 1, "values": {"score": score}},
        ]})

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(attempt, [1, 2]))
    assert sorted(response.status_code for response in responses) == [200, 409]
    current = call(client, "GET", f"{path}/{row['id']}")
    assert current["revision"] == 2 and current["values"]["score"] in [1, 2]
