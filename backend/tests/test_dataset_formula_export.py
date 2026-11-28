"""Exercise Formula-enabled project exports through both runtimes and database backends."""
import io
import json
from pathlib import Path
import runpy
import subprocess
import zipfile

import pytest

from app.engine.dataset_export import DatasetExport
from app.engine.dataset_typescript_standalone import typescript_standalone
from test_dataset_connected import token
from test_dataset_formula_persistence import column, formula, enabled  # noqa: F401
from test_dataset_project_export import target  # noqa: F401
from test_dataset_rows import call, insert
from test_dataset_runtime import dataset_node, graph, save
from test_dataset_typescript_standalone import configure, run_deno
from test_datasets import auth, client, create  # noqa: F401
from test_identity_migration import db  # noqa: F401
from test_typescript_export import DENO, DENO_ARGS, deno_env  # noqa: F401


PROBE = """
import { datasetAgent, datasetCall, setupDatasets } from "./formula-runtime.ts";

let results = [];
if (Deno.env.get("FORMULA_SETUP") === "1") {
  await setupDatasets(true);
  await setupDatasets(true);
}
for (const request of JSON.parse(Deno.env.get("FORMULA_REQUESTS") ?? "[]")) {
  try {
    if (request.operation === "agent") {
      results.push(await datasetAgent("DATASET_1", request.fields, { total: ["gte"] }, 5, request.arguments));
    } else {
      results.push(await datasetCall("DATASET_1", request.operation, request.fields, request.arguments, request.id));
    }
  } catch (error) {
    results.push({ error: error instanceof Error ? error.message.split(":")[0] : String(error) });
  }
}
console.log(JSON.stringify(results));
"""


def test_typescript_formula_conformance(tmp_path, deno_env):
    cases = json.loads((Path(__file__).parent / "fixtures/dataset_formula_contract.json").read_text())["valid"]
    bindings = {
        case["name"]: {"columns": [
            {"key": key, "kind": kind, **({"formula": {"version": 1, "expression": case["expressions"][key]}}
                                         if key in case["expressions"] else {})}
            for key, kind in case["fields"].items()
        ]}
        for case in cases
    }
    script = tmp_path / "formula-contract.ts"
    script.write_text(
        f"const DATASET_FORMULAS = {json.dumps(DatasetExport({}, bindings).formula_programs())};\n"
        + typescript_standalone()
        + f"\nconst cases = {json.dumps(cases)};\n"
        + """console.log(JSON.stringify(cases.map(item => {
          const values = { ...item.row };
          const errors = materializeDatasetFormulas(DATASET_FORMULAS[item.name], values);
          return [Object.fromEntries(Object.keys(item.expressions).map(key => [key, values[key]])), errors || {}];
        })));
"""
    )
    result = run_deno(deno_env, tmp_path, script)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == [[case["values"], case["errors"]] for case in cases]


@pytest.fixture(params=["python", "typescript"])
def formula_runner(request, monkeypatch):
    language = request.param
    if language == "typescript":
        deno = request.getfixturevalue("deno_env")

    def load(folder, code):
        if language == "python":
            script = folder / "formula-runtime.py"
            script.write_text(code)
            exported = runpy.run_path(str(script))

            def run(actions, *, setup=False, **environment):
                with monkeypatch.context() as change:
                    for name, value in environment.items():
                        change.setenv(name, value)
                    if setup:
                        exported["setup_datasets"](create=True)
                        exported["setup_datasets"](create=True)
                    results = []
                    for item in actions:
                        operation, fields, arguments = item["operation"], item["fields"], item["arguments"]
                        try:
                            if operation == "agent":
                                results.append(exported["dataset_agent"]("DATASET_1", fields, {"total": ["gte"]}, 5, arguments))
                            else:
                                results.append(exported["dataset_call"]("DATASET_1", operation, fields, arguments, item.get("id")))
                        except RuntimeError as exc:
                            results.append({"error": str(exc).split(":")[0]})
                    return results

        else:
            script = folder / "formula-runtime.ts"
            script.write_text(code)
            checked = subprocess.run([DENO, "check", "-q", *DENO_ARGS, str(script)], env=deno,
                                     capture_output=True, text=True, timeout=180)
            assert checked.returncode == 0, checked.stderr
            probe = folder / "probe.ts"
            probe.write_text(PROBE)

            def run(actions, *, setup=False, **environment):
                response = run_deno(deno, folder, probe, extra={
                    **environment, "FORMULA_SETUP": "1" if setup else "0", "FORMULA_REQUESTS": json.dumps(actions),
                })
                assert response.returncode == 0, response.stderr
                return json.loads(response.stdout)

        return run

    return language, load


def action(operation, fields, arguments, id_=None):
    return {"operation": operation, "fields": fields, "arguments": arguments, "id": id_}


