"""follow-up: live LLM tokens in the run stream, registry embeddings for knowledge bases, credential edit (respx)."""
import json, uuid
import httpx, pytest, respx
from fastapi.testclient import TestClient
from app.engine import embeddings, llm, providers
from app.engine.examples import EXAMPLE
from app.main import app

c = TestClient(app)
H = lambda t: {"Authorization": f"Bearer {t}"}
OLL = "http://localhost:11434"


def user():
    r = c.post("/api/auth/register", json={"email": f"ps{uuid.uuid4().hex[:6]}@example.com", "password": "secret12"})
    return r.json()["data"]["token"]


def sse(parts):
    chunk = lambda p: {"id": "x", "object": "chat.completion.chunk", "created": 1, "model": "m", "choices": [{"index": 0, "delta": {"content": p}, "finish_reason": None}]}
    usage = {"id": "x", "object": "chat.completion.chunk", "created": 1, "model": "m", "choices": [], "usage": {"prompt_tokens": 4, "completion_tokens": 3, "total_tokens": 7}}
    return "".join(f"data: {json.dumps(chunk(p))}\n\n" for p in parts) + f"data: {json.dumps(usage)}\n\ndata: [DONE]\n\n"


def ndjson(parts):
    rows = [{"model": "llama3.2", "created_at": "2026-01-01T00:00:00Z", "message": {"role": "assistant", "content": p}, "done": False} for p in parts]
    rows.append({"model": "llama3.2", "created_at": "2026-01-01T00:00:00Z", "message": {"role": "assistant", "content": ""}, "done": True,
                 "done_reason": "stop", "prompt_eval_count": 5, "eval_count": 2})
    return "".join(json.dumps(r) + "\n" for r in rows)


def run_ws(tok, wf, inp):
    with c.websocket_connect(f"/ws/run?token={tok}") as ws:
        ws.send_json({"workflow": wf, "input": inp}); evs = []
        while evs[-1:] == [] or evs[-1]["type"] not in ("run_summary", "error"): evs.append(ws.receive_json())
    return evs


# ---- 1) streaming --------------------------------------------------------------------------------

@respx.mock
def test_openai_compatible_streams_deltas_with_usage():
    respx.post("http://localhost:1234/v1/chat/completions").respond(text=sse(["Xin ", "chào ", "bạn"]), headers={"content-type": "text/event-stream"})
    got, usage = [], []
    out = llm.call_llm("hi", "m", {"provider": "lmstudio"}, usage.append, got.append)
    assert got == ["Xin ", "chào ", "bạn"] and out == "Xin chào bạn"
    assert usage[0]["tokens_in"] == 4 and usage[0]["tokens_out"] == 3 and not usage[0].get("estimated")


@respx.mock
def test_ollama_streams_ndjson():
    respx.post(f"{OLL}/api/chat").respond(text=ndjson(["Hel", "lo"]), headers={"content-type": "application/x-ndjson"})
    got = []
    assert llm.call_llm("hi", "llama3.2", {"provider": "ollama"}, None, got.append) == "Hello" and "".join(got) == "Hello"


def test_plain_http_provider_sends_one_delta(monkeypatch):
    monkeypatch.setattr(providers, "http_client", lambda: httpx.Client(transport=httpx.MockTransport(
        lambda r: httpx.Response(200, json={"choices": [{"message": {"content": "whole answer"}}]}))))
    got = []
    assert llm.call_llm("hi", "gpt-4o-mini", {"provider": "openai", "api_key": "k"}, None, got.append) == "whole answer" and got == ["whole answer"]


def test_token_buffer_coalesces():
    out = []; b = llm.TokenBuffer(out.append, interval=3600)
    for w in ("a", "b", "c"): b(w)
    assert out == []; b.flush(); assert out == ["abc"]


