"""Smoke test for a running stack (docker compose or dev): health, demo login, seeded example run over /ws/run, the API
trigger, and the frame headers of the studio and a published chat page (TASK-0143).
Usage: python scripts/compose_smoke.py [http://localhost:8080]   (needs `httpx` and `websockets`)
SMOKE_EMAIL / SMOKE_PASSWORD sign in as another account (production has no demo user: the all-in-one image smoke test)."""
import asyncio, json, os, sys
import httpx, websockets

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080").rstrip("/")
LOGIN = {"email": os.environ.get("SMOKE_EMAIL", "admin@example.com"), "password": os.environ.get("SMOKE_PASSWORD", "admin123")}


async def main():
    with httpx.Client(base_url=BASE, timeout=10) as c:
        health = c.get("/api/health").json()["data"]; print("health:", health)
        tok = c.post("/api/auth/login", json=LOGIN).json()["data"]["token"]
        H = {"Authorization": f"Bearer {tok}"}
        wf = c.get("/api/workflows", headers=H).json()["data"][0]; print("workflow:", wf["name"])
        assert c.post("/api/runs/nope/cancel", headers=H).json()["error"]["code"] == "RUN_NOT_FOUND"
    ws_url = BASE.replace("http", "ws", 1) + f"/ws/run?token={tok}"
    async with websockets.connect(ws_url) as ws:
        await ws.send(json.dumps({"workflow_id": wf["id"], "input": {"question": "hello"}}))
        types = []
        async for raw in ws:
            ev = json.loads(raw)
            # run_summary comes after the run is written to history; stopping at run_finished raced the write
            if ev["type"] == "run_summary": break
            types.append(ev["type"])
    print("events:", " ".join(types))
    assert types[0] == "run_started" and types[-1] == "run_finished", types
    with httpx.Client(base_url=BASE, timeout=10) as c:
        runs = c.get(f"/api/workflows/{wf['id']}/runs", headers=H).json()["data"]
        print("history:", len(runs), "latest status:", runs[0]["status"])
    print("SMOKE OK")


asyncio.run(main())


def api_trigger_check():
    """TASK-0007: token + sync trigger through nginx (executed by the worker service via the Redis queue)."""
    with httpx.Client(base_url=BASE, timeout=60) as c:
        tok = c.post("/api/auth/login", json=LOGIN).json()["data"]["token"]
        wid = c.get("/api/workflows", headers={"Authorization": f"Bearer {tok}"}).json()["data"][0]["id"]
        secret = c.post(f"/api/workflows/{wid}/tokens", json={"name": "smoke"}, headers={"Authorization": f"Bearer {tok}"}).json()["data"]["token"]
        d = c.post(f"/api/hooks/workflows/{wid}/runs", json={"input": {"message": "refund"}, "mode": "sync"},
                   headers={"Authorization": f"Bearer {secret}"}).json()["data"]
        print("api trigger:", d["status"], d["source"], d["final_state"]["intent"])
        assert d["status"] == "ok" and d["source"] == "api"
    print("API TRIGGER OK")


api_trigger_check()


def frame_check():
    """TASK-0143: no studio page may be framed; a published chat page names its embed sites in frame-ancestors (nginx
    auth_request in Compose, a middleware in the all-in-one image); the widget script is served at /c/widget.js."""
    with httpx.Client(base_url=BASE, timeout=10) as c:
        tok = c.post("/api/auth/login", json=LOGIN).json()["data"]["token"]
        H = {"Authorization": f"Bearer {tok}"}
        home = c.get("/")
        assert (home.headers.get("x-frame-options"), home.headers.get("content-security-policy")) == ("DENY", "frame-ancestors 'none'"), dict(home.headers)
        wf = {"name": "Smoke chat", "state": [{"name": "message", "type": "string"}, {"name": "reply", "type": "string"}],
              "nodes": [{"id": "s", "type": "start", "position": {"x": 0, "y": 0}, "data": {}}, {"id": "e", "type": "end", "position": {"x": 200, "y": 0}, "data": {}}],
              "edges": [{"id": "1", "source": "s", "target": "e"}]}
        wid = c.post("/api/workflows", json=wf, headers=H).json()["data"]["id"]
        slug = "smoke-" + "".join(ch for ch in wid.lower() if ch.isalnum())[:12]
        r = c.put(f"/api/workflows/{wid}/chat", headers=H, json={"enabled": True, "access": "anonymous", "slug": slug, "input_field": "message",
                                                                  "reply_field": "reply", "embed_origins": ["https://shop.example.com"]}).json()
        assert r["success"], r
        page = c.get(f"/c/{slug}")
        assert page.status_code == 200 and '<div id="root"' in page.text, page.status_code
        assert page.headers.get("content-security-policy") == "frame-ancestors 'self' https://shop.example.com", dict(page.headers)
        assert "x-frame-options" not in page.headers, dict(page.headers)
        assert c.get("/c/no-such-chat").headers.get("content-security-policy") == "frame-ancestors 'none'"
        widget = c.get("/c/widget.js")
        assert widget.status_code == 200 and "superstep-chat" in widget.text, widget.status_code
        c.delete(f"/api/workflows/{wid}", headers=H)
    print("FRAMES OK")


frame_check()
