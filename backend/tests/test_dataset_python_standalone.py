from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import runpy
import subprocess
import sys

import pytest

from test_dataset_connected import dataset, token
from test_dataset_rows import call as rows_call
from test_dataset_project_export import project, target, workflow  # noqa: F401
from test_dataset_runtime import save
from test_datasets import auth, client  # noqa: F401
from test_identity_migration import db  # noqa: F401
from test_python_export import E, F, N


def run_cli(path, *args):
    return subprocess.run([sys.executable, "-I", str(path), *args], cwd=path.parent,
                          capture_output=True, text=True, timeout=45)


def configure(monkeypatch, db, tmp_path, alias="DATASET_1"):
    settings = {"ID": "tickets", "BACKEND": db.engine.dialect.name}
    if settings["BACKEND"] == "sqlite":
        settings["SQLITE_PATH"] = str(tmp_path / "standalone # data.sqlite3")
    else:
        settings["POSTGRES_DSN"] = db.engine.url.render_as_string(hide_password=False)
    for name, value in settings.items():
        monkeypatch.setenv(f"{alias}_{name}", value)
    monkeypatch.setenv("LLM_PROVIDER", "")
    return settings


def test_python_standalone_runs_generated_project_and_replays_receipts(client, db, monkeypatch, tmp_path):
    source = dataset(client, name="Source")
    child = workflow(source["id"])
    child_id = save(client, child)
    parent = {"name": "Standalone parent", "state": child["state"],
              "nodes": [N("start", "start"), N("child", "subgraph", label="Child", workflow_id=child_id), N("end", "end")],
              "edges": [E("start", "child"), E("child", "end")]}
    wid = save(client, parent)
    settings = configure(monkeypatch, db, tmp_path)
    folder = project(client, wid, "python", tmp_path / "export", source["id"])
    script = folder / "agent.py"
    assert "psycopg[binary]>=3.2" in (folder / "requirements.txt").read_text()
    assert "DATASET_1_SQLITE_PATH=\n" in (folder / ".env.example").read_text()

    missing = run_cli(script)
    assert missing.returncode and "DATASET_SETUP_REQUIRED" in missing.stderr
    if settings["BACKEND"] == "sqlite":
        assert not Path(settings["SQLITE_PATH"]).exists()
    setup = run_cli(script, "--setup-datasets")
    assert setup.returncode == 0, setup.stderr
    run = run_cli(script)
    assert run.returncode == 0, run.stderr
    assert "FromExport" in run.stdout and '"dataset"' in run.stdout
    assert run_cli(script, "--setup-datasets").returncode == 0
    exported = runpy.run_path(str(script))
    call = exported["dataset_call"]

    def query(fields, **args):
        return call("DATASET_1", "find_rows", fields, args)

    values = query(["ticket", "score", "active"], filters=[
        {"field": "active", "op": "eq", "value": False},
    ])["items"]
    assert [row["values"] for row in values] == [{"ticket": "FromExport", "score": 1, "active": False}]
    assert values[0]["revision"] == 2

    def upsert(identity, score):
        return call("DATASET_1", "upsert_row", ["ticket", "score"],
                    {"key": "ticket", "values": {"ticket": "Concurrent", "score": score}}, identity)

    with ThreadPoolExecutor(max_workers=2) as workers:
        result = list(workers.map(lambda _: upsert("retry-key", 0), range(2)))
    assert result[0] == result[1] and result[0]["inserted"]
    assert result[0]["row"]["values"]["score"] == 0
    first_id = result[0]["row"]["id"]
    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(lambda n: upsert(f"update-{n}", n), (1, 2)))
    assert {item["row"]["revision"] for item in results} == {2, 3}
    assert all(item["row"]["id"] == first_id and not item["inserted"] for item in results)
    assert upsert("retry-key", 0) == result[0]
    with pytest.raises(RuntimeError, match="DATASET_RECEIPT_CONFLICT"):
        upsert("retry-key", 1)
    with pytest.raises(RuntimeError, match="DATASET_UNIQUE_CONFLICT"):
        call("DATASET_1", "insert_row", ["ticket"], {"values": {"ticket": "Concurrent"}}, "duplicate")
    assert len(query(["ticket"])["items"]) == 2

    changed_column = exported["DATASET_BINDINGS"]["DATASET_1"]["columns"][0]
    changed_column["kind"] = "select"
    with pytest.raises(RuntimeError, match="DATASET_BINDING_SCHEMA_MISMATCH"):
        query(["ticket"])
    with pytest.raises(RuntimeError, match="DATASET_BINDING_SCHEMA_MISMATCH"):
        exported["setup_datasets"](create=True)
    changed_column["kind"] = "text"
    assert len(query(["ticket"])["items"]) == 2
    ids_only = call("DATASET_1", "insert_row", [], {"values": {"ticket": "IdsOnly"}}, "ids-only")
    assert ids_only["inserted"] and set(ids_only["row"]) == {"id", "revision"}
    with pytest.raises(RuntimeError, match="DATASET_NODE_ARGUMENTS_INVALID"):
        query([])
    monkeypatch.setenv("DATASET_1_BACKEND", "mysql")
    malformed = run_cli(script)
    assert malformed.returncode and "DATASET_1_BACKEND" in malformed.stderr
    if settings["BACKEND"] == "sqlite":
        assert Path(settings["SQLITE_PATH"]).is_file()


