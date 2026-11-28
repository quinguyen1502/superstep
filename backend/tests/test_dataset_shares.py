"""Dataset share management, projected reads and capability isolation."""

import json

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import event, inspect, select

from app.api import deps
from app.core.dataset_types import MAX_PAGE_BYTES
from app.core.logging import redact
from app.main import app
from app.models import AuditEvent, DatasetShare, User, Workflow
from app.models.database import MIGRATIONS_DIR
from app.repositories.dataset_rows import DatasetRowRepository
from app.repositories.dataset_shares import DatasetShareRepository
from app.services.pat_service import digest
from app.services.rate_limit import InMemoryRateLimiter
from test_dataset_connected import request as connected_request, token as dataset_token
from test_dataset_rows import call, insert
from test_datasets import auth, client, create, error  # noqa: F401
from test_identity_migration import db  # noqa: F401

PUBLIC = "/api/public/v1/dataset-view"
SECRET = "X-Dataset-Share"


@pytest.fixture(autouse=True)
def share_limiter(monkeypatch):
    limiter = InMemoryRateLimiter()
    monkeypatch.setattr(deps, "get_rate_limiter", lambda: limiter)


def field(key, kind="text", **extras):
    return {"key": key, "kind": kind, "label": key.title(), **extras}


def make_dataset(client, name="Private dataset", columns=None, **props):
    dataset = create(client, name=name, columns=columns or [field("title"), field("internal"), field("published", "boolean")],
                     **props)
    return f"/api/datasets/{dataset['id']}"


def group(key, op, value=None):
    return {"type": "group", "conjunction": "and",
            "children": [{"type": "rule", "field": key, "op": op, "value": value}]}


def settings(fields=None, **extras):
    return {"name": "Published tickets", "fields": ["title"] if fields is None else fields, "schema_revision": 1, **extras}


def issue(client, base, **body):
    response = client.post(base + "/shares", headers=auth("owner"), json=body or settings())
    assert response.status_code == 201, response.text
    assert response.headers["cache-control"] == "no-store"
    return response.json()["data"]


def public(client, secret=None, path="", **query):
    response = client.get(PUBLIC + path, params=query, headers={SECRET: secret} if secret is not None else {})
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-robots-tag"] == "noindex"
    assert response.headers["referrer-policy"] == "no-referrer"
    return response


def data(response):
    assert response.status_code == 200, response.text
    return response.json()["data"]


def test_preview_matches_public_projection_and_search_only_uses_published_columns(client, db):
    base = make_dataset(client, description="private description")
    title = "H\u1ed7 tr\u1ee3 webhook"
    insert(client, base + "/rows", title=title, internal="unique-hidden-needle", published=True)
    insert(client, base + "/rows", title="Public printer", internal="private memo", published=True)
    excluded = insert(client, base + "/rows", title="Unpublished webhook", internal="unpublished", published=False)
    requested = settings(filter_tree=group("published", "eq", True))
    preview = data(client.post(base + "/shares/preview", headers=auth("owner"), json={**requested, "limit": 1}))
    secret = issue(client, base, **requested)["token"]
    assert data(public(client, secret)) == preview["view"] == {
        "name": "Published tickets", "columns": [{"key": "title", "label": "Title", "kind": "text"}], "searchable": True,
    }

    projections = []

    def capture(_conn, _cursor, statement, _params, _context, _many):
        selected, found, _ = statement.partition("FROM dataset_rows")
        if found:
            projections.append(selected)

    event.listen(db.engine, "before_cursor_execute", capture)
    try:
        assert data(public(client, secret, "/rows", limit=1)) == {
            "items": [{"title": title}], "next_offset": 1,
        } == {key: preview[key] for key in ("items", "next_offset")}
    finally:
        event.remove(db.engine, "before_cursor_execute", capture)
    assert projections
    assert all("dataset_rows.id" not in read and "formula_errors" not in read and "revision" not in read for read in projections)
    assert data(public(client, secret, "/rows", limit=1, offset=1)) == {
        "items": [{"title": "Public printer"}], "next_offset": None,
    }
    assert data(public(client, secret, "/rows", search=title.split(" webhook")[0].upper())) == {
        "items": [{"title": title}], "next_offset": None,
    }
    for query in [{"search": "unique-hidden-needle"}, {"search": "Unpublished"}, {"offset": 2}]:
        assert data(public(client, secret, "/rows", **query)) == {"items": [], "next_offset": None}
    for query in [
        {"fields": "internal"}, {"filter_tree": "{}"}, {"sort": "internal"}, {"include_total": True},
        {"dataset_id": base.split("/")[-1]}, {"id": excluded["id"]}, {"limit": 101}, {"limit": 0},
        {"offset": 25001}, {"search": "x" * 121},
    ]:
        response = public(client, secret, "/rows", **query)
        error(response, 422, "VALIDATION_ERROR")
        assert response.json()["data"] is None


