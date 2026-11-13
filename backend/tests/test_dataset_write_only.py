"""Security regressions: a caller that may write but not read a dataset never receives cell values."""
import asyncio
import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import select

from app.api import deps
from app.core.errors import AppError
from app.models import AuditEvent, DatasetWriteReceipt, Workflow
from app.repositories.dataset_rows import DatasetRowRepository, WorkflowWrite
from app.repositories.datasets import DatasetRepository
from test_agent_node import call as tool_call
from test_agent_node import final as agent_state, script, wf
from test_dataset_rows import call
from test_dataset_runtime import assert_error, final, grant, graph, run, save
from test_datasets import auth, client, create, error  # noqa: F401
from test_identity_migration import db  # noqa: F401

SECRET = "secret-7731"
TICKET = {"key": "ticket", "kind": "text", "unique": True, "required": True}
EMAIL = {"key": "email", "kind": "text"}
NOTE = {"key": "note", "kind": "text"}


def tickets(client):
    """A dataset with one existing row whose other cells a write-only caller must never see."""
    data = create(client, name="Tickets", columns=[{**column, "label": column["key"].title()} for column in (TICKET, EMAIL, NOTE)])
    base = f"/api/datasets/{data['id']}"
    row = call(client, "POST", f"{base}/rows", status=201,
               body={"values": {"ticket": "T-1", "email": f"{SECRET}@example.com", "note": SECRET}})["row"]
    return data["id"], base, row


def stored(client, base):
    return {item["values"]["ticket"]: item for item in call(client, "POST", f"{base}/rows/query", body={})["items"]}


def no_secret(value):
    assert SECRET not in json.dumps(value)


def upsert_node(did, fields, values=None):
    return {"id": "dataset", "type": "dataset", "data": {
        "dataset_id": did, "operation": "upsert_row", "fields": fields, "output_field": "result",
        "arguments": {"key": "ticket", "values": values or {"ticket": "{{state.ticket}}"}},
    }}


def audits(db, action):
    with db.session() as session:
        return list(session.scalars(select(AuditEvent).where(AuditEvent.action == action)))


def test_write_only_grant_node_gets_identifiers_and_cannot_request_fields(client, db):
    did, base, row = tickets(client)
    ids_only = save(client, graph("Ids only", upsert_node(did, [])))
    grant(client, did, ids_only, "write")
    events = run(client, {"workflow_id": ids_only, "input": {"ticket": "T-1"}})
    assert final(events) == {"row": {"id": row["id"], "revision": 1}, "inserted": False}
    no_secret(events)

    probe = save(client, graph("Probe", upsert_node(did, ["ticket", "email", "note"])))
    grant(client, did, probe, "write")
    assert_error(run(client, {"workflow_id": probe, "input": {"ticket": "T-1"}}), "DATASET_GRANT_DENIED")
    assert_error(run(client, {"workflow_id": probe, "input": {"ticket": "T-2"}}), "DATASET_GRANT_DENIED")
    assert set(stored(client, base)) == {"T-1"}  # refused before anything was written

    inserted = final(run(client, {"workflow_id": ids_only, "input": {"ticket": "T-2"}}))
    assert inserted["inserted"] is True and set(inserted["row"]) == {"id", "revision"}

    grant(client, did, probe, "read_write")  # read_write keeps the full projected row
    full = final(run(client, {"workflow_id": probe, "input": {"ticket": "T-1"}}))
    assert full["row"]["values"] == {"ticket": "T-1", "email": f"{SECRET}@example.com", "note": SECRET}


