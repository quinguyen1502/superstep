import io, os, tempfile, time, zipfile
os.environ.setdefault("STUDIO_DB", tempfile.mktemp(suffix=".db"))
# The API is off unless the flag is set. These tests keep the host subprocess; they do not need Docker.
os.environ.setdefault("STUDIO_ENABLE_IMPORT", "1")
os.environ.setdefault("STUDIO_IMPORT_RUNTIME", "subprocess")
import pytest
from fastapi.testclient import TestClient
from app.engine import repo_import as importer
from app.main import app

FIX = os.path.join(os.path.dirname(__file__), "fixtures")

def zip_dir(path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for dp, _, fns in os.walk(path):
            for f in fns:
                full = os.path.join(dp, f); z.write(full, os.path.join("repo", os.path.relpath(full, path)))
    return buf.getvalue()

@pytest.fixture(scope="module")
def job():
    jid = importer.start_job("u1", "zip", zip_bytes=zip_dir(os.path.join(FIX, "cond_repo")), sync=True)
    j = importer.JOBS[jid]; assert j["status"] == "ready", j["log"]
    return j

def test_find_graphs_fallback_scan():
    gs = importer.find_graphs(os.path.join(FIX, "scan_repo"))
    assert gs == [{"id": "agent.my_graph", "ref": "agent.py:my_graph", "via": "scan"}]

def test_reject_bad_url_and_zip_slip():
    with pytest.raises(importer.ImportError_): importer.start_job("u", "url", url="file:///etc")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z: z.writestr("../evil.txt", "x")
    jid = importer.start_job("u", "zip", zip_bytes=buf.getvalue(), sync=True)
    assert importer.JOBS[jid]["status"] == "error" and "unsafe path" in importer.JOBS[jid]["error"]

def test_inspect_and_convert(job):
    assert job["graphs"][0]["id"] == "router" and job["required_env"] == ["OPENAI_API_KEY"]
    wf = importer.to_workflow(job, "router")
    types = {n["id"]: n["type"] for n in wf["nodes"]}
    assert types == {"__start__": "start", "classify": "code", "answer": "code", "echo": "code", "__end__": "end"}
    cond = {(e["source"], e["target"], e.get("label")) for e in wf["edges"] if e["conditional"]}
    assert ("classify", "answer", "answer") in cond and ("classify", "echo", "echo") in cond and ("echo", "__end__", "__end__") in cond
    code = next(n for n in wf["nodes"] if n["id"] == "classify")["data"]
    assert code["ref"].endswith(":classify") and "def classify" in code["source"]
    assert {f["name"] for f in wf["state"]} >= {"text", "count", "kind"}

def test_run_streaming_loop(job):
    wf = importer.to_workflow(job, "router")
    evs = list(importer.run_imported(wf, {"text": "hi"}))
    fin = [e["node"] for e in evs if e["type"] == "node_finished"]
    assert fin == ["__start__", "classify", "echo", "echo", "__end__"]
    assert evs[-1]["type"] == "run_finished" and evs[-1]["state"]["text"] == "hi!!"
    assert all("duration_ms" in e for e in evs if e["type"] == "node_finished")

def test_run_missing_key_is_clear_error(job):
    wf = importer.to_workflow(job, "router")
    evs = list(importer.run_imported(wf, {"text": "boom"}))
    assert evs[-1]["type"] == "error" and "API key" in evs[-1]["errors"][0] and "OPENAI_API_KEY" in evs[-1]["errors"][-1]

def test_api_import_finalize_ws():
    c = TestClient(app)
    tok = c.post("/api/auth/login", json={"email": "admin@example.com", "password": "admin123"}).json()["data"]["token"]
    H = {"Authorization": f"Bearer {tok}"}
    jid = c.post("/api/import", files={"file": ("r.zip", zip_dir(os.path.join(FIX, "cond_repo")), "application/zip")}, headers=H).json()["data"]["job_id"]
    for _ in range(240):
        st = c.get(f"/api/import/{jid}", headers=H).json()["data"]
        if st["status"] in ("ready", "error"): break
        time.sleep(0.5)
    assert st["status"] == "ready", st
    wid = c.post(f"/api/import/{jid}/finalize", json={"graph_id": "router"}, headers=H).json()["data"]["id"]
    wf = c.get(f"/api/workflows/{wid}", headers=H).json()["data"]; assert wf["source"]["kind"] == "langgraph_import"
    # client cannot tamper with source on save
    c.post("/api/workflows", json={**wf, "source": {"kind": "langgraph_import", "repo_dir": "/tmp"}}, headers=H)
    assert c.get(f"/api/workflows/{wid}", headers=H).json()["data"]["source"]["repo_dir"] == wf["source"]["repo_dir"]
    with c.websocket_connect(f"/ws/run?token={tok}") as ws:
        ws.send_json({"workflow_id": wid, "input": {"text": "why?"}})
        evs = []
        while True:
            evs.append(ws.receive_json())
            if evs[-1]["type"] in ("run_finished", "error"): break
    assert evs[-1]["type"] == "run_finished" and evs[-1]["state"]["text"] == "answer to: why?"

def test_run_checkpoints_and_resumes_in_a_fresh_subprocess(job):
    """the runner attaches a LangGraph saver, streams serialized superstep checkpoints, and a new
    subprocess continues from one of them (what a recovered queue job does)."""
    wf = importer.to_workflow(job, "router")
    evs = list(importer.run_imported(wf, {"text": "hi"}, checkpointing=True))
    cps = [e for e in evs if e["type"] == "_checkpoint"]
    assert evs[-1]["type"] == "run_finished" and cps and all(c["blob"]["data"] for c in cps)
    mid = next(c for c in cps if c["nodes"] == ["echo"])  # after classify, before the first echo
    again = list(importer.run_imported(wf, {"text": "ignored"}, resume={"blob": mid["blob"]}, checkpointing=True))
    fin = [e["node"] for e in again if e["type"] == "node_finished"]
    assert "classify" not in fin and fin[:2] == ["echo", "echo"] and again[-1]["state"]["text"] == "hi!!"