def test_formula_projects_match_connected_and_standalone(client, db, enabled, target, monkeypatch, tmp_path, formula_runner):
    language, load = formula_runner
    note = formula("note", '[ticket] & " 🖨"', "text")
    total = formula("total", "[hours] * [rate] + [serial]")
    source = create(client, name="Formula export", columns=[
        column("ticket", "text", unique=True), column("hours", "number"), column("rate", "number"),
        column("serial", "auto_number"), total, formula("rate_per", "[rate] / [hours]"), note,
    ])
    did = source["id"]
    api = f"/api/datasets/{did}"
    rows = f"{api}/rows"
    insert(client, rows, ticket="Snapshot", hours=0, rate=3_000_000)
    writer = token(client, api)["token"]
    ids_only_writer = token(client, api, "write")["token"]
    node = dataset_node(did, "find_rows", {}, ["total", "note"])
    node["data"]["label"] = "Compile formulas"
    wid = save(client, graph("Read formula", node))
    headers = auth("owner")
    response = client.get(f"/api/workflows/{wid}/export/{language}/project", headers=headers,
                          params={"backend": f"DATASET_1:{db.engine.dialect.name}", "snapshot": "DATASET_1"})
    assert response.status_code == 200, response.text
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        archive.extractall(tmp_path)
    folder = next(path.parent for path in tmp_path.glob("*/dataset-snapshots.json"))
    manifest = json.loads((folder / "datasets.json").read_text())
    contract = {item["key"]: item for item in manifest["bindings"][0]["columns"]}
    assert contract["total"]["formula"] == total["formula"]
    snapshot = folder / "dataset-snapshots.json"
    archived = json.loads(snapshot.read_text())
    archived["snapshots"][0]["rows"][0]["values"]["total"] = 999
    snapshot.write_text(json.dumps(archived))
    code = client.get(f"/api/workflows/{wid}/export/{language}", headers=headers)
    assert code.status_code == 200, code.text
    configure(monkeypatch, db, tmp_path)
    run = load(folder, code.text)
    connected = {"DATASET_1_BACKEND": "superstep", "DATASET_1_ID": did, "DATASET_1_API_URL": target[0],
                 "DATASET_1_API_TOKEN": writer}

    fields = ["total", "rate_per", "note"]
    upsert = action("upsert_row", fields, {"key": "ticket", "values": {"ticket": "Snapshot", "hours": 2}}, "repair")
    actions = [
        action("find_rows", fields, {}),
        action("find_rows", ["total"], {}),
        upsert,
        upsert,
        action("upsert_row", fields, upsert["arguments"], "unchanged"),
        action("insert_row", fields, {"values": {"ticket": "Invalid", "total": 42}}, "invalid"),
        action("aggregate_rows", ["total"], {"summaries": {"total": "sum"}}),
        action("agent", ["total", "note"], {"filters": [{"field": "total", "op": "gte", "value": 6_000_000}]}),
    ]

    for environment in ({}, connected):
        original, projected, changed, retried, unchanged, rejected, aggregate, agent = run(actions, setup=True, **environment)
        row, = original["items"]
        assert row["values"] == {"total": 1, "rate_per": None, "note": "Snapshot 🖨"}
        assert row["formula_errors"] == {"rate_per": "division_by_zero"}
        assert "formula_errors" not in projected["items"][0]
        assert changed == retried == unchanged
        assert changed["row"]["values"] == {"total": 6_000_001, "rate_per": 1_500_000, "note": "Snapshot 🖨"}
        assert "formula_errors" not in changed["row"]
        assert rejected == {"error": "DATASET_COLUMN_READ_ONLY"}
        assert aggregate["groups"] == [{"group": None, "total": 1, "values": {"total": 6_000_001}}]
        assert agent == {"rows": [{"total": 6_000_001, "note": "Snapshot 🖨"}], "truncated": False}

        hidden = action("insert_row", [], {"values": {"ticket": "Hidden", "hours": 0, "rate": 12}}, "ids-only")
        credentials = {**environment, "DATASET_1_API_TOKEN": ids_only_writer} if environment else {}
        outcome, replay = run([hidden, hidden], **credentials)
        assert outcome == replay and set(outcome["row"]) == {"id", "revision"}
        hidden_row, = run([action("get_row", ["total", "rate_per"], {"row_id": outcome["row"]["id"]})], **environment)
        assert hidden_row["values"] == {"total": 2, "rate_per": None}
        assert hidden_row["formula_errors"] == {"rate_per": "division_by_zero"}

    call(client, "PUT", f"{api}/columns/total", body={"revision": source["revision"],
         "column": formula("total", "[hours] * [rate] + [serial] + 1")})
    assert run([action("find_rows", ["total"], {})], **connected) == [{"error": "DATASET_BINDING_SCHEMA_MISMATCH"}]
