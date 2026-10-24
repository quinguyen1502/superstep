"""Live check of the LangGraph Agent Server API subset (`/api/lg`) with the official clients.

    backend/.venv/bin/python scripts/agent_server_smoke.py

Starts the backend on a temporary database (PORT, default 8131), signs in as the dev admin, creates a workflow token
for the seeded "example" workflow and a Human-node workflow, then uses `langgraph_sdk.get_client` (async, over the
network) and `langgraph.pregel.remote.RemoteGraph`: assistants, threads, runs.wait, runs.stream, get_state, an
interrupt resumed with Command(resume=...). Exits non-zero on any failure.
"""
import asyncio, os, subprocess, sys, tempfile, time
import httpx
from langgraph_sdk import get_client

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = int(os.environ.get("PORT", "8131"))
BASE = f"http://127.0.0.1:{PORT}"
N = lambda i, t, **d: {"id": i, "type": t, "position": {"x": 0, "y": 0}, "data": {"label": i, **d}}  # noqa: E731
APPROVAL = {"name": "Approval", "state": [{"name": "message", "type": "string"}, {"name": "decision", "type": "string"}],
            "nodes": [N("start", "start"), N("ask", "human", prompt="Approve {{state.message}}?", output_field="decision"), N("end", "end")],
            "edges": [{"id": "1", "source": "start", "target": "ask"}, {"id": "2", "source": "ask", "target": "end"}]}


async def check(token: str, jwt: str, hitl: str) -> None:
    client = get_client(url=f"{BASE}/api/lg", api_key=token)
    assert [a["assistant_id"] for a in await client.assistants.search()] == ["example"]
    thread = await client.threads.create()
    out = await client.runs.wait(thread["thread_id"], "example", input={"message": "Where is order A100?"})
    assert out["intent"] == "order_status", out
    print("runs.wait:", out["answer"])
    modes = [p.event async for p in client.runs.stream(thread["thread_id"], "example", input={"message": "hello"}, stream_mode=["updates", "values"])]
    assert modes[0] == "metadata" and "updates" in modes and "values" in modes, modes
    print("runs.stream events:", modes)
    state = await client.threads.get_state(thread["thread_id"])
    print("threads.get_state:", sorted(state["values"]))

    user = get_client(url=f"{BASE}/api/lg", api_key=jwt)  # a user JWT: every workflow the user may run
    t = await user.threads.create()
    waiting = await user.runs.wait(t["thread_id"], hitl, input={"message": "refund"})
    assert waiting["__interrupt__"][0]["value"]["node"] == "ask", waiting
    done = await user.runs.wait(t["thread_id"], hitl, command={"resume": "approved"})
    assert done["decision"] == "approved", done
    print("interrupt + resume:", waiting["__interrupt__"][0]["value"], "->", done["decision"])

    from langgraph.pregel.remote import RemoteGraph
    remote = RemoteGraph("example", url=f"{BASE}/api/lg", api_key=token)
    res = await remote.ainvoke({"message": "hello"})
    assert res["intent"] == "general", res
    print("RemoteGraph.ainvoke:", res["answer"])


def main() -> None:
    work = tempfile.mkdtemp(prefix="superstep-lg-")
    env = {**os.environ, "STUDIO_DB": f"{work}/it.db", "STUDIO_IMPORT_DIR": f"{work}/imports", "STUDIO_SECRET_KEY_FILE": f"{work}/secret.key",
           "OPENAI_API_KEY": "", "STUDIO_ENABLE_DEMO_TOOLS": "1", "STUDIO_TRIGGER_RATE_LIMIT": "0"}
    server = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
                              cwd=os.path.join(ROOT, "backend"), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    try:
        for _ in range(120):
            try:
                if httpx.get(f"{BASE}/api/health").status_code == 200: break
            except httpx.HTTPError: pass
            time.sleep(0.5)
        jwt = httpx.post(f"{BASE}/api/auth/login", json={"email": "admin@example.com", "password": "admin123"}).json()["data"]["token"]
        h = {"Authorization": f"Bearer {jwt}"}
        token = httpx.post(f"{BASE}/api/workflows/example/tokens", json={"name": "lg-smoke"}, headers=h).json()["data"]["token"]
        hitl = httpx.post(f"{BASE}/api/workflows", json=APPROVAL, headers=h).json()["data"]["id"]
        asyncio.run(check(token, jwt, hitl))
        print("ok")
    finally:
        server.terminate(); server.wait(10)


if __name__ == "__main__":
    main()
