import csv
import io

from test_dataset_rows import call, insert
from test_datasets import auth, client, create, error  # noqa: F401
from test_identity_migration import db  # noqa: F401


COLUMNS = [
    {"key": "notes", "label": "Notes", "kind": "long_text"},
    {"key": "site", "label": "Site", "kind": "url"},
    {"key": "created_at", "label": "Created", "kind": "created_time"},
    {"key": "updated_at", "label": "Updated", "kind": "updated_time"},
]


def test_scalar_columns_validate_csv_and_query(client):
    dataset = create(client, name="Scalar types", columns=COLUMNS)
    base = f"/api/datasets/{dataset['id']}"
    rows = f"{base}/rows"
    notes = "First line\nSecond line"
    first = insert(client, rows, notes=notes, site="https://example.org/case")
    assert first["values"]["notes"] == notes
    assert first["values"]["created_at"] == first["values"]["updated_at"]
    assert first["values"]["created_at"].endswith("Z")
    error(client.post(rows, headers=auth("owner"), json={"values": {"created_at": first["values"]["created_at"]}}),
          400, "DATASET_COLUMN_READ_ONLY")
    for site in ["javascript:alert(1)", "https://", "https://example.org:bogus", "https://user@example.org"]:
        error(client.post(rows, headers=auth("owner"), json={"values": {"site": site}}), 400, "DATASET_VALUE_INVALID")

    result = call(client, "POST", "/api/datasets/csv/import", body={
        "dataset_id": dataset["id"], "schema_revision": dataset["revision"],
        "text": 'Notes,Site,Created\n"Later\ntext",http://example.com,2000-01-01\n',
    })
    assert result["imported"] == 1
    updated = call(client, "PATCH", f"{rows}/{first['id']}", body={
        "revision": first["revision"], "values": {"notes": notes + "\nEdited"},
    })["row"]
    assert updated["values"]["created_at"] == first["values"]["created_at"]
    assert updated["values"]["updated_at"] >= first["values"]["updated_at"]
    query = call(client, "POST", f"{rows}/query", body={
        "filters": [{"field": "created_at", "op": "eq", "value": first["values"]["created_at"]},
                    {"field": "site", "op": "contains", "value": "example.org"}],
        "sorts": [{"field": "updated_at", "descending": True}],
    })
    assert [item["id"] for item in query["items"]] == [first["id"]]

    result = client.get(f"{base}/csv", headers=auth("owner"))
    assert result.status_code == 200
    output = list(csv.DictReader(io.StringIO(result.content.decode("utf-8-sig"))))
    assert output[0]["Notes"] == updated["values"]["notes"]
    assert output[0]["Created"] == first["values"]["created_at"]
    assert output[1]["Site"] == "http://example.com" and output[1]["Created"].endswith("Z")
