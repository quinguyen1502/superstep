"""TASK-0218 / DEC-0077: external identity, JWT rejection, cross-origin transport and session isolation."""
from __future__ import annotations
import base64, hashlib, hmac, json, time, uuid
import pytest
from app.api.deps import chat_session_service, run_service
from app.models import ChatTurn
from tests.test_chat_sessions import ECHO, H, c, user
from tests.test_public_chat_api import err, visitor
from tests.test_chat_ws_v1 import CLIENT, SERVER

BASE = "/api/public/v1/chat"


@pytest.fixture(autouse=True)
def no_limits(monkeypatch):
    for k in ("READ", "VISITOR", "IP", "USER"): monkeypatch.setenv(f"STUDIO_PUBLIC_CHAT_RATE_{k}", "0")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


def setup(origins=None):
    owner = user(); slug = "tokens-" + uuid.uuid4().hex[:10]
    wf = {**ECHO, "state": [*ECHO["state"], {"name": "chat", "type": "object"}, {"name": "files", "type": "list"}]}
    wid = c.post("/api/workflows", headers=H(owner), json=wf).json()["data"]["id"]
    assert c.put(f"/api/workflows/{wid}/chat", headers=H(owner), json={"enabled": True, "access": ["anonymous", "app"], "slug": slug,
        "attachments": {"enabled": True, "field": "files"}}).status_code == 200
    key = c.post(f"/api/workflows/{wid}/chat/app-keys", headers=H(owner), json={"label": "Server", "origins": origins or []}).json()["data"]
    return owner, wid, slug, key


def encoded(v): return base64.urlsafe_b64encode(json.dumps(v, separators=(",", ":")).encode()).decode().rstrip("=")


def mint(key, slug, sub="user-a", header=None, claims=None, secret=None):
    now = time.time()
    h = {"alg": "HS256", "typ": "JWT", "kid": key["key_id"], **(header or {})}
    p = {"iss": key["key_id"], "aud": f"superstep-chat:{slug}", "sub": sub, "iat": now, "exp": now + 600, **(claims or {})}
    unsigned = encoded(h) + "." + encoded(p)
    sig = hmac.new((secret or key["secret"]).encode(), unsigned.encode(), hashlib.sha256).digest()
    return unsigned + "." + base64.urlsafe_b64encode(sig).decode().rstrip("=")


def headers(token, origin=None): return {**H(token), **({"Origin": origin} if origin else {})}


def create(v, slug, token, origin=None):
    response = v.post(f"{BASE}/{slug}/sessions", headers=headers(token, origin))
    assert response.status_code == 200, response.json()
    return response.json()["data"]["id"]


def talk(v, slug, token, frame, origin="https://shop.example", query=False):
    out = []
    with v.websocket_connect(f"/ws/public/v1/chat/{slug}" + (f"?token={token}" if query else ""), headers={"Origin": origin}) as ws:
        assert ws.receive_json()["type"] == "ready"
        if not query:
            auth = {"type": "auth", "token": token}; CLIENT.validate(auth); ws.send_json(auth)
        CLIENT.validate(frame); ws.send_json(frame)
        while True:
            event = ws.receive_json(); SERVER.validate(event); out.append(event)
            if event["type"] in ("done", "error"): return out


