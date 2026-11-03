"""Public workflow-trigger API: OpenAPI contract (security schemes, models, public-only spec) and that real responses
match the documented models."""
import importlib.util, pathlib, time, uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.api.openapi_public import public_openapi
from app.schemas.envelope import ErrorEnvelope
from app.schemas.public_api import RunAcceptedEnvelope, RunResultEnvelope

ROOT = pathlib.Path(__file__).resolve().parents[2]
PUBLIC_OPS = {("post", "/api/hooks/workflows/{wid}/runs"): "startRun", ("get", "/api/hooks/workflows/{wid}/runs/{run_id}"): "getRun"}


@pytest.fixture(scope="module")
def c():
    with TestClient(app) as client:
        yield client


def H(t): return {"Authorization": f"Bearer {t}"}


@pytest.fixture(scope="module")
def wft(c):
    jwt = c.post("/api/auth/register", json={"email": f"p{uuid.uuid4().hex[:6]}@example.com", "password": "secret12"}).json()["data"]["token"]
    wid = c.get("/api/workflows", headers=H(jwt)).json()["data"][0]["id"]
    return wid, c.post(f"/api/workflows/{wid}/tokens", json={"name": "spec"}, headers=H(jwt)).json()["data"]["token"]


def test_committed_public_spec_matches_the_app():
    spec = importlib.util.spec_from_file_location("gen", ROOT / "scripts/gen_public_openapi.py")
    gen = importlib.util.module_from_spec(spec); spec.loader.exec_module(gen)
    assert gen.main(check=True) == 0, "run: python scripts/gen_public_openapi.py"


def test_public_spec_has_only_the_public_routes(c):
    spec = c.get("/openapi.public.json").json()
    assert spec == public_openapi()
    ops = {(m, p): op for p, item in spec["paths"].items() for m, op in item.items() if op["tags"] != ["Chat"]}  # Chat: test_public_chat_v1
    assert {k: v["operationId"] for k, v in ops.items()} == PUBLIC_OPS
    schemes = spec["components"]["securitySchemes"]
    assert schemes["WorkflowToken"] == {**schemes["WorkflowToken"], "type": "apiKey", "in": "header", "name": "X-Workflow-Token"}
    assert schemes["WorkflowBearer"]["scheme"] == "bearer"
    for op in ops.values():
        assert op["tags"] == ["public"] and op["security"] == [{"WorkflowToken": []}, {"WorkflowBearer": []}]
        for status, r in op["responses"].items():
            schema = r["content"]["application/json"]["schema"]
            assert "$ref" in schema, f"untyped {status} response"  # no bare dicts
            if status.startswith(("4", "5")): assert schema["$ref"].endswith("/ErrorEnvelope") and r["content"]["application/json"]["examples"]
    assert "HTTPValidationError" not in spec["components"]["schemas"]


def test_full_spec_and_swagger_still_work(c):
    full = c.get("/openapi.json").json()
    assert full["paths"]["/api/hooks/workflows/{wid}/runs"]["post"]["operationId"] == "startRun"
    assert "/api/workflows" in full["paths"] and "WorkflowToken" in full["components"]["securitySchemes"]
    for url in ("/docs", "/docs/public"):
        r = c.get(url); assert r.status_code == 200 and "swagger-ui" in r.text
    assert "/openapi.public.json" in c.get("/docs/public").text


def test_responses_match_the_documented_models(c, wft):
    wid, tok = wft
    r = c.post(f"/api/hooks/workflows/{wid}/runs", json={"input": {"message": "where is my order A100"}}, headers={"X-Workflow-Token": tok})
    assert r.status_code == 202
    acc = RunAcceptedEnvelope.model_validate(r.json()).data
    assert r.headers["location"] == acc.poll_url and acc.poll_url.endswith(f"/api/hooks/workflows/{wid}/runs/{acc.run_id}")
    for _ in range(150):
        res = RunResultEnvelope.model_validate(c.get(acc.poll_url, headers=H(tok)).json()).data
        if res.status not in ("queued", "running"): break
        time.sleep(0.1)
    assert res.status == "ok" and res.final_state and res.metrics is not None
    r = c.post(f"/api/hooks/workflows/{wid}/runs", json={"input": {"message": "hi"}, "mode": "sync"}, headers=H(tok))
    assert r.status_code == 200 and RunResultEnvelope.model_validate(r.json()).data.status == "ok"
    for resp, code in ((c.get(f"/api/hooks/workflows/{wid}/runs/nope", headers=H(tok)), "RUN_NOT_FOUND"),
                       (c.post(f"/api/hooks/workflows/{wid}/runs", json={"mode": "later"}, headers=H(tok)), "VALIDATION_ERROR"),
                       (c.post(f"/api/hooks/workflows/{wid}/runs", json={}, headers={"X-Workflow-Token": "wft_bad", **H(tok)}), "TRIGGER_TOKEN_INVALID")):
        assert ErrorEnvelope.model_validate(resp.json()).error.code == code