def test_write_only_dry_run_and_receipt_replay(client, db):
    did, base, row = tickets(client)
    node = upsert_node(did, [], {"ticket": "{{state.ticket}}", "note": "changed"})
    wid = save(client, graph("Writer", node))
    grant(client, did, wid, "write")

    svc = deps.run_service()
    plan = svc.plan("owner", {"workflow_id": wid, "input": {"ticket": "T-1"}})
    svc.apply_test(plan, {"mock": True})
    events = []

    async def send(event):
        events.append(event)
        return True

    async def listen():
        await asyncio.Future()

    assert asyncio.run(svc.execute(plan, send, listen, "owner")) == "ok"
    assert final(events) == {"row": {"id": row["id"], "revision": 1}, "inserted": False, "dry_run": True}
    no_secret(events)
    assert stored(client, base)["T-1"]["values"]["note"] == SECRET

    def execute(binding, operation_id="op-1", **arguments):
        return svc.dataset_runtime.execute(
            actor="owner", workflow_id=wid, root_workflow_id=wid, run_id="replay-run", fence=None, public=False,
            unsaved=False, dry_run=False, operation_id=operation_id, binding=binding,
            arguments=arguments or {"key": "ticket", "values": {"ticket": "T-1", "note": "changed"}},
        )

    binding = node["data"]
    first = execute(binding)
    assert first == {"row": {"id": row["id"], "revision": 2}, "inserted": False}
    assert execute(binding) == first  # the replayed receipt is filtered the same way

    # A receipt written while the grant could read is not replayed with values after a downgrade.
    grant(client, did, wid, "read_write")
    readable = {**binding, "fields": ["email"]}
    assert execute(readable, "op-2")["row"]["values"] == {"email": f"{SECRET}@example.com"}
    grant(client, did, wid, "write")
    with pytest.raises(AppError) as denied:
        execute(readable, "op-2")
    assert denied.value.code == "DATASET_GRANT_DENIED"
    assert execute(binding) == first


def connected(operation, fields, **args):
    return {"version": 1, "operation": operation, "columns": [TICKET, EMAIL, NOTE], "fields": fields, **args}


def post(client, base, secret, payload):
    return client.post(f"{base}/connected", headers={"Authorization": f"Bearer {secret}"}, json=payload)


def test_write_only_token_reproduces_review_probe(client, db):
    did, base, row = tickets(client)
    secret = call(client, "POST", f"{base}/access/tokens", status=201,
                  body={"name": "Form", "permission": "write", "allow_delete": False})["token"]
    upsert = {"key": "ticket", "values": {"ticket": "T-1"}}

    probe = post(client, base, secret, connected("upsert_row", ["ticket", "email", "note"],
                                                 operation_id="probe:1", arguments=upsert))
    error(probe, 403, "DATASET_GRANT_DENIED")
    no_secret(probe.json())

    ids_only = post(client, base, secret, connected("upsert_row", [], operation_id="probe:2", arguments=upsert))
    assert ids_only.status_code == 200, ids_only.text
    assert ids_only.json()["data"] == {"row": {"id": row["id"], "revision": 1}, "inserted": False}
    no_secret(ids_only.json())
    replayed = post(client, base, secret, connected("upsert_row", [], operation_id="probe:2", arguments=upsert))
    assert replayed.json()["data"] == ids_only.json()["data"]
    added = post(client, base, secret, connected("insert_row", [], operation_id="probe:3",
                                                 arguments={"values": {"ticket": "T-2", "note": "new"}}))
    assert added.json()["data"]["inserted"] is True and set(added.json()["data"]["row"]) == {"id", "revision"}
    error(post(client, base, secret, connected("find_rows", ["ticket"])), 401, "AUTH_TOKEN_INVALID")
    error(post(client, base, secret, connected("get_row", ["note"], arguments={"row_id": row["id"]})), 401,
          "AUTH_TOKEN_INVALID")
    assert stored(client, base)["T-1"]["revision"] == 1

    full = call(client, "POST", f"{base}/access/tokens", status=201,
                body={"name": "Sync", "permission": "read_write", "allow_delete": False})["token"]
    reply = post(client, base, full, connected("upsert_row", ["note"], operation_id="sync:1", arguments=upsert))
    assert reply.json()["data"]["row"]["values"] == {"note": SECRET}


def ticket_tool(did, **overrides):
    return {"name": "file_ticket", "source": "dataset", "dataset_id": did, "fields": ["ticket", "email", "note"],
            "filter_ops": {"ticket": ["eq"]}, "limit": 1, "operations": ["upsert_row"],
            "write_fields": ["ticket", "note"], "key": "ticket", **overrides}


