"""provider registry (Ollama, LM Studio, OpenAI-compatible, OpenRouter) with mocked HTTP (respx)."""
import json, uuid
import httpx, pytest, respx
from fastapi.testclient import TestClient
from app.engine import llm, providers
from app.main import app

c = TestClient(app)
H = lambda t: {"Authorization": f"Bearer {t}"}
OR_KEY = "sk-or-test-0123456789abcdef"


def user():
    r = c.post("/api/auth/register", json={"email": f"lp{uuid.uuid4().hex[:6]}@example.com", "password": "secret12"})
    return r.json()["data"]["token"]


def chat_reply(text="hello", tools=None):
    msg = {"role": "assistant", "content": text}
    if tools: msg = {"role": "assistant", "content": None, "tool_calls": tools}
    return {"id": "x", "object": "chat.completion", "created": 1, "model": "m",
            "choices": [{"index": 0, "message": msg, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5}}


def test_registry_lists_new_providers_with_defaults():
    t = user(); ps = {p["id"]: p for p in c.get("/api/providers", headers=H(t)).json()["data"]}
    assert ps["ollama"]["default_base_url"] == "http://localhost:11434" and not ps["ollama"]["key_required"]
    assert ps["lmstudio"]["default_base_url"] == "http://localhost:1234/v1" and ps["lmstudio"]["local"]
    assert ps["openrouter"]["key_required"] and ps["openrouter"]["header_fields"] == ["HTTP-Referer", "X-Title"]
    assert "openai_compatible" in ps and ps["openai"]["key_required"]


@respx.mock
def test_ollama_models_and_chat():
    respx.get("http://localhost:11434/api/tags").respond(json={"models": [{"name": "qwen2.5:7b", "model": "qwen2.5:7b"}, {"name": "llama3.2:latest", "model": "llama3.2:latest"}]})
    assert providers.get("ollama").list_models({"provider": "ollama"}) == ["llama3.2:latest", "qwen2.5:7b"]
    route = respx.post("http://localhost:11434/api/chat").respond(
        json={"model": "llama3.2", "created_at": "2026-01-01T00:00:00Z", "message": {"role": "assistant", "content": "xin chào"},
              "done": True, "done_reason": "stop", "prompt_eval_count": 4, "eval_count": 2})
    usage = []
    assert llm.call_llm("hi", "llama3.2", {"provider": "ollama", "base_url": None}, usage.append) == "xin chào"
    assert json.loads(route.calls[0].request.content)["model"] == "llama3.2"
    assert usage[0]["provider"] == "ollama" and usage[0]["tokens_in"] == 4 and not usage[0].get("estimated")


@respx.mock
def test_ollama_errors_map_to_codes():
    respx.post("http://localhost:11434/api/chat").respond(404, json={"error": "model \"nope\" not found, try pulling it first"})
    with pytest.raises(providers.ProviderError) as e: llm.call_llm("hi", "nope", {"provider": "ollama"})
    assert e.value.code == "MODEL_NOT_FOUND"
    respx.get("http://127.0.0.1:9/api/tags").mock(side_effect=httpx.ConnectError("refused"))
    with pytest.raises(providers.ProviderError) as e: providers.get("ollama").list_models({"base_url": "http://127.0.0.1:9"})
    assert e.value.code == "PROVIDER_UNREACHABLE" and "127.0.0.1:9" in str(e.value)


@respx.mock
def test_lmstudio_chat_streaming_and_tools():
    respx.get("http://localhost:1234/v1/models").respond(json={"data": [{"id": "qwen2.5-7b-instruct"}]})
    assert providers.get("lmstudio").list_models({}) == ["qwen2.5-7b-instruct"]
    route = respx.post("http://localhost:1234/v1/chat/completions")
    route.respond(json=chat_reply("ok from lm studio"))
    cred = {"provider": "lmstudio", "base_url": None, "api_key": ""}
    assert llm.call_llm("hi", "qwen2.5-7b-instruct", cred) == "ok from lm studio"
    assert route.calls[0].request.headers["authorization"] == "Bearer not-needed"
    # tool calling through bind_tools
    route.respond(json=chat_reply(tools=[{"id": "c1", "type": "function", "function": {"name": "lookup", "arguments": "{\"q\": \"A100\"}"}}]))
    def lookup(q: str) -> str:
        """Look up an order."""
        return q
    msg = llm.chat_model(cred, "m").bind_tools([lookup]).invoke("where is A100")
    assert msg.tool_calls[0]["name"] == "lookup" and msg.tool_calls[0]["args"] == {"q": "A100"}
    assert json.loads(route.calls[-1].request.content)["tools"][0]["function"]["name"] == "lookup"
    # streaming (SSE)
    sse = "".join(f"data: {json.dumps({'id': 'x', 'object': 'chat.completion.chunk', 'created': 1, 'model': 'm', 'choices': [{'index': 0, 'delta': {'content': p}, 'finish_reason': None}]})}\n\n" for p in ("Xin ", "chào")) + "data: [DONE]\n\n"
    route.respond(text=sse, headers={"content-type": "text/event-stream"})
    assert "".join(ch.content for ch in llm.chat_model(cred, "m").stream("hi")) == "Xin chào"


@respx.mock
def test_openrouter_sends_key_and_headers_and_maps_auth():
    models = respx.get("https://openrouter.ai/api/v1/models").respond(json={"data": [{"id": "meta-llama/llama-3.1-8b-instruct"}, {"id": "openrouter/auto"}]})
    chat = respx.post("https://openrouter.ai/api/v1/chat/completions").respond(json=chat_reply("routed"))
    cred = {"provider": "openrouter", "api_key": OR_KEY, "headers": {"HTTP-Referer": "https://studio.example", "X-Title": "Superstep"}}
    assert providers.get("openrouter").list_models(cred)[1] == "openrouter/auto"
    assert models.calls[0].request.headers["authorization"] == f"Bearer {OR_KEY}"
    assert llm.call_llm("hi", "", cred) == "routed"
    req = chat.calls[0].request
    assert req.headers["http-referer"] == "https://studio.example" and req.headers["x-title"] == "Superstep"
    assert json.loads(req.content)["model"] == "openrouter/auto"
    chat.respond(401, json={"error": {"message": "No auth credentials found", "code": 401}})
    with pytest.raises(providers.ProviderError) as e: llm.call_llm("hi", "x", cred)
    assert e.value.code == "PROVIDER_AUTH_FAILED"


@respx.mock
def test_generic_openai_compatible_model_not_found():
    respx.post("http://gpu-box:8000/v1/chat/completions").respond(404, json={"error": {"message": "The model `x` does not exist."}})
    with pytest.raises(providers.ProviderError) as e: llm.call_llm("hi", "x", {"provider": "openai_compatible", "base_url": "http://gpu-box:8000/v1"})
    assert e.value.code == "MODEL_NOT_FOUND" and e.value.params["model"] == "x"


@respx.mock
def test_api_credential_setup_test_connection_and_models():
    t = user()
    # key optional for local providers, required for OpenRouter, headers validated per provider
    r = c.post("/api/credentials", json={"name": "Local Ollama", "provider": "ollama"}, headers=H(t)).json()
    assert r["success"] and r["data"]["hint"] == "" and r["data"]["base_url"] is None
    assert c.post("/api/credentials", json={"name": "or", "provider": "openrouter"}, headers=H(t)).json()["error"]["code"] == "CREDENTIAL_KEY_REQUIRED"
    bad = c.post("/api/credentials", json={"name": "x", "provider": "ollama", "headers": {"X-Title": "x"}}, headers=H(t)).json()
    assert bad["error"]["code"] == "CREDENTIAL_HEADER_UNSUPPORTED"
    orc = c.post("/api/credentials", json={"name": "OR", "provider": "openrouter", "api_key": OR_KEY, "headers": {"X-Title": "Studio"}}, headers=H(t)).json()["data"]
    assert orc["headers"] == {"X-Title": "Studio"} and OR_KEY not in json.dumps(orc)
    # saved credential: models / test connection
    respx.get("http://localhost:11434/api/tags").respond(json={"models": [{"name": "llama3.2"}]})
    m = c.get(f"/api/credentials/{r['data']['id']}/models", headers=H(t)).json()["data"]
    assert m["ok"] and m["models"] == ["llama3.2"] and m["base_url"] == "http://localhost:11434"
    # unsaved probe + error envelope
    respx.get("http://localhost:1234/v1/models").mock(side_effect=httpx.ConnectError("refused"))
    e = c.post("/api/providers/lmstudio/test", json={}, headers=H(t))
    assert e.status_code == 502 and e.json()["error"]["code"] == "PROVIDER_UNREACHABLE"
    assert "http://localhost:1234/v1" in e.json()["error"]["message"]
    respx.get("https://openrouter.ai/api/v1/models").respond(401, json={"error": {"message": "bad key"}})
    e = c.post("/api/providers/openrouter/test", json={"api_key": "nope"}, headers=H(t))
    assert e.status_code == 400 and e.json()["error"]["code"] == "PROVIDER_AUTH_FAILED"
    assert c.post("/api/providers/nope/test", json={}, headers=H(t)).json()["error"]["code"] == "CREDENTIAL_PROVIDER_UNSUPPORTED"
