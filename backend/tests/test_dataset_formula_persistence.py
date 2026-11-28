import csv
import io
from concurrent.futures import ThreadPoolExecutor

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.api import deps
from app.core.errors import AppError
from app.engine import dataset_export
from app.models.database import MIGRATIONS_DIR
from app.repositories import datasets as dataset_repository
from test_dataset_connected import post as connected_post, token
from test_dataset_rows import call, insert, query
from test_dataset_runtime import dataset_node, final, grant, graph, run, save
from test_datasets import auth, client, create, error  # noqa: F401
from test_identity_migration import db  # noqa: F401


def column(key, kind, **settings):
    return {"key": key, "label": key.title(), "kind": kind, **settings}


def formula(key, expression, kind="number"):
    return column(key, kind, formula={"version": 1, "expression": expression})


BASE_COLUMNS = [column("ticket", "text", unique=True), column("hours", "number"), column("rate", "number")]


@pytest.fixture
def enabled(monkeypatch):
    monkeypatch.setenv("STUDIO_ENABLE_DATASET_FORMULAS", "1")


def make_dataset(client, columns=BASE_COLUMNS, *, team_id="support"):
    dataset = create(client, name="Formula tickets", team_id=team_id, columns=columns)
    return dataset, f"/api/datasets/{dataset['id']}"


def add(client, base, column, revision=1):
    return call(client, "POST", f"{base}/columns", body={"revision": revision, "column": column}, status=201)


def test_formula_gate_keeps_existing_definitions_working(client, monkeypatch):
    dataset, base = make_dataset(client)
    enabled_column = formula("cost", "[hours] * [rate]")
    monkeypatch.delenv("STUDIO_ENABLE_DATASET_FORMULAS", raising=False)
    payload = {"revision": 1, "column": enabled_column}
    error(client.post(f"{base}/columns", json=payload, headers=auth("owner")), 403, "DATASET_FORMULA_DISABLED")
    error(client.post("/api/datasets", json={"name": "Disabled", "columns": [formula("constant", "1")]},
                      headers=auth("owner")), 403, "DATASET_FORMULA_DISABLED")
    assert call(client, "GET", base) == dataset

    monkeypatch.setenv("STUDIO_ENABLE_DATASET_FORMULAS", "1")
    add(client, base, enabled_column)
    monkeypatch.delenv("STUDIO_ENABLE_DATASET_FORMULAS", raising=False)
    row = insert(client, f"{base}/rows", ticket="A", hours=2, rate=15)
    assert row["values"]["cost"] == 30
    legacy_column = column("cost", "number", label="Cost label")
    renamed = call(client, "PUT", f"{base}/columns/cost", body={"revision": 2, "column": legacy_column})
    assert renamed["columns"][-1]["formula"] == enabled_column["formula"]
    assert call(client, "GET", f"{base}/rows/{row['id']}") == row


