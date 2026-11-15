"""Decision nodes call TypeSafe's Jev with typed questions and write the answers to state."""
import copy, json, uuid
import httpx, pytest
from fastapi.testclient import TestClient
from app.engine import decisions, providers
from app.engine.effects import Effects
from app.engine.runtime import run_stream
from app.engine.validator import validate
from app.main import app

c = TestClient(app)
KEY = "ts-test-key-0123456789abcdef"


def H(t): return {"Authorization": f"Bearer {t}"}
def user(): return c.post("/api/auth/register", json={"email": f"jev{uuid.uuid4().hex[:6]}@example.com", "password": "secret12"}).json()["data"]["token"]
def N(i, t, **d): return {"id": i, "type": t, "data": {"label": i, **d}}
def E(i, s, t, label=None): return {"id": i, "source": s, "target": t, **({"label": label} if label else {})}

QUESTIONS = [
    {"id": "intent", "type": "choice", "instructions": "Which team should answer {{state.message}}?", "field": "intent",
     "options": [{"label": "order", "description": "Order status or delivery"}, {"label": "refund", "description": "Money back"}, {"label": "other", "description": ""}]},
    {"id": "urgency", "type": "score", "instructions": "How urgent is it?", "levels": ["Not urgent", "Soon", "Now"], "field": "urgency"},
    {"id": "angry", "type": "noul", "instructions": "The customer is angry.", "field": "angry"},
]
STATE = [{"name": "message", "type": "string"}, {"name": "ticket", "type": "object"}, {"name": "intent", "type": "string"},
         {"name": "urgency", "type": "number"}, {"name": "angry", "type": "number"}, {"name": "answers", "type": "object"}, {"name": "reply", "type": "string"}]


def flow(text="{{state.message}}", **extra):
    d = {"label": "Classify", "model": "jev-latest", "text": text, "questions": copy.deepcopy(QUESTIONS), "output_field": "answers", **extra}
    nodes = [N("s", "start"), {"id": "dec", "type": "decision", "data": d}, N("route", "condition", field="intent", default="other"),
             N("o", "tool", function="lookup_order", output_field="reply"), N("e", "end")]
    edges = [E("1", "s", "dec"), E("2", "dec", "route"), E("3", "route", "o", "order"), E("4", "route", "e", "other"), E("5", "o", "e")]
    return {"name": f"jev {uuid.uuid4().hex[:4]}", "state": copy.deepcopy(STATE), "nodes": nodes, "edges": edges}


@pytest.fixture
def jev(monkeypatch):
    calls = []
    def handler(req: httpx.Request):
        calls.append(req); body = json.loads(req.content)
        if req.headers.get("authorization") != f"Bearer {KEY}": return httpx.Response(401, json={"error": {"message": "invalid api key"}})
        if req.url.path != "/v1/systemone": return httpx.Response(404)
        ans = {}
        for qid, q in body["questions"].items():
            if q["type"] == "choice": ans[qid] = {"type": "choice", "choice": "refund", "confidence": 0.8, "probabilities": {k: (0.9 if k == "refund" else 0.05) for k in q["criteria"]}}
            elif q["type"] == "score": ans[qid] = {"type": "score", "score": 1.43, "confidence": 0.35, "legend": {"0": "a"}, "probabilities": {"0": 0.0, "1": 0.57, "2": 0.43}}
            else: ans[qid] = {"type": "noul", "noul": 0.99}
        return httpx.Response(200, json={"model": "jev-1.13.0", "answers": ans, "usage": {"input_tokens": 400, "output_tokens": 70}})
    monkeypatch.setattr(providers, "http_client", lambda: httpx.Client(transport=httpx.MockTransport(handler)))
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    return calls


def run_ws(tok, wid, inp):
    with c.websocket_connect(f"/ws/run?token={tok}") as ws:
        ws.send_json({"workflow_id": wid, "input": inp}); evs = []
        while True:
            evs.append(ws.receive_json())
            if evs[-1]["type"] in ("run_finished", "error"): return evs


