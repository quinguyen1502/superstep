from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, select

from app.models import User
from app.models.database import MIGRATIONS_DIR
from app.models.dataset import DatasetRelationEdge, DatasetRow
from app.repositories.datasets import DatasetRepository
from app.repositories.teams import TeamRepository
from app.repositories.user_data import UserDataRepository
from test_dataset_connected import token
from test_dataset_rows import call, insert
from test_datasets import auth, client, create, error  # noqa: F401
from test_identity_migration import db  # noqa: F401


def column(key, kind="text", **extra):
    return {"key": key, "label": key.title(), "kind": kind, **extra}


def link_column(target, display="name", **extra):
    return column("company", "relation", relation={"target_dataset_id": target, "display_key": display}, **extra)


def base(dataset):
    return f"/api/datasets/{dataset['id']}"


def relation_path(source, row):
    return f"{base(source)}/rows/{row['id']}/relations/company"


def link_body(source, row, target_id):
    return {"target_row_id": target_id, "revision": row["revision"], "schema_revision": source["revision"]}


@pytest.fixture
def enabled(monkeypatch):
    monkeypatch.setenv("STUDIO_ENABLE_DATASET_RELATIONS", "1")


def test_same_scope_column_creation_and_opaque_target_errors(client, enabled, monkeypatch):
    source = create(client, name="Support cases", team_id="support", columns=[column("subject")])
    target = create(client, name="Companies", team_id="support", columns=[column("name"), column("score", "number")])
    personal = create(client, name="Personal companies", columns=[column("name")])
    headers = auth("owner")
    private = client.post("/api/datasets", headers=auth("other"),
                          json={"name": "Private target", "columns": [column("name")]})
    assert private.status_code == 201
    hidden = private.json()["data"]["id"]
    endpoint = f"{base(source)}/columns"

    def add(definition, uid="owner"):
        return client.post(endpoint, headers=auth(uid), json={"column": definition, "revision": 1})

    with monkeypatch.context() as disabled:
        disabled.delenv("STUDIO_ENABLE_DATASET_RELATIONS")
        error(add(link_column(target["id"])), 403, "DATASET_RELATION_DISABLED")

    cases = [link_column(dataset_id) for dataset_id in (hidden, "f" * 32, personal["id"], source["id"])]
    cases += [link_column(target["id"], key) for key in ("unknown", "score")]
    rejected = [add(case) for case in cases]
    for response in rejected:
        error(response, 404, "DATASET_RELATION_TARGET_INVALID")
    assert all(response.json()["error"] == rejected[0].json()["error"] for response in rejected)
    error(add(link_column(target["id"], unique=True)), 400, "DATASET_DEFINITION_INVALID")
    error(add(link_column(target["id"]), "member"), 403, "PERMISSION_DENIED")
    csv = {"text": "Subject\nTicket\n", "create": {
        "name": "CSV with Relation", "columns": [column("subject"), link_column(hidden)],
    }}
    for path in ("preview", "import"):
        error(client.post(f"/api/datasets/csv/{path}", headers=headers, json=csv), 400, "DATASET_CSV_MAPPING_INVALID")

    added = add(link_column(target["id"]))
    assert added.status_code == 201, added.text
    assert added.json()["data"]["columns"][-1]["relation"] == link_column(target["id"])["relation"]
    error(client.put(f"{endpoint}/company", headers=headers, json={
        "revision": 2, "column": link_column(personal["id"]),
    }), 409, "DATASET_SCHEMA_INCOMPATIBLE")
    assert call(client, "GET", base(source))["revision"] == 2


