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


def token(client, base, permission="read_write"):
    return call(client, "POST", f"{base}/access/tokens", body={"name": permission, "permission": permission}, status=201)


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
    assert replayed.json()["data"] == result
    got = post(client, base, secret, request("get_row", fields=["active"], arguments={"row_id": row_id}))
    assert got.json()["data"]["values"] == {"active": False}
    found = post(client, base, secret, request("find_rows", fields=["score"], arguments={
        "filters": [{"field": "ticket", "op": "eq", "value": "A"}], "limit": 1,
    }))
    assert [row["values"] for row in found.json()["data"]["items"]] == [{"score": 1}]

    token_path = f"{base}/access/tokens/{issued['id']}"
    rotated = call(client, "POST", f"{token_path}/rotate")
    error(post(client, base, secret, insert), 401, "AUTH_TOKEN_INVALID")
    assert post(client, base, rotated["token"], insert).json()["data"] == result
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


def test_connected_schema_and_scope_fail_explicitly(client):
    data = dataset(client)
    base = f"/api/datasets/{data['id']}"
    read = token(client, base, "read")["token"]
    write = token(client, base, "write")["token"]
    lookup = request("find_rows")
    error(client.post(f"{base}/connected", json=lookup), 401, "AUTH_REQUIRED")
    error(client.post(f"{base}/connected", headers=auth("owner"), json=lookup), 401, "AUTH_TOKEN_INVALID")
    error(post(client, base, write, lookup), 401, "AUTH_TOKEN_INVALID")
    other = dataset(client, name="Another")
    error(post(client, f"/api/datasets/{other['id']}", read, lookup), 401, "AUTH_TOKEN_INVALID")
    insert = request("insert_row", operation_id="job:write", arguments={"values": {"ticket": "A"}})
    error(post(client, base, read, insert), 401, "AUTH_TOKEN_INVALID")
    error(post(client, base, write, {**insert, "operation_id": None}), 400, "DATASET_NODE_ARGUMENTS_INVALID")
    error(post(client, base, read, {**lookup, "columns": [TICKET]}), 409, "DATASET_BINDING_SCHEMA_MISMATCH")
    renamed = call(client, "PUT", f"{base}/columns/score", body={
        "revision": data["revision"], "column": {**SCORE, "label": "Total"},
    })
    assert post(client, base, read, lookup).status_code == 200
    call(client, "DELETE", f"{base}/columns/score?revision={renamed['revision']}")
    error(post(client, base, read, lookup), 409, "DATASET_BINDING_SCHEMA_MISMATCH")
