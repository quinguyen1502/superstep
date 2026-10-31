"""Public Chat API v1 (TASK-0215, REQ-0082, DEC-0078): the versioned paths, the unversioned aliases, the public spec
and incremental history with `turns?after=`."""
import pytest
from app.api.openapi_public import public_openapi
from app.schemas.envelope import ErrorEnvelope
from app.schemas.public_chat import (ChatPageEnvelope, ChatSessionEnvelope, ChatSessionListEnvelope, ChatSessionViewEnvelope,
                                     ChatTurnsEnvelope, OkEnvelope, ChatRatingEnvelope)
from tests.test_chat_sessions import user
from tests.test_public_chat_api import publish
from tests.test_public_chat_runs import say, start, turns

V1, OLD = "/api/public/v1/chat", "/api/public/chat"
OPS = {("get", "/{slug}"): "getChatPage", ("get", "/{slug}/logo"): "getChatLogo", ("get", "/{slug}/sessions"): "listChatSessions",
       ("post", "/{slug}/sessions"): "createChatSession", ("get", "/{slug}/sessions/{sid}"): "getChatSession",
       ("get", "/{slug}/sessions/{sid}/turns"): "listChatTurns",
       ("post", "/{slug}/sessions/{sid}/attachments"): "uploadChatAttachment",
       ("get", "/{slug}/sessions/{sid}/attachments/{aid}"): "downloadChatAttachment",
       ("delete", "/{slug}/sessions/{sid}/attachments/{aid}"): "deleteChatAttachment",
       ("put", "/{slug}/sessions/{sid}/turns/{tid}/rating"): "rateChatTurn",
       ("delete", "/{slug}/sessions/{sid}/turns/{tid}/rating"): "unrateChatTurn"}


@pytest.fixture(autouse=True)
def no_limits(monkeypatch):
    for k in ("READ", "VISITOR", "IP"): monkeypatch.setenv(f"STUDIO_PUBLIC_CHAT_RATE_{k}", "0")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


def test_the_public_spec_lists_every_v1_chat_endpoint():
    spec = public_openapi()
    ops = {(m, p[len(V1):]): op for p, item in spec["paths"].items() if p.startswith(V1) for m, op in item.items()}
    assert {k: v["operationId"] for k, v in ops.items()} == OPS
    for op in ops.values():
        assert op["tags"] == ["Chat"]
        for status, r in op["responses"].items():
            schema = r["content"]["application/json"]["schema"]
            if status.startswith(("4", "5")): assert schema["$ref"].endswith("/ErrorEnvelope")
            elif op["operationId"] not in ("getChatLogo", "downloadChatAttachment"): assert schema["$ref"].endswith("Envelope")
    assert not [p for p in spec["paths"] if p.startswith(OLD + "/")], "the aliases are not part of the contract"
    assert "HTTPValidationError" not in spec["components"]["schemas"]


def test_v1_and_the_alias_answer_the_same():
    slug = publish(user())[1]
    v, vt, sid = start(slug)
    say(v, slug, vt, {"chat_session_id": sid, "message": "hello"})
    turns(v, slug, vt, sid, 2)
    h = {"X-Chat-Visitor": vt}
    for path, model in ((f"/{slug}", ChatPageEnvelope), (f"/{slug}/sessions", ChatSessionListEnvelope),
                        (f"/{slug}/sessions/{sid}", ChatSessionViewEnvelope), (f"/{slug}/sessions/{sid}/turns", ChatTurnsEnvelope)):
        a, b = v.get(V1 + path, headers=h), v.get(OLD + path, headers=h)
        assert a.status_code == b.status_code == 200 and a.json() == b.json(), path
        model.model_validate(a.json())
    r = v.post(f"{V1}/{slug}/sessions", headers=h); ChatSessionEnvelope.model_validate(r.json())
    r = v.get(f"{V1}/{slug}/sessions/nope", headers=h)
    assert r.status_code == 404 and ErrorEnvelope.model_validate(r.json()).error.code == "CHAT_SESSION_NOT_FOUND"
    assert v.get(f"{V1}/missing-{slug}").json()["error"]["code"] == "CHAT_NOT_PUBLISHED"