def test_external_user_chats_with_identity_and_isolated_history():
    owner, wid, slug, key = setup(["https://shop.example"]); v = visitor()
    token = mint(key, slug, claims={"name": "Lan", "meta": {"customer": "42", "role": "untrusted"}})
    sid = create(v, slug, token, "https://shop.example")
    frames = talk(v, slug, token, {"type": "message", "chat_session_id": sid, "text": "hello"})
    assert frames[-1]["type"] == "done" and frames[-1]["status"] == "ok"
    view = v.get(f"{BASE}/{slug}/sessions/{sid}", headers=headers(token, "https://shop.example")).json()["data"]
    rid = view["turns"][-1]["run_id"]
    inp = json.loads(run_service().runs.get(rid).input)
    assert inp["chat"] == {"user": {"id": "user-a", "name": "Lan", "kind": "app"}, "meta": {"customer": "42", "role": "untrusted"}}
    row = chat_session_service().sessions.get(sid)
    assert row.external_user == "user-a" and row.app_key_id and row.owner is None and row.visitor is None
    keys = c.get(f"/api/workflows/{wid}/chat/app-keys", headers=H(owner)).json()["data"]
    assert keys[0]["last_used_at"] is not None
    other_device = visitor()
    assert other_device.get(f"{BASE}/{slug}/sessions", headers=headers(token, "https://shop.example")).json()["data"]["sessions"][0]["id"] == sid


def test_user_a_cannot_read_rate_or_attach_to_user_b_or_anonymous():
    _, _, slug, key = setup(); v = visitor(); a, b = mint(key, slug), mint(key, slug, "user-b")
    sa, sb = create(v, slug, a), create(v, slug, b)
    anon = v.post(f"{BASE}/{slug}/sessions", headers={"X-Chat-Visitor": "new"}).json()["data"]
    svc = chat_session_service()
    for sid in (sb, anon["id"]):
        turn = "answer-" + uuid.uuid4().hex
        svc.sessions.add_turn(ChatTurn(id=turn, session_id=sid, role="assistant", text="private", status="ok", created=time.time()))
        file = v.post(f"{BASE}/{slug}/sessions/{sid}/attachments", headers=H(b) if sid == sb else {"X-Chat-Visitor": anon["visitor_token"]},
                      files={"file": ("private.txt", b"private", "text/plain")}).json()["data"]["id"]
        root = f"{BASE}/{slug}/sessions/{sid}"
        operations = [("get", root, {}), ("get", root + "/turns", {}),
                      ("put", root + f"/turns/{turn}/rating", {"json": {"value": "up"}}),
                      ("delete", root + f"/turns/{turn}/rating", {}),
                      ("post", root + "/attachments", {"files": {"file": ("a.txt", b"a", "text/plain")}}),
                      ("get", root + f"/attachments/{file}", {}), ("delete", root + f"/attachments/{file}", {})]
        for method, path, kwargs in operations:
            response = getattr(v, method)(path, headers=H(a), **kwargs)
            assert response.status_code == 404 and err(response) == "CHAT_SESSION_NOT_FOUND", path
        assert talk(v, slug, a, {"type": "message", "chat_session_id": sid, "text": "steal"})[-1]["error"]["code"] == "CHAT_SESSION_NOT_FOUND"
    listed = v.get(f"{BASE}/{slug}/sessions", headers=H(a)).json()["data"]
    assert [s["id"] for s in listed["sessions"]] == [sa] and "visitor_token" not in listed
    # An existing anonymous cookie must not win over a valid app token, and cannot read an app session.
    assert err(v.get(f"{BASE}/{slug}/sessions/{sa}", headers={"X-Chat-Visitor": anon["visitor_token"]})) == "CHAT_SESSION_NOT_FOUND"


