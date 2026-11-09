"""Envelope + error-code contract: every REST response, success or error."""
import pathlib, json, re
from fastapi.testclient import TestClient
from app.core.errors import CATALOG
from app.main import app

c = TestClient(app, raise_server_exceptions=False)
ROOT = pathlib.Path(__file__).resolve().parents[2]


def tok(): return c.post("/api/auth/login", json={"email": "admin@example.com", "password": "admin123"}).json()["data"]["token"]


def is_error(r, status, code):
    b = r.json()
    assert r.status_code == status and b["success"] is False and b["data"] is None and b["error"]["code"] == code, b
    return b["error"]


def test_success_envelope():
    b = c.get("/api/health").json()
    assert b == {"success": True, "data": b["data"], "error": None} and b["data"]["ok"] is True


def test_validation_404_405_auth_and_500():
    e = is_error(c.post("/api/auth/login", json={"email": 1}), 422, "VALIDATION_ERROR")
    assert {"field": "password", "message": "Field required"} in e["details"]
    is_error(c.get("/api/nope"), 404, "NOT_FOUND")
    is_error(c.put("/api/health"), 405, "METHOD_NOT_ALLOWED")
    is_error(c.get("/api/workflows"), 401, "AUTH_REQUIRED")
    is_error(c.get("/api/workflows", headers={"Authorization": "Bearer x"}), 401, "AUTH_TOKEN_INVALID")
    is_error(c.get("/api/workflows/missing", headers={"Authorization": f"Bearer {tok()}"}), 404, "WORKFLOW_NOT_FOUND")


def test_expired_token_keeps_header():
    from app.core.security import make_token
    r = c.get("/api/me", headers={"Authorization": f"Bearer {make_token('u', 'a@b.cd', ttl=-10)}"})
    is_error(r, 401, "AUTH_TOKEN_EXPIRED"); assert r.headers["X-Auth-Error"] == "expired"


def test_unhandled_500(monkeypatch):
    from app.services import workflow_service
    monkeypatch.setattr(workflow_service.WorkflowService, "list", lambda *a: 1 / 0)
    e = is_error(c.get("/api/workflows", headers={"Authorization": f"Bearer {tok()}"}), 500, "INTERNAL_ERROR")
    assert "division" not in e["message"]


def test_ws_errors_are_structured():
    with c.websocket_connect(f"/ws/run?token={tok()}") as ws:
        ws.send_json({"workflow_id": "missing"}); ev = ws.receive_json()
    assert ev["type"] == "error" and ev["error"]["code"] == "WORKFLOW_NOT_FOUND" and ev["errors"] == [ev["error"]["message"]]
    with c.websocket_connect(f"/ws/run?token={tok()}") as ws:
        ws.send_json({"workflow": {"nodes": [], "edges": []}, "input": {}})
        while (ev := ws.receive_json())["type"] != "error": pass
    assert ev["error"]["code"] == "WORKFLOW_INVALID" and ev["error"]["details"] == ev["errors"]


def test_catalog_is_documented_and_translated():
    """Single source of truth: every catalog code is in the docs and in both locale files."""
    doc = (ROOT / "docs/api-errors.md").read_text()
    locales = {l: json.loads((ROOT / f"frontend/src/locales/{l}.json").read_text())["errors"] for l in ("en", "vi")}
    for code, (status, _) in CATALOG.items():
        assert re.search(rf"\| `{code}` \| {status} \|", doc), code
        for l, msgs in locales.items(): assert code in msgs, (l, code)
    assert re.fullmatch(r"[A-Z_]+", "".join(CATALOG))


def test_locale_files_have_identical_keys():
    def flat(d, p=""):
        return {k2 for k, v in d.items() for k2 in (flat(v, f"{p}{k}.") if isinstance(v, dict) else {p + k})}
    en, vi = (json.loads((ROOT / f"frontend/src/locales/{l}.json").read_text()) for l in ("en", "vi"))
    assert flat(en) == flat(vi)
