import csv
import io

from test_dataset_rows import call, insert, query
from test_datasets import auth, client, create, error  # noqa: F401
from test_identity_migration import db  # noqa: F401

PREVIEW = "/api/datasets/csv/preview"
IMPORT = "/api/datasets/csv/import"


def test_csv_creates_typed_dataset_after_preview(client):
    text = '\ufeffTicket,Subject,Score,Done\r\nA,"Line one, comma\r\nline two",0,false\r\nB,"=""quoted""",2,true\r\n'
    preview = call(client, "POST", PREVIEW, body={"text": text})
    assert preview["mapping"] == ["ticket", "subject", "score", "done"]
    assert [column["kind"] for column in preview["columns"]] == ["text", "text", "number", "boolean"]
    assert preview["sample"][1]["row"] == 4
    assert call(client, "GET", "/api/datasets")["items"] == []
    columns = preview["columns"]
    columns[0]["unique"] = True
    columns[0]["required"] = True
    params = {"text": text, "mapping": preview["mapping"], "create": {"name": "Imported", "team_id": "support", "columns": columns}}
    imported = call(client, "POST", IMPORT, body=params)
    assert imported["imported"] == 2
    dataset = imported["dataset"]
    rows = f"/api/datasets/{dataset['id']}/rows"
    assert [item["values"] for item in query(client, rows)["items"]] == [
        {"ticket": "A", "subject": "Line one, comma\r\nline two", "score": 0, "done": False},
        {"ticket": "B", "subject": '="quoted"', "score": 2, "done": True},
    ]
    error(client.post(IMPORT, headers=auth("owner"), json=params), 409, "DATASET_NAME_TAKEN")
    exported = client.get(f"/api/datasets/{dataset['id']}/csv", headers=auth("member"))
    assert exported.status_code == 200
    assert "attachment;" in exported.headers["content-disposition"]
    records = list(csv.reader(io.StringIO(exported.content.decode("utf-8-sig"), newline="")))
    assert records == [["Ticket", "Subject", "Score", "Done"],
                       ["A", "Line one, comma\r\nline two", "0.0", "false"],
                       ["B", '\'="quoted"', "2.0", "true"]]


def test_csv_reports_bad_rows_and_does_not_apply_partial_import(client):
    dataset = create(client, name="Tickets", team_id="support", columns=[
        {"key": "ticket", "kind": "text", "label": "Ticket", "required": True, "unique": True},
        {"key": "score", "kind": "number", "label": "Score"},
    ])
    url = f"/api/datasets/{dataset['id']}"
    insert(client, f"{url}/rows", ticket="A")
    payload = {"dataset_id": dataset["id"], "schema_revision": 1, "text": "Ticket,Score\nB,1\nA,2\nC,no\nD\n"}
    preview = call(client, "POST", PREVIEW, body=payload)
    assert [(item["row"], item["error"]["code"]) for item in preview["issues"]] == [
        (4, "DATASET_VALUE_INVALID"), (5, "DATASET_CSV_INVALID"), (3, "DATASET_UNIQUE_CONFLICT"),
    ]
    error(client.post(IMPORT, headers=auth("owner"), json=payload), 400, "DATASET_CSV_ROWS_INVALID")
    assert len(query(client, f"{url}/rows")["items"]) == 1
    error(client.post(PREVIEW, headers=auth("member"), json=payload), 403, "PERMISSION_DENIED")
    error(client.get(f"{url}/csv", headers=auth("other")), 404, "DATASET_NOT_FOUND")
    error(client.post(IMPORT, headers=auth("owner"), json={**payload, "schema_revision": 2}), 409, "DATASET_SCHEMA_CONFLICT")


def test_csv_export_includes_multiple_pages_and_escapes_formula_strings(client):
    dataset = create(client, name="Tickets", columns=[
        {"key": "value", "kind": "text", "label": "=Field"},
    ])
    base = f"/api/datasets/{dataset['id']}"
    text = "Value\n" + "\n".join(["@SUM(1)", *map(str, range(59))])
    assert call(client, "POST", IMPORT, body={
        "text": text, "dataset_id": dataset["id"], "schema_revision": 1, "mapping": ["value"],
    })["imported"] == 60
    exported = client.get(f"{base}/csv", headers=auth("owner"))
    records = list(csv.reader(io.StringIO(exported.content.decode("utf-8-sig"))))
    assert len(records) == 61
    assert records[:2] == [["'=Field"], ["'@SUM(1)"]]
    assert records[-1] == ["58"]