def test_relation_lifecycle_projection_paging_and_cleanup(client, db, enabled, monkeypatch):
    target = create(client, name="Company directory", team_id="support", columns=[column("name"), column("alias")])
    source = create(client, name="Tickets with company", team_id="support", columns=[
        column("subject"), link_column(target["id"]),
    ])
    target_rows = f"{base(target)}/rows"
    source_rows = f"{base(source)}/rows"
    headers = auth("owner")
    error(client.delete(f"{base(target)}?revision=1", headers=headers), 409, "DATASET_RELATION_REFERENCED")
    error(client.delete(f"{base(target)}/columns/name?revision=1", headers=headers), 409, "DATASET_RELATION_REFERENCED")
    alpha = insert(client, target_rows, name="\xc1nh D\u01b0\u01a1ng", alias="Sunny")
    beta = insert(client, target_rows, name="B\xecnh Minh", alias="Morning")
    empty = insert(client, source_rows, subject="Empty")
    ticket = insert(client, source_rows, subject="Linked")
    url = relation_path(source, ticket)

    error(client.patch(f"{source_rows}/{ticket['id']}", headers=headers, json={
        "revision": 1, "values": {"company": alpha["id"]},
    }), 400, "DATASET_COLUMN_READ_ONLY")
    error(client.put(url, headers=auth("member"), json=link_body(source, ticket, alpha["id"])), 403, "PERMISSION_DENIED")
    error(client.put(url, headers=headers, json=link_body(source, ticket, "f" * 32)), 404, "DATASET_RELATION_TARGET_INVALID")
    marker = call(client, "GET", f"{base(source)}/revisions")
    linked = call(client, "PUT", url, body=link_body(source, ticket, alpha["id"]))
    assert linked == {"id": ticket["id"], "revision": 2, "target_row_id": alpha["id"]}
    assert call(client, "GET", f"{base(source)}/revisions") == {
        "schema_revision": marker["schema_revision"], "data_revision": marker["data_revision"] + 1,
    }
    error(client.put(url, headers=headers, json=link_body(source, ticket, beta["id"])), 409, "DATASET_ROW_CONFLICT")

    with db.session() as session:
        linked_row = session.get(DatasetRow, (source["id"], ticket["id"]))
        assert linked_row.values == {"subject": "Linked"}
        edge = session.get(DatasetRelationEdge, (source["id"], ticket["id"], "company"))
        assert edge.target_dataset_id == target["id"] and edge.target_row_id == alpha["id"]

    assert call(client, "GET", f"{source_rows}/{ticket['id']}", uid="member")["values"] == {
        "subject": "Linked", "company": alpha["id"],
    }
    match = call(client, "POST", f"{source_rows}/query", uid="member", body={
        "limit": 1, "fields": ["company"], "filters": [{"field": "company", "op": "eq", "value": alpha["id"]}],
    })
    assert match["total"] == 1 and match["items"][0]["values"] == {"company": alpha["id"]}
    without = call(client, "POST", f"{source_rows}/query", body={"filters": [{"field": "company", "op": "is_null"}]})
    assert [row["id"] for row in without["items"]] == [empty["id"]]
    renamed = call(client, "PATCH", f"{source_rows}/{ticket['id']}", body={"revision": 2, "values": {"subject": "Edited"}})["row"]
    assert renamed["values"]["company"] == alpha["id"]

    lookup = f"{base(source)}/columns/company/relation/rows"
    found = call(client, "GET", f"{lookup}?schema_revision=1&search=\xc1NH", uid="member")
    assert found == {"items": [{"id": alpha["id"], "label": "\xc1nh D\u01b0\u01a1ng"}], "next_offset": None}
    page = client.get(f"{lookup}?schema_revision=1&limit=1", headers=auth("member"))
    assert page.status_code == 200 and page.headers["cache-control"] == "no-store"
    assert len(page.json()["data"]["items"]) == 1 and page.json()["data"]["next_offset"] == 1
    error(client.get(f"{lookup}?schema_revision=1&row_ids={alpha['id']}", headers=auth("other")), 404, "DATASET_NOT_FOUND")
    call(client, "PATCH", f"{target_rows}/{alpha['id']}", body={"revision": 1, "values": {"name": "Renamed"}})
    assert call(client, "GET", f"{lookup}?schema_revision=1&row_ids={alpha['id']}")["items"][0]["label"] == "Renamed"
    csv = client.get(f"{base(source)}/csv", headers=headers)
    assert csv.status_code == 200 and alpha["id"] in csv.text and "Renamed" not in csv.text

    error(client.delete(f"{target_rows}/{alpha['id']}?revision=2", headers=headers), 409, "DATASET_RELATION_REFERENCED")
    delete_token = token(client, base(target), permission="read", allow_delete=True)["token"]
    connected_delete = client.post(f"{base(target)}/connected", headers={"Authorization": f"Bearer {delete_token}"}, json={
        "version": 1, "columns": [{"key": "name", "kind": "text"}],
        "operation": "delete_row", "operation_id": "protected-delete", "fields": ["name"], "arguments": {"row_id": alpha["id"]},
    })
    error(connected_delete, 409, "DATASET_RELATION_REFERENCED")
    assert ticket["id"] not in connected_delete.text
    blocked = client.patch(f"{target_rows}/batch", headers=headers, json={
        "schema_revision": 1, "rows": [{"id": beta["id"], "revision": 1, "values": {"name": "Must roll back"}}],
        "remove": {alpha["id"]: 2},
    })
    error(blocked, 409, "DATASET_BATCH_CONFLICT")
    issue, = blocked.json()["error"]["details"]["issues"]
    assert issue["error"]["code"] == "DATASET_RELATION_REFERENCED" and ticket["id"] not in blocked.text
    assert call(client, "GET", f"{target_rows}/{beta['id']}")["values"]["name"] == "B\xecnh Minh"

    replaced = call(client, "PUT", url, body=link_body(source, renamed, beta["id"]))
    assert replaced["target_row_id"] == beta["id"] and replaced["revision"] == 4
    assert call(client, "DELETE", f"{target_rows}/{alpha['id']}?revision=2") == {"ok": True}
    unchanged = call(client, "PUT", url, body=link_body(source, replaced, beta["id"]))
    assert unchanged["revision"] == replaced["revision"]

    changed = call(client, "PUT", f"{base(source)}/columns/company", body={
        "column": link_column(target["id"], "alias"), "revision": 1,
    })
    assert changed["revision"] == 2
    assert call(client, "GET", f"{lookup}?schema_revision=2")["items"][0]["label"] == "Morning"
    call(client, "DELETE", f"{base(target)}/columns/name?revision=1")

    monkeypatch.delenv("STUDIO_ENABLE_DATASET_RELATIONS")
    error(client.put(url, headers=headers, json=link_body(changed, replaced, beta["id"])), 403, "DATASET_RELATION_DISABLED")
    unlinked = call(client, "DELETE", f"{url}?revision=4&schema_revision=2")
    assert unlinked["revision"] == 5 and unlinked["target_row_id"] is None
    call(client, "DELETE", f"{target_rows}/{beta['id']}?revision=1")
    call(client, "DELETE", f"{base(source)}/columns/company?revision=2")
    call(client, "DELETE", f"{base(target)}?revision=2")


