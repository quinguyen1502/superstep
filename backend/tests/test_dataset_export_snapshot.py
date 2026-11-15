"""Project export chooses a backend per binding and can carry an explicit row snapshot."""
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import zipfile

from test_dataset_connected import dataset
from test_dataset_rows import insert
from test_dataset_runtime import save
from test_datasets import auth, client, error  # noqa: F401
from test_identity_migration import db  # noqa: F401
from test_python_export import E, F, N
from test_typescript_export import DENO, DENO_ARGS, deno_env  # noqa: F401


def workflow(did):
    nodes = [N("start", "start"),
             N("found", "dataset", label="Found", dataset_id=did, operation="find_rows", fields=["ticket"], arguments={}, output_field="found"),
             N("end", "end")]
    return {"name": "Snapshot export", "nodes": nodes, "edges": [E("start", "found"), E("found", "end")],
            "state": [F("found", "object")]}


def download(client, wid, **params):
    response = client.get(f"/api/workflows/{wid}/export/python/project", headers=auth("owner"), params=params)
    assert response.status_code == 200, response.text
    return response.content


def unzip(blob, root):
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        archive.extractall(root)
        return {name: archive.read(name) for name in archive.namelist()}


def test_project_export_keeps_the_graph_and_requires_an_explicit_snapshot(client, db, monkeypatch, tmp_path):
    source = dataset(client, name="Snapshot source")
    secret = "SnapshotSecret"
    row = insert(client, f"/api/datasets/{source['id']}/rows", ticket=secret, score=0, active=False)
    wid = save(client, workflow(source["id"]))
    plain = download(client, wid)
    sqlite_choice = download(client, wid, backend="DATASET_1:sqlite")
    postgres_choice = download(client, wid, backend="DATASET_1:postgresql")

    def member(blob, suffix):
        with zipfile.ZipFile(io.BytesIO(blob)) as archive:
            return archive.read(next(name for name in archive.namelist() if name.endswith(suffix)))

    assert member(plain, "/agent.py") == member(sqlite_choice, "/agent.py") == member(postgres_choice, "/agent.py")
    with zipfile.ZipFile(io.BytesIO(plain)) as archive:
        assert not any(name.endswith("/dataset-snapshots.json") for name in archive.namelist())
        assert all(secret.encode() not in archive.read(name) and source["id"].encode() not in archive.read(name) for name in archive.namelist())
    assert b"DATASET_1_BACKEND=\n" in member(plain, "/.env.example")
    assert b"DATASET_1_BACKEND=sqlite\n" in member(sqlite_choice, "/.env.example")
    files = unzip(sqlite_choice, tmp_path / "plain-choice")
    assert secret.encode() not in b"".join(files.values())

    snap = download(client, wid, backend="DATASET_1:sqlite", snapshot="DATASET_1")
    packed = unzip(snap, tmp_path / "snap")
    snapshot = next(value for name, value in packed.items() if name.endswith("/dataset-snapshots.json"))
    assert secret.encode() in snapshot and source["id"].encode() not in snapshot
    document = json.loads(snapshot)
    assert document["snapshots"][0]["rows"][0]["id"] == row["id"]
    assert b"reads each backend from the environment" in packed[next(name for name in packed if name.endswith("/README.md"))]

    error(client.get(f"/api/workflows/{wid}/export/python/project", headers=auth("owner"), params={"backend": "DATASET_1:superstep", "snapshot": "DATASET_1"}), 400, "DATASET_SNAPSHOT_INVALID")
    error(client.get(f"/api/workflows/{wid}/export/python/project", headers=auth("owner"), params={"backend": "DATASET_1:mysql"}), 400, "DATASET_BINDING_INVALID")
    error(client.get(f"/api/workflows/{wid}/export/python/project", headers=auth("other"), params={"snapshot": "DATASET_1", "backend": "DATASET_1:sqlite"}), 404, "WORKFLOW_NOT_FOUND")
    monkeypatch.setattr("app.services.workflow_service.SNAPSHOT_MAX_ROWS", 0)
    error(client.get(f"/api/workflows/{wid}/export/python/project", headers=auth("owner"), params={"backend": "DATASET_1:sqlite", "snapshot": "DATASET_1"}), 409, "DATASET_SNAPSHOT_TOO_LARGE")


