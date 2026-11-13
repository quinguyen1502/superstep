import io
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import zipfile

import pytest

from test_dataset_connected import dataset, token
from test_dataset_rows import call
from test_dataset_runtime import save
from test_datasets import auth, client  # noqa: F401
from test_identity_migration import db  # noqa: F401
from test_python_export import E, F, KEYS, N
from test_typescript_export import DENO, DENO_ARGS, deno_env  # noqa: F401


def workflow(did):
    def node(id_, operation, fields, arguments):
        return N(id_, "dataset", label=id_, dataset_id=did, operation=operation,
                 arguments=arguments, fields=fields, output_field=id_)

    nodes = [
        N("start", "start"),
        node("inserted", "insert_row", ["ticket", "score", "active"], {"values": {"ticket": "FromExport", "score": 0, "active": False}}),
        node("updated", "upsert_row", ["ticket", "score"], {"key": "ticket", "values": {"ticket": "FromExport", "score": 1}}),
        node("found", "find_rows", ["ticket"], {"filters": [{"field": "active", "op": "eq", "value": False}], "limit": 1}),
        node("loaded", "get_row", ["active"], {"row_id": "{{state.updated.row.id}}"}),
        N("agent", "agent", prompt="Use find_records.", output_field="answer", steps_field="steps", tools=[
            {"name": "find_records", "source": "dataset", "dataset_id": did, "fields": ["ticket"],
             "filter_ops": {"ticket": ["eq"]}, "limit": 1},
        ]),
        N("end", "end"),
    ]
    return {"name": "Connected export", "nodes": nodes, "edges": [E(a["id"], b["id"]) for a, b in zip(nodes, nodes[1:])],
            "state": [F(key, "object") for key in ("inserted", "updated", "found", "loaded")] + [F("answer"), F("steps", "list")]}


@pytest.fixture
def target(client):
    requests = []

    class Studio(BaseHTTPRequestHandler):
        def do_POST(self):
            raw = self.rfile.read(int(self.headers["Content-Length"]))
            request = json.loads(raw)
            requests.append(request)
            result = client.post(self.path, headers={"Authorization": self.headers["Authorization"], "Content-Type": "application/json"}, content=raw)
            # The receiver commits the first write, then a gateway loses its response.
            if len(requests) == 1 and result.status_code == 200:
                self.send_response(503)
                self.end_headers()
                return
            self.send_response(result.status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(result.content)))
            self.end_headers()
            self.wfile.write(result.content)

        def log_message(self, *args):
            pass

    with ThreadingHTTPServer(("127.0.0.1", 0), Studio) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        yield f"http://127.0.0.1:{server.server_port}", requests
        server.shutdown()
        thread.join()


def project(client, wid, language, root, *secrets):
    response = client.get(f"/api/workflows/{wid}/export/{language}/project", headers=auth("owner"))
    assert response.status_code == 200, response.text
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        for name in archive.namelist():
            assert all(secret.encode() not in archive.read(name) for secret in secrets)
        archive.extractall(root)
    folder = next(path.parent for path in root.glob("*/datasets.json"))
    bindings = json.loads((folder / "datasets.json").read_text())
    assert bindings["version"] == 1
    binding, = bindings["bindings"]
    assert binding["name"] == "DATASET_1"
    assert {column["key"] for column in binding["columns"]} == {"ticket", "score", "active"}
    assert set(binding["operations"]) == {"insert_row", "upsert_row", "find_rows", "get_row"}
    assert "DATASET_1_API_TOKEN=\n" in (folder / ".env.example").read_text()
    if language == "typescript" and not os.getenv("STUDIO_DATASET_EXPORT_JS_MODULES"):
        source = client.get(f"/api/workflows/{wid}/export/typescript", headers=auth("owner"))
        assert source.status_code == 200, source.text
        (folder / "deno-agent.ts").write_text(source.text)
    return folder


@pytest.fixture(params=["python", "typescript"])
def export_runner(request):
    language = request.param
    env = {key: value for key, value in os.environ.items()
           if key not in KEYS and not key.startswith("DATASET_") and key != "LLM_PROVIDER"}
    modules = os.getenv("STUDIO_DATASET_EXPORT_JS_MODULES")
    if language == "typescript" and not modules:
        deno = request.getfixturevalue("deno_env")
        env["DENO_DIR"] = deno["DENO_DIR"]

    def run(folder, **settings):
        command = [sys.executable, "-I", str(next(folder.glob("*.py")))] if language == "python" else None
        if language == "typescript":
            path = folder / ("agent.ts" if modules else "deno-agent.ts")
            if modules:
                installed = Path(modules).resolve()
                if not (folder / "node_modules").exists():
                    (folder / "node_modules").symlink_to(installed, target_is_directory=True)
                command = [shutil.which("node"), "--experimental-strip-types", str(path)]
            else:
                command = [DENO, "run", "-q", *DENO_ARGS, "--allow-env", "--allow-read", "--allow-sys=homedir",
                           "--allow-net", str(path)]
        return subprocess.run(command, env={**env, **settings, "RUN_EXAMPLE": "1"}, cwd=folder,
                              capture_output=True, text=True, timeout=45, stdin=subprocess.DEVNULL)
    return language, run


def test_exported_project_runs_against_connected_dataset(client, target, tmp_path, export_runner):
    language, run = export_runner
    source, destination = dataset(client, name="Source"), dataset(client, name="Destination")
    base = f"/api/datasets/{destination['id']}"
    issued = token(client, base)
    url, requests = target
    wid = save(client, workflow(source["id"]))
    folder = project(client, wid, language, tmp_path, source["id"], destination["id"], issued["token"], url)
    missing = run(folder)
    assert missing.returncode and "DATASET_1_BACKEND=superstep" in missing.stderr
    settings = {"DATASET_1_BACKEND": "superstep", "DATASET_1_API_URL": url,
                "DATASET_1_ID": destination["id"], "DATASET_1_API_TOKEN": issued["token"]}
    output = run(folder, **settings)
    assert output.returncode == 0, output.stderr
    assert "FromExport" in output.stdout and '"dataset"' in output.stdout
    assert [req["operation"] for req in requests] == ["insert_row", "insert_row", "upsert_row", "find_rows", "get_row", "find_rows"]
    assert requests[0] == requests[1] and requests[0]["operation_id"] != requests[2]["operation_id"]
    assert requests[-1]["fields"] == ["ticket"] and "operation_id" not in requests[-1]
    rows = call(client, "POST", f"{base}/rows/query", body={})["items"]
    assert len(rows) == 1 and rows[0]["values"] == {"ticket": "FromExport", "score": 1, "active": False}
    call(client, "DELETE", f"{base}/columns/active?revision={destination['revision']}")
    drift = run(folder, **settings)
    assert drift.returncode and "DATASET_BINDING_SCHEMA_MISMATCH" in drift.stderr
    call(client, "DELETE", f"{base}/access/tokens/{issued['id']}")
    revoked = run(folder, **settings)
    assert revoked.returncode and "AUTH_TOKEN_INVALID" in revoked.stderr