def test_generated_python_mixes_connected_and_standalone_bindings(client, db, monkeypatch, target, tmp_path):
    source = dataset(client, name="Local source")
    destination = dataset(client, name="API destination")
    url, requests = target
    secret = token(client, f"/api/datasets/{destination['id']}", "read")["token"]
    graph = workflow(source["id"])
    graph["nodes"].insert(-1, N("remote", "dataset", label="Remote", dataset_id=destination["id"],
                                operation="find_rows", fields=["ticket"], arguments={}, output_field="remote"))
    graph["edges"][-1:] = [E("agent", "remote"), E("remote", "end")]
    graph["state"].append({"name": "remote", "type": "object"})
    wid = save(client, graph)
    configure(monkeypatch, db, tmp_path)
    for name, value in {"BACKEND": "superstep", "API_URL": url, "ID": destination["id"], "API_TOKEN": secret}.items():
        monkeypatch.setenv(f"DATASET_2_{name}", value)
    response = client.get(f"/api/workflows/{wid}/export/python", headers=auth("owner"))
    assert response.status_code == 200, response.text
    script = tmp_path / "mixed.py"
    script.write_text(response.text)
    setup = run_cli(script, "--setup-datasets")
    assert setup.returncode == 0, setup.stderr
    assert requests == []
    result = run_cli(script)
    assert result.returncode == 0, result.stderr
    assert "FromExport" in result.stdout and '"remote"' in result.stdout
    assert [request["operation"] for request in requests] == ["find_rows"]