def test_public_projection_preserves_typed_cells_and_omits_formula_diagnostics(client, monkeypatch):
    monkeypatch.setenv("STUDIO_ENABLE_DATASET_FORMULAS", "1")
    base = make_dataset(client, columns=[
        field("score", "number"), field("flag", "boolean"), field("tags", "multi_select", options=["A", "B"]),
        field("start", "created_time"), field("num", "auto_number"), field("blank"), field("original", "number"),
        field("computed", "number", formula={"expression": "10 / [original]"}),
    ])
    row = insert(client, base + "/rows", score=1.5, flag=False, tags=["A", "B"], original=0)
    assert row["formula_errors"]
    fields = ["computed", "score", "flag", "tags", "blank", "start", "num"]
    secret = issue(client, base, **settings(fields))["token"]
    result = data(public(client, secret, "/rows"))
    assert list(result["items"][0]) == fields
    assert result["items"] == [{
        "computed": None, "score": 1.5, "flag": False, "tags": ["A", "B"], "blank": None,
        "start": row["values"]["start"], "num": row["values"]["num"],
    }]
    assert result["items"][0]["flag"] is False
    assert data(public(client, secret))["columns"][0] == {"key": "computed", "kind": "number", "label": "Computed"}


def test_manager_authorization_rotation_revocation_deletion_and_audit(client, db):
    base = make_dataset(client, team_id="support")
    another = make_dataset(client, "Another")
    path = base + "/shares"
    with db.session() as session:
        session.get(User, "member").role = "editor"
        session.commit()
    grant = issue(client, base)
    sid = grant["id"]
    original = grant["token"]
    for method, suffix, kwargs in [
        ("GET", "", {}), ("POST", "", {"json": settings()}), ("POST", "/preview", {"json": settings()}),
        ("POST", f"/{sid}/rotate", {}), ("DELETE", f"/{sid}", {}),
    ]:
        error(client.request(method, path + suffix, headers=auth("member"), **kwargs), 403, "DATASET_MANAGE_DENIED")
        error(client.request(method, path + suffix, headers=auth("other"), **kwargs), 404, "DATASET_NOT_FOUND")
        error(client.request(method, path + suffix, **kwargs), 401, "AUTH_REQUIRED")
    error(client.post(f"{another}/shares/{sid}/rotate", headers=auth("owner")), 404, "DATASET_SHARE_NOT_FOUND")
    error(client.delete(f"{another}/shares/{sid}", headers=auth("owner")), 404, "DATASET_SHARE_NOT_FOUND")

    listed = data(client.get(path, headers=auth("owner")))
    assert listed["items"] == [{key: value for key, value in grant.items() if key != "token"}]
    assert "token_hash" not in json.dumps(listed)
    rotated = data(client.post(f"{path}/{sid}/rotate", headers=auth("owner")))
    assert rotated["id"] == sid and rotated["token"] != original
    error(public(client, original), 404, "DATASET_SHARE_NOT_FOUND")
    data(public(client, rotated["token"]))
    assert data(client.delete(f"{path}/{sid}", headers=auth("owner"))) == {"ok": True}
    error(public(client, rotated["token"], "/rows"), 404, "DATASET_SHARE_NOT_FOUND")
    error(client.post(f"{path}/{sid}/rotate", headers=auth("owner")), 404, "DATASET_SHARE_NOT_FOUND")
    assert data(client.get(path, headers=auth("owner"))) == {"items": [], "next_offset": None}
    with db.session() as session:
        record = session.get(DatasetShare, sid)
        assert record.token_hash == digest(rotated["token"]) and record.revoked is not None
        audit = list(session.scalars(select(AuditEvent).where(AuditEvent.target_id == sid).order_by(AuditEvent.ts)))
        assert [e.action for e in audit] == ["share.dataset_create", "share.dataset_rotate", "share.dataset_revoke"]
        assert all(json.loads(e.details) == {"dataset_id": base.split("/")[-1]} for e in audit)
    live = issue(client, base)
    assert data(client.delete(base + "?revision=1", headers=auth("owner"))) == {"ok": True}
    error(public(client, live["token"]), 404, "DATASET_SHARE_NOT_FOUND")
    with db.session() as session:
        assert list(session.scalars(select(DatasetShare))) == []


