import json
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import func, select

from app.models import DatasetRowKey
from test_agent_node import wf
from test_dataset_agent_tool import write_tool
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
    agent = save(client, wf(tools=[write_tool(dataset["id"], operations=["upsert_row"], fields=["ticket"], write_fields=["ticket"])]))
    assert set_unique(client, url, dataset, "ticket", False, status=409)["error"]["details"]["workflow_id"] == agent
    call(client, "DELETE", f"/api/workflows/{agent}")
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


def raw_rows(db, dataset_id):
    from app.models import DatasetRow
    with db.session() as session:
        return [row.values for row in session.scalars(select(DatasetRow).where(DatasetRow.dataset_id == dataset_id).order_by(DatasetRow.created))]


def test_removed_columns_free_the_active_limit_and_keep_keys_reserved(client, monkeypatch):
    from app.services import dataset_service
    dataset = create(client, name="Wide", columns=[{"key": f"c{i}", "label": f"C{i}", "kind": "text"} for i in range(100)])
    url = f"/api/datasets/{dataset['id']}"
    extra = {"key": "extra", "label": "Extra", "kind": "text"}
    body = client.post(f"{url}/columns", headers=auth("owner"), json={"revision": 1, "column": extra}).json()
    assert body["error"]["code"] == "DATASET_COLUMN_LIMIT" and body["error"]["details"] == {"max": 100}
    revision = call(client, "DELETE", f"{url}/columns/c0?revision=1")["revision"]
    added = call(client, "POST", f"{url}/columns", body={"revision": revision, "column": extra}, status=201)
    assert len(added["columns"]) == 100 and "c0" not in [item["key"] for item in added["columns"]]
    revision = call(client, "DELETE", f"{url}/columns/c1?revision={added['revision']}")["revision"]
    error(client.post(f"{url}/columns", headers=auth("owner"), json={
        "revision": revision, "column": {"key": "c0", "label": "Again", "kind": "text"}}), 409, "DATASET_COLUMN_KEY_TAKEN")
    monkeypatch.setattr(dataset_service, "MAX_COLUMN_DEFINITIONS", 101)
    body = client.post(f"{url}/columns", headers=auth("owner"), json={
        "revision": revision, "column": {"key": "another", "label": "Another", "kind": "text"}}).json()
    assert body["error"]["code"] == "DATASET_COLUMN_LIMIT" and body["error"]["details"] == {"max": 101}


def test_removing_a_column_clears_its_values_in_batches(client, db, monkeypatch):
    import json as jsonlib
    from app.models import AuditEvent
    from app.repositories import datasets as repository
    monkeypatch.setattr(repository, "CLEAR_BATCH", 2)
    dataset = create(client, name="Clear", columns=[
        {"key": "ticket", "label": "Ticket", "kind": "text", "unique": True},
        {"key": "title", "label": "Title", "kind": "text"},
    ])
    url = f"/api/datasets/{dataset['id']}"
    for index in range(5):
        insert(client, f"{url}/rows", ticket=f"T-{index}", title=None if index == 4 else f"Title {index}")
    revision = call(client, "DELETE", f"{url}/columns/ticket?revision=1")["revision"]
    assert all("ticket" not in values for values in raw_rows(db, dataset["id"]))
    assert key_count(db, dataset["id"], "ticket") == 0
    call(client, "DELETE", f"{url}/columns/title?revision={revision}")
    assert raw_rows(db, dataset["id"]) == [{}] * 5
    with db.session() as session:
        events = list(session.scalars(select(AuditEvent).where(AuditEvent.action == "dataset.column_remove").order_by(AuditEvent.ts)))
        assert [jsonlib.loads(event.details) for event in events] == [{"field": "ticket", "rows": 5}, {"field": "title", "rows": 5}]
    exported = client.get(f"{url}/csv", headers=auth("owner"))
    assert exported.status_code == 200 and "Ticket" not in exported.text and "Title" not in exported.text


def test_export_snapshot_excludes_removed_keys(client, db):
    from app.api import deps
    dataset = create(client, name="Snapshot", columns=[
        {"key": "ticket", "label": "Ticket", "kind": "text"}, {"key": "secret", "label": "Secret", "kind": "text"},
    ])
    url = f"/api/datasets/{dataset['id']}"
    insert(client, f"{url}/rows", ticket="A", secret="hidden")
    call(client, "DELETE", f"{url}/columns/secret?revision=1")
    rows = deps.dataset_row_service().export_rows("owner", dataset["id"], 10)
    assert [row["values"] for row in rows] == [{"ticket": "A"}]
    assert raw_rows(db, dataset["id"]) == [{"ticket": "A"}]


