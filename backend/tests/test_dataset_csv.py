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


def test_csv_round_trip_keeps_leading_zeros_plus_signs_and_formulas(client):
    keys = ["code", "phone", "formula", "note", "long"]
    values = [
        {"code": "00123", "phone": "+84901234567", "formula": "=SUM(A1)", "note": "'=already guarded", "long": "1234567890123456"},
        {"code": "007", "phone": "+15550100", "formula": "-5", "note": "it's fine", "long": "9876543210987654"},
    ]
    source = create(client, name="Contacts", team_id="support",
                    columns=[{"key": key, "kind": "text", "label": key.title()} for key in keys])
    for row in values:
        insert(client, f"/api/datasets/{source['id']}/rows", **row)
    exported = client.get(f"/api/datasets/{source['id']}/csv", headers=auth("owner")).content.decode("utf-8-sig")
    records = list(csv.reader(io.StringIO(exported, newline="")))
    assert records[1] == ["00123", "'+84901234567", "'=SUM(A1)", "''=already guarded", "1234567890123456"]
    preview = call(client, "POST", PREVIEW, body={"text": exported})
    assert [column["kind"] for column in preview["columns"]] == ["text"] * 5
    assert preview["sample"][0]["cells"] == list(values[0].values())
    copy = call(client, "POST", IMPORT, body={"text": exported, "mapping": preview["mapping"],
                                              "create": {"name": "Copy", "team_id": "support", "columns": preview["columns"]}})
    for dataset in (source, copy["dataset"]):
        rows = query(client, f"/api/datasets/{dataset['id']}/rows", sort="code", descending=False)["items"]
        assert [row["values"] for row in rows] == values


def test_csv_infers_codes_phone_numbers_and_long_digit_runs_as_text(client):
    text = "Code,Phone,Long,Score,Ratio\n00123,+84901234567,1234567890123456,0,0.5\n-007,+1,1,12,-1.5\n"
    preview = call(client, "POST", PREVIEW, body={"text": text})
    assert [column["kind"] for column in preview["columns"]] == ["text", "text", "text", "number", "number"]


def test_csv_import_into_a_typed_column_still_reads_numbers(client):
    dataset = create(client, name="Scores", team_id="support", columns=[{"key": "score", "kind": "number", "label": "Score"}])
    call(client, "POST", IMPORT, body={"text": "Score\n007\n'-5\n", "dataset_id": dataset["id"], "schema_revision": 1, "mapping": ["score"]})
    rows = query(client, f"/api/datasets/{dataset['id']}/rows", sort="score", descending=False)["items"]
    assert [row["values"]["score"] for row in rows] == [-5, 7]


def test_studio_deletes_require_the_revision(client):
    dataset = create(client, name="Tickets", columns=[
        {"key": "ticket", "kind": "text", "label": "Ticket"}, {"key": "note", "kind": "text", "label": "Note"}])
    url = f"/api/datasets/{dataset['id']}"
    row = insert(client, f"{url}/rows", ticket="A")
    row_url = f"{url}/rows/{row['id']}"
    error(client.delete(row_url, headers=auth("owner")), 422, "VALIDATION_ERROR")
    error(client.delete(f"{row_url}?revision={row['revision'] + 1}", headers=auth("owner")), 409, "DATASET_ROW_CONFLICT")
    assert call(client, "DELETE", f"{row_url}?revision={row['revision']}") == {"ok": True}
    error(client.delete(f"{url}/columns/note", headers=auth("owner")), 422, "VALIDATION_ERROR")
    error(client.delete(f"{url}/columns/note?revision=2", headers=auth("owner")), 409, "DATASET_SCHEMA_CONFLICT")
    error(client.delete(url, headers=auth("owner")), 422, "VALIDATION_ERROR")
    error(client.delete(f"{url}?revision=2", headers=auth("owner")), 409, "DATASET_SCHEMA_CONFLICT")
    assert call(client, "DELETE", f"{url}?revision=1") == {"ok": True}