@pytest.mark.parametrize("change,code", [
    ({"header": {"alg": "none"}}, "CHAT_TOKEN_INVALID"), ({"header": {"alg": "HS512"}}, "CHAT_TOKEN_INVALID"),
    ({"header": {"kid": "ck_unknown"}}, "CHAT_TOKEN_INVALID"), ({"claims": {"aud": "wrong"}}, "CHAT_TOKEN_INVALID"),
    ({"claims": {"iss": "wrong"}}, "CHAT_TOKEN_INVALID"), ({"secret": "wrong-secret"}, "CHAT_TOKEN_INVALID"),
    ({"claims": {"iat": 1, "exp": 2}}, "CHAT_TOKEN_EXPIRED"),
    ({"claims": {"iat": time.time() + 600, "exp": time.time() + 1200}}, "CHAT_TOKEN_INVALID"),
    ({"claims": {"exp": time.time() + 4000}}, "CHAT_TOKEN_INVALID"),
    ({"claims": {"iat": True}}, "CHAT_TOKEN_INVALID"), ({"claims": {"sub": ""}}, "CHAT_TOKEN_INVALID"),
    ({"claims": {"meta": {"x": "a" * 1024}}}, "CHAT_TOKEN_INVALID"),
    ({"claims": {"meta": []}}, "CHAT_TOKEN_INVALID"), ({"claims": {"name": "a" * 81}}, "CHAT_TOKEN_INVALID"),
    ({"claims": {"nbf": time.time() + 600}}, "CHAT_TOKEN_INVALID"),
])
def test_rejects_invalid_tokens_without_visitor_fallback(change, code):
    _, _, slug, key = setup(); v = visitor()
    v.post(f"{BASE}/{slug}/sessions")  # even with a valid anonymous cookie
    token = mint(key, slug, **change)
    response = v.get(f"{BASE}/{slug}/sessions", headers=H(token))
    assert response.status_code == 401 and err(response) == code
    frames = talk(v, slug, token, {"type": "message", "chat_session_id": "no-session", "text": "a"})
    assert frames[-1]["error"]["code"] == code


def test_rotation_revoke_and_chat_access_changes():
    owner, wid, slug, key = setup(); v = visitor(); a = mint(key, slug)
    sid = create(v, slug, a)
    second = c.post(f"/api/workflows/{wid}/chat/app-keys", headers=H(owner), json={"label": "Rotation"}).json()["data"]
    b = mint(second, slug)
    assert v.get(f"{BASE}/{slug}/sessions/{sid}", headers=H(b)).status_code == 200  # same user across keys
    c.delete(f"/api/workflows/{wid}/chat/app-keys/{key['key_id']}", headers=H(owner))
    assert err(v.get(f"{BASE}/{slug}/sessions/{sid}", headers=H(a))) == "CHAT_APP_KEY_REVOKED"  # no cache
    assert v.get(f"{BASE}/{slug}/sessions/{sid}", headers=H(b)).status_code == 200
    _, _, other_slug, _ = setup()
    assert err(v.get(f"{BASE}/{other_slug}/sessions", headers=H(b))) == "CHAT_TOKEN_INVALID"
    c.put(f"/api/workflows/{wid}/chat", headers=H(owner), json={"access": "anonymous"})
    assert err(v.get(f"{BASE}/{slug}/sessions", headers=H(b))) == "CHAT_NOT_PUBLISHED"


def test_user_answers_human_and_socket_does_not_reauthenticate(monkeypatch):
    from tests.test_chat_sessions import asking
    from app.services.chat_token_verifier import Hs256ChatTokenVerifier
    owner, wid, slug, key = setup(); v = visitor()
    wf = {**asking(), "id": wid}
    assert c.post("/api/workflows", headers=H(owner), json=wf).status_code == 200
    token = mint(key, slug); sid = create(v, slug, token)
    frames = talk(v, slug, token, {"type": "message", "chat_session_id": sid, "text": "refund"})
    assert frames[-1]["status"] == "waiting"
    question = next(f for f in frames if f["type"] == "question")
    calls = []
    original = Hs256ChatTokenVerifier.verify
    def once(self, *args):
        if calls: raise AssertionError("A running socket must not reauthenticate after token expiry")
        result = original(self, *args); calls.append(True); return result
    monkeypatch.setattr(Hs256ChatTokenVerifier, "verify", once)
    frames = talk(v, slug, token, {"type": "answer", "chat_session_id": sid, "node": question["node"], "response": "yes"})
    assert frames[-1]["type"] == "done" and frames[-1]["status"] == "ok" and len(calls) == 1