def test_required_column_with_default_backfills_existing_rows(client, db):
    dataset = create(client, name="Backfill", columns=[{"key": "ticket", "label": "Ticket", "kind": "text"}])
    url = f"/api/datasets/{dataset['id']}"
    for ticket in ("A", "B"):
        insert(client, f"{url}/rows", ticket=ticket)
    error(client.post(f"{url}/columns", headers=auth("owner"), json={
        "revision": 1, "column": {"key": "status", "label": "Status", "kind": "text", "required": True}}), 409, "DATASET_SCHEMA_HAS_ROWS")
    added = call(client, "POST", f"{url}/columns", body={"revision": 1, "column": {
        "key": "status", "label": "Status", "kind": "select", "required": True, "options": ["Open", "Closed"], "default": "Open"}}, status=201)
    assert [values["status"] for values in raw_rows(db, dataset["id"])] == ["Open", "Open"]
    found = call(client, "POST", f"{url}/rows/query", body={"filters": [{"field": "status", "op": "eq", "value": "Open"}]})["items"]
    assert len(found) == 2
    revision = added["revision"]
    body = client.post(f"{url}/columns", headers=auth("owner"), json={"revision": revision, "column": {
        "key": "code", "label": "Code", "kind": "number", "required": True, "unique": True, "default": 7}}).json()
    assert body["error"]["code"] == "DATASET_UNIQUE_DUPLICATES" and body["error"]["details"]["count"] == 2
    assert all("code" not in values for values in raw_rows(db, dataset["id"]))
    assert call(client, "GET", url)["revision"] == revision
    flag = call(client, "POST", f"{url}/columns", body={"revision": revision, "column": {
        "key": "done", "label": "Done", "kind": "boolean", "required": True, "default": False}}, status=201)
    assert [values["done"] for values in raw_rows(db, dataset["id"])] == [False, False]
    assert flag["revision"] == revision + 1


def test_required_default_checks_the_row_byte_limit_first(client, db):
    dataset = create(client, name="Large", columns=[{"key": f"body{i}", "label": f"Body {i}", "kind": "text"} for i in range(4)])
    url = f"/api/datasets/{dataset['id']}"
    insert(client, f"{url}/rows", **{f"body{i}": "x" * 15_000 for i in range(4)})
    before = raw_rows(db, dataset["id"])
    body = client.post(f"{url}/columns", headers=auth("owner"), json={"revision": 1, "column": {
        "key": "extra", "label": "Extra", "kind": "text", "required": True, "default": "y" * 6_000}}).json()
    assert body["error"]["code"] == "DATASET_ROW_TOO_LARGE"
    assert raw_rows(db, dataset["id"]) == before and call(client, "GET", url)["revision"] == 1


def test_schema_row_changes_stay_within_the_query_budget(client, db):
    from uuid import uuid4

    from sqlalchemy import event

    from app.models import DatasetRow
    dataset = create(client, name="Budget", columns=[{"key": "ticket", "label": "Ticket", "kind": "text"},
                                                     {"key": "note", "label": "Note", "kind": "text"}])
    url = f"/api/datasets/{dataset['id']}"
    with db.session() as session:
        session.add_all(DatasetRow(dataset_id=dataset["id"], id=uuid4().hex, values={"ticket": f"T-{i}", "note": "n"},
                                   revision=1, created=i, updated=i) for i in range(1_600))
        session.commit()
    statements = []

    def count(*_args):
        statements.append(1)

    event.listen(db.engine, "before_cursor_execute", count)
    try:
        revision = call(client, "DELETE", f"{url}/columns/note?revision=1")["revision"]
        removed = len(statements)
        statements.clear()
        call(client, "POST", f"{url}/columns", body={"revision": revision, "column": {
            "key": "state", "label": "State", "kind": "text", "required": True, "default": "new"}}, status=201)
        added = len(statements)
    finally:
        event.remove(db.engine, "before_cursor_execute", count)
    assert removed <= 30 and added <= 30, (removed, added)
    values = raw_rows(db, dataset["id"])
    assert len(values) == 1_600 and all(item == {"ticket": item["ticket"], "state": "new"} for item in values)
