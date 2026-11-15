"""One support-ticket path across Agent writes, public entries, Delete row, and a standalone export."""
import io
import os
from pathlib import Path
import runpy
import subprocess
import sys
import zipfile

from test_agent_node import call as tool_call
from test_agent_node import script, wf
from test_dataset_public_entry import execute, tickets
from test_dataset_rows import call
from test_dataset_runtime import assert_error, dataset_fixture, dataset_node, graph, grant, save
from test_datasets import auth, client  # noqa: F401
from test_identity_migration import db  # noqa: F401


def agent_steps(events):
    return next(event for event in events if event["type"] == "run_finished")["state"]["steps"]


def test_support_ticket_agent_upsert_public_find_and_studio_delete(client, monkeypatch, tmp_path):
    did = dataset_fixture(client)
    base = f"/api/datasets/{did}"
    call(client, "POST", f"{base}/rows", body={"values": {"ticket": "KEEP-1", "score": 1}}, status=201)

    # An Agent with write access but no delete upserts a ticket from a public chat.
    writer_tool = {"name": "file_ticket", "source": "dataset", "dataset_id": did, "operations": ["find_rows", "upsert_row"],
                   "fields": ["ticket", "score"], "write_fields": ["ticket", "score"], "key": "ticket", "filter_ops": {}, "limit": 5}
    agent = save(client, wf(tools=[writer_tool], steps_field="steps"))
    grant(client, did, agent, "write")
    script(monkeypatch, [("", [tool_call("file_ticket", {"operation": "upsert_row", "values": {"ticket": "T-100", "score": 3}})]),
                         ("Filed", [])])
    status, events = execute("chat", {"workflow_id": agent})
    step, = agent_steps(events)
    assert status == "ok" and step["status"] == "ok" and step["dataset"] == {"count": 1, "operation": "upsert_row"}
    assert tickets(client, did) == ["KEEP-1", "T-100"]

    # A read-only Agent tool cannot write, even when the model asks.
    reader_tool = {"name": "look_up", "source": "dataset", "dataset_id": did, "fields": ["ticket"], "filter_ops": {}, "limit": 5}
    reader = save(client, wf(tools=[reader_tool], steps_field="steps"))
    grant(client, did, reader, "write")
    script(monkeypatch, [("", [tool_call("look_up", {"operation": "upsert_row", "values": {"ticket": "T-200"}})]), ("Done", [])])
    status, events = execute("chat", {"workflow_id": reader})
    assert agent_steps(events)[0]["status"] == "error"

    # The API trigger and chat find the ticket.
    finder = save(client, graph("Find", dataset_node(did, "find_rows", {
        "filters": [{"field": "ticket", "op": "eq", "value": "{{state.ticket}}"}], "limit": 1}, ["ticket", "score"])))
    grant(client, did, finder, "read")
    for source in ("chat", "api"):
        status, events = execute(source, {"workflow_id": finder, "input": {"ticket": "T-100"}})
        result = next(event for event in events if event["type"] == "run_finished")["state"]["result"]
        assert status == "ok" and result["items"][0]["values"] == {"ticket": "T-100", "score": 3}

    # Delete needs the delete capability, and public entries never delete.
    deleter = save(client, graph("Delete", dataset_node(did, "delete_row", {"key": "ticket", "value": "{{state.ticket}}"})))
    grant(client, did, deleter, "read_write")
    status, events = execute("ui", {"workflow_id": deleter, "input": {"ticket": "T-100"}})
    assert status == "error"
    assert_error(events, "DATASET_GRANT_DENIED")
    grant(client, did, deleter, "read_write", allow_delete=True)
    for source in ("chat", "api"):
        status, events = execute(source, {"workflow_id": deleter, "input": {"ticket": "T-100"}})
        assert status == "error"
        assert_error(events, "DATASET_GRANT_DENIED")
    assert tickets(client, did) == ["KEEP-1", "T-100"]
    monkeypatch.setenv("STUDIO_DEMO_MODE", "true")
    status, events = execute("ui", {"workflow_id": deleter, "input": {"ticket": "T-100"}})
    assert status == "error"
    assert_error(events, "DATASET_GRANT_DENIED")
    monkeypatch.delenv("STUDIO_DEMO_MODE")
    status, events = execute("ui", {"workflow_id": deleter, "input": {"ticket": "T-100"}})
    result = next(event for event in events if event["type"] == "run_finished")["state"]["result"]
    assert status == "ok" and result["deleted"] is True
    assert tickets(client, did) == ["KEEP-1"]

    # A Dataset token needs delete allowed before a connected delete.
    columns = [{key: value for key, value in column.items() if key != "label"} for column in call(client, "GET", base)["columns"]]
    request = {"version": 1, "operation": "delete_row", "columns": columns, "fields": ["ticket"],
               "arguments": {"key": "ticket", "value": "KEEP-1"}, "operation_id": "connected-delete"}
    for allow_delete, status_code in ((False, 403), (True, 200)):
        secret = call(client, "POST", f"{base}/access/tokens", status=201,
                      body={"name": "export", "permission": "read_write", "allow_delete": allow_delete})["token"]
        response = client.post(f"{base}/connected", headers={"Authorization": f"Bearer {secret}"}, json=request)
        assert response.status_code == status_code, response.text
        if allow_delete:
            assert response.json()["data"]["deleted"] is True
        else:
            assert response.json()["error"]["code"] == "DATASET_TOKEN_SCOPE"
    assert tickets(client, did) == []

    # The exported Delete workflow runs on its own SQLite database, and repeated setup keeps the rows left.
    response = client.get(f"/api/workflows/{deleter}/export/python/project", headers=auth("owner"),
                          params={"backend": "DATASET_1:sqlite"})
    assert response.status_code == 200, response.text
    folder = tmp_path / "project"
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        archive.extractall(folder)
    agent_file = next(folder.rglob("agent.py"))
    database = tmp_path / "tickets.sqlite3"
    settings = {"DATASET_1_BACKEND": "sqlite", "DATASET_1_ID": "tickets", "DATASET_1_SQLITE_PATH": str(database), "LLM_PROVIDER": ""}

    def setup():
        done = subprocess.run([sys.executable, "-I", str(agent_file), "--setup-datasets"], cwd=agent_file.parent,
                              env={**os.environ, **settings}, capture_output=True, text=True, timeout=60)
        assert done.returncode == 0, done.stderr

    setup()
    for name, value in settings.items():
        monkeypatch.setenv(name, value)
    exported = runpy.run_path(str(agent_file))
    dataset_call = exported["dataset_call"]
    for ticket in ("LOCAL-1", "LOCAL-2"):
        dataset_call("DATASET_1", "insert_row", ["ticket"], {"values": {"ticket": ticket}}, f"insert-{ticket}")
    assert dataset_call("DATASET_1", "delete_row", ["ticket"], {"key": "ticket", "value": "LOCAL-1"}, "delete-local")["deleted"]
    setup()
    remaining = dataset_call("DATASET_1", "find_rows", ["ticket"], {})["items"]
    assert [row["values"] for row in remaining] == [{"ticket": "LOCAL-2"}]
    assert Path(database).is_file()
