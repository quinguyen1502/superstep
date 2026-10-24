"""Public demo mode: one account per visitor (history and chats are private), expired visitors are removed, and the
offline answers follow the requester's language."""
import time
import pytest
from app.core import security
from app.engine import locale, nodes
from app.engine.llm import mock_llm
from app.engine.ports import Ports
from app.engine.tools import lookup_order
from app.models import ChatSession, Run
from app.models.database import Database
from app.repositories import ChatSessionRepository, RunRepository, UserRepository, WorkflowShareRepository
from app.services import demo_service, seed
from app.services.auth_service import AuthService


@pytest.fixture
def demo(monkeypatch): monkeypatch.setenv("STUDIO_DEMO_MODE", "true")


@pytest.fixture
def db(tmp_path, demo):
    d = Database(f"sqlite:///{tmp_path}/demo.db"); seed.bootstrap(d); return d


def _login(d: Database) -> dict:
    auth = AuthService(UserRepository(d), visit=lambda: demo_service.start_visit(d))
    return auth.login(demo_service.VISITOR_EMAIL, demo_service.VISITOR_PASSWORD)["user"]


def test_each_demo_sign_in_gets_its_own_viewer_with_the_samples(db):
    a, b = _login(db), _login(db)
    assert a["id"] != b["id"] and a["id"].startswith(demo_service.VISITOR_PREFIX) and a["role"] == "viewer"
    shares = WorkflowShareRepository(db)
    for wid in ("example", "demo-chatbot", "demo-router", "demo-approval"):
        assert shares.role_of(wid, a["id"]) == "viewer" and shares.role_of(wid, b["id"]) == "viewer", wid
    assert demo_service.refuses("PUT", "/api/workflows/example", a["id"])  # still read-only
    assert not demo_service.refuses("POST", "/api/workflows/demo-chatbot/chat/sessions", a["id"])


def test_a_visitor_account_has_no_password_to_sign_in_with(db):
    v = _login(db)
    with pytest.raises(Exception): AuthService(UserRepository(db)).login(v["email"], "")


def test_without_demo_mode_the_login_is_unchanged(tmp_path, monkeypatch):
    monkeypatch.delenv("STUDIO_DEMO_MODE", raising=False)
    d = Database(f"sqlite:///{tmp_path}/plain.db"); seed.bootstrap(d)
    UserRepository(d).add("u1", "a@b.c", security.hash_password("pw123456a"), time.time())
    calls = []
    auth = AuthService(UserRepository(d), visit=lambda: calls.append(1) or "x")
    assert auth.login("a@b.c", "pw123456a")["user"]["id"] == "u1" and calls == []


def test_history_and_chats_are_per_visitor(db):
    a, b = _login(db)["id"], _login(db)["id"]
    runs = RunRepository(db); now = time.time()
    with db.session() as s:
        for rid, uid in (("ra", a), ("rb", b)):
            s.add(Run(id=rid, workflow_id="demo-chatbot", owner=uid, status="ok", started=now, ended=now, input="{}", events="[]", source="ui"))
        s.commit()
    chats = ChatSessionRepository(db)
    for sid, uid in (("sa", a), ("sb", b)):
        chats.add(ChatSession(id=sid, workflow_id="demo-chatbot", trigger_id="t", owner=uid, created=now, updated=now))
    assert [c.id for c in chats.list_for("demo-chatbot", a)] == ["sa"]
    rows = [r for r in runs.list_for_workflow("demo-chatbot") if r.owner == a]
    assert [r.id for r in rows] == ["ra"]


def test_expired_visitors_are_removed_with_their_data(db, monkeypatch):
    monkeypatch.setenv("STUDIO_DEMO_VISITOR_TTL", "3600")
    old = demo_service.start_visit(db, now=time.time() - 7200)
    now = time.time()
    with db.session() as s:
        s.add(Run(id="rold", workflow_id="demo-chatbot", owner=old, status="ok", started=now, ended=now, input="{}", events="[]", source="ui")); s.commit()
    ChatSessionRepository(db).add(ChatSession(id="sold", workflow_id="demo-chatbot", trigger_id="t", owner=old, created=now, updated=now))
    fresh = demo_service.start_visit(db)  # each sign-in cleans up first
    assert demo_service.purge_expired(db) == 0
    users = UserRepository(db)
    assert users.get_by_id(old) is None and users.get_by_id(fresh) is not None
    assert users.get_by_id(demo_service.VISITOR_ID) is not None  # the template stays
    assert RunRepository(db).get("rold") is None and ChatSessionRepository(db).get("sold") is None
    assert WorkflowShareRepository(db).role_of("demo-chatbot", old) is None


def test_locale_pick():
    assert locale.pick(None, None) == "en" and locale.pick("vi", "en-US") == "vi" and locale.pick("fr", "vi-VN,vi;q=0.9") == "vi"
    assert locale.pick("", "de-DE") == "en" and locale.pick(42, "EN") == "en"


def test_mock_answers_follow_the_locale():
    assert mock_llm("Hello", "m") == "[mock:m] Answer: Hello"
    assert mock_llm("Hello", "m", "vi") == "[mock:m] Trả lời: Hello"
    assert mock_llm("Classify: where is my order A100", "m", "vi") == "order_status"  # labels are not translated
    assert lookup_order({"message": "Where is A100?"}) == "Order A100: Delivered on 2026-10-10"
    assert lookup_order({"message": "Đơn A100?"}, "vi").startswith("Đơn A100: Đã giao hàng")
    assert lookup_order({"message": "hi"}, "vi") == "Không tìm thấy mã đơn hàng trong tin nhắn."
    assert lookup_order({"message": "Z999"}) == "Order Z999: not in our system"


def test_nodes_pass_the_run_locale(demo):
    llm = nodes.node_fn({"id": "l", "type": "llm", "data": {"prompt": "hi", "output_field": "a", "model": "m"}}, ports=Ports(locale="vi"))
    assert llm({})["a"] == "[mock:m] Trả lời: hi"
    tool = nodes.node_fn({"id": "t", "type": "tool", "data": {"mode": "function", "function": "lookup_order", "output_field": "o"}}, ports=Ports(locale="vi"))
    assert tool({"message": "B200"})["o"].startswith("Đơn B200")
    assert nodes.node_fn({"id": "l", "type": "llm", "data": {"prompt": "hi", "output_field": "a", "model": "m"}})({})["a"] == "[mock:m] Answer: hi"
