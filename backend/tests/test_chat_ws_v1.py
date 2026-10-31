"""The chat socket protocol v1 (TASK-0216, REQ-0082, DEC-0078): typed frames on /ws/public/v1/chat/{slug}, every frame
validated against the published JSON Schema, and the unversioned socket unchanged."""
import json, pathlib
import pytest
from jsonschema import Draft202012Validator
from app.services import chat_ws_v1 as v1
from tests.test_chat_sessions import H, asking, user
from tests.test_public_chat_api import c, publish
from tests.test_public_chat_runs import say, start

SCHEMAS = pathlib.Path(__file__).resolve().parents[1] / "app/api/schemas/chat_ws_v1"
SERVER = Draft202012Validator(json.loads((SCHEMAS / "server.json").read_text()))
CLIENT = Draft202012Validator(json.loads((SCHEMAS / "client.json").read_text()))


@pytest.fixture(autouse=True)
def no_limits(monkeypatch):
    for k in ("READ", "VISITOR", "IP"): monkeypatch.setenv(f"STUDIO_PUBLIC_CHAT_RATE_{k}", "0")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


def talk(v, slug, *frames, query=""):
    """Sends the client frames (each checked against the client schema) and reads every server frame until the socket
    closes, checking each against the server schema and the seq order."""
    out = []
    with v.websocket_connect(f"/ws/public/v1/chat/{slug}{query}") as w:
        for f in frames:
            CLIENT.validate(f) if isinstance(f, dict) and f.get("type") in v1.CLIENT_TYPES and not f.get("_bad") else None
            w.send_json({k: x for k, x in f.items() if k != "_bad"} if isinstance(f, dict) else f)
        while True:
            try: e = w.receive_json()
            except Exception: break
            SERVER.validate(e); out.append(e)
            if e["type"] in ("done", "error"):
                try: out.append(w.receive_json())  # nothing more: the server closes
                except Exception: pass
                break
    assert [e["seq"] for e in out] == list(range(len(out))) and all(e["v"] == 1 for e in out)
    return out


def types(frames): return [f["type"] for f in frames]


def test_a_v1_conversation_with_a_question_validates_frame_by_frame():
    tok = user(); wid = c.post("/api/workflows", json={**asking(), "name": "Ask"}, headers=H(tok)).json()["data"]["id"]
    slug = f"ask1-{wid[:6]}"
    assert c.put(f"/api/workflows/{wid}/chat", json={"enabled": True, "access": "anonymous", "slug": slug}, headers=H(tok)).json()["success"]
    v, vt, sid = start(slug)
    fs = talk(v, slug, {"type": "auth", "visitor": vt}, {"type": "message", "chat_session_id": sid, "text": "the refund"})
    assert fs[0] == {"type": "ready", "protocol": "superstep-chat", "v": 1, "seq": 0}
    q = next(f for f in fs if f["type"] == "question")
    assert q["prompt"] == "Sure about the refund?" and "state" not in q
    assert types(fs)[-2:] == ["turn", "done"] and fs[-1]["status"] == "waiting"
    fs = talk(v, slug, {"type": "auth", "visitor": vt}, {"type": "answer", "chat_session_id": sid, "node": q["node"], "response": "yes"})
    assert "token" in types(fs) and "node_token" not in types(fs)
    turn, done = fs[-2], fs[-1]
    assert (turn["type"], turn["status"], done["type"], done["status"]) == ("turn", "ok", "done", "ok")
    d = v.get(f"/api/public/v1/chat/{slug}/sessions/{sid}", headers={"X-Chat-Visitor": vt}).json()["data"]["turns"]
    assert d[-1]["id"] == turn["turn_id"]  # the id to rate the answer with
    r = v.put(f"/api/public/v1/chat/{slug}/sessions/{sid}/turns/{turn['turn_id']}/rating", json={"value": "up"}, headers={"X-Chat-Visitor": vt})
    assert r.json()["success"]