def test_python_standalone_delete_row_locks_replays_and_skips_missing_rows(client, db, monkeypatch, target, tmp_path):
    source = dataset(client, name="Delete source")
    graph = workflow(source["id"])
    graph["nodes"].insert(-1, N("removed", "dataset", label="Removed", dataset_id=source["id"], operation="delete_row",
                                fields=["ticket"], arguments={"key": "ticket", "value": "{{state.updated.row.values.ticket}}"},
                                output_field="removed"))
    destination = dataset(client, name="API read destination")  # one run reads through the API and deletes locally
    graph["nodes"].insert(-1, N("remote", "dataset", label="Remote", dataset_id=destination["id"],
                                operation="find_rows", fields=["ticket"], arguments={}, output_field="remote"))
    graph["edges"][-1:] = [E("agent", "removed"), E("removed", "remote"), E("remote", "end")]
    graph["state"] += [{"name": "removed", "type": "object"}, {"name": "remote", "type": "object"}]
    wid = save(client, graph)
    configure(monkeypatch, db, tmp_path)
    url, requests = target
    secret = token(client, f"/api/datasets/{destination['id']}", "read")["token"]
    for name, value in {"BACKEND": "superstep", "API_URL": url, "ID": destination["id"], "API_TOKEN": secret}.items():
        monkeypatch.setenv(f"DATASET_2_{name}", value)
    response = client.get(f"/api/workflows/{wid}/export/python", headers=auth("owner"))
    assert response.status_code == 200, response.text
    script = tmp_path / "delete.py"
    script.write_text(response.text)
    assert run_cli(script, "--setup-datasets").returncode == 0
    for _ in range(2):  # a deleted row lets the next run insert it again
        run = run_cli(script)
        assert run.returncode == 0, run.stderr
        assert '"deleted": true' in run.stdout
    assert [request["operation"] for request in requests] == ["find_rows", "find_rows"]
    assert run_cli(script, "--setup-datasets").returncode == 0
    exported = runpy.run_path(str(script))
    call = exported["dataset_call"]

    def insert(ticket, identity=None):
        return call("DATASET_1", "insert_row", ["ticket"], {"values": {"ticket": ticket}}, identity or f"insert-{ticket}")["row"]["id"]

    def delete(identity, **arguments):
        return call("DATASET_1", "delete_row", ["ticket"], arguments, identity)

    assert call("DATASET_1", "find_rows", ["ticket"], {})["items"] == []
    with pytest.raises(RuntimeError, match="DATASET_ROW_NOT_FOUND"):
        delete("late", key="ticket", value="Later")
    first = insert("Later")
    assert delete("late", key="ticket", value="Later") == {"row_id": first, "deleted": True}  # the miss stored no receipt
    assert delete("late", key="ticket", value="Later") == {"row_id": first, "deleted": True}
    with pytest.raises(RuntimeError, match="DATASET_RECEIPT_CONFLICT"):
        delete("late", row_id=first)
    with pytest.raises(RuntimeError, match="DATASET_UPSERT_KEY_INVALID"):
        delete("bad-key", key="score", value=1)
    with pytest.raises(RuntimeError, match="DATASET_NODE_ARGUMENTS_INVALID"):
        delete("both", row_id=first, key="ticket", value="Later")

    kept, gone = insert("Kept"), insert("Gone")
    with ThreadPoolExecutor(max_workers=2) as workers:
        outcomes = list(workers.map(lambda n: _attempt(delete, f"race-{n}", row_id=gone), (1, 2)))
    assert sorted(map(str, outcomes)) == ["DATASET_ROW_NOT_FOUND", str({"row_id": gone, "deleted": True})]
    rows = call("DATASET_1", "find_rows", ["ticket"], {})["items"]
    assert [row["id"] for row in rows] == [kept]
    assert insert("Gone", "insert-again") != gone  # the unique key was released with the row


def _attempt(function, *args, **kwargs):
    try:
        return function(*args, **kwargs)
    except RuntimeError as error:
        return str(error).split(":")[0]


