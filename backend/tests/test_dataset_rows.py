from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import select

from app.models import DatasetRow, DatasetRowKey
from app.services import dataset_rows
from test_datasets import auth, client, create, error  # noqa: F401
from test_identity_migration import db  # noqa: F401


@pytest.fixture
def rows(client):
    dataset = create(client, name="Tickets", team_id="support", columns=[
        {"key": "ticket", "kind": "text", "label": "Ticket", "unique": True, "required": True},
        {"key": "title", "kind": "text", "label": "Title"},
        {"key": "score", "kind": "number", "label": "Score", "unique": True},
        {"key": "done", "kind": "boolean", "label": "Done", "default": False},
        {"key": "when", "kind": "datetime", "label": "When"},
    ])
    return f"/api/datasets/{dataset['id']}/rows"


def call(client, method, url, *, uid="owner", body=None, status=200):
    response = client.request(method, url, headers=auth(uid), **({"json": body} if body is not None else {}))
    assert response.status_code == status, response.text
    return response.json()["data"]


def insert(client, rows, **values):
    return call(client, "POST", rows, body={"values": values}, status=201)["row"]


def query(client, rows, **options):
    return call(client, "POST", f"{rows}/query", uid="member", body=options)


def test_row_crud_permissions_and_versions(client, rows):
    first = insert(client, rows, ticket="A", title="Request", score=0, when="2025-01-02T03:04:05+01:00")
    assert first["values"] == {"ticket": "A", "title": "Request", "score": 0, "done": False, "when": "2025-01-02T02:04:05.000Z"}
    url = f"{rows}/{first['id']}"
    assert call(client, "GET", url, uid="member") == first
    error(client.get(url, headers=auth("other")), 404, "DATASET_NOT_FOUND")
    error(client.patch(url, headers=auth("member"), json={"revision": 1, "values": {"done": True}}), 403, "PERMISSION_DENIED")
    updated = call(client, "PATCH", url, body={"revision": 1, "values": {"done": True}})["row"]
    assert updated["revision"] == 2 and updated["values"]["done"] is True and updated["values"]["title"] == "Request"
    error(client.patch(url, headers=auth("owner"), json={"revision": 1, "values": {"done": False}}), 409, "DATASET_ROW_CONFLICT")
    error(client.delete(url + "?revision=1", headers=auth("owner")), 409, "DATASET_ROW_CONFLICT")
    assert call(client, "DELETE", url + "?revision=2") == {"ok": True}
    error(client.get(url, headers=auth("owner")), 404, "DATASET_ROW_NOT_FOUND")
    assert insert(client, rows, ticket="A", score=0)["id"] != first["id"]


def test_row_filter_projection_sort_and_paging(client, rows, monkeypatch):
    a = insert(client, rows, ticket="A", title="Hello%", score=10)
    b = insert(client, rows, ticket="B", title="Hello", score=2)
    c = insert(client, rows, ticket="C", title=None)
    d = insert(client, rows, ticket="D", title="hello")
    page = query(client, rows, sort="score", descending=False, limit=1, fields=["ticket"])
    assert page["next_offset"] == 1 and page["items"][0]["values"] == {"ticket": "B"}
    page = query(client, rows, sort="score", descending=False, limit=1, offset=1)
    assert page["items"][0]["id"] == a["id"]
    assert [row["id"] for row in query(client, rows, filters=[{"field": "score", "op": "eq", "value": 2.0}])["items"]] == [b["id"]]
    assert [row["id"] for row in query(client, rows, filters=[{"field": "score", "op": "lt", "value": 3}])["items"]] == [b["id"]]
    assert [row["id"] for row in query(client, rows, filters=[{"field": "title", "op": "is_null"}])["items"]] == [c["id"]]
    assert [row["id"] for row in query(client, rows, filters=[{"field": "title", "op": "contains", "value": "%"}])["items"]] == [a["id"]]
    assert [row["id"] for row in query(client, rows, search="Hello")["items"]] == [a["id"], b["id"], d["id"]]
    assert len(query(client, rows, filters=[{"field": "done", "op": "eq", "value": False}])["items"]) == 4
    assert query(client, rows, filters=[{"field": "done", "op": "ne", "value": False}])["items"] == []
    error(client.post(f"{rows}/query", headers=auth("owner"), json={"filters": [{"field": "done", "op": "lt", "value": True}]}),
          400, "DATASET_FILTER_INVALID")
    monkeypatch.setattr(dataset_rows, "MAX_PAGE_BYTES", 250)
    bounded = query(client, rows)
    assert len(bounded["items"]) == 1 and bounded["next_offset"] == 1


def test_row_constraints_and_concurrent_upsert(client, rows):
    insert(client, rows, ticket="A", score=1)
    error(client.post(rows, headers=auth("owner"), json={"values": {"ticket": "B", "score": 1.0}}),
          409, "DATASET_UNIQUE_CONFLICT")
    error(client.post(rows, headers=auth("owner"), json={"values": {"title": "Missing key"}}),
          400, "DATASET_VALUE_INVALID")
    error(client.post(f"{rows}/upsert", headers=auth("owner"), json={"key": "title", "values": {"title": "Not unique"}}),
          400, "DATASET_UPSERT_KEY_INVALID")

    def upsert(title):
        return call(client, "POST", f"{rows}/upsert", body={"key": "ticket", "values": {"ticket": "C", "title": title}})

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(upsert, ["First", "Second"]))
    assert results[0]["row"]["id"] == results[1]["row"]["id"]
    assert sorted(result["inserted"] for result in results) == [False, True]
    assert len(query(client, rows, filters=[{"field": "ticket", "op": "eq", "value": "C"}])["items"]) == 1