def test_a_new_visitor_on_v1_gets_a_token_and_a_cookie_for_both_paths():
    slug = publish(user())[1]
    v, vt, sid = start(slug)
    r = v.post(f"{V1}/{slug}/sessions")  # a direct visit: the cookie, scoped to both the alias and v1
    paths = {p.split("=", 1)[1] for h in r.headers.get_list("set-cookie") for p in h.split("; ") if p.startswith("Path=")}
    assert {f"{OLD}/{slug}", f"{V1}/{slug}", f"/ws/public/chat/{slug}", f"/ws/public/v1/chat/{slug}"} <= paths


def test_turns_after_returns_only_newer_turns_of_the_callers_chat():
    slug = publish(user())[1]
    v, vt, sid = start(slug)
    h = {"X-Chat-Visitor": vt}
    say(v, slug, vt, {"chat_session_id": sid, "message": "one"})
    first = turns(v, slug, vt, sid, 2)["turns"]
    say(v, slug, vt, {"chat_session_id": sid, "message": "two"})
    turns(v, slug, vt, sid, 4)
    every = v.get(f"{V1}/{slug}/sessions/{sid}/turns", headers=h).json()["data"]["turns"]
    assert [t["id"] for t in every[:2]] == [t["id"] for t in first] and len(every) == 4
    newer = v.get(f"{V1}/{slug}/sessions/{sid}/turns", params={"after": first[-1]["id"]}, headers=h).json()["data"]["turns"]
    assert [t["id"] for t in newer] == [t["id"] for t in every[2:]] and newer[0]["text"] == "two"
    assert v.get(f"{V1}/{slug}/sessions/{sid}/turns", params={"after": every[-1]["id"]}, headers=h).json()["data"]["turns"] == []
    r = v.get(f"{V1}/{slug}/sessions/{sid}/turns", params={"after": "nope"}, headers=h)
    assert (r.status_code, r.json()["error"]["code"]) == (404, "CHAT_TURN_NOT_FOUND")
    o, ot, osid = start(slug)  # another visitor reads neither the chat nor its turns
    r = o.get(f"{V1}/{slug}/sessions/{sid}/turns", headers={"X-Chat-Visitor": ot})
    assert r.json()["error"]["code"] == "CHAT_SESSION_NOT_FOUND"


def test_rating_on_v1_matches_the_documented_models():
    slug = publish(user())[1]
    v, vt, sid = start(slug)
    h = {"X-Chat-Visitor": vt}
    say(v, slug, vt, {"chat_session_id": sid, "message": "hi"})
    answer = turns(v, slug, vt, sid, 2)["turns"][-1]
    r = v.put(f"{V1}/{slug}/sessions/{sid}/turns/{answer['id']}/rating", json={"value": "up"}, headers=h)
    assert ChatRatingEnvelope.model_validate(r.json()).data.value == "up"
    r = v.delete(f"{V1}/{slug}/sessions/{sid}/turns/{answer['id']}/rating", headers=h)
    assert OkEnvelope.model_validate(r.json()).data.ok


def test_nginx_lets_v1_uploads_through_the_upload_location():
    import pathlib, re
    conf = pathlib.Path(__file__).resolve().parents[2] / "frontend/nginx.conf.template"
    if not conf.exists(): pytest.skip("no frontend in this checkout")
    rx = next(m for m in re.findall(r"location ~ (\^/api/[^ ]+) \{", conf.read_text()) if "attachments" in m)
    for path in ("/api/public/chat/help/sessions/s1/attachments", "/api/public/v1/chat/help/sessions/s1/attachments"):
        assert re.match(rx, path), path