def test_python_setup_restores_a_snapshot_without_overwriting(client, db, tmp_path):
    source = dataset(client, name="Restore source")
    row = insert(client, f"/api/datasets/{source['id']}/rows", ticket="KeepMe", score=1, active=True)
    wid = save(client, workflow(source["id"]))
    folder = tmp_path / "project"
    unzip(download(client, wid, backend="DATASET_1:sqlite", snapshot="DATASET_1"), folder)
    script = next(folder.rglob("agent.py"))
    database = tmp_path / "standalone # data.sqlite3"
    env = os.environ.copy()
    env.update(DATASET_1_BACKEND="sqlite", DATASET_1_ID="tickets", DATASET_1_SQLITE_PATH=str(database), LLM_PROVIDER="")

    def setup():
        return subprocess.run([sys.executable, "-I", str(script), "--setup-datasets"], cwd=script.parent, env=env,
                              capture_output=True, text=True, timeout=60)

    ready = setup()
    assert ready.returncode == 0, ready.stderr
    with sqlite3.connect(database) as connection:
        stored = json.loads(connection.execute('select "values" from superstep_dataset_rows').fetchone()[0])
        assert stored["ticket"] == "KeepMe" and stored["score"] == 1
        connection.execute('update superstep_dataset_rows set "values" = ?', (json.dumps({**stored, "score": 7}),))
        connection.commit()
    again = setup()
    assert again.returncode == 0, again.stderr
    with sqlite3.connect(database) as connection:
        kept = json.loads(connection.execute('select "values" from superstep_dataset_rows').fetchone()[0])
        assert kept["score"] == 7 and connection.execute("select count(*) from superstep_dataset_rows").fetchone()[0] == 1
    snapshot_path = script.parent / "dataset-snapshots.json"
    document = json.loads(snapshot_path.read_text())
    document["snapshots"][0]["contract"]["version"] = 2
    snapshot_path.write_text(json.dumps(document))
    rejected = setup()
    assert rejected.returncode and "DATASET_BINDING_SCHEMA_MISMATCH" in rejected.stderr
    with sqlite3.connect(database) as connection:
        assert json.loads(connection.execute('select "values" from superstep_dataset_rows').fetchone()[0])["score"] == 7
    assert row["id"]


def test_typescript_setup_restores_a_snapshot_without_overwriting(client, db, tmp_path, deno_env):
    source = dataset(client, name="TypeScript snapshot")
    insert(client, f"/api/datasets/{source['id']}/rows", ticket="KeepMe", score=1, active=True)
    wid = save(client, workflow(source["id"]))
    response = client.get(f"/api/workflows/{wid}/export/typescript/project", headers=auth("owner"),
                          params={"backend": "DATASET_1:sqlite", "snapshot": "DATASET_1"})
    assert response.status_code == 200, response.text
    folder = tmp_path / "ts"
    unzip(response.content, folder)
    root = next(path.parent for path in folder.rglob("dataset-snapshots.json"))
    code = client.get(f"/api/workflows/{wid}/export/typescript", headers=auth("owner"))
    assert code.status_code == 200, code.text
    script = root / "deno-agent.ts"
    script.write_text(code.text)
    database = tmp_path / "ts # data.sqlite3"
    env = os.environ.copy()
    env.update(DATASET_1_BACKEND="sqlite", DATASET_1_ID="tickets", DATASET_1_SQLITE_PATH=str(database),
               LLM_PROVIDER="", DENO_DIR=deno_env["DENO_DIR"], NO_COLOR="1")

    def setup():
        return subprocess.run([DENO, "run", "-q", *DENO_ARGS, "--allow-env", "--allow-read", "--allow-write", "--allow-net",
                               "--allow-sys=homedir", str(script), "--setup-datasets"], cwd=root, env=env,
                              capture_output=True, text=True, timeout=180)

    ready = setup()
    assert ready.returncode == 0, ready.stderr
    with sqlite3.connect(database) as connection:
        stored = json.loads(connection.execute('select "values" from superstep_dataset_rows').fetchone()[0])
        connection.execute('update superstep_dataset_rows set "values" = ?', (json.dumps({**stored, "score": 4}),))
        connection.commit()
    again = setup()
    assert again.returncode == 0, again.stderr
    with sqlite3.connect(database) as connection:
        assert json.loads(connection.execute('select "values" from superstep_dataset_rows').fetchone()[0])["score"] == 4
