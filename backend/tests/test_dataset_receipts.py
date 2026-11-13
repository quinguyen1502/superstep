from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import select

from app.core.errors import AppError
from app.models import DatasetWriteReceipt, Run, Workflow
from app.repositories.dataset_rows import DatasetRowRepository, WorkflowWrite
from app.repositories.datasets import DatasetRepository
from app.repositories.runs import StaleLease
from test_dataset_rows import call
from test_datasets import client, create  # noqa: F401
from test_identity_migration import db  # noqa: F401


@pytest.fixture
def writes(client, db):
    dataset = create(client, name="Receipts", columns=[{"key": "ticket", "label": "Ticket", "kind": "text", "unique": True}])
    with db.session() as session:
        session.add(Workflow(id="receipts-flow", name="Receipts", owner="owner"))
        session.add(Run(id="receipts-run", workflow_id="receipts-flow", lease_gen=1))
        session.commit()
    base = f"/api/datasets/{dataset['id']}"
    call(client, "PUT", f"{base}/access/grants/receipts-flow", body={"permission": "write"})
    repo = DatasetRowRepository(DatasetRepository(db))
    return repo, repo.datasets.get("owner", dataset["id"]), base


def write(repo, dataset, operation, ticket, fence=1):
    values = {"ticket": ticket}
    return repo.save("owner", dataset, lambda _: values, workflow=WorkflowWrite(
        run_id="receipts-run", workflow_id="receipts-flow", operation_id=operation,
        arguments={"operation": "insert", "values": values}, fence=fence,
    ))


def test_receipt_replays_original_result_after_commit_and_worker_takeover(client, db, writes):
    repo, dataset, base = writes
    with ThreadPoolExecutor(max_workers=2) as workers:
        replies = list(workers.map(lambda _: write(repo, dataset, "step#1", "A"), range(2)))
    row, inserted, _ = replies[0]
    assert inserted and replies[1][0].id == row.id
    call(client, "PATCH", f"{base}/rows/{row.id}", body={"revision": 1, "values": {"ticket": "Updated"}})
    with db.session() as session:
        run = session.get(Run, "receipts-run")
        run.lease_gen = 2
        session.commit()
    with pytest.raises(StaleLease):
        write(repo, dataset, "step#2", "B")
    replayed, _, reused = write(repo, dataset, "step#1", "A", fence=2)
    assert reused and replayed.id == row.id and replayed.values == {"ticket": "A"} and replayed.revision == 1
    with pytest.raises(AppError) as conflict:
        write(repo, dataset, "step#1", "B", fence=2)
    assert conflict.value.code == "DATASET_RECEIPT_CONFLICT"
    second, _, _ = write(repo, dataset, "step#2", "B", fence=2)
    assert second.id != row.id
    with db.session() as session:
        assert len(list(session.scalars(select(DatasetWriteReceipt)))) == 2


def test_failed_write_has_no_receipt_and_revocation_blocks_replay(client, db, writes):
    repo, dataset, base = writes
    write(repo, dataset, "step#1", "A")
    with pytest.raises(AppError) as duplicate:
        write(repo, dataset, "step#2", "A")
    assert duplicate.value.code == "DATASET_UNIQUE_CONFLICT"
    with db.session() as session:
        assert len(list(session.scalars(select(DatasetWriteReceipt)))) == 1
    assert write(repo, dataset, "step#2", "B")[1]
    call(client, "DELETE", f"{base}/access/grants/receipts-flow")
    with pytest.raises(AppError) as denied:
        write(repo, dataset, "step#1", "A")
    assert denied.value.code == "DATASET_GRANT_DENIED"