def test_only_the_dedicated_header_authorizes_public_read_routes(client, db, caplog):
    base = make_dataset(client)
    secret = issue(client, base)["token"]
    token = dataset_token(client, base)["token"]
    with db.session() as session:
        session.add(Workflow(id="share-proof", name="Share proof", owner="owner"))
        session.commit()
    workflow_token = call(client, "POST", "/api/workflows/share-proof/tokens", body={"name": "Workflow API"})["token"]
    unavailable = public(client).json()
    for wrong in [token, workflow_token, "pat_" + "a" * 43, "dssh_" + "a" * 43, secret + "x"]:
        response = public(client, wrong)
        error(response, 404, "DATASET_SHARE_NOT_FOUND")
        assert response.json() == unavailable
    error(public(client, secret, "/unknown"), 404, "NOT_FOUND")
    error(public(client, token=secret), 404, "DATASET_SHARE_NOT_FOUND")
    error(client.get(PUBLIC, headers={"Authorization": "Bearer " + secret}), 404, "DATASET_SHARE_NOT_FOUND")
    error(client.get(PUBLIC, headers=[(SECRET, secret), (SECRET, secret)]), 404, "DATASET_SHARE_NOT_FOUND")
    error(client.get(base + "/shares", headers={SECRET: secret}), 401, "AUTH_REQUIRED")
    error(client.post(base + "/rows", headers={SECRET: secret}, json={"values": {"title": "No"}}), 401, "AUTH_REQUIRED")
    error(client.post(PUBLIC + "/rows", headers={SECRET: secret}), 405, "METHOD_NOT_ALLOWED")
    request = connected_request("insert_row", operation_id="share-write", arguments={"values": {"ticket": "No"}})
    error(client.post(base + "/connected", headers={"Authorization": "Bearer " + secret}, json=request),
          401, "AUTH_TOKEN_INVALID")
    assert secret not in redact(f"header {SECRET}: {secret}")
    response = client.get(PUBLIC, headers={SECRET: secret, "X-Request-ID": secret})
    assert response.headers["x-request-id"] != secret
    assert secret not in caplog.text


def test_public_recovery_errors_are_not_cached(client, monkeypatch, caplog):
    base = make_dataset(client)
    secret = issue(client, base)["token"]

    def unavailable(*_args):
        raise RuntimeError("Temporary storage error")

    monkeypatch.setattr(DatasetShareRepository, "resolve", unavailable)
    response = public(TestClient(app, raise_server_exceptions=False), secret)
    error(response, 500, "INTERNAL_ERROR")
    assert secret not in caplog.text


def test_share_bounds_and_link_and_ip_quotas(client, monkeypatch):
    base = make_dataset(client)
    share = issue(client, base)
    second = issue(client, base, **settings(name="Second view"))
    response = client.post(base + "/shares", headers=auth("owner"), content=b"x" * (256 * 1024 + 1))
    error(response, 413, "PAYLOAD_TOO_LARGE")
    assert response.headers["cache-control"] == "no-store"
    for fields in [[], ["title", "title"]]:
        error(client.post(base + "/shares", headers=auth("owner"), json=settings(fields)), 422, "VALIDATION_ERROR")
    error(client.post(base + "/shares", headers=auth("owner"), json=settings(["typo"])), 400, "DATASET_SHARE_FIELD_UNAVAILABLE")
    error(client.post(base + "/shares", headers=auth("owner"), json=settings(schema_revision=9)), 409, "DATASET_SCHEMA_CONFLICT")
    error(client.post(base + "/shares", headers=auth("owner"), json=settings(filter_tree=group("published", "contains", "x"))),
          400, "DATASET_FILTER_INVALID")
    assert data(client.get(base + "/shares?limit=1", headers=auth("owner")))["next_offset"] == 1

    monkeypatch.setattr("app.services.rate_limit._window", lambda _window, _now: (1, 60))
    monkeypatch.setenv("STUDIO_PUBLIC_DATASET_RATE_IP", "2")
    monkeypatch.setenv("STUDIO_PUBLIC_DATASET_RATE_LINK", "1")
    visitor = TestClient(app, client=("192.0.2.4", 5000))
    distinct = TestClient(app, client=("192.0.2.5", 5000))
    data(public(visitor, share["token"]))
    limited = public(distinct, share["token"], "/rows")
    error(limited, 429, "RATE_LIMITED")
    assert int(limited.headers["retry-after"]) >= 1
    error(public(visitor, "invalid"), 404, "DATASET_SHARE_NOT_FOUND")
    error(public(visitor, second["token"]), 429, "RATE_LIMITED")
    data(public(distinct, second["token"]))


