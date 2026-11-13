import pytest
from sqlalchemy import select

from app.api import deps
from app.core.errors import AppError
from app.models import AuditEvent, DatasetApiToken, Workflow, WorkflowTeamShare
from test_dataset_rows import call
from test_datasets import auth, client, create, error  # noqa: F401
from test_identity_migration import db  # noqa: F401


def test_grants_require_saved_workflow_and_explicit_team_scope(client, db):
    dataset = create(client, name="Support", team_id="support")
    with db.session() as session:
        session.add_all([
            Workflow(id="support-flow", name="Support", owner="owner"),
            Workflow(id="other-flow", name="Other", owner="other"),
        ])
        session.flush()  # PostgreSQL checks the share’s foreign key when the row is inserted.
        session.add(WorkflowTeamShare(workflow_id="support-flow", team_id="support", role="viewer", created=1, shared_by="owner"))
        session.commit()
    base = f"/api/datasets/{dataset['id']}/access"
    svc = deps.dataset_access_service()
    with pytest.raises(AppError, match="required dataset grant"):
        svc.for_workflow("owner", "support-flow", dataset["id"], "read")
    error(client.put(f"{base}/grants/support-flow", headers=auth("member"), json={"permission": "read"}), 403, "PERMISSION_DENIED")
    error(client.put(f"{base}/grants/other-flow", headers=auth("owner"), json={"permission": "read"}), 404, "WORKFLOW_NOT_FOUND")
    call(client, "PUT", f"{base}/grants/support-flow", body={"permission": "read"})
    assert svc.for_workflow("member", "support-flow", dataset["id"], "read").subject_id == "support-flow"
    for wid, op, public in [(None, "read", False), ("support-flow", "write", False), ("support-flow", "read", True)]:
        with pytest.raises(AppError, match="required dataset grant"):
            svc.for_workflow("owner", wid, dataset["id"], op, public=public)
    call(client, "DELETE", f"{base}/grants/support-flow")
    with pytest.raises(AppError, match="required dataset grant"):
        svc.for_workflow("owner", "support-flow", dataset["id"], "read")


def test_dataset_token_rotation_and_scope(client, db):
    dataset = create(client, name="Support", team_id="support")
    other = create(client, name="Other")
    base = f"/api/datasets/{dataset['id']}/access"
    issued = client.post(f"{base}/tokens", headers=auth("owner"), json={"name": "Export", "permission": "write"})
    assert issued.status_code == 201 and issued.headers["cache-control"] == "no-store"
    credential = issued.json()["data"]
    token = credential["token"]
    assert call(client, "GET", base)["tokens"] == [{key: value for key, value in credential.items() if key != "token"}]
    svc = deps.dataset_access_service()
    assert svc.for_token(token, dataset["id"], "write").subject_id == credential["id"]
    for did, op in [(dataset["id"], "read"), (other["id"], "write")]:
        with pytest.raises(AppError) as exc:
            svc.for_token(token, did, op)
        assert exc.value.code == "AUTH_TOKEN_INVALID"
    error(client.get(f"/api/datasets/{dataset['id']}", headers={"Authorization": f"Bearer {token}"}), 401, "AUTH_TOKEN_INVALID")
    token_url = f"{base}/tokens/{credential['id']}"
    rotated = call(client, "POST", f"{token_url}/rotate")["token"]
    assert rotated != token
    with pytest.raises(AppError):
        svc.for_token(token, dataset["id"], "write")
    assert svc.for_token(rotated, dataset["id"], "write").subject_id == credential["id"]
    call(client, "DELETE", token_url)
    assert call(client, "GET", base)["tokens"] == []
    with pytest.raises(AppError):
        svc.for_token(rotated, dataset["id"], "write")
    with db.session() as session:
        stored = session.scalar(select(DatasetApiToken).where(DatasetApiToken.id == credential["id"]))
        assert len(stored.token_hash) == 64 and stored.token_hash != rotated
        audit = list(session.scalars(select(AuditEvent).where(AuditEvent.target_id == dataset["id"])))
        assert not any(token in str(event.details) or rotated in str(event.details) for event in audit)