def test_row_filter_modes_and_multicolumn_sort(client, rows):
    insert(client, rows, ticket="A", title="Shared", score=1)
    insert(client, rows, ticket="B", title="Shared", score=3, done=True)
    insert(client, rows, ticket="C", title="Other", score=2, done=True)
    insert(client, rows, ticket="D", title="Other", score=4)
    insert(client, rows, ticket="E", title="Shared")
    filters = [{"field": "title", "op": "eq", "value": "Shared"}, {"field": "done", "op": "eq", "value": True}]
    sorts = [{"field": "title"}, {"field": "score", "descending": True}]

    def tickets(**options):
        return [row["values"]["ticket"] for row in query(client, rows, filters=filters, sorts=sorts, **options)["items"]]

    assert tickets() == ["B"]
    assert tickets(filter_mode="or") == ["C", "B", "A", "E"]
    assert tickets(filter_mode="or", search="Shared") == ["B", "A", "E"]
    assert tickets(filter_mode="or", offset=1, limit=2) == ["B", "A"]
    error(client.post(f"{rows}/query", headers=auth("other"), json={"filters": filters, "filter_mode": "or"}),
          404, "DATASET_NOT_FOUND")


def test_schema_evolution_and_row_cleanup(client, rows, db):
    insert(client, rows, ticket="A", title="Original")
    dataset_url = rows.removesuffix("/rows")
    error(client.post(f"{dataset_url}/columns", headers=auth("owner"), json={
        "revision": 1, "column": {"key": "new", "label": "New", "kind": "text", "required": True},
    }), 409, "DATASET_SCHEMA_HAS_ROWS")
    assert call(client, "POST", f"{dataset_url}/columns", body={
        "revision": 1, "column": {"key": "new", "label": "New", "kind": "text", "default": "Default"},
    }, status=201)["revision"] == 2
    assert query(client, rows)["items"][0]["values"]["new"] is None
    assert insert(client, rows, ticket="B")["values"]["new"] == "Default"
    assert call(client, "DELETE", f"{dataset_url}/columns/title?revision=2")["revision"] == 3
    assert "title" not in query(client, rows)["items"][0]["values"]
    assert call(client, "DELETE", f"{dataset_url}?revision=3") == {"ok": True}
    with db.session() as session:
        assert list(session.scalars(select(DatasetRow))) == []
        assert list(session.scalars(select(DatasetRowKey))) == []


def test_ne_matches_empty_cells_and_text_matching_ignores_case(client, rows):
    a = insert(client, rows, ticket="A", title="Webhook retry", score=5)
    b = insert(client, rows, ticket="B", title="WEBHOOK timeout", score=1)
    c = insert(client, rows, ticket="C", title="webhook")
    d = insert(client, rows, ticket="D", title="\u0110\u01a1n h\u00e0ng \u1ea4n \u0110\u1ed9", score=2, done=True)
    e = insert(client, rows, ticket="E")

    def ids(**options):
        return [row["id"] for row in query(client, rows, **options)["items"]]

    assert ids(filters=[{"field": "score", "op": "ne", "value": 5}]) == [b["id"], c["id"], d["id"], e["id"]]
    assert ids(filters=[{"field": "title", "op": "ne", "value": "webhook"}]) == [a["id"], b["id"], d["id"], e["id"]]
    assert ids(filters=[{"field": "done", "op": "ne", "value": True}]) == [a["id"], b["id"], c["id"], e["id"]]
    for term in ("webhook", "WEBHOOK", "Webhook"):
        assert ids(search=term) == [a["id"], b["id"], c["id"]]
        assert ids(filters=[{"field": "title", "op": "contains", "value": term}]) == [a["id"], b["id"], c["id"]]
    assert ids(search="\u0111\u01a1n h\u00e0ng \u1ea5n \u0111\u1ed9") == [d["id"]]
    assert ids(filters=[{"field": "title", "op": "contains", "value": "\u0110\u1ed8"}]) == [d["id"]]
    assert ids(filters=[{"field": "title", "op": "eq", "value": "webhook"}]) == [c["id"]]
    assert ids(filters=[{"field": "title", "op": "eq", "value": "Webhook"}]) == []
    assert ids(filters=[{"field": "ticket", "op": "eq", "value": "a"}]) == []


def test_text_sort_ignores_case_with_an_exact_tiebreak(client, rows):
    for ticket, title in (("A", "beta"), ("B", "Alpha"), ("C", "alpha"), ("D", "\u0110\u00e0 N\u1eb5ng"), ("E", "\u0111\u00e0 l\u1ea1t"), ("F", None), ("G", "ALPHA")):
        insert(client, rows, ticket=ticket, title=title)

    def tickets(descending=False):
        return [row["values"]["ticket"] for row in query(client, rows, sorts=[{"field": "title", "descending": descending}])["items"]]

    assert tickets() == ["G", "B", "C", "A", "E", "D", "F"]
    assert tickets(descending=True) == ["D", "E", "A", "C", "B", "G", "F"]