def test_studio_and_app_modes_do_not_mix_identities():
    owner, wid, slug, key = setup(); v = visitor(); token = mint(key, slug)
    c.put(f"/api/workflows/{wid}/chat", headers=H(owner), json={"access": ["signed_in", "app", "anonymous"]})
    app_session, studio_session = create(v, slug, token), create(v, slug, owner)
    assert chat_session_service().sessions.get(studio_session).owner is not None
    assert err(v.get(f"{BASE}/{slug}/sessions/{app_session}", headers=H(owner))) == "CHAT_SESSION_NOT_FOUND"
    assert err(v.get(f"{BASE}/{slug}/sessions/{studio_session}", headers=H(token))) == "CHAT_SESSION_NOT_FOUND"


def test_expiry_leeway_and_malformed_claims():
    _, _, slug, key = setup(); v = visitor()
    # 60 s leeway applies to exp, but the signed lifetime itself cannot exceed one hour.
    now = time.time()
    valid = mint(key, slug, claims={"iat": now - 100, "exp": now - 30})
    assert v.get(f"{BASE}/{slug}/sessions", headers=H(valid)).status_code == 200
    for token in ("bad", "a.b.c", "x" * 8193, mint(key, slug, claims={"iat": float("nan")}),
                  mint(key, slug, claims={"meta": {"x": float("nan")}}), mint(key, slug, header={"kid": "\ud800"}),
                  mint(key, slug, claims={"sub": "\ud800"}), mint(key, slug, claims={"name": "\ud800"})):
        assert err(v.get(f"{BASE}/{slug}/sessions", headers=H(token))) == "CHAT_TOKEN_INVALID"


def test_cross_origin_socket_without_app_auth_is_rejected():
    _, _, slug, _ = setup(); v = visitor()
    anon = v.post(f"{BASE}/{slug}/sessions", headers={"X-Chat-Visitor": "new"}).json()["data"]
    with v.websocket_connect(f"/ws/public/v1/chat/{slug}?visitor={anon['visitor_token']}", headers={"Origin": "https://shop.example"}) as ws:
        assert ws.receive_json()["type"] == "ready"
        ws.send_json({"type": "message", "chat_session_id": anon["id"], "text": "no app token"})
        assert ws.receive_json()["error"]["code"] == "CHAT_TOKEN_REQUIRED"


def test_legacy_socket_cannot_bypass_app_auth_through_global_cors(monkeypatch):
    monkeypatch.setenv("STUDIO_CORS_ORIGINS", "https://evil.example")
    _, _, slug, _ = setup(); v = visitor()
    anon = v.post(f"{BASE}/{slug}/sessions", headers={"X-Chat-Visitor": "new"}).json()["data"]
    with pytest.raises(Exception):
        with v.websocket_connect(f"/ws/public/chat/{slug}?visitor={anon['visitor_token']}", headers={"Origin": "https://evil.example"}) as ws:
            ws.receive_json()


def test_cors_is_app_only_and_origin_scoped_even_with_global_cors(monkeypatch):
    monkeypatch.setenv("STUDIO_CORS_ORIGINS", "https://evil.example")
    owner, _, slug, key = setup(["https://shop.example"]); v = visitor(); token = mint(key, slug)
    path = f"{BASE}/{slug}/sessions"
    preflight = v.options(path, headers={"Origin": "https://shop.example", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "authorization,content-type"})
    assert preflight.status_code == 204 and preflight.headers["access-control-allow-origin"] == "https://shop.example"
    good = v.post(path, headers=headers(token, "https://shop.example"))
    assert good.status_code == 200 and good.headers["access-control-allow-origin"] == "https://shop.example"
    assert "access-control-allow-credentials" not in good.headers and "set-cookie" not in good.headers
    for origin in ("https://evil.example", "https://shop.example:444", "null"):
        bad = v.get(path, headers=headers(token, origin))
        assert err(bad) == "CHAT_ORIGIN_FORBIDDEN" and "access-control-allow-origin" not in bad.headers
    assert err(v.get(path, headers=H(token))) == "CHAT_ORIGIN_FORBIDDEN"  # restricted key requires Origin
    for h in ({"Origin": "https://evil.example"}, headers(owner, "https://evil.example")):
        denied = v.get(path, headers=h)
        assert denied.status_code in (401, 404) and "access-control-allow-origin" not in denied.headers
    expired = mint(key, slug, claims={"iat": 1, "exp": 2})
    response = v.get(path, headers=headers(expired, "https://shop.example"))
    assert err(response) == "CHAT_TOKEN_EXPIRED" and response.headers["access-control-allow-origin"] == "https://shop.example"