@pytest.mark.parametrize("revocation", ["membership", "role"])
def test_relation_capabilities_and_revocation(client, db, enabled, monkeypatch, revocation):
    target = create(client, name="Shared companies", team_id="support", columns=[column("name")])
    source = create(client, name="Shared tickets", team_id="support", columns=[column("subject"), link_column(target["id"])])
    ticket = insert(client, f"{base(source)}/rows", subject="Source")
    company = insert(client, f"{base(target)}/rows", name="Target label")
    url = relation_path(source, ticket)
    choices = f"{base(source)}/columns/company/relation/rows?schema_revision=1"
    issued = token(client, base(source))["token"]
    assert client.get(choices, headers={"Authorization": f"Bearer {issued}"}).status_code == 401
    assert client.put(url, headers={"Authorization": f"Bearer {issued}"},
                      json=link_body(source, ticket, company["id"])).status_code == 401
    error(client.post(f"{base(source)}/shares", headers=auth("owner"), json={
        "name": "Try to share linked cells", "fields": ["company"], "schema_revision": 1,
    }), 400, "DATASET_SHARE_FIELD_UNAVAILABLE")

    original_lock = DatasetRepository.lock_relations

    def revoked(repo, session, uid, *args, **kwargs):
        if revocation == "membership":
            TeamRepository(db).remove_member("support", uid)
        else:
            with db.session() as control:
                control.get(User, uid).role = "viewer"
                control.commit()
        return original_lock(repo, session, uid, *args, **kwargs)

    monkeypatch.setattr(DatasetRepository, "lock_relations", revoked)
    response = client.put(url, headers=auth("owner"), json=link_body(source, ticket, company["id"]))
    assert "Target label" not in response.text
    if revocation == "membership":
        assert response.status_code in {404, 409}
        error(client.get(choices, headers=auth("owner")), 404, "DATASET_NOT_FOUND")
    else:
        error(response, 403, "PERMISSION_DENIED")
        assert call(client, "GET", choices)["items"][0]["label"] == "Target label"
    with db.session() as session:
        assert not session.scalars(select(DatasetRelationEdge)).all()
        assert session.get(DatasetRow, (source["id"], ticket["id"])).revision == 1