def test_run_streams_tokens_live_but_does_not_store_them(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    tok = user(); wf = json.loads(json.dumps(EXAMPLE))
    evs = run_ws(tok, wf, {"message": "Xin chào, hôm nay thế nào?"})
    toks = [e for e in evs if e["type"] == "node_token"]
    fin = {e["node"]: e for e in evs if e["type"] == "node_finished"}
    assert toks and {e["node"] for e in toks} <= {n["id"] for n in wf["nodes"] if n["type"] == "llm"}
    for nid in {e["node"] for e in toks}:  # concatenated deltas == the node's final text (unchanged)
        field = next(n for n in wf["nodes"] if n["id"] == nid)["data"]["output_field"]
        assert "".join(e["delta"] for e in toks if e["node"] == nid).strip() == fin[nid]["delta"][field]
    started = [i for i, e in enumerate(evs) if e["type"] == "node_started" and e["node"] == toks[0]["node"]][0]
    assert started < evs.index(toks[0]) < evs.index(fin[toks[0]["node"]])
    run_id = next(e["run_id"] for e in evs if e["type"] == "run_started")
    hist = c.get(f"/api/workflows/{wf['id']}/runs", headers=H(tok)).json()["data"] if wf.get("id") else []
    for h in hist:
        if h["id"] == run_id: assert not any(e["type"] == "node_token" for e in h["events"])


# ---- 2) embeddings ---------------------------------------------------------------------------------

@respx.mock
def test_registry_embeddings_per_provider():
    r = respx.post(f"{OLL}/api/embed").respond(json={"model": "nomic-embed-text", "embeddings": [[0.1, 0.2, 0.3], [0.3, 0.2, 0.1]]})
    assert embeddings.embed(["a", "b"], None, {"provider": "ollama"}) == [[0.1, 0.2, 0.3], [0.3, 0.2, 0.1]]
    assert json.loads(r.calls[0].request.content) == {"model": "nomic-embed-text", "input": ["a", "b"]}
    assert embeddings.embedder_id(None, {"provider": "ollama"}) == "ollama:nomic-embed-text"
    respx.post("http://localhost:1234/v1/embeddings").respond(json={"data": [{"index": 1, "embedding": [2.0]}, {"index": 0, "embedding": [1.0]}]})
    assert embeddings.embed(["x", "y"], "e5", {"provider": "lmstudio"}) == [[1.0], [2.0]]
    o = respx.post("https://openrouter.ai/api/v1/embeddings").respond(json={"data": [{"index": 0, "embedding": [0.5, 0.5]}]})
    assert embeddings.embed(["x"], None, {"provider": "openrouter", "api_key": "sk-or"}) == [[0.5, 0.5]]
    assert json.loads(o.calls[0].request.content)["model"] == "openai/text-embedding-3-small"
    with pytest.raises(providers.ProviderError) as e: embeddings.embed(["x"], None, {"provider": "anthropic", "api_key": "k"})
    assert e.value.code == "PROVIDER_EMBEDDINGS_UNSUPPORTED"
    respx.post("http://gpu:8000/v1/embeddings").respond(json={"data": [{"index": 0, "embedding": [1.0]}, {"index": 1, "embedding": [1.0, 2.0]}]})
    with pytest.raises(providers.ProviderError) as e: embeddings.embed(["x", "y"], "m", {"provider": "openai_compatible", "base_url": "http://gpu:8000/v1"})
    assert e.value.code == "PROVIDER_BAD_RESPONSE"


@respx.mock
def test_kb_with_ollama_dims_stored_and_mismatch_refused():
    tok = user()
    cid = c.post("/api/credentials", json={"name": "oll", "provider": "ollama"}, headers=H(tok)).json()["data"]["id"]
    kb = c.post("/api/knowledge-bases", json={"name": "Local KB", "credential_id": cid}, headers=H(tok)).json()["data"]
    assert kb["model"] == "nomic-embed-text"  # provider default when none is given
    route = respx.post(f"{OLL}/api/embed")
    route.side_effect = lambda req: httpx.Response(200, json={"embeddings": [[1.0, 0.0, 0.0]] * len(json.loads(req.content)["input"])})
    up = c.post(f"/api/knowledge-bases/{kb['id']}/documents", files={"file": ("a.txt", b"alpha beta gamma")}, headers=H(tok)).json()
    assert up["success"], up
    got = c.get(f"/api/knowledge-bases/{kb['id']}", headers=H(tok)).json()["data"]
    assert got["embedder"] == "ollama:nomic-embed-text" and got["dims"] == 3
    assert c.post(f"/api/knowledge-bases/{kb['id']}/search", json={"query": "alpha"}, headers=H(tok)).json()["data"][0]["score"] > 0.99
    # same model name, now 4-dimensional (re-pulled model): refused with a clear code instead of mixing vectors
    route.side_effect = lambda req: httpx.Response(200, json={"embeddings": [[1.0, 0.0, 0.0, 0.0]] * len(json.loads(req.content)["input"])})
    e = c.post(f"/api/knowledge-bases/{kb['id']}/search", json={"query": "alpha"}, headers=H(tok))
    assert e.status_code == 409 and e.json()["error"]["code"] == "KB_EMBEDDING_DIMENSION_MISMATCH" and "4" in e.json()["error"]["message"]
    assert c.post(f"/api/knowledge-bases/{kb['id']}/documents", files={"file": ("b.txt", b"delta")}, headers=H(tok)).json()["error"]["code"] == "KB_EMBEDDING_DIMENSION_MISMATCH"
    r = c.post(f"/api/knowledge-bases/{kb['id']}/reindex", headers=H(tok)).json()["data"]  # re-index adopts the new size
    assert r["dims"] == 4 and c.post(f"/api/knowledge-bases/{kb['id']}/search", json={"query": "alpha"}, headers=H(tok)).json()["success"]
    # unreachable server → provider code, not a generic failure
    route.side_effect = httpx.ConnectError("refused")
    assert c.post(f"/api/knowledge-bases/{kb['id']}/search", json={"query": "alpha"}, headers=H(tok)).json()["error"]["code"] == "PROVIDER_UNREACHABLE"


def test_legacy_kb_dims_read_from_stored_chunk(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    from app.api.deps import get_db
    from sqlalchemy import text
    tok = user()
    kb = c.post("/api/knowledge-bases", json={"name": "Old"}, headers=H(tok)).json()["data"]
    c.post(f"/api/knowledge-bases/{kb['id']}/documents", files={"file": ("a.txt", b"alpha beta")}, headers=H(tok))
    with get_db().session() as s: s.execute(text("UPDATE knowledge_bases SET dims = NULL WHERE id = :k"), {"k": kb["id"]}); s.commit()
    assert c.post(f"/api/knowledge-bases/{kb['id']}/search", json={"query": "alpha"}, headers=H(tok)).json()["success"]
    assert c.get(f"/api/knowledge-bases/{kb['id']}", headers=H(tok)).json()["data"]["dims"] == embeddings.MOCK_DIMS


@respx.mock
def test_embedding_test_endpoint():
    tok = user()
    oll = c.post("/api/credentials", json={"name": "o", "provider": "ollama"}, headers=H(tok)).json()["data"]["id"]
    ant = c.post("/api/credentials", json={"name": "a", "provider": "anthropic", "api_key": "sk-ant-x"}, headers=H(tok)).json()["data"]["id"]
    respx.post(f"{OLL}/api/embed").respond(json={"embeddings": [[0.0] * 768]})
    r = c.post(f"/api/credentials/{oll}/embeddings/test", json={}, headers=H(tok)).json()["data"]
    assert r["dims"] == 768 and r["model"] == "nomic-embed-text"
    assert c.post(f"/api/credentials/{ant}/embeddings/test", json={}, headers=H(tok)).json()["error"]["code"] == "PROVIDER_EMBEDDINGS_UNSUPPORTED"
    respx.post(f"{OLL}/api/embed").respond(404, json={"error": "model \"x\" not found"})
    assert c.post(f"/api/credentials/{oll}/embeddings/test", json={"model": "x"}, headers=H(tok)).json()["error"]["code"] == "MODEL_NOT_FOUND"


# ---- 3) credential edit -----------------------------------------------------------------------------

def test_edit_credential_keeps_secret_unless_reentered():
    from app.api.deps import credential_service
    tok = user()
    cr = c.post("/api/credentials", json={"name": "OR", "provider": "openrouter", "api_key": "sk-or-first-1111"}, headers=H(tok)).json()["data"]
    put = lambda body: c.put(f"/api/credentials/{cr['id']}", json=body, headers=H(tok)).json()
    r = put({"name": "OpenRouter team", "base_url": "https://openrouter.ai/api/v1", "headers": {"X-Title": "Studio"}}); assert r["success"], r; r = r["data"]
    assert r["name"] == "OpenRouter team" and r["hint"] == cr["hint"] and r["headers"] == {"X-Title": "Studio"} and r["provider"] == "openrouter"
    uid = c.get("/api/me", headers=H(tok)).json()["data"]["id"]
    svc = credential_service(); assert svc.resolve(uid, cr["id"])["api_key"] == "sk-or-first-1111"
    r = put({"name": "OpenRouter team", "api_key": "sk-or-second-2222"})["data"]
    assert r["hint"].endswith("2222") and "sk-or-second" not in json.dumps(r) and svc.resolve(uid, cr["id"])["api_key"] == "sk-or-second-2222"
    assert put({"name": "x", "clear_key": True})["error"]["code"] == "CREDENTIAL_KEY_REQUIRED"  # OpenRouter needs a key
    assert put({"name": "x", "headers": {"X-Nope": "1"}})["error"]["code"] == "CREDENTIAL_HEADER_UNSUPPORTED"
    assert put({"name": "x", "base_url": "ftp://x"})["error"]["code"] == "CREDENTIAL_BASE_URL_INVALID"
    oll = c.post("/api/credentials", json={"name": "o", "provider": "ollama", "api_key": "proxy-token-9999"}, headers=H(tok)).json()["data"]
    r = c.put(f"/api/credentials/{oll['id']}", json={"name": "o", "clear_key": True}, headers=H(tok)).json()["data"]
    assert r["hint"] == "" and svc.resolve(uid, oll["id"])["api_key"] == ""
    other = user()
    assert c.put(f"/api/credentials/{cr['id']}", json={"name": "steal"}, headers=H(other)).json()["error"]["code"] == "CREDENTIAL_NOT_FOUND"


@respx.mock
def test_probe_while_editing_uses_stored_key():
    tok = user()
    cr = c.post("/api/credentials", json={"name": "OR", "provider": "openrouter", "api_key": "sk-or-stored-1"}, headers=H(tok)).json()["data"]
    m = respx.get("https://openrouter.ai/api/v1/models").respond(json={"data": [{"id": "openrouter/auto"}]})
    assert c.post("/api/providers/openrouter/test", json={"credential_id": cr["id"]}, headers=H(tok)).json()["success"]
    assert m.calls[0].request.headers["authorization"] == "Bearer sk-or-stored-1"
    other = user()  # someone else's credential id gives nothing
    assert c.post("/api/providers/openrouter/test", json={"credential_id": cr["id"]}, headers=H(other)).json()["error"]["code"] == "CREDENTIAL_NOT_FOUND"