def test_generated_python_agent_writes_and_connected_delete(client, db, monkeypatch, target, tmp_path):
    source = dataset(client, name="Agent source")
    destination = dataset(client, name="API delete destination")
    url, requests = target
    base = f"/api/datasets/{destination['id']}"
    graph = {
        "name": "Agent writes", "state": [F("answer"), F("steps", "list"), F("removed", "object")],
        "nodes": [
            N("start", "start"),
            N("agent", "agent", prompt="TK-9", output_field="answer", steps_field="steps", tools=[
                {"name": "save_ticket", "source": "dataset", "dataset_id": source["id"], "fields": ["ticket", "score"],
                 "filter_ops": {}, "limit": 1, "operations": ["upsert_row"], "write_fields": ["ticket"], "key": "ticket"},
            ]),
            N("removed", "dataset", label="Removed", dataset_id=destination["id"], operation="delete_row",
              fields=["ticket"], arguments={"key": "ticket", "value": "Remote"}, output_field="removed"),
            N("end", "end"),
        ],
    }
    graph["edges"] = [E(a["id"], b["id"]) for a, b in zip(graph["nodes"], graph["nodes"][1:])]
    wid = save(client, graph)
    response = client.get(f"/api/workflows/{wid}/export/python", headers=auth("owner"))
    assert response.status_code == 200, response.text
    assert "step_id = dataset_operation_id(config)" in response.text
    script = tmp_path / "agent_writes.py"
    script.write_text(response.text)
    configure(monkeypatch, db, tmp_path)
    reader = token(client, base, "read_write")["token"]
    for name, value in {"BACKEND": "superstep", "API_URL": url, "ID": destination["id"], "API_TOKEN": reader}.items():
        monkeypatch.setenv(f"DATASET_2_{name}", value)
    assert run_cli(script, "--setup-datasets").returncode == 0
    remote = call_api(client, base, "Remote")
    denied = run_cli(script)
    assert denied.returncode and "DATASET_TOKEN_SCOPE" in denied.stderr
    monkeypatch.setenv("DATASET_2_API_TOKEN", token(client, base, "read_write", allow_delete=True)["token"])
    result = run_cli(script)
    assert result.returncode == 0, result.stderr
    assert '"deleted": true' in result.stdout and remote in result.stdout
    assert '"operation": "upsert_row"' in result.stdout and '"count": 1' in result.stdout
    assert [request["operation"] for request in requests] == ["delete_row", "delete_row"]

    exported = runpy.run_path(str(script))
    assert [exported["DATASET_BINDINGS"][name]["operations"] for name in ("DATASET_1", "DATASET_2")] == [["upsert_row"], ["delete_row"]]
    rows = exported["dataset_call"]("DATASET_1", "find_rows", ["ticket", "score"], {})["items"]
    assert [row["values"] for row in rows] == [{"ticket": "TK-9", "score": None}]  # two runs, one upserted row
    agent = exported["dataset_agent"]
    writes = {"operations": ["upsert_row"], "write_fields": ["ticket"], "key": "ticket"}
    for args in ({"operation": "upsert_row", "values": {"score": 3}}, {"operation": "insert_row", "values": {"ticket": "X"}},
                 {"operation": "delete_row"}, {"filters": []}):
        with pytest.raises(ValueError):
            agent("DATASET_1", ["ticket"], {}, 1, args, writes, "call-1")
    first = agent("DATASET_1", ["ticket"], {}, 1, {"operation": "upsert_row", "values": {"ticket": "TK-10"}}, writes, "call-2")
    assert set(first) == {"row_id", "inserted"}  # a tool that cannot Find gets identifiers only
    assert first["inserted"] and agent("DATASET_1", ["ticket"], {}, 1, {"operation": "upsert_row", "values": {"ticket": "TK-10"}},
                                       writes, "call-2") == first
    with pytest.raises(ValueError):
        agent("DATASET_1", ["ticket"], {}, 1, {"operation": "upsert_row", "values": {"ticket": "TK-10"}}, None, "call-3")
    both = {"operations": ["find_rows", "insert_row"], "write_fields": ["ticket"]}
    inserted = agent("DATASET_1", ["ticket"], {"ticket": ["eq"]}, 5, {"operation": "insert_row", "values": {"ticket": "TK-11"}}, both, "call-4")
    assert inserted["inserted"] and inserted["values"] == {"ticket": "TK-11"}
    with pytest.raises(RuntimeError, match="DATASET_RECEIPT_CONFLICT"):
        agent("DATASET_1", ["ticket"], {}, 5, {"operation": "insert_row", "values": {"ticket": "TK-12"}}, both, "call-4")
    found = agent("DATASET_1", ["ticket"], {"ticket": ["eq"]}, 5, {"filters": [{"field": "ticket", "op": "eq", "value": "TK-11"}]}, both)
    assert found == {"rows": [{"ticket": "TK-11"}], "truncated": False}


def call_api(client, base, ticket):
    return rows_call(client, "POST", f"{base}/rows", body={"values": {"ticket": ticket}}, status=201)["row"]["id"]