def test_native_query_token_and_per_user_limits(monkeypatch):
    _, _, slug, key = setup(); v = visitor(); a, b = mint(key, slug), mint(key, slug, "user-b")
    sa, sb = create(v, slug, a), create(v, slug, b)
    monkeypatch.setenv("STUDIO_PUBLIC_CHAT_RATE_USER", "1")
    assert talk(v, slug, a, {"type": "message", "chat_session_id": sa, "text": "one"}, query=True, origin="")[-1]["status"] == "ok"
    assert talk(v, slug, a, {"type": "message", "chat_session_id": sa, "text": "two"})[-1]["error"]["code"] == "RATE_LIMITED"
    assert talk(v, slug, b, {"type": "message", "chat_session_id": sb, "text": "other"})[-1]["status"] == "ok"


def test_failed_verifications_hit_the_message_ip_limit(monkeypatch):
    """Failed JWT checks share the per-IP message budget (DEC-0077).

    Drive the public HTTP path with a unique X-Forwarded-For so we never share
    counters with other tests and never nest asyncio.run inside pytest-asyncio.
    """
    from app.services.rate_limit import InMemoryRateLimiter
    import app.api.deps as deps
    _, _, slug, _ = setup()
    monkeypatch.setenv("STUDIO_PUBLIC_CHAT_RATE_IP", "2")
    monkeypatch.setenv("STUDIO_TRUST_PROXY", "1")
    # One shared in-memory limiter for every PublicChatService built this test.
    limiter = InMemoryRateLimiter()
    monkeypatch.setattr(deps, "get_rate_limiter", lambda: limiter)
    ip = f"203.0.113.{(uuid.uuid4().int % 200) + 20}"
    v = visitor()
    codes = []
    for _ in range(3):
        response = v.get(f"{BASE}/{slug}/sessions", headers={**H("bad.jwt.token"), "X-Forwarded-For": ip})
        codes.append(err(response))
    assert codes == ["CHAT_TOKEN_INVALID", "CHAT_TOKEN_INVALID", "RATE_LIMITED"], codes


def test_same_origin_browser_get_uses_only_a_verified_own_referrer(monkeypatch):
    monkeypatch.setenv("STUDIO_PUBLIC_URL", "https://studio.example")
    _, _, slug, key = setup(["https://studio.example"])
    token = mint(key, slug)
    v = visitor()
    path = f"{BASE}/{slug}/sessions"
    own = {**H(token), "Sec-Fetch-Site": "same-origin", "Referer": "https://studio.example/c/support?embed=1"}
    assert v.get(path, headers=own).status_code == 200
    for extra in ({"Referer": "https://shop.example/c/support"},
                  {"Sec-Fetch-Site": "cross-site"},
                  {"Sec-Fetch-Site": "none"},
                  {"Origin": "https://shop.example"},
                  {"Referer": "https://studio.example@evil.example/"}):
        response = v.get(path, headers={**own, **extra})
        assert response.status_code == 403 and err(response) == "CHAT_ORIGIN_FORBIDDEN"
    # Native callers with restricted keys must still explicitly supply an allowed Origin.
    assert err(v.get(path, headers=H(token))) == "CHAT_ORIGIN_FORBIDDEN"