def test_formula_backfill_diagnostics_queries_and_column_changes(client, enabled):
    _, base = make_dataset(client)
    rows = f"{base}/rows"
    first = insert(client, rows, ticket="A", hours=2, rate=20)
    second = insert(client, rows, ticket="B", hours=0, rate=10)
    missing = insert(client, rows, ticket="C", rate=5)
    cost = formula("cost", "[hours] * [rate]")
    adjusted = formula("adjusted", "[rate] / [hours] + [cost]")
    assert add(client, base, cost)["columns"][-1]["formula"] == cost["formula"]
    add(client, base, adjusted, revision=2)

    ordered = query(client, rows, sorts=[{"field": "cost"}], fields=["ticket", "adjusted", "cost"])
    assert [row["values"] for row in ordered["items"]] == [
        {"ticket": "B", "cost": 0, "adjusted": None},
        {"ticket": "A", "cost": 40, "adjusted": 50},
        {"ticket": "C", "cost": None, "adjusted": None},
    ]
    assert ordered["items"][0]["formula_errors"] == {"adjusted": "division_by_zero"}
    assert "formula_errors" not in ordered["items"][2]
    assert "formula_errors" not in query(client, rows, fields=["ticket"])["items"][1]
    filtered = query(client, rows, filters=[{"field": "cost", "op": "gte", "value": 10}])
    assert [row["id"] for row in filtered["items"]] == [first["id"]]
    summary = call(client, "POST", f"{rows}/summary", uid="member", body={"summaries": {"adjusted": "sum"}})
    assert summary["values"] == {"adjusted": 50}

    bad_formula = client.put(f"{base}/columns/cost", headers=auth("owner"), json={
        "revision": 3, "column": formula("cost", "[adjusted]"),
    })
    error(bad_formula, 400, "DATASET_FORMULA_INVALID")
    assert bad_formula.json()["error"]["details"]["reason"] == "cycle"
    error(client.delete(f"{base}/columns/hours?revision=3", headers=auth("owner")), 400, "DATASET_FORMULA_INVALID")
    error(client.patch(f"{rows}/{first['id']}", headers=auth("owner"),
                       json={"revision": first["revision"], "values": {"hours": 5}}), 409, "DATASET_ROW_CONFLICT")
    error(client.post(rows, headers=auth("owner"), json={"values": {"cost": 1}}), 400, "DATASET_COLUMN_READ_ONLY")

    updated = call(client, "PUT", f"{base}/columns/cost", body={"revision": 3, "column": formula("cost", "[rate] * 2")})
    assert updated["revision"] == 4
    a = call(client, "GET", f"{rows}/{first['id']}")
    b = call(client, "GET", f"{rows}/{second['id']}")
    c = call(client, "GET", f"{rows}/{missing['id']}")
    assert (a["values"]["adjusted"], b["values"]["cost"], c["values"]["cost"]) == (50, 20, 10)
    assert b["formula_errors"] == {"adjusted": "division_by_zero"}
    assert a["revision"] == 3  # writes whose derived values did not change preserve the row revision
    call(client, "DELETE", f"{base}/columns/adjusted?revision=4")
    after = call(client, "GET", f"{rows}/{second['id']}")
    assert "adjusted" not in after["values"] and "formula_errors" not in after
    error(client.get(f"{rows}/{first['id']}", headers=auth("other")), 404, "DATASET_NOT_FOUND")


def test_formula_batch_undo_csv_and_auto_number(client, enabled):
    data, base = make_dataset(client, [*BASE_COLUMNS, column("seq", "auto_number"), formula("cost", "[seq] * [hours]")])
    rows = f"{base}/rows"
    original = insert(client, rows, ticket="A", hours=3)
    assert original["values"]["cost"] == 3
    imported = {
        "dataset_id": data["id"], "schema_revision": 1, "text": "Ticket,Hours,Cost\nB,4,999\n",
    }
    preview = call(client, "POST", "/api/datasets/csv/preview", body=imported)
    assert preview["mapping"] == ["ticket", "hours", None]
    error(client.post("/api/datasets/csv/import", headers=auth("owner"),
                      json={**imported, "mapping": ["ticket", "hours", "cost"]}), 400, "DATASET_CSV_MAPPING_INVALID")
    assert call(client, "POST", "/api/datasets/csv/import", body=imported)["imported"] == 1
    conflict = client.patch(f"{rows}/batch", headers=auth("owner"), json={"schema_revision": 1, "rows": [
        {"id": original["id"], "revision": original["revision"], "values": {"hours": 5}},
    ], "append": [{"ticket": "B", "hours": 1}]})
    error(conflict, 409, "DATASET_BATCH_CONFLICT")
    assert call(client, "GET", f"{rows}/{original['id']}") == original
    saved = call(client, "PATCH", f"{rows}/batch", body={"schema_revision": 1, "rows": [
        {"id": original["id"], "revision": original["revision"], "values": {"hours": 5}},
    ], "append": [{"ticket": "C", "hours": 2}]})
    assert saved["rows"][0]["previous"] == {"hours": 3}
    assert call(client, "GET", f"{rows}/{original['id']}")["values"]["cost"] == 5
    added, = saved["added"]
    assert call(client, "GET", f"{rows}/{added['id']}")["values"]["cost"] == 6

    edit, = saved["rows"]
    call(client, "PATCH", f"{rows}/batch", body={"schema_revision": 1, "rows": [
        {"id": edit["id"], "revision": edit["revision"], "values": edit["previous"]},
    ], "remove": {added["id"]: added["revision"]}})
    assert call(client, "GET", f"{rows}/{original['id']}")["values"]["cost"] == 3
    exported = client.get(f"{base}/csv", headers=auth("member"))
    assert exported.status_code == 200
    values = {record["Ticket"]: float(record["Cost"]) for record in csv.DictReader(io.StringIO(exported.content.decode("utf-8-sig")))}
    assert values == {"A": 3, "B": 8}


