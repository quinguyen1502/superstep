"""The published chat page's API (TASK-0140, REQ-0074, DEC-0067): publish settings, the page by slug, visitor identity
and isolation, signed_in, frame-ancestors and the per-IP limit."""
import uuid
import pytest
from fastapi.testclient import TestClient
from app.core import config
from app.main import app
from app.services.chat_session_service import origin_of
from app.api.routes.public_chat import cookie_name
from tests.test_chat_sessions import ECHO, H, user

c = TestClient(app)


@pytest.fixture(autouse=True)
def no_read_limit(monkeypatch): monkeypatch.setenv("STUDIO_PUBLIC_CHAT_RATE_READ", "0")


def visitor(): return TestClient(app, base_url="https://testserver")  # its own cookie jar, no studio session; https keeps a Secure cookie


def publish(tok, **settings):
    wid = c.post("/api/workflows", json=ECHO, headers=H(tok)).json()["data"]["id"]
    slug = f"help-{uuid.uuid4().hex[:6]}"
    r = c.put(f"/api/workflows/{wid}/chat", json={"enabled": True, "access": "anonymous", "slug": slug, **settings}, headers=H(tok)).json()
    assert r["success"], r
    return wid, slug


def err(r): return r.json()["error"]["code"]


def test_publish_settings_are_checked():
    tok = user(); wid, slug = publish(tok, title="Help desk", intro="Ask **anything**", suggestions=[" Where is my order? "],
                                      embed_origins=["https://Shop.example.com/", "http://localhost:5173"])
    d = c.get(f"/api/workflows/{wid}/chat", headers=H(tok)).json()["data"]
    assert (d["slug"], d["title"], d["suggestions"], d["embed_origins"]) == (slug, "Help desk", ["Where is my order?"], ["https://shop.example.com", "http://localhost:5173"])
    put = lambda body: c.put(f"/api/workflows/{wid}/chat", json=body, headers=H(tok))  # noqa: E731
    for slug_bad in ("ab", "Has-Caps", "-dash", "api", "a" * 65, "with space"):
        assert err(put({"slug": slug_bad})) == "CHAT_SLUG_INVALID", slug_bad
    _, other = publish(tok)
    r = put({"slug": other}); assert (err(r), r.status_code) == ("CHAT_SLUG_TAKEN", 409)
    for body, field in [({"title": "x" * 61}, "title"), ({"suggestions": ["a"] * 5}, "suggestions"), ({"suggestions": [""]}, "suggestions"),
                        ({"daily_limit": -1}, "daily_limit"), ({"intro": "x" * 1001}, "intro")]:
        e = put(body).json()["error"]; assert (e["code"], e["details"]["field"]) == ("CHAT_SETTINGS_INVALID", field), body
    for o in ("http://shop.example.com", "https://a.example/path", "ftp://a.example", "https://u:p@a.example", "nope"):
        assert err(put({"embed_origins": [o]})) == "CHAT_EMBED_ORIGIN_INVALID", o
    assert origin_of("https://a.example:8443") == "https://a.example:8443"


def test_a_chat_that_is_not_published_says_nothing():
    tok = user(); wid, slug = publish(tok)
    v = visitor()
    page = v.get(f"/api/public/chat/{slug}").json()["data"]
    assert page == {"slug": slug, "title": "Echo chat", "intro": "", "suggestions": [], "access": "anonymous", "steps_mode": "labels", "signed_in": False}
    c.put(f"/api/workflows/{wid}/chat", json={"access": "studio"}, headers=H(tok))
    r = v.get(f"/api/public/chat/{slug}"); assert (err(r), r.status_code) == ("CHAT_NOT_PUBLISHED", 404)
    assert wid not in r.text and "Echo" not in r.text
    c.put(f"/api/workflows/{wid}/chat", json={"access": "anonymous", "enabled": False}, headers=H(tok))
    assert err(v.post(f"/api/public/chat/{slug}/sessions")) == "CHAT_NOT_PUBLISHED"
    assert err(v.get("/api/public/chat/no-such-chat")) == "CHAT_NOT_PUBLISHED"