def test_schema_drift_rejects_incompatible_views_without_affecting_compatible_shares(client, monkeypatch):
    monkeypatch.setenv("STUDIO_ENABLE_DATASET_FORMULAS", "1")
    source = field("derived", "number", formula={"expression": "[base] + 1"})
    outer = field("computed", "number", formula={"expression": "[derived] + 1"})
    base = make_dataset(client, columns=[field("title"), field("base", "number"), field("category"), source, outer])
    plain = issue(client, base)["token"]
    conditional = issue(client, base, **settings(filter_tree=group("category", "eq", "visible")))["token"]
    calculated = issue(client, base, **settings(["computed"]))
    assert data(public(client, calculated["token"]))["searchable"] is False
    call(client, "POST", base + "/columns", status=201, body={"revision": 1, "column": field("other")})
    data(public(client, conditional))
    data(public(client, calculated["token"]))
    call(client, "PUT", base + "/columns/derived", body={
        "revision": 2, "column": {**source, "formula": {"expression": "[base] + 2"}},
    })
    error(public(client, calculated["token"]), 404, "DATASET_SHARE_NOT_FOUND")
    error(client.post(f"{base}/shares/{calculated['id']}/rotate", headers=auth("owner")), 409, "DATASET_SHARE_SCHEMA_CHANGED")
    call(client, "DELETE", base + "/columns/category?revision=3")
    error(public(client, conditional, "/rows"), 404, "DATASET_SHARE_NOT_FOUND")
    call(client, "PUT", base + "/columns/title", body={"revision": 4, "column": field("title", label="Public subject")})
    assert data(public(client, plain))["columns"][0]["label"] == "Public subject"
    call(client, "DELETE", base + "/columns/title?revision=5")
    error(public(client, plain), 404, "DATASET_SHARE_NOT_FOUND")
    assert not any(item["available"] for item in data(client.get(base + "/shares", headers=auth("owner")))["items"])


def test_rows_recheck_share_after_projection(client, monkeypatch):
    base = make_dataset(client)
    insert(client, base + "/rows", title="In-flight result")
    share = issue(client, base)
    original = DatasetRowRepository.project_page

    def rotate_after_read(repo, dataset_id, **kwargs):
        rows = original(repo, dataset_id, **kwargs)
        deps.dataset_share_service().rotate("owner", dataset_id, share["id"])
        return rows

    monkeypatch.setattr(DatasetRowRepository, "project_page", rotate_after_read)
    response = public(client, share["token"], "/rows")
    error(response, 404, "DATASET_SHARE_NOT_FOUND")
    assert "In-flight result" not in response.text


def test_public_paging_covers_byte_trimmed_matches_and_skips_deleted_rows(client):
    base = make_dataset(client, columns=[field("a", "long_text"), field("b", "long_text"), field("c", "long_text")])
    secret = issue(client, base, **settings(["a", "b", "c"]))["token"]
    first = insert(client, base + "/rows", a="Deleted")
    call(client, "DELETE", f"{base}/rows/{first['id']}?revision={first['revision']}")
    suffix = "q" * 16_000
    payload = [{"a": f"{index}-{suffix}", "b": suffix, "c": suffix} for index in range(24)]
    for batch in (payload[:12], payload[12:]):
        call(client, "PATCH", base + "/rows/batch", body={"schema_revision": 1, "append": batch})
    response = public(client, secret, "/rows")
    assert len(response.content) <= MAX_PAGE_BYTES
    page = data(response)
    assert 0 < page["next_offset"] < len(payload)
    next_page = data(public(client, secret, "/rows", offset=page["next_offset"]))
    assert sorted(page["items"] + next_page["items"], key=lambda row: row["a"]) == sorted(payload, key=lambda row: row["a"])
    assert next_page["next_offset"] is None


def test_share_migration_keeps_existing_dataset_and_rows(client, db):
    base = make_dataset(client)
    row = insert(client, base + "/rows", title="Already stored")
    cfg = Config()
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    with db.engine.begin() as conn:
        cfg.attributes["connection"] = conn
        command.downgrade(cfg, "0073_dataset_data_revision")
    assert "dataset_shares" not in inspect(db.engine).get_table_names()
    db.migrate()
    assert "dataset_shares" in inspect(db.engine).get_table_names()
    secret = issue(client, base)["token"]
    assert data(public(client, secret, "/rows"))["items"] == [{"title": row["values"]["title"]}]
