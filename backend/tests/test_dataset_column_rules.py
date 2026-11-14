from test_dataset_rows import call, insert
from test_datasets import auth, client, create, error  # noqa: F401
from test_identity_migration import db  # noqa: F401


def test_rules_stop_conflicting_schema_changes_then_apply_to_new_writes_and_csv(client):
    score = {"key": "score", "label": "Score", "kind": "number"}
    dataset = create(client, name="Validated dataset", columns=[score])
    url = f"/api/datasets/{dataset['id']}"
    row = insert(client, f"{url}/rows", score=1.5)
    column = f"{url}/columns/score"
    proposed = {**score, "validation_rules": {"min": 2, "integer": True},
                "display_format": {"decimals": 2, "style": "currency", "currency": "USD"}}
    rejected = client.put(column, headers=auth("owner"), json={"revision": 1, "column": proposed})
    error(rejected, 409, "DATASET_COLUMN_RULE_EXISTING_ROWS")
    assert rejected.json()["error"]["details"]["sample_row_ids"] == [row["id"]]
    assert rejected.json()["error"]["details"]["count"] == 1
    call(client, "PATCH", f"{url}/rows/{row['id']}", body={"revision": 1, "values": {"score": 9}})
    updated = call(client, "PUT", column, body={"revision": 1, "column": proposed})
    assert updated["revision"] == 2
    assert updated["columns"][0]["display_format"]["currency"] == "USD"
    error(client.post(f"{url}/rows", headers=auth("owner"), json={"values": {"score": 3.5}}),
          400, "DATASET_COLUMN_RULE_VIOLATION")
    preview = call(client, "POST", "/api/datasets/csv/preview", body={
        "dataset_id": dataset["id"], "text": "Score\n3.5\n8\n",
    })
    assert preview["invalid_rows"] == 1
    assert preview["issues"][0]["error"]["code"] == "DATASET_COLUMN_RULE_VIOLATION"
    read = call(client, "POST", f"{url}/rows/query", body={"filters": [{"field": "score", "op": "gt", "value": 1.5}]})
    assert read["items"][0]["values"]["score"] == 9
