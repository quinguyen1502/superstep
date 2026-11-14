from concurrent.futures import ThreadPoolExecutor
import json

from sqlalchemy import select

from app.models import AuditEvent
from test_dataset_rows import call
from test_datasets import auth, client, create, error  # noqa: F401
from test_identity_migration import db  # noqa: F401


TICKET = {"key": "ticket", "kind": "text", "unique": True, "required": True}
SCORE = {"key": "score", "kind": "number"}
ACTIVE = {"key": "active", "kind": "boolean"}


def dataset(client, name="Connected"):
    columns = [{**column, "label": column["key"].capitalize()} for column in (TICKET, SCORE, ACTIVE)]
    return create(client, name=name, columns=columns)


def token(client, base, permission="read_write", allow_delete=False):
    return call(client, "POST", f"{base}/access/tokens",
                body={"name": permission, "permission": permission, "allow_delete": allow_delete}, status=201)


def request(operation, **args):
    return {"version": 1, "operation": operation, "columns": [TICKET, SCORE, ACTIVE],
            "fields": ["ticket", "score", "active"], **args}


def post(client, base, secret, payload):
    return client.post(f"{base}/connected", headers={"Authorization": f"Bearer {secret}"}, json=payload)


def test_connected_write_receipt_projection_and_token_rotation(client, db):
    data = dataset(client)
    base = f"/api/datasets/{data['id']}"
    issued = token(client, base)
    secret = issued["token"]
    insert = request("insert_row", operation_id="job-a:write",
                     arguments={"values": {"ticket": "A", "score": 0, "active": False}})
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies = list(pool.map(lambda _: post(client, base, secret, insert), range(2)))
    assert all(reply.status_code == 200 and reply.headers["cache-control"] == "no-store" for reply in replies)
    result = replies[0].json()["data"]
    assert result == replies[1].json()["data"]
    assert result["inserted"] and result["row"]["values"] == {"ticket": "A", "score": 0, "active": False}
    row_id = result["row"]["id"]
    different = {**insert, "arguments": {"values": {"ticket": "B"}}}
    error(post(client, base, secret, different), 409, "DATASET_RECEIPT_CONFLICT")
    update = request("upsert_row", operation_id="job-b:write", fields=["ticket", "score"],
                     arguments={"key": "ticket", "values": {"ticket": "A", "score": 1}})
    updated = post(client, base, secret, update)
    assert updated.status_code == 200
    assert updated.json()["data"]["row"]["values"] == {"ticket": "A", "score": 1}
    assert updated.json()["data"]["inserted"] is False
    replayed = post(client, base, secret, insert)
    current = replayed.json()["data"]
    assert current["inserted"] and current["row"]["id"] == row_id
    assert current["row"]["revision"] == 2 and current["row"]["values"] == {"ticket": "A", "score": 1, "active": False}
    got = post(client, base, secret, request("get_row", fields=["active"], arguments={"row_id": row_id}))
    assert got.json()["data"]["values"] == {"active": False}
    found = post(client, base, secret, request("find_rows", fields=["score"], arguments={
        "filters": [{"field": "ticket", "op": "eq", "value": "A"}], "limit": 1,
    }))
    assert [row["values"] for row in found.json()["data"]["items"]] == [{"score": 1}]

    token_path = f"{base}/access/tokens/{issued['id']}"
    rotated = call(client, "POST", f"{token_path}/rotate")
    error(post(client, base, secret, insert), 401, "AUTH_TOKEN_INVALID")
    assert post(client, base, rotated["token"], insert).json()["data"] == current
    call(client, "DELETE", token_path)
    error(post(client, base, rotated["token"], insert), 401, "AUTH_TOKEN_INVALID")
    assert len(call(client, "POST", f"{base}/rows/query", body={})["items"]) == 1

    with db.session() as session:
        events = list(session.scalars(select(AuditEvent).where(
            AuditEvent.action.in_(("dataset.row_insert", "dataset.row_update", "dataset.connected_read")),
        )))
    assert len(events) == 4
    assert all(json.loads(event.details)["credential_id"] == issued["id"] for event in events)
    assert all(secret not in event.details for event in events)


