"""One support-ticket path: CSV import, lookup, upsert, denial, and a standalone snapshot."""
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import zipfile

from test_dataset_rows import call
from test_dataset_runtime import save
from test_datasets import auth, client, error  # noqa: F401
from test_identity_migration import db  # noqa: F401
from test_python_export import E, F, N


def test_support_ticket_import_lookup_upsert_and_snapshot(client, db, tmp_path):
    text = "Ticket,Subject,Score\nA,Printer jam,0\nB,New laptop,1\n"
    preview = call(client, "POST", "/api/datasets/csv/preview", body={"text": text})
    columns = preview["columns"]
    columns[0]["unique"] = True
    columns[0]["required"] = True
    imported = call(client, "POST", "/api/datasets/csv/import", body={
        "text": text, "mapping": preview["mapping"],
        "create": {"name": "Support tickets", "columns": columns},
    })
    dataset = imported["dataset"]
    assert imported["imported"] == 2
    rows = f"/api/datasets/{dataset['id']}/rows"
    found = call(client, "POST", f"{rows}/query", body={"filters": [{"field": "ticket", "op": "eq", "value": "A"}], "fields": ["ticket", "score"]})
    assert found["items"][0]["values"] == {"ticket": "A", "score": 0.0}
    updated = call(client, "POST", f"{rows}/upsert", body={"key": "ticket", "values": {"ticket": "A", "score": 2}})
    assert updated["row"]["values"]["score"] == 2 and updated["inserted"] is False
    error(client.get(f"/api/datasets/{dataset['id']}/csv", headers=auth("other")), 404, "DATASET_NOT_FOUND")
    error(client.post("/api/datasets/csv/import", headers=auth("owner"), json={
        "text": text, "dataset_id": dataset["id"], "schema_revision": dataset["revision"] + 1, "mapping": ["ticket", "subject", "score"],
    }), 409, "DATASET_SCHEMA_CONFLICT")

    nodes = [N("start", "start"),
             N("found", "dataset", label="Found", dataset_id=dataset["id"], operation="find_rows",
               fields=["ticket", "score"], arguments={"filters": [{"field": "ticket", "op": "eq", "value": "A"}]}, output_field="found"),
             N("end", "end")]
    wid = save(client, {"name": "Support lookup", "nodes": nodes, "edges": [E("start", "found"), E("found", "end")],
                        "state": [F("found", "object")]})
    response = client.get(f"/api/workflows/{wid}/export/python/project", headers=auth("owner"),
                          params={"backend": "DATASET_1:sqlite", "snapshot": "DATASET_1"})
    assert response.status_code == 200, response.text
    folder = tmp_path / "project"
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        archive.extractall(folder)
    script = next(folder.rglob("agent.py"))
    database = tmp_path / "tickets.sqlite3"
    env = os.environ.copy()
    env.update(DATASET_1_BACKEND="sqlite", DATASET_1_ID="tickets", DATASET_1_SQLITE_PATH=str(database), LLM_PROVIDER="")
    ready = subprocess.run([sys.executable, "-I", str(script), "--setup-datasets"], cwd=script.parent, env=env,
                           capture_output=True, text=True, timeout=60)
    assert ready.returncode == 0, ready.stderr
    with sqlite3.connect(database) as connection:
        stored = [json.loads(row[0]) for row in connection.execute('select "values" from superstep_dataset_rows order by created')]
    restored = [{key: item[key] for key in ("ticket", "score")} for item in stored]
    assert any(item["ticket"] == "A" and item["score"] in (2, 2.0) for item in restored)
    again = subprocess.run([sys.executable, "-I", str(script), "--setup-datasets"], cwd=script.parent, env=env,
                           capture_output=True, text=True, timeout=60)
    assert again.returncode == 0, again.stderr
    with sqlite3.connect(database) as connection:
        assert connection.execute("select count(*) from superstep_dataset_rows").fetchone()[0] == 2