def test_formula_connected_receipts_scope_workflow_and_export_contract(client, enabled):
    data, base = make_dataset(client, [*BASE_COLUMNS, formula("cost", "[rate] / [hours]")], team_id=None)
    contract = [{key: value for key, value in definition.items() if key != "label"} for definition in data["columns"]]
    writer = token(client, base, "write")["token"]
    reader = token(client, base, "read")["token"]
    request = {"version": 1, "operation": "upsert_row", "columns": contract, "fields": [],
               "operation_id": "import:ticket",
               "arguments": {"key": "ticket", "values": {"ticket": "A", "hours": 0, "rate": 30}}}
    saved = connected_post(client, base, writer, request)
    assert saved.status_code == 200, saved.text
    saved = saved.json()["data"]
    assert set(saved["row"]) == {"id", "revision"}
    assert connected_post(client, base, writer, request).json()["data"] == saved
    error(connected_post(client, base, writer, {**request, "operation_id": "direct",
          "arguments": {"key": "ticket", "values": {"ticket": "A", "cost": 42}}}), 400, "DATASET_COLUMN_READ_ONLY")

    read = {"version": 1, "operation": "get_row", "columns": contract, "fields": ["cost"],
            "arguments": {"row_id": saved["row"]["id"]}}
    row = connected_post(client, base, reader, read).json()["data"]
    assert row["values"] == {"cost": None} and row["formula_errors"] == {"cost": "division_by_zero"}
    old_contract = [field for field in contract if field["key"] != "cost"]
    result = connected_post(client, base, reader, {**read, "fields": ["ticket"], "columns": old_contract})
    assert result.status_code == 200 and "formula_errors" not in result.json()["data"]
    error(connected_post(client, base, reader, {**read, "columns": old_contract}), 409, "DATASET_BINDING_SCHEMA_MISMATCH")
    old_write = connected_post(client, base, writer, {
        **request, "columns": old_contract, "operation_id": "legacy:ticket",
        "arguments": {"key": "ticket", "values": {"ticket": "B", "hours": 2, "rate": 30}},
    })
    assert old_write.status_code == 200, old_write.text
    second_id = old_write.json()["data"]["row"]["id"]
    assert call(client, "GET", f"{base}/rows/{second_id}")["values"]["cost"] == 15

    preview = deps.dataset_row_service().save("owner", data["id"], values={"ticket": "A", "hours": 2},
                                              schema_revision=1, key="ticket", fields=["cost"], dry_run=True)
    assert preview["row"]["values"] == {"cost": 15}
    assert call(client, "GET", f"{base}/rows/{saved['row']['id']}")["values"]["cost"] is None

    node = dataset_node(data["id"], "upsert_row", {"key": "ticket", "values": {"ticket": "A", "hours": 3}}, ["cost"])
    forbidden = graph("Write computed field", dataset_node(
        data["id"], "upsert_row", {"key": "ticket", "values": {"ticket": "A", "cost": 2}}, ["cost"],
    ))
    error(client.post("/api/workflows", headers=auth("owner"), json=forbidden), 400, "DATASET_COLUMN_READ_ONLY")
    workflow = graph("Update formula sources", node)
    wid = save(client, workflow)
    grant(client, data["id"], wid, "read_write")
    computed = final(run(client, {"workflow_id": wid}))["row"]
    assert computed["values"] == {"cost": 10} and "formula_errors" not in computed
    exported = dataset_export.prepare([workflow], lambda _: data["columns"], phase3=True)
    cost = next(column for column in exported.bindings["DATASET_1"]["columns"] if column["key"] == "cost")
    assert cost["formula"] == {"version": 1, "expression": "[rate] / [hours]"}
    with pytest.raises(AppError) as read_only:
        dataset_export.prepare([forbidden], lambda _: data["columns"], phase3=True)
    assert read_only.value.code == "DATASET_COLUMN_READ_ONLY"


def test_formula_schema_definition_and_row_write_serialize(client, enabled):
    _, base = make_dataset(client)
    add(client, base, formula("cost", "[hours] * [rate]"))
    rows = f"{base}/rows"
    row = insert(client, rows, ticket="A", hours=2, rate=10)

    def revise():
        return client.put(f"{base}/columns/cost", headers=auth("owner"), json={
            "revision": 2, "column": formula("cost", "[hours] * [rate] + 1"),
        })

    def patch():
        return client.patch(f"{rows}/{row['id']}", headers=auth("owner"), json={
            "schema_revision": 2, "revision": row["revision"], "values": {"hours": 9},
        })

    with ThreadPoolExecutor(max_workers=2) as pool:
        definition, change = pool.submit(revise), pool.submit(patch)
        assert definition.result().status_code == 200
        assert change.result().status_code in {200, 409}
    persisted = call(client, "GET", f"{rows}/{row['id']}")
    assert persisted["values"]["cost"] == persisted["values"]["hours"] * 10 + 1


