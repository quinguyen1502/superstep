"""Generated TypeScript projects run Dataset operations on SQLite and PostgreSQL."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess

import pytest

from test_dataset_connected import dataset, token
from test_dataset_rows import call as rows_call
from test_dataset_project_export import project, target, workflow  # noqa: F401
from test_dataset_runtime import save
from test_datasets import auth, client  # noqa: F401
from test_identity_migration import db  # noqa: F401
from test_python_export import E, F, N
from test_typescript_export import DENO, DENO_ARGS, deno_env  # noqa: F401


PROBE = r'''
import { datasetAgent, datasetCall, setupDatasets, DATASET_BINDINGS } from "./deno-agent.ts";

const command = Deno.env.get("DATASET_PROBE") ?? "";
const columns = DATASET_BINDINGS.DATASET_1.columns as { kind: string }[];

function fail(error: unknown): never {
  console.error(error instanceof Error ? error.message : String(error));
  Deno.exit(1);
}

if (command === "query" || command === "count") {
  const fields = command === "count" ? ["ticket"] : ["ticket", "score", "active"];
  const args = command === "count" ? {} : { filters: [{ field: "active", op: "eq", value: false }] };
  console.log(JSON.stringify(await datasetCall("DATASET_1", "find_rows", fields, args)));
}

if (command === "upsert") {
  const score = Number(Deno.env.get("PROBE_SCORE"));
  const result = await datasetCall("DATASET_1", "upsert_row", ["ticket", "score"], {
    key: "ticket", values: { ticket: "Concurrent", score },
  }, Deno.env.get("PROBE_ID") ?? "");
  console.log(JSON.stringify(result));
}

if (command === "bad-type") {
  try {
    await datasetCall("DATASET_1", "upsert_row", ["ticket", "score"], {
      key: "ticket", values: { ticket: "Typed", score: "nope" },
    }, "bad-type");
    console.log("UNEXPECTED");
  } catch (error) { fail(error); }
}

if (command === "ids-only") {
  console.log(JSON.stringify(await datasetCall("DATASET_1", "insert_row", [], { values: { ticket: "IdsOnly" } }, "ids-only")));
}

if (command === "duplicate") {
  try {
    await datasetCall("DATASET_1", "insert_row", ["ticket"], { values: { ticket: "Concurrent" } }, "duplicate");
    console.log("UNEXPECTED");
  } catch (error) { fail(error); }
}

if (command === "insert" || command === "delete") {
  try {
    const args = command === "insert" ? { values: { ticket: Deno.env.get("PROBE_TICKET") } } : JSON.parse(Deno.env.get("PROBE_ARGS") ?? "{}");
    console.log(JSON.stringify(await datasetCall("DATASET_1", command === "insert" ? "insert_row" : "delete_row", ["ticket"], args,
      Deno.env.get("PROBE_ID") ?? "")));
  } catch (error) { fail(error); }
}

if (command === "agent") {
  const writes = { operations: ["find_rows", "insert_row"], write_fields: ["ticket"] };
  try {
    console.log(JSON.stringify(await datasetAgent("DATASET_1", ["ticket"], { ticket: ["eq"] }, 5,
      JSON.parse(Deno.env.get("PROBE_ARGS") ?? "{}"), writes, Deno.env.get("PROBE_ID"))));
  } catch (error) { fail(error); }
}

if (command === "mismatch" || command === "mismatch-setup") {
  columns[0].kind = "select";
  try {
    if (command === "mismatch") await datasetCall("DATASET_1", "find_rows", ["ticket"], {});
    else await setupDatasets(true);
    console.log("UNEXPECTED");
  } catch (error) { fail(error); }
}
'''


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


def run_deno(deno_env, folder, script, *args, extra=None):
    env = os.environ.copy()
    env.update(DENO_DIR=deno_env["DENO_DIR"], NO_COLOR="1")
    if extra:
        env.update(extra)
    return subprocess.run(
        [DENO, "run", "-q", *DENO_ARGS, "--allow-env", "--allow-read", "--allow-write", "--allow-net",
         "--allow-sys=homedir", str(script), *args],
        cwd=folder, env=env, capture_output=True, text=True, timeout=180, stdin=subprocess.DEVNULL,
    )


def probe(deno_env, folder, command, **extra):
    path = folder / "probe.ts"
    path.write_text(PROBE)
    return run_deno(deno_env, folder, path, extra={"DATASET_PROBE": command, **extra})


def test_typescript_standalone_runs_generated_project_and_replays_receipts(client, db, monkeypatch, tmp_path, deno_env):
    source = dataset(client, name="Source")
    child = workflow(source["id"])
    child_id = save(client, child)
    parent = {"name": "Standalone parent", "state": child["state"],
              "nodes": [N("start", "start"), N("child", "subgraph", label="Child", workflow_id=child_id), N("end", "end")],
              "edges": [E("start", "child"), E("child", "end")]}
    wid = save(client, parent)
    settings = configure(monkeypatch, db, tmp_path)
    folder = project(client, wid, "typescript", tmp_path / "export", source["id"])
    script = folder / "deno-agent.ts"
    package = json.loads((folder / "package.json").read_text())
    assert package["dependencies"]["pg"] == "^8"
    assert package["engines"]["node"] == ">=22.13"
    assert "node:sqlite" in (folder / "agent.ts").read_text()
    assert "DATASET_1_SQLITE_PATH=\n" in (folder / ".env.example").read_text()
    assert "DATASET_1_POSTGRES_DSN=\n" in (folder / ".env.example").read_text()

    missing = run_deno(deno_env, folder, script)
    assert missing.returncode and "DATASET_SETUP_REQUIRED" in missing.stderr
    if settings["BACKEND"] == "sqlite":
        assert not Path(settings["SQLITE_PATH"]).exists()
    setup = run_deno(deno_env, folder, script, "--setup-datasets")
    assert setup.returncode == 0, setup.stderr
    run = run_deno(deno_env, folder, script)
    assert run.returncode == 0, run.stderr
    assert "FromExport" in run.stdout and '"dataset"' in run.stdout
    assert run_deno(deno_env, folder, script, "--setup-datasets").returncode == 0

    queried = probe(deno_env, folder, "query")
    assert queried.returncode == 0, queried.stderr
    values = json.loads(queried.stdout)["items"]
    assert [row["values"] for row in values] == [{"ticket": "FromExport", "score": 1, "active": False}]
    assert values[0]["revision"] == 2

    def upsert(identity, score):
        return probe(deno_env, folder, "upsert", PROBE_ID=identity, PROBE_SCORE=str(score))

    with ThreadPoolExecutor(max_workers=2) as workers:
        raced = list(workers.map(lambda _: upsert("retry-key", 0), range(2)))
    assert all(item.returncode == 0 for item in raced), [item.stderr for item in raced]
    result = [json.loads(item.stdout) for item in raced]
    assert result[0] == result[1] and result[0]["inserted"]
    assert result[0]["row"]["values"]["score"] == 0
    first_id = result[0]["row"]["id"]
    with ThreadPoolExecutor(max_workers=2) as workers:
        updated = list(workers.map(lambda item: upsert(f"update-{item[0]}", item[1]), ((1, 1), (2, 2))))
    assert all(item.returncode == 0 for item in updated), [item.stderr for item in updated]
    revised = [json.loads(item.stdout) for item in updated]
    assert {item["row"]["revision"] for item in revised} == {2, 3}
    assert all(item["row"]["id"] == first_id and not item["inserted"] for item in revised)
    replay = upsert("retry-key", 0)
    assert replay.returncode == 0, replay.stderr
    replayed = json.loads(replay.stdout)
    assert replayed["inserted"] and replayed["row"]["id"] == first_id and replayed["row"]["revision"] == 3
    noop = upsert("no-op", replayed["row"]["values"]["score"])
    assert noop.returncode == 0, noop.stderr
    assert json.loads(noop.stdout) == {"inserted": False, "row": replayed["row"]}
    conflict = upsert("retry-key", 1)
    assert conflict.returncode and "DATASET_RECEIPT_CONFLICT" in conflict.stderr
    duplicate = probe(deno_env, folder, "duplicate")
    assert duplicate.returncode and "DATASET_UNIQUE_CONFLICT" in duplicate.stderr
    counted = probe(deno_env, folder, "count")
    assert counted.returncode == 0, counted.stderr
    assert len(json.loads(counted.stdout)["items"]) == 2
    invalid = probe(deno_env, folder, "bad-type")
    assert invalid.returncode and "DATASET_VALUE_INVALID" in invalid.stderr

    mismatch = probe(deno_env, folder, "mismatch")
    assert mismatch.returncode and "DATASET_BINDING_SCHEMA_MISMATCH" in mismatch.stderr
    mismatch_setup = probe(deno_env, folder, "mismatch-setup")
    assert mismatch_setup.returncode and "DATASET_BINDING_SCHEMA_MISMATCH" in mismatch_setup.stderr
    assert len(json.loads(probe(deno_env, folder, "count").stdout)["items"]) == 2
    ids_only = probe(deno_env, folder, "ids-only")
    assert ids_only.returncode == 0, ids_only.stderr
    outcome = json.loads(ids_only.stdout)
    assert outcome["inserted"] and set(outcome["row"]) == {"id", "revision"}
    monkeypatch.setenv("DATASET_1_BACKEND", "mysql")
    malformed = run_deno(deno_env, folder, script)
    assert malformed.returncode and "DATASET_1_BACKEND" in malformed.stderr
    if settings["BACKEND"] == "sqlite":
        assert Path(settings["SQLITE_PATH"]).is_file()


def test_generated_typescript_mixes_connected_and_standalone_bindings(client, db, monkeypatch, target, tmp_path, deno_env):
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
    response = client.get(f"/api/workflows/{wid}/export/typescript", headers=auth("owner"))
    assert response.status_code == 200, response.text
    script = tmp_path / "mixed.ts"
    script.write_text(response.text)
    setup = run_deno(deno_env, tmp_path, script, "--setup-datasets")
    assert setup.returncode == 0, setup.stderr
    assert requests == []
    result = run_deno(deno_env, tmp_path, script)
    assert result.returncode == 0, result.stderr
    assert "FromExport" in result.stdout and '"remote"' in result.stdout
    assert [request["operation"] for request in requests] == ["find_rows"]


def test_typescript_standalone_delete_row_locks_replays_and_skips_missing_rows(client, db, monkeypatch, target, tmp_path, deno_env):
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
    response = client.get(f"/api/workflows/{wid}/export/typescript", headers=auth("owner"))
    assert response.status_code == 200, response.text
    script = tmp_path / "deno-agent.ts"
    script.write_text(response.text)
    assert run_deno(deno_env, tmp_path, script, "--setup-datasets").returncode == 0
    for _ in range(2):  # a deleted row lets the next run insert it again
        run = run_deno(deno_env, tmp_path, script)
        assert run.returncode == 0, run.stderr
        assert '"deleted": true' in run.stdout
    assert [request["operation"] for request in requests] == ["find_rows", "find_rows"]
    assert run_deno(deno_env, tmp_path, script, "--setup-datasets").returncode == 0

    def insert(ticket, identity):
        result = probe(deno_env, tmp_path, "insert", PROBE_TICKET=ticket, PROBE_ID=identity)
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)["row"]["id"]

    def delete(identity, **arguments):
        return probe(deno_env, tmp_path, "delete", PROBE_ID=identity, PROBE_ARGS=json.dumps(arguments))

    assert json.loads(probe(deno_env, tmp_path, "count").stdout)["items"] == []
    missing = delete("late", key="ticket", value="Later")
    assert missing.returncode and "DATASET_ROW_NOT_FOUND" in missing.stderr
    first = insert("Later", "insert-1")
    for _ in range(2):  # the miss stored no receipt; the hit replays
        removed = delete("late", key="ticket", value="Later")
        assert removed.returncode == 0, removed.stderr
        assert json.loads(removed.stdout) == {"deleted": True, "row_id": first}
    conflict = delete("late", row_id=first)
    assert conflict.returncode and "DATASET_RECEIPT_CONFLICT" in conflict.stderr
    assert "DATASET_UPSERT_KEY_INVALID" in delete("bad-key", key="score", value=1).stderr
    assert "DATASET_NODE_ARGUMENTS_INVALID" in delete("both", row_id=first, key="ticket", value="Later").stderr

    kept, gone = insert("Kept", "insert-2"), insert("Gone", "insert-3")
    with ThreadPoolExecutor(max_workers=2) as workers:
        raced = list(workers.map(lambda n: delete(f"race-{n}", row_id=gone), (1, 2)))
    assert sorted(item.returncode for item in raced) == [0, 1]
    assert any("DATASET_ROW_NOT_FOUND" in item.stderr for item in raced)
    rows = json.loads(probe(deno_env, tmp_path, "count").stdout)["items"]
    assert [row["id"] for row in rows] == [kept]
    assert insert("Gone", "insert-4") != gone  # the unique key was released with the row


def test_generated_typescript_agent_writes_and_connected_delete(client, db, monkeypatch, target, tmp_path, deno_env):
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
    response = client.get(f"/api/workflows/{wid}/export/typescript", headers=auth("owner"))
    assert response.status_code == 200, response.text
    assert "const stepId = await datasetOperationId(config);" in response.text
    script = tmp_path / "deno-agent.ts"
    script.write_text(response.text)
    configure(monkeypatch, db, tmp_path)
    reader = token(client, base, "read_write")["token"]
    for name, value in {"BACKEND": "superstep", "API_URL": url, "ID": destination["id"], "API_TOKEN": reader}.items():
        monkeypatch.setenv(f"DATASET_2_{name}", value)
    assert run_deno(deno_env, tmp_path, script, "--setup-datasets").returncode == 0
    remote = rows_call(client, "POST", f"{base}/rows", body={"values": {"ticket": "Remote"}}, status=201)["row"]["id"]
    denied = run_deno(deno_env, tmp_path, script)
    assert denied.returncode and "DATASET_TOKEN_SCOPE" in denied.stderr
    monkeypatch.setenv("DATASET_2_API_TOKEN", token(client, base, "read_write", allow_delete=True)["token"])
    result = run_deno(deno_env, tmp_path, script)
    assert result.returncode == 0, result.stderr
    assert '"deleted": true' in result.stdout and remote in result.stdout
    assert '"operation": "upsert_row"' in result.stdout and '"count": 1' in result.stdout
    assert [request["operation"] for request in requests] == ["delete_row", "delete_row"]
    rows = json.loads(probe(deno_env, tmp_path, "count").stdout)["items"]
    assert [row["values"] for row in rows] == [{"ticket": "TK-9"}]  # two runs, one upserted row
    assert '\\"inserted\\": false}' in result.stdout and '\\"values\\"' not in result.stdout  # identifiers only without Find

    def agent(identity, **args):
        return probe(deno_env, tmp_path, "agent", PROBE_ID=identity, PROBE_ARGS=json.dumps(args))

    inserted = agent("call-1", operation="insert_row", values={"ticket": "TK-11"})
    assert inserted.returncode == 0, inserted.stderr
    first = json.loads(inserted.stdout)
    assert first["inserted"] and first["values"] == {"ticket": "TK-11"}
    assert json.loads(agent("call-1", operation="insert_row", values={"ticket": "TK-11"}).stdout) == first
    assert "DATASET_RECEIPT_CONFLICT" in agent("call-1", operation="insert_row", values={"ticket": "TK-12"}).stderr
    for args in ({"operation": "insert_row", "values": {"score": 1}}, {"operation": "upsert_row", "values": {"ticket": "X"}},
                 {"operation": "delete_row"}, {"operation": "insert_row", "values": {}}):
        assert "DATASET_NODE_ARGUMENTS_INVALID" in agent("call-2", **args).stderr
    found = agent("call-3", filters=[{"field": "ticket", "op": "eq", "value": "TK-11"}])
    assert json.loads(found.stdout) == {"rows": [{"ticket": "TK-11"}], "truncated": False}