# ---------- offline ----------
def test_offline_mock_answers_and_routes(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    evs = list(run_stream(flow(), {"message": "Where is my order A100?"}))
    st = evs[-1]["state"]
    assert evs[-1]["type"] == "run_finished" and st["intent"] == "order" and st["urgency"] == 0.0 and st["angry"] == 0.5
    assert set(st["answers"]) == {"intent", "urgency", "angry"} and st["answers"]["intent"]["probabilities"]["order"] == 1.0
    assert "A100" in st["reply"]  # the Condition followed the choice
    fin = next(e for e in evs if e["type"] == "node_finished" and e["node"] == "dec")
    assert fin["usage"]["provider"] == "mock" and fin["usage"]["cost_usd"] == 0.0


def test_request_body():
    body = decisions.build(flow(text="{{state.ticket}}")["nodes"][1]["data"], {"ticket": {"id": 7, "text": "help"}, "message": "late parcel"})
    assert body["state"] == {"id": 7, "text": "help"}  # an exact reference keeps its type
    q = body["questions"]
    assert q["intent"] == {"type": "choice", "instructions": "Which team should answer late parcel?",
                           "criteria": {"order": "Order status or delivery", "refund": "Money back", "other": None}}
    assert q["urgency"]["criteria"] == ["Not urgent", "Soon", "Now"] and q["angry"] == {"type": "noul", "instructions": "The customer is angry."}
    assert body["model"] == "jev-latest"


# ---------- TypeSafe API ----------
def test_run_with_a_typesafe_credential(jev):
    t = user()
    cid = c.post("/api/credentials", json={"name": "ts", "provider": "typesafe", "api_key": KEY}, headers=H(t)).json()["data"]["id"]
    wf = flow(credential_id=cid); wid = c.post("/api/workflows", json=wf, headers=H(t)).json()["data"]["id"]
    evs = run_ws(t, wid, {"message": "I want my money back!"})
    assert evs[-1]["type"] == "run_finished", evs[-1]
    st = evs[-1]["state"]
    assert st["intent"] == "refund" and st["urgency"] == 1.43 and st["angry"] == 0.99 and st["answers"]["intent"]["confidence"] == 0.8
    assert len(jev) == 1 and jev[0].url == "https://api.typesafe.ai/v1/systemone" and json.loads(jev[0].content)["state"] == "I want my money back!"
    fin = next(e for e in evs if e["type"] == "node_finished" and e["node"] == "dec")
    assert fin["usage"]["provider"] == "typesafe" and fin["usage"]["model"] == "jev-1.13.0" and fin["usage"]["cost_usd"] == pytest.approx(400 * 0.042 / 1e6)
    assert KEY not in json.dumps(evs)


def test_bad_key_and_wrong_credential_kind(jev):
    t = user()
    bad = c.post("/api/credentials", json={"name": "ts", "provider": "typesafe", "api_key": "ts-wrong"}, headers=H(t)).json()["data"]["id"]
    wid = c.post("/api/workflows", json=flow(credential_id=bad), headers=H(t)).json()["data"]["id"]
    evs = run_ws(t, wid, {"message": "hi"})
    assert evs[-1]["type"] == "error" and evs[-1]["error"]["code"] == "PROVIDER_AUTH_FAILED" and "invalid api key" in evs[-1]["errors"][0]
    oai = c.post("/api/credentials", json={"name": "oai", "provider": "openai", "api_key": "sk-x"}, headers=H(t)).json()["data"]["id"]
    wid = c.post("/api/workflows", json=flow(credential_id=oai), headers=H(t)).json()["data"]["id"]
    evs = run_ws(t, wid, {"message": "hi"})
    assert evs[-1]["type"] == "error" and "need a TypeSafe credential" in evs[-1]["errors"][0]


def test_credential_check_and_provider_list(jev):
    t = user()
    r = c.post("/api/providers/typesafe/test", json={"api_key": KEY, "base_url": None, "headers": {}}, headers=H(t)).json()["data"]
    assert r["ok"] and r["models"] == ["jev-1.13.0", "jev-latest"]
    info = {p["id"]: p for p in c.get("/api/providers", headers=H(t)).json()["data"]}
    assert info["typesafe"]["kind"] == "decision" and info["typesafe"]["supports_embeddings"] is False and info["openai"]["kind"] == "chat"
    with pytest.raises(providers.ProviderError): providers.get("typesafe").invoke("hi", "jev-latest", {"api_key": KEY})


def test_answers_are_reused_from_the_ledger_on_recovery(jev, monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", KEY)
    class Ledger(dict):
        def get(self, nid, it): return super().get((nid, it))
        def put(self, nid, it, delta, key): self[(nid, it)] = delta
    led = Ledger(); wf = flow()
    list(run_stream(wf, {"message": "refund please"}, effects=Effects(run_id="r", ledger=led)))
    list(run_stream(wf, {"message": "refund please"}, effects=Effects(run_id="r", ledger=led)))  # the job runs again
    assert len(jev) == 1 and led[("dec", 1)]["intent"] == "refund"


# ---------- validation ----------
def has(errs, frag): return any(frag in e for e in errs), errs


def test_valid_flow():
    assert validate(flow()) == []


def q(i): return lambda w: w["nodes"][1]["data"]["questions"][i]
@pytest.mark.parametrize("mutate,frag", [
    (lambda w: w["nodes"][1]["data"].update(questions=[]), "add at least one question"),
    (lambda w: w["nodes"][1]["data"].update(text=" "), "the text to evaluate is empty"),
    (lambda w: q(0)(w).update(id="1st"), "the id must start with a letter"),
    (lambda w: q(1)(w).update(id="intent"), "duplicate question id 'intent'"),
    (lambda w: q(0)(w).update(type="rank"), "type must be one of choice, score, noul"),
    (lambda w: q(2)(w).update(instructions=""), "instructions are empty"),
    (lambda w: q(0)(w).update(options=[{"label": "only"}]), "needs 2-255 options"),
    (lambda w: q(0)(w)["options"].append({"label": "order"}), "option labels must be different"),
    (lambda w: q(1)(w).update(levels=["a"] * 11), "needs 2-10 levels"),
    (lambda w: q(1)(w).update(levels=["a", ""]), "every level needs a description"),
    (lambda w: q(0)(w).update(field="urgency"), "field 'urgency' must be of type string"),
    (lambda w: q(2)(w).update(field="ghost"), "field 'ghost' is not in the state"),
    (lambda w: w["nodes"][1]["data"].update(output_field="reply"), "output_field 'reply' must be of type object"),
    (lambda w: [w["nodes"][1]["data"].pop("output_field")] + [x.pop("field") for x in w["nodes"][1]["data"]["questions"]], "choose an output field"),
    (lambda w: q(0)(w).update(instructions="{{state.nope}}"), "variable state.nope is not in the state"),
])
def test_validation_errors(mutate, frag):
    w = flow(); mutate(w)
    ok, errs = has(validate(w), frag); assert ok, errs