def test_formula_backfill_rolls_back_schema_and_earlier_pages(client, enabled, monkeypatch):
    _, base = make_dataset(client, [column("notes", "long_text")])
    rows = f"{base}/rows"
    ordered = sorted([insert(client, rows, notes="a"), insert(client, rows, notes="b")], key=lambda row: row["id"])
    latest = call(client, "PATCH", f"{rows}/{ordered[1]['id']}", body={
        "revision": 1, "values": {"notes": "z" * 80},
    })["row"]
    monkeypatch.setattr(dataset_repository, "KEY_BATCH", 1)
    monkeypatch.setattr(dataset_repository, "MAX_ROW_BYTES", 128)
    error(client.post(f"{base}/columns", headers=auth("owner"), json={
        "revision": 1, "column": formula("copied", "[notes] & [notes]", kind="text"),
    }), 413, "DATASET_ROW_TOO_LARGE")
    assert call(client, "GET", base)["revision"] == 1
    assert call(client, "GET", f"{rows}/{ordered[0]['id']}") == ordered[0]
    assert call(client, "GET", f"{rows}/{latest['id']}") == latest


def test_formula_migration_preserves_legacy_rows_and_guards_downgrade(client, db, enabled):
    _, base = make_dataset(client)
    rows = f"{base}/rows"
    legacy = insert(client, rows, ticket="A", hours=2, rate=15)
    cfg = Config()
    cfg.set_main_option("script_location", MIGRATIONS_DIR)

    def downgrade():
        with db.engine.begin() as connection:
            cfg.attributes["connection"] = connection
            command.downgrade(cfg, "0071_dataset_column_rules")

    downgrade()
    assert "formula_errors" not in {item["name"] for item in inspect(db.engine).get_columns("dataset_rows")}
    db.migrate()
    assert call(client, "GET", f"{rows}/{legacy['id']}") == legacy

    add(client, base, formula("cost", "[hours] * [rate]"))
    with pytest.raises(RuntimeError, match="Remove active Dataset Formula"):
        downgrade()
    current = call(client, "GET", f"{rows}/{legacy['id']}")
    assert current["values"]["cost"] == 30
    call(client, "DELETE", f"{base}/columns/cost?revision=2")
    downgrade()
    db.migrate()
    assert call(client, "GET", f"{rows}/{legacy['id']}")["values"] == legacy["values"]


def test_formula_preview_uses_saved_rows_or_transitive_sample_inputs(client, enabled):
    data, base = make_dataset(client, [*BASE_COLUMNS, formula("cost", "[hours] * [rate]")])
    rows = f"{base}/rows"
    row = insert(client, rows, ticket="A", hours=4, rate=20)
    preview = f"{base}/columns/formula/preview"
    request = {"revision": 1, "column": formula("result", "[cost] / [hours]")}
    assert data["formula_config_enabled"] is True
    assert call(client, "POST", preview, body={**request, "row_id": row["id"]}) == {
        "value": 20, "inputs": ["hours", "rate"], "error": None,
    }
    assert call(client, "POST", preview, body={**request, "sample": {"hours": 0, "rate": 5}}) == {
        "value": None, "inputs": ["hours", "rate"], "error": "division_by_zero",
    }
    assert call(client, "POST", preview, body=request) == {
        "value": None, "inputs": ["hours", "rate"], "error": None,
    }
    changed = {"revision": 1, "column": formula("cost", "[rate] + 2")}
    assert call(client, "POST", preview, body={**changed, "row_id": row["id"]})["value"] == 22
    assert call(client, "GET", f"{rows}/{row['id']}") == row
    assert call(client, "GET", base) == data
    error(client.post(preview, json=request, headers=auth("member")), 403, "PERMISSION_DENIED")
    error(client.post(preview, json=request, headers=auth("other")), 404, "DATASET_NOT_FOUND")
    error(client.post(preview, json={**request, "row_id": "missing"}, headers=auth("owner")), 404, "DATASET_ROW_NOT_FOUND")
    error(client.post(preview, json={**request, "revision": 2}, headers=auth("owner")), 409, "DATASET_SCHEMA_CONFLICT")
    failure = client.post(preview, json={**request, "column": formula("result", "[missing]")}, headers=auth("owner"))
    error(failure, 400, "DATASET_FORMULA_INVALID")
    assert failure.json()["error"]["details"] == {"reason": "unknown_field", "offset": 0, "dependency": "missing", "field": "result"}