def test_connected_delete_replays_and_ignores_write_permission(client, db):
    data = dataset(client)
    base = f"/api/datasets/{data['id']}"
    writer = token(client, base)
    inserted = post(client, base, writer["token"], request(
        "insert_row", operation_id="job:write", arguments={"values": {"ticket": "A", "score": 1, "active": False}},
    )).json()["data"]
    row_id = inserted["row"]["id"]
    denied = request("delete_row", operation_id="job:delete", arguments={"row_id": row_id})
    error(post(client, base, writer["token"], denied), 403, "DATASET_TOKEN_SCOPE")
    remover = token(client, base, "read", allow_delete=True)
    secret = remover["token"]
    deleted = post(client, base, secret, denied)
    assert deleted.status_code == 200
    assert deleted.json()["data"] == {"row_id": row_id, "deleted": True}
    assert post(client, base, secret, denied).json()["data"] == deleted.json()["data"]
    conflict = request("delete_row", operation_id="job:delete", arguments={"key": "ticket", "value": "A"})
    error(post(client, base, secret, conflict), 409, "DATASET_RECEIPT_CONFLICT")
    missing = request("delete_row", operation_id="job:missing", arguments={"row_id": "absent"})
    error(post(client, base, secret, missing), 404, "DATASET_ROW_NOT_FOUND")
    again = post(client, base, writer["token"], request(
        "insert_row", operation_id="job:again", arguments={"values": {"ticket": "B", "score": 0, "active": True}},
    ))
    assert again.status_code == 200
    by_key = request("delete_row", operation_id="job:missing", arguments={"key": "ticket", "value": "B"})
    assert post(client, base, secret, by_key).json()["data"]["deleted"] is True
    assert call(client, "POST", f"{base}/rows/query", body={})["items"] == []
    error(post(client, base, secret, request(
        "delete_row", operation_id="job:bad", arguments={"key": "score", "value": 1},
    )), 400, "DATASET_UPSERT_KEY_INVALID")
    with db.session() as session:
        audits = list(session.scalars(select(AuditEvent).where(AuditEvent.action == "dataset.row_delete")))
    assert len(audits) == 2
    assert all(json.loads(event.details)["credential_id"] == remover["id"] for event in audits)
    assert all("A" not in event.details and "B" not in event.details and secret not in event.details for event in audits)


def test_connected_schema_and_scope_fail_explicitly(client):
    data = dataset(client)
    base = f"/api/datasets/{data['id']}"
    read = token(client, base, "read")["token"]
    write = token(client, base, "write")["token"]
    lookup = request("find_rows")
    error(client.post(f"{base}/connected", json=lookup), 401, "AUTH_REQUIRED")
    error(client.post(f"{base}/connected", headers=auth("owner"), json=lookup), 401, "AUTH_TOKEN_INVALID")
    error(post(client, base, write, lookup), 403, "DATASET_TOKEN_SCOPE")
    other = dataset(client, name="Another")
    wrong_dataset = post(client, f"/api/datasets/{other['id']}", read, lookup)
    error(wrong_dataset, 401, "AUTH_TOKEN_INVALID")
    missing = post(client, "/api/datasets/missing", read, lookup)
    assert wrong_dataset.json()["error"] == missing.json()["error"]
    insert = request("insert_row", operation_id="job:write", arguments={"values": {"ticket": "A"}})
    error(post(client, base, read, insert), 403, "DATASET_TOKEN_SCOPE")
    error(post(client, base, write, {**insert, "operation_id": None}), 400, "DATASET_NODE_ARGUMENTS_INVALID")
    error(post(client, base, read, {**lookup, "columns": [TICKET]}), 409, "DATASET_BINDING_SCHEMA_MISMATCH")
    renamed = call(client, "PUT", f"{base}/columns/score", body={
        "revision": data["revision"], "column": {**SCORE, "label": "Total"},
    })
    assert post(client, base, read, lookup).status_code == 200
    call(client, "DELETE", f"{base}/columns/score?revision={renamed['revision']}")
    error(post(client, base, read, lookup), 409, "DATASET_BINDING_SCHEMA_MISMATCH")
