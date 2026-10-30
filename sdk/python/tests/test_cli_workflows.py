"""workflows list, export, import, pull and push (TASK-0168)."""
import io
import json
import zipfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import httpx
import pytest

from superstep.cli import run
from superstep.cli.session import SessionError, call


TOKEN = "pat_secret-value"
URL = "http://studio.example"
ROOT = Path(__file__).resolve().parents[1] / "src" / "superstep" / "cli" / "locales"


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("SUPERSTEP_URL", raising=False)
    monkeypatch.delenv("SUPERSTEP_TOKEN", raising=False)
    monkeypatch.delenv("LANG", raising=False)
    monkeypatch.delenv("LC_MESSAGES", raising=False)
    monkeypatch.delenv("LC_ALL", raising=False)


@pytest.fixture
def signed_in(monkeypatch):
    monkeypatch.setenv("SUPERSTEP_URL", URL)
    monkeypatch.setenv("SUPERSTEP_TOKEN", TOKEN)


def invoke(argv, client=None):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = run(argv, client=client)
    return code, out.getvalue(), err.getvalue()


def envelope(data, status=200):
    return httpx.Response(status, json={"success": status < 400, "data": data if status < 400 else None, "error": None if status < 400 else data})


def client_for(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


class Studio:
    def __init__(self):
        self.rows = {}
        self.posts = []
        self.calls = []
        self.next_id = 1
        self.export_missing = False
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("agent.py", "print('project')\n")
        self.zip_bytes = buffer.getvalue()

    def add(self, wid, name, version=1, nodes=None):
        self.rows[wid] = {
            "id": wid, "name": name, "nodes": list(nodes or []), "edges": [], "state": [],
            "version": version, "updated": 10.0, "access": "owner", "mine": True, "owner_email": "ada@example.com",
        }
        return self

    def handler(self, request: httpx.Request):
        self.calls.append((request.method, request.url.path, request.headers.get("authorization")))
        path = request.url.path
        if path == "/api/health":
            return envelope({"version": "0.9.0"})
        if path == "/api/workflows" and request.method == "GET":
            return envelope([self._summary(row) for row in self.rows.values()])
        if path == "/api/workflows" and request.method == "POST":
            return self._post(json.loads(request.content.decode()))
        if path.startswith("/api/workflows/") and "/export/" in path:
            return self._export(path)
        if path.startswith("/api/workflows/") and request.method == "GET":
            wid = path.split("/")[3]
            row = self.rows.get(wid)
            if row is None:
                return envelope({"code": "WORKFLOW_NOT_FOUND", "message": "no"}, 404)
            return envelope(dict(row))
        raise AssertionError(path)

    def _summary(self, row):
        return {
            "id": row["id"], "name": row["name"], "updated": row["updated"], "node_count": len(row["nodes"]),
            "last_run_status": None, "last_run_at": None, "access": "owner", "mine": True,
            "owner_email": "ada@example.com", "version": row["version"],
        }

    def _post(self, body):
        self.posts.append(body)
        assert not ({"access", "mine", "owner_email", "version", "updated"} & set(body))
        wid = body.get("id")
        if not wid:
            wid = "new" + str(self.next_id)
            self.next_id += 1
        current = self.rows.get(wid)
        stored = {
            "id": wid, "name": body.get("name") or "Untitled", "nodes": body.get("nodes") or [],
            "edges": body.get("edges") or [], "state": body.get("state") or [],
            "access": "owner", "mine": True, "owner_email": "ada@example.com", "updated": 50.0,
        }
        for key, value in body.items():
            if key not in stored:
                stored[key] = value
        if current is None:
            stored["version"] = 1
        else:
            same = all(current.get(key) == stored.get(key) for key in ("name", "nodes", "edges", "state"))
            stored["version"] = current["version"] if same else current["version"] + 1
        self.rows[wid] = stored
        return envelope({"id": wid, "errors": [], "issues": []})

    def _export(self, path):
        wid = path.split("/")[3]
        if self.export_missing or wid not in self.rows:
            return envelope({"code": "NOT_FOUND", "message": "no"}, 404)
        if path.endswith("/export/python/project"):
            return httpx.Response(200, content=self.zip_bytes)
        if path.endswith("/export/typescript"):
            return httpx.Response(200, content=b"export const graph = {}\n")
        if path.endswith("/export/python"):
            return httpx.Response(200, content=b"print('python')\n")
        raise AssertionError(path)

    def client(self):
        return client_for(self.handler)

    def posts_only(self):
        return [item for item in self.calls if item[0] == "POST"]


def lock_of(directory):
    return json.loads((directory / ".superstep" / "lock.json").read_text(encoding="utf-8"))


def error_code(out):
    body = json.loads(out)
    assert body["ok"] is False and list(body) == ["ok", "error"]
    return body["error"]["code"], body["error"]["message"]


def test_pull_writes_one_file_per_workflow_and_a_second_pull_keeps_local_files(tmp_path, signed_in):
    studio = Studio().add("w1", "Alpha", version=1, nodes=[{"id": "a"}]).add("w2", "Beta", version=3, nodes=[{"id": "b"}])
    http = studio.client()
    code, out, err = invoke(["pull", str(tmp_path)], http)
    assert code == 0 and out == "" and TOKEN not in err
    first = json.loads((tmp_path / "w1.json").read_text(encoding="utf-8"))
    second = json.loads((tmp_path / "w2.json").read_text(encoding="utf-8"))
    assert first["id"] == "w1" and first["name"] == "Alpha" and first["nodes"] == [{"id": "a"}]
    forbidden = {"access", "mine", "owner_email", "version", "updated"}
    assert not (forbidden & set(first)) and not (forbidden & set(second))
    lock = lock_of(tmp_path)
    assert lock["format"] == 1 and lock["url"] == URL
    assert lock["workflows"]["w1"] == {"name": "Alpha", "version": 1}
    assert lock["workflows"]["w2"] == {"name": "Beta", "version": 3}
    assert studio.calls[0][2] == "Bearer " + TOKEN

    local = tmp_path / "notes.json"
    local.write_text('{"keep": true}\n', encoding="utf-8")
    studio.rows["w1"]["version"] = 2
    studio.rows["w1"]["nodes"] = [{"id": "changed"}]
    code, out, err = invoke(["pull", str(tmp_path)], http)
    assert code == 0 and out == ""
    assert json.loads((tmp_path / "w1.json").read_text(encoding="utf-8"))["nodes"] == [{"id": "changed"}]
    assert local.read_text(encoding="utf-8") == '{"keep": true}\n'
    assert lock_of(tmp_path)["workflows"]["w1"]["version"] == 2
    assert "w2" in lock_of(tmp_path)["workflows"]


def test_push_of_an_unchanged_folder_does_not_post_and_force_recovers(tmp_path, signed_in):
    studio = Studio().add("w1", "Alpha", version=1, nodes=[{"id": "a"}]).add("w2", "Beta", version=3, nodes=[{"id": "b"}])
    studio.add("remote-only", "Kept", version=4, nodes=[{"id": "r"}])
    http = studio.client()
    assert invoke(["pull", str(tmp_path)], http)[0] == 0
    # The remote workflow has no local file. Push must not delete it, and an unchanged folder must not POST.
    (tmp_path / "remote-only.json").unlink()
    before = [path.read_bytes() for path in sorted(tmp_path.glob("*.json"))]
    lock_bytes = (tmp_path / ".superstep" / "lock.json").read_bytes()
    posted = len(studio.posts)
    code, out, err = invoke(["push", str(tmp_path), "--json"], http)
    assert code == 0 and err == "" and json.loads(out)["pushed"] == [] and json.loads(out)["unchanged"]
    assert len(studio.posts) == posted and studio.posts_only() == []
    assert [path.read_bytes() for path in sorted(tmp_path.glob("*.json"))] == before
    assert (tmp_path / ".superstep" / "lock.json").read_bytes() == lock_bytes
    assert "remote-only" in studio.rows

    studio.rows["w1"]["version"] = 5
    studio.rows["w1"]["nodes"] = [{"id": "studio"}]
    code, out, err = invoke(["push", str(tmp_path), "--json"], http)
    assert code == 1 and err == ""
    code_name, message = error_code(out)
    assert code_name == "WORKFLOW_CHANGED" and "Alpha" in message and "--force" in message
    assert len(studio.posts) == posted
    assert [path.read_bytes() for path in sorted(tmp_path.glob("*.json"))] == before
    assert (tmp_path / ".superstep" / "lock.json").read_bytes() == lock_bytes
    assert studio.rows["w1"]["nodes"] == [{"id": "studio"}]

    code, out, err = invoke(["push", str(tmp_path), "--force", "--json"], http)
    assert code == 0 and err == "" and TOKEN not in out
    body = json.loads(out)
    assert "w1" in body["pushed"] and "w2" in body["pushed"]
    assert studio.rows["w1"]["nodes"] == [{"id": "a"}]
    refreshed = lock_of(tmp_path)
    assert refreshed["url"] == URL
    assert refreshed["workflows"]["w1"]["version"] == studio.rows["w1"]["version"]
    assert refreshed["workflows"]["w2"]["version"] == studio.rows["w2"]["version"]
    assert refreshed["workflows"]["w1"]["version"] != 1
    assert "remote-only" in studio.rows and "remote-only" not in refreshed["workflows"]


def test_a_later_version_mismatch_posts_nothing_and_a_local_edit_does(tmp_path, signed_in):
    studio = Studio().add("w1", "Alpha", version=1, nodes=[{"id": "a"}]).add("w2", "Beta", version=3, nodes=[{"id": "b"}])
    http = studio.client()
    assert invoke(["pull", str(tmp_path)], http)[0] == 0
    edited = json.loads((tmp_path / "w1.json").read_text(encoding="utf-8"))
    edited["nodes"] = [{"id": "local"}]
    (tmp_path / "w1.json").write_text(json.dumps(edited), encoding="utf-8")
    studio.rows["w2"]["version"] = 9
    studio.rows["w2"]["nodes"] = [{"id": "moved"}]
    code, out, _err = invoke(["push", str(tmp_path), "--json"], http)
    assert code == 1 and error_code(out)[0] == "WORKFLOW_CHANGED" and studio.posts == []
    assert studio.rows["w2"]["nodes"] == [{"id": "moved"}]

    studio.rows["w2"]["version"] = 3
    studio.rows["w2"]["nodes"] = [{"id": "b"}]
    code, out, _err = invoke(["push", str(tmp_path), "--json"], http)
    assert code == 0 and json.loads(out)["pushed"] == ["w1"]
    assert studio.posts == [{"id": "w1", "name": "Alpha", "nodes": [{"id": "local"}], "edges": [], "state": []}]
    assert lock_of(tmp_path)["workflows"]["w1"]["version"] == studio.rows["w1"]["version"] == 2
    code, _out, _err = invoke(["push", str(tmp_path)], http)
    assert code == 0 and len(studio.posts) == 1


def test_a_different_origin_is_wrong_server_unless_force(tmp_path, signed_in):
    studio = Studio().add("w1", "Alpha", version=1, nodes=[{"id": "a"}])
    http = studio.client()
    assert invoke(["pull", str(tmp_path)], http)[0] == 0

    def replace(url):
        lock = lock_of(tmp_path)
        lock["url"] = url
        (tmp_path / ".superstep" / "lock.json").write_text(json.dumps(lock), encoding="utf-8")

    replace("http://other.example")
    code, out, err = invoke(["push", str(tmp_path)], http)
    assert code == 1 and out == "" and "WRONG_SERVER" not in err and "other.example" in err
    code, out, _err = invoke(["push", str(tmp_path), "--json"], http)
    code_name, message = error_code(out)
    assert code_name == "WRONG_SERVER" and "other.example" in message and URL in message
    assert studio.posts == []

    replace("http://studio.example:8000")
    code, out, _err = invoke(["push", str(tmp_path), "--json"], http)
    assert error_code(out)[0] == "WRONG_SERVER" and studio.posts == []
    replace("https://studio.example")
    code, out, _err = invoke(["push", str(tmp_path), "--json"], http)
    assert error_code(out)[0] == "WRONG_SERVER"

    replace("http://studio.example:80")
    code, out, _err = invoke(["push", str(tmp_path), "--json"], http)
    assert code == 0 and json.loads(out)["pushed"] == [] and studio.posts == []
    replace("http://studio.example/studio")
    code, _out, _err = invoke(["push", str(tmp_path)], http)
    assert code == 0 and studio.posts == []

    replace("http://other.example")
    code, out, _err = invoke(["push", str(tmp_path), "--force", "--json"], http)
    assert code == 0 and "w1" in json.loads(out)["pushed"]
    assert studio.posts and lock_of(tmp_path)["url"] == URL
    assert lock_of(tmp_path)["workflows"]["w1"]["version"] == studio.rows["w1"]["version"]


def test_export_matches_pull_and_import_rejects_code(tmp_path, signed_in, monkeypatch):
    studio = Studio().add("w1", "Alpha", version=2, nodes=[{"id": "a"}])
    http = studio.client()
    assert invoke(["pull", str(tmp_path / "folder")], http)[0] == 0
    monkeypatch.chdir(tmp_path)
    code, out, err = invoke(["workflows", "export", "Alpha", "--format", "json"], http)
    assert code == 0 and out == "" and (tmp_path / "w1.json").read_text(encoding="utf-8") == (tmp_path / "folder" / "w1.json").read_text(encoding="utf-8")
    assert "access" not in (tmp_path / "w1.json").read_text(encoding="utf-8")

    code, _out, err = invoke(["workflows", "export", "w1", "--format", "python", "--output", str(tmp_path / "flow.py")], http)
    assert code == 0 and (tmp_path / "flow.py").read_bytes() == b"print('python')\n" and "flow.py" in err
    code, _out, _err = invoke(["workflows", "export", "w1", "--format", "typescript", "--output", str(tmp_path / "flow.ts")], http)
    assert code == 0 and (tmp_path / "flow.ts").read_bytes() == b"export const graph = {}\n"
    assert any(path.endswith("/export/typescript") for _method, path, _auth in studio.calls)
    code, _out, _err = invoke(["workflows", "export", "w1", "--format", "langgraph", "--output", str(tmp_path / "flow.zip")], http)
    assert code == 0 and (tmp_path / "flow.zip").read_bytes() == studio.zip_bytes and zipfile.is_zipfile(tmp_path / "flow.zip")
    assert any(path.endswith("/export/python/project") for _method, path, _auth in studio.calls)

    source = {"name": "Imported", "nodes": [{"id": "n"}], "edges": [], "state": [], "access": "owner", "mine": True, "owner_email": "a@b.c", "version": 4, "updated": 9}
    (tmp_path / "in.json").write_text(json.dumps(source), encoding="utf-8")
    code, out, err = invoke(["workflows", "import", str(tmp_path / "in.json"), "--json"], http)
    assert code == 0 and err == "" and json.loads(out) == {"ok": True, "id": "new1"}
    assert studio.posts[-1]["name"] == "Imported" and "version" not in studio.posts[-1] and "id" not in studio.posts[-1]
    assert "new1" in studio.rows

    before = len(studio.calls)
    for name in ("notes.py", "Flow.PY", "widget.ts", "Bundle.ZIP", "broken.json", "list.json"):
        path = tmp_path / name
        path.write_text("{" if name == "broken.json" else ("[1]" if name == "list.json" else "print('no')\n"), encoding="utf-8")
        code, out, err = invoke(["workflows", "import", str(path), "--json"], http)
        assert code == 1 and out != "" and error_code(out)[0] == "NOT_A_WORKFLOW" and str(path) in json.loads(out)["error"]["message"]
        assert err == ""
    assert len(studio.calls) == before


def test_two_workflows_named_support_are_ambiguous(signed_in):
    studio = Studio().add("one", "Support", version=1).add("two", "Support", version=1)
    code, out, err = invoke(["workflows", "export", "Support", "--format", "json", "--json"], studio.client())
    assert code == 1 and err == ""
    code_name, message = error_code(out)
    assert code_name == "AMBIGUOUS" and "id" in message and "Support" in message
    assert studio.posts_only() == []
    assert not any("/export/" in path for _method, path, _auth in studio.calls)

    code, out, err = invoke(["workflows", "export", "missing", "--format", "json", "--json"], studio.client())
    assert code == 1 and error_code(out)[0] == "WORKFLOW_NOT_FOUND"


def test_help_has_an_example_and_json_is_one_object(tmp_path, signed_in):
    examples = {
        ("workflows", "--help"): "Example: superstep workflows list",
        ("workflows", "list", "--help"): "Example: superstep workflows list",
        ("workflows", "export", "--help"): "Example: superstep workflows export demo --format json",
        ("workflows", "import", "--help"): "Example: superstep workflows import ./demo.json",
        ("pull", "--help"): "Example: superstep pull ./workflows",
        ("push", "--help"): "Example: superstep push ./workflows",
    }
    for argv, example in examples.items():
        code, out, err = invoke(list(argv))
        assert code == 0 and out == "" and example in err
    code, out, err = invoke(["--lang", "vi", "pull", "--help"])
    assert code == 0 and out == "" and "Ví dụ: superstep pull ./workflows" in err
    code, _out, err = invoke(["--lang", "vi", "workflows", "export", "--help"])
    assert "Ví dụ: superstep workflows export demo --format json" in err
    en = json.loads((ROOT / "en.json").read_text(encoding="utf-8"))
    vi = json.loads((ROOT / "vi.json").read_text(encoding="utf-8"))
    assert set(en) == set(vi)
    for key in ("error.workflow_changed", "error.wrong_server", "error.ambiguous", "error.not_a_workflow", "error.not_found"):
        assert key in en and en[key] and vi[key]

    studio = Studio().add("w1", "Alpha", version=1, nodes=[{"id": "a"}])
    code, out, err = invoke(["workflows", "list", "--json"], studio.client())
    assert code == 0 and err == "" and out.endswith("\n") and out.count("\n") == 1
    body = json.loads(out)
    assert body["ok"] is True and body["workflows"][0]["id"] == "w1" and body["workflows"][0]["version"] == 1
    assert TOKEN not in out
    code, out, err = invoke(["workflows", "list"], studio.client())
    assert code == 0 and out == "" and "Alpha" in err and "w1" in err and TOKEN not in err


def test_a_missing_export_route_names_the_server_version(signed_in):
    studio = Studio().add("w1", "Alpha", version=1)
    studio.export_missing = True
    code, out, err = invoke(["workflows", "export", "w1", "--format", "python", "--json"], studio.client())
    assert code == 1 and err == ""
    code_name, message = error_code(out)
    assert code_name == "SERVER_TOO_OLD" and "0.9.0" in message


def test_a_file_without_an_id_is_created_and_written_back(tmp_path, signed_in):
    studio = Studio().add("w1", "Alpha", version=1, nodes=[{"id": "a"}])
    http = studio.client()
    assert invoke(["pull", str(tmp_path)], http)[0] == 0
    draft = tmp_path / "draft.json"
    draft.write_text(json.dumps({"name": "Draft", "nodes": [], "edges": [], "state": []}), encoding="utf-8")
    code, out, _err = invoke(["push", str(tmp_path), "--json"], http)
    assert code == 0 and json.loads(out)["pushed"] == ["new1"]
    saved = json.loads(draft.read_text(encoding="utf-8"))
    assert saved["id"] == "new1" and "version" not in saved
    assert lock_of(tmp_path)["workflows"]["new1"] == {"name": "Draft", "version": 1}
    assert studio.posts[-1] == {"name": "Draft", "nodes": [], "edges": [], "state": []}


def test_call_uses_the_errors_map_and_leaves_the_default_alone():
    def handler(_request):
        return envelope({"code": "WORKFLOW_NOT_FOUND", "message": "no"}, 409)

    http = client_for(handler)
    with pytest.raises(SessionError) as caught:
        call("GET", URL, "/api/workflows/missing", client=http, token=TOKEN, errors={"WORKFLOW_NOT_FOUND": "error.not_found"})
    assert caught.value.code == "WORKFLOW_NOT_FOUND" and caught.value.key == "error.not_found"
    with pytest.raises(SessionError) as caught:
        call("GET", URL, "/api/workflows/missing", client=http, token=TOKEN)
    assert caught.value.code == "BAD_RESPONSE"

    def missing(request):
        if request.url.path == "/api/health":
            return envelope({"version": "1.2.3"})
        return envelope({"code": "WORKFLOW_NOT_FOUND", "message": "no"}, 404)

    with pytest.raises(SessionError) as caught:
        call("GET", URL, "/api/workflows/missing", client=client_for(missing), token=TOKEN, phase2=True, errors={"WORKFLOW_NOT_FOUND": "error.not_found"})
    assert caught.value.code == "SERVER_TOO_OLD" and caught.value.fmt["version"] == "1.2.3"