def test_streaming_tokens_and_steps_are_typed():
    slug = publish(user())[1]
    v, vt, sid = start(slug)
    fs = talk(v, slug, {"type": "message", "chat_session_id": sid, "text": "hello"}, query=f"?visitor={vt}")
    assert types(fs)[:2] == ["ready", "run_started"] and types(fs)[-1] == "done" and fs[-1]["status"] == "ok"
    assert any(f["type"] == "token" and f["field"] == "reply" for f in fs)
    assert {f["event"] for f in fs if f["type"] == "step"} <= {"started", "finished", "error"}


@pytest.mark.parametrize("frame,reason", [({"type": "hello"}, "unknown type"), ({"chat_session_id": "x"}, "missing type"),
                                          ({"type": "message", "chat_session_id": "x", "text": "a", "extra": 1, "_bad": 1}, "unknown field"),
                                          ({"type": "message", "chat_session_id": "x", "_bad": 1}, "text"), ({"type": "cancel"}, "expected a message"),
                                          ([1, 2], "not an object")])
def test_a_frame_that_is_not_v1_is_an_error_frame_with_a_catalog_code(frame, reason):
    slug = publish(user())[1]
    v, vt, sid = start(slug)
    fs = talk(v, slug, frame, query=f"?visitor={vt}")
    assert types(fs) == ["ready", "error"] and fs[1]["error"]["code"] == "CHAT_FRAME_INVALID" and reason in fs[1]["error"]["message"]


def test_errors_of_the_chat_keep_their_codes_on_v1():
    slug = publish(user())[1]
    v, vt, sid = start(slug)
    fs = talk(v, slug, {"type": "message", "chat_session_id": "nope", "text": "x"}, query=f"?visitor={vt}")
    assert fs[-1]["type"] == "error" and fs[-1]["error"]["code"] == "CHAT_SESSION_NOT_FOUND"


def test_the_old_socket_keeps_untyped_frames_and_node_token():
    slug = publish(user())[1]
    v, vt, sid = start(slug)
    evs = say(v, slug, vt, {"chat_session_id": sid, "message": "hello"})
    assert "node_token" in types(evs) and evs[-1]["type"] == "run_summary"
    assert not any("seq" in e or "v" in e for e in evs) and "ready" not in types(evs)


def test_translation_drops_what_v1_does_not_carry():
    assert v1.server_frame({"type": "run_cancelled"}) is None
    assert v1.server_frame({"type": "something_new"}) is None
    assert v1.plan_request({"type": "message", "chat_session_id": "s", "text": "hi", "attachments": ["a"], "locale": "vi"}) == \
        {"chat_session_id": "s", "message": "hi", "attachment_ids": ["a"], "locale": "vi"}
    with pytest.raises(Exception): v1.client_frame({"type": "auth", "visitor": 5})


def test_the_asyncapi_document_is_served_committed_and_resolves():
    import yaml
    from app.api.asyncapi_public import asyncapi
    r = c.get("/asyncapi.public.yaml")
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/yaml")
    doc = yaml.safe_load(r.text)
    assert doc == asyncapi() and doc["asyncapi"] == "3.0.0" and doc["channels"]["chat"]["address"] == "/ws/public/v1/chat/{slug}"
    committed = pathlib.Path(__file__).resolve().parents[2] / "docs/asyncapi/chat-v1.yaml"
    assert yaml.safe_load(committed.read_text()) == doc, "run: python scripts/gen_public_openapi.py"

    def refs(n):
        if isinstance(n, dict):
            for k, x in n.items():
                if k == "$ref": yield x
                else: yield from refs(x)
        elif isinstance(n, list):
            for x in n: yield from refs(x)
    for ref in refs(doc):
        node = doc
        for part in ref.lstrip("#/").split("/"): node = node[part]
    sent = {m["$ref"].rsplit("/", 1)[1] for m in doc["operations"]["receiveFrame"]["messages"]}
    assert sent == {f"server_{t}" for t in ("ready", "run_started", "token", "step", "question", "turn", "done", "error")}