def test_agent_tool_without_find_gets_identifiers_only(client, db, monkeypatch):
    did, base, row = tickets(client)
    tool = ticket_tool(did)
    wid = save(client, wf(tools=[tool], steps_field="steps"))
    grant(client, did, wid, "read_write")  # even a readable grant: the tool cannot Find
    seen = script(monkeypatch, [("", [tool_call(tool["name"], {"operation": "upsert_row", "values": {"ticket": "T-1"}})]),
                                ("Finished", [])])
    events = run(client, {"workflow_id": wid})
    steps = agent_state(events)["steps"]
    assert steps[0]["status"] == "ok" and steps[0]["dataset"] == {"count": 1, "operation": "upsert_row"}
    message = next(json.loads(msg["content"]) for msg in seen[1][0] if msg["role"] == "tool")
    assert message == {"row_id": row["id"], "inserted": False}
    no_secret(seen)
    no_secret(events)

    finder = ticket_tool(did, name="find_and_file", operations=["find_rows", "upsert_row"])
    wid = save(client, wf(tools=[finder], steps_field="steps"))
    grant(client, did, wid, "write")  # Find configured, but the grant cannot read
    seen = script(monkeypatch, [("", [tool_call(finder["name"], {"operation": "upsert_row", "values": {"ticket": "T-1"}})]),
                                ("Finished", [])])
    run(client, {"workflow_id": wid})
    message = next(json.loads(msg["content"]) for msg in seen[1][0] if msg["role"] == "tool")
    assert message == {"row_id": row["id"], "inserted": False}
    no_secret(seen)


def test_noop_upsert_keeps_revision_updated_and_audit(client, db):
    did, base, row = tickets(client)
    same = {"key": "ticket", "values": {"ticket": "T-1", "note": SECRET}}
    for _ in range(2):
        result = call(client, "POST", f"{base}/rows/upsert", body=same)
        assert result["inserted"] is False and result["row"]["revision"] == 1
    current = stored(client, base)["T-1"]
    assert (current["revision"], current["updated"]) == (1, row["updated"])
    assert audits(db, "dataset.row_update") == [] and len(audits(db, "dataset.row_insert")) == 1

    changed = call(client, "POST", f"{base}/rows/upsert", body={"key": "ticket", "values": {"ticket": "T-1", "note": "B"}})
    assert changed["row"]["revision"] == 2
    call(client, "POST", f"{base}/rows/upsert", body={"key": "ticket", "values": {"ticket": "T-1", "note": "B"}})
    assert stored(client, base)["T-1"]["revision"] == 2 and len(audits(db, "dataset.row_update")) == 1
    # A no-op still enforces the unique key: the value stays matched after the skipped rewrite.
    assert call(client, "POST", f"{base}/rows/query", body={"filters": [
        {"field": "ticket", "op": "eq", "value": "T-1"}]})["items"][0]["id"] == row["id"]


def test_concurrent_noop_and_real_update_are_serialized(client, db):
    did, base, row = tickets(client)
    noop = {"key": "ticket", "values": {"ticket": "T-1", "note": SECRET}}
    update = {"key": "ticket", "values": {"ticket": "T-1", "note": "C"}}
    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(lambda body: call(client, "POST", f"{base}/rows/upsert", body=body), [noop, update]))
    assert results[1]["row"]["revision"] == 2
    current = stored(client, base)["T-1"]
    # Whichever ran first, exactly one write changed the row.
    assert current["values"]["note"] in {"C", SECRET} and current["revision"] in {2, 3}
    assert len(audits(db, "dataset.row_update")) == current["revision"] - 1


def test_value_reveal_is_rechecked_under_the_writer_lock(client, db):
    did, base, row = tickets(client)
    with db.session() as session:
        session.add(Workflow(id="locked-flow", name="Locked", owner="owner"))
        session.commit()
    grant(client, did, "locked-flow", "write")
    repo = DatasetRowRepository(DatasetRepository(db))
    dataset = repo.datasets.get("owner", did)
    receipt = WorkflowWrite(run_id="locked-run", workflow_id="locked-flow", operation_id="op",
                            arguments={"operation": "insert_row", "values": {"ticket": "T-9"}})
    with pytest.raises(AppError) as denied:
        repo.save("owner", dataset, lambda _: {"ticket": "T-9", "email": None, "note": None}, workflow=receipt, reveal=True)
    assert denied.value.code == "DATASET_GRANT_DENIED"
    assert set(stored(client, base)) == {"T-1"}
    with db.session() as session:
        assert list(session.scalars(select(DatasetWriteReceipt))) == []
