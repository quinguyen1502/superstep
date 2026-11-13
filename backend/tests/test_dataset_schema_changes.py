import json
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import func, select

from app.models import DatasetRowKey
from test_dataset_rows import call, insert, query
from test_dataset_runtime import dataset_node, graph, save
from test_datasets import auth, client, create, error  # noqa: F401
from test_identity_migration import db  # noqa: F401

IMPORT = "/api/datasets/csv/import"


def column(dataset, key):
    return next(item for item in dataset["columns"] if item["key"] == key)


def set_unique(client, url, dataset, key, unique, *, status=200):
    body = {"revision": dataset["revision"], "column": {**column(dataset, key), "unique": unique}}
    response = client.put(f"{url}/columns/{key}", headers=auth("owner"), json=body)
    assert response.status_code == status, response.text
    return response.json()


def key_count(db, dataset_id, field):
    with db.session() as session:
        return session.scalar(select(func.count()).select_from(DatasetRowKey).where(
            DatasetRowKey.dataset_id == dataset_id, DatasetRowKey.field == field))


def test_csv_import_then_unique_allows_upsert(client, db):
    text = "Ticket ID,Subject\nT-1,First\nT-2,Second\n,No key\n"
    preview = call(client, "POST", "/api/datasets/csv/preview", body={"text": text})
    imported = call(client, "POST", IMPORT, body={
        "text": text, "mapping": preview["mapping"],
        "create": {"name": "Imported", "team_id": "support", "columns": preview["columns"]},
    })
    dataset = imported["dataset"]
    url = f"/api/datasets/{dataset['id']}"
    error(client.post(f"{url}/rows/upsert", headers=auth("owner"), json={"key": "ticket_id", "values": {"ticket_id": "T-1"}}),
          400, "DATASET_UPSERT_KEY_INVALID")
    updated = set_unique(client, url, dataset, "ticket_id", True)["data"]
    assert column(updated, "ticket_id")["unique"] is True and updated["revision"] == dataset["revision"] + 1
    assert key_count(db, dataset["id"], "ticket_id") == 2
    result = call(client, "POST", f"{url}/rows/upsert", body={"key": "ticket_id", "values": {"ticket_id": "T-2", "subject": "Changed"}})
    assert result["inserted"] is False
    found = query(client, f"{url}/rows", filters=[{"field": "ticket_id", "op": "eq", "value": "T-2"}])["items"]
    assert [item["values"]["subject"] for item in found] == ["Changed"]
    error(client.post(f"{url}/rows", headers=auth("owner"), json={"values": {"ticket_id": "T-1"}}), 409, "DATASET_UNIQUE_CONFLICT")
    with db.session() as session:
        from app.models import AuditEvent
        events = list(session.scalars(select(AuditEvent).where(AuditEvent.action == "dataset.column_update")))
        assert [json.loads(event.details) for event in events] == [{"field": "ticket_id", "unique": True}]


def test_duplicates_block_unique_with_count_and_samples(client, db):
    dataset = create(client, name="Duplicates", columns=[
        {"key": "code", "label": "Code", "kind": "number"}, {"key": "name", "label": "Name", "kind": "text"},
    ])
    url = f"/api/datasets/{dataset['id']}"
    rows = [insert(client, f"{url}/rows", code=value) for value in (1, 1.0, 2, 3, 3, 3, None, None)]
    body = set_unique(client, url, dataset, "code", True, status=409)
    assert body["error"]["code"] == "DATASET_UNIQUE_DUPLICATES"
    details = body["error"]["details"]
    assert details["field"] == "code" and details["count"] == 5 and details["values"] == 2 and details["value"] == 1
    assert details["rows"] == [rows[0]["id"], rows[1]["id"], rows[3]["id"], rows[4]["id"], rows[5]["id"]]
    assert key_count(db, dataset["id"], "code") == 0
    assert call(client, "GET", url)["revision"] == dataset["revision"]
    error(client.put(f"{url}/columns/code", headers=auth("member"), json={
        "revision": dataset["revision"], "column": {**column(dataset, "code"), "unique": True}}), 404, "DATASET_NOT_FOUND")


def test_bound_key_keeps_unique_and_unique_off_drops_keys(client, db):
    dataset = create(client, name="Bound", columns=[
        {"key": "ticket", "label": "Ticket", "kind": "text", "unique": True, "required": True},
        {"key": "score", "label": "Score", "kind": "number"},
    ])
    url = f"/api/datasets/{dataset['id']}"
    insert(client, f"{url}/rows", ticket="A")
    upsert = save(client, graph("Upsert tickets", dataset_node(dataset["id"], "upsert_row", {"key": "ticket", "values": {"ticket": "{{ticket}}"}})))
    body = set_unique(client, url, dataset, "ticket", False, status=409)
    assert body["error"]["code"] == "DATASET_SCHEMA_INCOMPATIBLE"
    assert body["error"]["details"] == {"field": "ticket", "workflow_id": upsert, "workflow": "Upsert tickets"}
    call(client, "DELETE", f"/api/workflows/{upsert}")
    remover = save(client, graph("Delete tickets", dataset_node(dataset["id"], "delete_row", {"key": "ticket", "value": "{{ticket}}"})))
    assert set_unique(client, url, dataset, "ticket", False, status=409)["error"]["details"]["workflow_id"] == remover
    call(client, "DELETE", f"/api/workflows/{remover}")
    save(client, graph("Find tickets", dataset_node(dataset["id"], "find_rows", {"filters": [{"field": "ticket", "op": "eq", "value": "A"}]})))
    updated = set_unique(client, url, dataset, "ticket", False)["data"]
    assert column(updated, "ticket")["unique"] is False and key_count(db, dataset["id"], "ticket") == 0
    assert insert(client, f"{url}/rows", ticket="A")["values"]["ticket"] == "A"
    error(client.put(f"{url}/columns/ticket", headers=auth("owner"), json={
        "revision": updated["revision"], "column": {**column(updated, "ticket"), "unique": True}}), 409, "DATASET_UNIQUE_DUPLICATES")


def test_concurrent_insert_during_backfill_never_leaves_duplicates(client, db):
    for attempt in range(4):
        dataset = create(client, name=f"Race {attempt}", columns=[{"key": "code", "label": "Code", "kind": "text"}])
        url = f"/api/datasets/{dataset['id']}"
        insert(client, f"{url}/rows", code="X")

        def mark():
            return client.put(f"{url}/columns/code", headers=auth("owner"), json={
                "revision": dataset["revision"], "column": {**column(dataset, "code"), "unique": True}})

        def duplicate():
            return client.post(f"{url}/rows", headers=auth("owner"), json={"values": {"code": "X"}})

        with ThreadPoolExecutor(max_workers=2) as pool:
            marked, inserted = [future.result() for future in (pool.submit(mark), pool.submit(duplicate))]
        assert not (marked.status_code == 200 and inserted.status_code == 201), (marked.text, inserted.text)
        values = [item["values"]["code"] for item in call(client, "POST", f"{url}/rows/query", body={})["items"]]
        if marked.status_code == 200:
            assert values == ["X"] and key_count(db, dataset["id"], "code") == 1
        else:
            assert marked.json()["error"]["code"] in {"DATASET_UNIQUE_DUPLICATES", "DATASET_SCHEMA_CONFLICT"}