def test_link_and_delete_race_preserves_referential_integrity(client, enabled):
    target = create(client, name="Racing target", columns=[column("name")])
    source = create(client, name="Racing source", columns=[link_column(target["id"])])
    headers = auth("owner")
    for index in range(6):
        company = insert(client, f"{base(target)}/rows", name=f"Racing {index}")
        ticket = insert(client, f"{base(source)}/rows")
        gate = Barrier(2)

        def link():
            gate.wait(timeout=10)
            return client.put(relation_path(source, ticket), headers=headers, json=link_body(source, ticket, company["id"]))

        def remove():
            gate.wait(timeout=10)
            return client.delete(f"{base(target)}/rows/{company['id']}?revision=1", headers=headers)

        with ThreadPoolExecutor(max_workers=2) as pool:
            linking, deleting = pool.submit(link), pool.submit(remove)
            linked, removed = linking.result(15), deleting.result(15)
        current = call(client, "GET", f"{base(source)}/rows/{ticket['id']}")
        if linked.status_code == 200:
            error(removed, 409, "DATASET_RELATION_REFERENCED")
            assert current["values"]["company"] == company["id"]
            assert call(client, "GET", f"{base(target)}/rows/{company['id']}") == company
        else:
            error(linked, 404, "DATASET_RELATION_TARGET_INVALID")
            assert removed.status_code == 200 and current["values"]["company"] is None


@pytest.mark.parametrize("team_id", ["support", None])
def test_cleanup_removes_edges_inside_its_deletion_scope(client, db, enabled, team_id):
    target = create(client, name="Cleanup target", team_id=team_id, columns=[column("name")])
    source = create(client, name="Cleanup source", team_id=team_id, columns=[link_column(target["id"])])
    ticket = insert(client, f"{base(source)}/rows")
    company = insert(client, f"{base(target)}/rows", name="Removed with the scope")
    call(client, "PUT", relation_path(source, ticket), body=link_body(source, ticket, company["id"]))
    if team_id is None:
        UserDataRepository(db).purge("owner", runs=False)
    else:
        TeamRepository(db).delete(team_id)
    with db.session() as session:
        assert not session.scalars(select(DatasetRelationEdge)).all()
        assert list(session.scalars(select(DatasetRow))) == []


def test_additive_migration_guards_active_relation_definitions(client, db, enabled):
    target = create(client, name="Upgrade target", columns=[column("name")])
    original = insert(client, f"{base(target)}/rows", name="Preserved across upgrade")
    cfg = Config()
    cfg.set_main_option("script_location", MIGRATIONS_DIR)

    def downgrade():
        with db.engine.begin() as connection:
            cfg.attributes["connection"] = connection
            command.downgrade(cfg, "0074_dataset_shares")

    downgrade()
    assert not inspect(db.engine).has_table("dataset_relation_edges")
    db.migrate()
    db.migrate()
    assert call(client, "GET", f"{base(target)}/rows/{original['id']}") == original
    assert {item["name"] for item in inspect(db.engine).get_foreign_keys("dataset_relation_edges")} == {
        "fk_dataset_relation_source_field", "fk_dataset_relation_source_row", "fk_dataset_relation_target_row",
    }
    source = create(client, name="Upgrade source", columns=[link_column(target["id"])])
    with pytest.raises(RuntimeError, match="Remove active Dataset Relation columns"):
        downgrade()
    assert inspect(db.engine).has_table("dataset_relation_edges")
    call(client, "DELETE", f"{base(source)}/columns/company?revision=1")
    downgrade()
    assert not inspect(db.engine).has_table("dataset_relation_edges")