def test_each_anonymous_visitor_sees_only_their_own_chats():
    tok = user(); wid, slug = publish(tok)
    a, b = visitor(), visitor()
    r = a.post(f"/api/public/chat/{slug}/sessions")
    s = r.json()["data"]; assert s["channel"] == "web"
    cookie = r.headers["set-cookie"].lower()
    flags = "samesite=none; secure" if config.cookie_secure() else "samesite=lax"  # over HTTPS it also works in an iframe
    assert cookie_name(slug) in cookie and "httponly" in cookie and f"path=/api/public/chat/{slug}" in cookie and flags in cookie
    assert ("partitioned" in cookie) == config.cookie_secure()
    assert [x["id"] for x in a.get(f"/api/public/chat/{slug}/sessions").json()["data"]["sessions"]] == [s["id"]]
    assert a.get(f"/api/public/chat/{slug}/sessions/{s['id']}").json()["data"]["turns"] == []
    assert b.get(f"/api/public/chat/{slug}/sessions").json()["data"]["sessions"] == []
    assert err(b.get(f"/api/public/chat/{slug}/sessions/{s['id']}")) == "CHAT_SESSION_NOT_FOUND"
    forged = visitor(); forged.cookies.set(cookie_name(slug), path=f"/api/public/chat/{slug}", value=a.cookies.get(cookie_name(slug), path=f"/api/public/chat/{slug}").split(".")[0] + "." + "0" * 32)
    assert forged.get(f"/api/public/chat/{slug}/sessions").json()["data"]["sessions"] == []
    # the builder's studio chats are not reachable from the page
    studio = c.post(f"/api/workflows/{wid}/chat/sessions", headers=H(tok)).json()["data"]["id"]
    assert err(a.get(f"/api/public/chat/{slug}/sessions/{studio}")) == "CHAT_SESSION_NOT_FOUND"


def test_the_widget_carries_its_token_in_a_header():
    tok = user(); _, slug = publish(tok)
    w = visitor()
    r = w.post(f"/api/public/chat/{slug}/sessions", json={"embed": True}, headers={"X-Chat-Visitor": "new"})
    d = r.json()["data"]; assert d["channel"] == "embed" and d["visitor_token"] and "set-cookie" not in r.headers
    got = w.get(f"/api/public/chat/{slug}/sessions", headers={"X-Chat-Visitor": d["visitor_token"]}).json()["data"]
    assert [x["id"] for x in got["sessions"]] == [d["id"]] and "visitor_token" not in got
    _, slug2 = publish(tok)  # a token is bound to its chat
    assert "visitor_token" in w.get(f"/api/public/chat/{slug2}/sessions", headers={"X-Chat-Visitor": d["visitor_token"]}).json()["data"]


def test_signed_in_chats_need_an_account_but_not_the_run_right():
    tok = user(); _, slug = publish(tok, access="signed_in")
    r = visitor().get(f"/api/public/chat/{slug}/sessions"); assert (err(r), r.status_code) == ("CHAT_SIGN_IN_REQUIRED", 401)
    assert visitor().get(f"/api/public/chat/{slug}").json()["data"]["signed_in"] is False
    guest, other = user(), user()
    s = c.post(f"/api/public/chat/{slug}/sessions", headers=H(guest)).json()["data"]
    me = c.get("/api/me", headers=H(guest)).json()["data"]["id"]
    from app.api.deps import chat_session_service
    assert chat_session_service().sessions.get(s["id"]).owner == me
    assert [x["id"] for x in c.get(f"/api/public/chat/{slug}/sessions", headers=H(guest)).json()["data"]["sessions"]] == [s["id"]]
    assert c.get(f"/api/public/chat/{slug}/sessions", headers=H(other)).json()["data"]["sessions"] == []
    assert err(c.get(f"/api/public/chat/{slug}/sessions/{s['id']}", headers=H(other))) == "CHAT_SESSION_NOT_FOUND"


def test_frame_ancestors_follow_the_allowed_sites():
    tok = user(); wid, slug = publish(tok, embed_origins=["https://shop.example.com"])
    r = visitor().get(f"/api/public/chat/{slug}/frame")
    assert r.headers["content-security-policy"] == "frame-ancestors 'self' https://shop.example.com"
    c.put(f"/api/workflows/{wid}/chat", json={"embed_origins": []}, headers=H(tok))
    assert visitor().get(f"/api/public/chat/{slug}/frame").headers["content-security-policy"] == "frame-ancestors 'none'"
    assert visitor().get("/api/public/chat/nope-nope/frame").headers["content-security-policy"] == "frame-ancestors 'none'"


def test_page_loads_are_limited_per_ip(monkeypatch):
    tok = user(); _, slug = publish(tok)
    monkeypatch.setenv("STUDIO_PUBLIC_CHAT_RATE_READ", "3"); monkeypatch.setenv("STUDIO_PUBLIC_CHAT_RATE_WINDOW", "3600")
    v = visitor(); codes = [v.get(f"/api/public/chat/{slug}").status_code for _ in range(5)]
    assert codes[:3] == [200, 200, 200] and codes[3] == 429


def test_demo_mode_publishes_nothing(monkeypatch):
    tok = user(); _, slug = publish(tok)
    monkeypatch.setenv("STUDIO_DEMO_MODE", "1")
    assert err(visitor().get(f"/api/public/chat/{slug}")) == "CHAT_NOT_PUBLISHED"
