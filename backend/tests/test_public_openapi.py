"""Public API: OpenAPI contract (security schemes, models, public-only spec) and that real responses
match the documented models."""
import importlib.util, pathlib, time, uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.api.openapi_public import public_openapi
from app.schemas.dataset import DatasetConnectedInput, DatasetGroupedRowQuery
from app.schemas.envelope import ErrorEnvelope
from app.schemas.public_api import RunAcceptedEnvelope, RunResultEnvelope, ScheduleEnvelope, ScheduleListEnvelope, SchedulePreviewEnvelope

ROOT = pathlib.Path(__file__).resolve().parents[2]
DATASET_PATH = "/api/datasets/{dataset_id}/connected"
DATASET_OPS = {"find_rows", "aggregate_rows", "get_row", "insert_row", "upsert_row", "delete_row"}
PUBLIC_OPS = {
    ("post", "/api/hooks/workflows/{wid}/runs"): "startRun",
    ("get", "/api/hooks/workflows/{wid}/runs/{run_id}"): "getRun",
    ("get", "/api/hooks/workflows/{wid}/schedules"): "listSchedules",
    ("post", "/api/hooks/workflows/{wid}/schedules"): "createSchedule",
    ("post", "/api/hooks/workflows/{wid}/schedules/preview"): "previewSchedule",
    ("patch", "/api/hooks/workflows/{wid}/schedules/{sid}"): "updateSchedule",
    ("delete", "/api/hooks/workflows/{wid}/schedules/{sid}"): "deleteSchedule",
}


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
    ops = {
        (method, path): op
        for path, item in spec["paths"].items() if not path.startswith("/api/public/v1/chat/")
        for method, op in item.items()
    }
    assert {key: op["operationId"] for key, op in ops.items()} == {
        **PUBLIC_OPS, ("post", DATASET_PATH): "executeDatasetOperation",
    }
    schemes = spec["components"]["securitySchemes"]
    assert schemes["WorkflowToken"] == {**schemes["WorkflowToken"], "type": "apiKey", "in": "header", "name": "X-Workflow-Token"}
    assert schemes["WorkflowBearer"]["scheme"] == "bearer"
    for key in PUBLIC_OPS:
        op = ops[key]
        assert op["tags"] == ["public"] and op["security"] == [{"WorkflowToken": []}, {"WorkflowBearer": []}]
        for status, r in op["responses"].items():
            schema = r["content"]["application/json"]["schema"]
            assert "$ref" in schema, f"untyped {status} response"  # no bare dicts
            if status.startswith(("4", "5")): assert schema["$ref"].endswith("/ErrorEnvelope") and r["content"]["application/json"]["examples"]
    assert "HTTPValidationError" not in spec["components"]["schemas"]


def test_dataset_public_openapi_contract():
    spec = public_openapi()
    assert set(spec["paths"][DATASET_PATH]) == {"post"}
    op = spec["paths"][DATASET_PATH]["post"]
    assert op["operationId"] == "executeDatasetOperation"
    assert op["tags"] == ["Datasets"] and op["security"] == [{"DatasetBearer": []}]
    scheme = spec["components"]["securitySchemes"]["DatasetBearer"]
    assert scheme["type"] == "http" and scheme["scheme"] == "bearer" and scheme["bearerFormat"] == "dsat_…"
    assert [(p["name"], p["in"]) for p in op["parameters"]] == [("dataset_id", "path")]
    request = op["requestBody"]["content"]["application/json"]
    schema = spec["components"]["schemas"][request["schema"]["$ref"].rsplit("/", 1)[-1]]
    assert schema["discriminator"]["propertyName"] == "operation"
    assert set(schema["discriminator"]["mapping"]) == DATASET_OPS == set(request["examples"])
    assert len(schema["oneOf"]) == len(DATASET_OPS)
    models = spec["components"]["schemas"]
    find = models["DatasetFindArguments"]["properties"]
    runtime_query = DatasetGroupedRowQuery.model_json_schema()["properties"]
    assert {key: find[key] for key in ("limit", "offset")} == {key: runtime_query[key] for key in ("limit", "offset")}
    operation_id = DatasetConnectedInput.model_json_schema()["properties"]["operation_id"]["anyOf"][0]
    assert models["DatasetConnectedInsert"]["properties"]["operation_id"]["pattern"] == operation_id["pattern"]
    assert op["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("/DatasetConnectedEnvelope")
    for status, codes in {
        "400": {"DATASET_NODE_ARGUMENTS_INVALID"}, "401": {"AUTH_REQUIRED", "AUTH_TOKEN_INVALID"},
        "403": {"DATASET_TOKEN_SCOPE", "DATASET_GRANT_DENIED"},
        "409": {"DATASET_BINDING_SCHEMA_MISMATCH", "DATASET_RECEIPT_CONFLICT"}, "422": {"VALIDATION_ERROR"},
    }.items():
        reply = op["responses"][status]["content"]["application/json"]
        assert reply["schema"]["$ref"].endswith("/ErrorEnvelope")
        assert codes <= set(reply["examples"])
        for name, example in reply["examples"].items():
            assert ErrorEnvelope.model_validate(example["value"]).error.code == name


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
    created = c.post(f"/api/hooks/workflows/{wid}/schedules",
                     json={"name": "Morning", "cron": "0 9 * * MON-FRI", "timezone": "Asia/Ho_Chi_Minh", "input": {"message": "hi"}},
                     headers=H(tok))
    assert created.status_code == 201
    schedule = ScheduleEnvelope.model_validate(created.json()).data
    assert schedule.cron == "0 9 * * MON-FRI" and schedule.next_runs
    listed = ScheduleListEnvelope.model_validate(c.get(f"/api/hooks/workflows/{wid}/schedules", headers=H(tok)).json()).data
    assert [item.id for item in listed] == [schedule.id]
    preview = SchedulePreviewEnvelope.model_validate(c.post(
        f"/api/hooks/workflows/{wid}/schedules/preview", json={"cron": "*/15 * * * *", "timezone": "UTC"}, headers=H(tok)).json()).data
    assert len(preview.next_runs) >= 1
