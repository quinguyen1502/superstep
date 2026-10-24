"""Run an exported LangGraph project with `langgraph dev` and call it with the official langgraph-sdk.

    python scripts/langgraph_dev_smoke.py python      # needs: pip install "langgraph-cli[inmem]" langgraph-sdk
    python scripts/langgraph_dev_smoke.py typescript  # needs: Node 20+ and npm (installs the project's packages)

Exports the built-in example workflow as a project (backend/app/engine/project_export.py), starts the server in it,
then searches assistants, creates a thread, waits for a run and streams one. Exits non-zero on any failure.
"""
import asyncio, io, os, shutil, signal, subprocess, sys, tempfile, time, zipfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from app.engine import project_export  # noqa: E402
from app.engine.examples import EXAMPLE  # noqa: E402
from app.engine.python_export import to_python  # noqa: E402
from app.engine.typescript_export import to_typescript  # noqa: E402

PORT = int(os.environ.get("SMOKE_PORT", "2124"))


async def check(url: str) -> None:
    from langgraph_sdk import get_client
    c = get_client(url=url)
    assistants = await c.assistants.search()
    assert [a["graph_id"] for a in assistants] == ["customer_support"], assistants
    aid = assistants[0]["assistant_id"]
    thread = await c.threads.create()
    out = await c.runs.wait(thread["thread_id"], aid, input={"message": "hello there"})
    assert out["intent"] == "general" and out["answer"], out
    events = [ch.event async for ch in c.runs.stream(thread["thread_id"], aid, input={"message": "hi"}, stream_mode="updates")]
    assert "updates" in events, events
    print(f"ok: assistants/search, threads.create, runs.wait -> {out['answer']!r}, runs.stream -> {len(events)} events")


def main(language: str) -> None:
    write = to_python if language == "python" else to_typescript
    code = write(EXAMPLE, "Customer Support", None, {}, None).code
    root = tempfile.mkdtemp(prefix="lg-smoke-", dir=os.environ.get("SMOKE_DIR"))
    zipfile.ZipFile(io.BytesIO(project_export.to_project(language, code, "Customer Support"))).extractall(root)
    proj = os.path.join(root, "customer-support")
    if language == "python":
        cmd = [shutil.which("langgraph") or "langgraph", "dev", "--no-browser", "--port", str(PORT)]
    else:
        subprocess.run(["npm", "install", "--no-audit", "--no-fund"], cwd=proj, check=True)
        cmd = ["npx", "langgraphjs", "dev", "--no-browser", "--port", str(PORT)]
    server = subprocess.Popen(cmd, cwd=proj, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    try:
        url = f"http://localhost:{PORT}"
        for _ in range(90):
            try:
                asyncio.run(check(url)); return
            except Exception as e:  # noqa: BLE001  (not up yet, or a real failure on the last try)
                last = e; time.sleep(1)
        raise SystemExit(f"failed: {last!r}")
    finally:
        os.killpg(server.pid, signal.SIGTERM)
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "python")
