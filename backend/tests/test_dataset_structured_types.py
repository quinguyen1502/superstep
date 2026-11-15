from concurrent.futures import ThreadPoolExecutor

from test_dataset_rows import call, insert
from test_datasets import auth, client, create, error  # noqa: F401
from test_identity_migration import db  # noqa: F401


def test_auto_number_backfill_concurrency_and_deletion(client):
    data = create(client, name="Numbered", columns=[{"key": "title", "label": "Title", "kind": "text"}])
    base = f"/api/datasets/{data['id']}"
    path = f"{base}/rows"
    first = insert(client, path, title="First")
    second = insert(client, path, title="Second")
    call(client, "POST", f"{base}/columns", body={"revision": 1, "column": {
        "key": "sequence", "label": "Sequence", "kind": "auto_number",
    }}, status=201)
    assert call(client, "GET", f"{path}/{first['id']}")["values"]["sequence"] == 1
    assert call(client, "GET", f"{path}/{second['id']}")["values"]["sequence"] == 2
    with ThreadPoolExecutor(max_workers=4) as pool:
        concurrent = list(pool.map(lambda n: insert(client, path, title=f"Row {n}"), range(8)))
    assert sorted(row["values"]["sequence"] for row in concurrent) == list(range(3, 11))
    call(client, "DELETE", f"{path}/{second['id']}?revision=2")
    assert insert(client, path, title="After delete")["values"]["sequence"] == 11
    error(client.post(path, headers=auth("owner"), json={"values": {"sequence": 100}}), 400, "DATASET_COLUMN_READ_ONLY")
    result = call(client, "POST", f"{path}/query", body={"filters": [{"field": "sequence", "op": "eq", "value": 11}]})
    assert result["items"][0]["values"]["title"] == "After delete"


def test_multi_select_filters_and_csv(client):
    data = create(client, name="Multi-select", columns=[
        {"key": "labels", "label": "Labels", "kind": "multi_select", "options": ["Red", "Blue", "Green"]},
    ])
    url = f"/api/datasets/{data['id']}"
    rows = f"{url}/rows"
    red = insert(client, rows, labels=["Red"])
    both = insert(client, rows, labels=["Blue", "Red"])
    empty = insert(client, rows, labels=[])
    assert both["values"]["labels"] == ["Red", "Blue"]
    assert empty["values"]["labels"] is None
    for op, value, expected in [
        ("contains_any", ["Red", "Green"], [red["id"], both["id"]]),
        ("contains_all", ["Red", "Blue"], [both["id"]]),
        ("is_null", None, [empty["id"]]),
    ]:
        result = call(client, "POST", f"{rows}/query", body={"filters": [{"field": "labels", "op": op, "value": value}]})
        assert [row["id"] for row in result["items"]] == expected
    error(client.post(rows, headers=auth("owner"), json={"values": {"labels": ["Unknown"]}}), 400, "DATASET_VALUE_INVALID")
    data = call(client, "POST", "/api/datasets/csv/import", body={
        "dataset_id": data["id"], "schema_revision": data["revision"], "text": "Labels\nRed;Green\n",
    })
    assert data["imported"] == 1
    exported = client.get(f"{url}/csv", headers=auth("owner"))
    assert exported.status_code == 200 and "Red;Green" in exported.text
